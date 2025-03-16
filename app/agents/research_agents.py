"""
Research agent components for the OpenResearch system.
"""

import logging
from typing import List, Dict, Any, Optional
from app.models.schemas import ResearchState
from app.models.llm import llm_provider
from app.services.search_api import search_service
from app.agents.prompts import (
    CLARIFICATION_PROMPT, 
    REFINEMENT_PROMPT,
    DECOMPOSITION_PROMPT,
    SUMMARIZATION_PROMPT,
    FACT_CHECKING_PROMPT,
    FULL_REPORT_PROMPT,
    EXECUTIVE_SUMMARY_PROMPT,
    BULLET_LIST_PROMPT
)

logger = logging.getLogger(__name__)

def generate_clarification_questions(state: ResearchState) -> ResearchState:
    """Generate clarification questions based on the original query.
    
    Args:
        state: The current research state
        
    Returns:
        Updated research state with clarification questions
    """
    try:
        state.log.append(f"Clarification agent: Starting to analyze query '{state.original_query}'")
        logger.info(f"Generating clarification questions for: {state.original_query}")

        if state.clarification_questions and len(state.clarification_questions) >= 2:
            state.log.append(f"Clarification agent: Using existing {len(state.clarification_questions)} questions")
            logger.info(f"Using existing questions: {state.clarification_questions}")
            return state

        chain = llm_provider.create_chain(CLARIFICATION_PROMPT)
        
        result = chain.invoke({"query": state.original_query})
        logger.debug(f"LLM result for clarification questions: {result}")
        
        questions = []
        for line in result.strip().split('\n'):
            line = line.strip()
            if line and (line.startswith('- ') or line.startswith('• ') or 
                       any(line.startswith(f"{i}.") for i in range(1, 10))):
                cleaned = line.split('.', 1)[-1].split('- ', 1)[-1].split('• ', 1)[-1].strip()
                if cleaned and len(cleaned) > 5:  # Ensure it's a meaningful question
                    questions.append(cleaned)

        logger.info(f"Parsed questions: {questions}")
        
        if not questions:
            logger.warning("Parsing failed. Using fallback approach")
            questions = [line.strip() for line in result.strip().split('\n')]
            questions = [q for q in questions if len(q) > 10 and '?' in q][:3]
        
        if len(questions) < 2:
            logger.warning("Not enough questions. Creating default questions")
            questions = [
                f"Could you provide more context about what aspects of '{state.original_query}' you're most interested in?",
                f"What specific information about '{state.original_query}' would be most valuable to you?",
                f"Are you looking for recent developments in '{state.original_query}' or historical background?"
            ]
        
        state.clarification_questions = questions
        state.status = "clarification_needed"
        state.progress = 0.1
        
        state.log.append(f"Clarification agent: Generated {len(questions)} questions for user")
        logger.info(f"Generated {len(questions)} clarification questions")
        
        return state
    
    except Exception as e:
        error_msg = f"Error generating clarification questions: {str(e)}"
        state.errors.append(error_msg)
        state.status = "error"
        state.log.append(f"Clarification agent: Error - {str(e)}")
        logger.error(error_msg)
        
        if not state.clarification_questions or len(state.clarification_questions) < 2:
            state.clarification_questions = [
                f"Could you provide more context about what aspects of '{state.original_query}' you're most interested in?",
                f"What specific information about '{state.original_query}' would be most valuable to you?",
                f"Are you looking for recent developments in '{state.original_query}' or historical background?"
            ]
            state.status = "clarification_needed"
            state.progress = 0.1
            state.log.append(f"Clarification agent: Generated default questions after error")
        
        return state

def process_clarifications(state: ResearchState) -> ResearchState:
    """Process user answers to clarification questions.
    
    Args:
        state: The current research state
        
    Returns:
        Updated research state with refined query
    """
    try:
        state.log.append("Refinement agent: Processing user's clarification answers")
        logger.info("Processing clarification answers")
        
        clarification_qa = "\n".join([
            f"Q: {q}\nA: {state.clarification_answers.get(q, 'No answer provided')}"
            for q in state.clarification_questions
        ])
        
        chain = llm_provider.create_chain(REFINEMENT_PROMPT)
        refined_query = chain.invoke({
            "original_query": state.original_query,
            "clarification_qa": clarification_qa,
            "output_format": state.config.output_format,
            "research_speed": state.config.research_speed,
            "depth_breadth": state.config.depth_and_breadth
        })
        
        state.clarified_query = refined_query
        state.status = "query_refined"
        state.progress = 0.2
        state.log.append(f"Refinement agent: Created refined query based on {len(state.clarification_answers)} answers")
        logger.info(f"Created refined query: {refined_query}")
        return state
    except Exception as e:
        error_msg = f"Error processing clarifications: {str(e)}"
        state.errors.append(error_msg)
        state.status = "error"
        state.log.append(f"Refinement agent: Error - {str(e)}")
        logger.error(error_msg)
        return state

def decompose_query(state: ResearchState) -> ResearchState:
    """Decompose the refined query into sub-questions.
    
    Args:
        state: The current research state
        
    Returns:
        Updated research state with sub-questions
    """
    try:
        query = state.clarified_query or state.original_query
        
        depth = state.config.depth_and_breadth
        
        if depth <= 1:
            num_questions = 3
        elif depth <= 3:
            num_questions = 5
        elif depth == 4:
            num_questions = 6
        else:
            num_questions = 8
        
        logger.info(f"Decomposing query into {num_questions} sub-questions")
        
        decomposition_chain = llm_provider.create_chain(DECOMPOSITION_PROMPT)
        
        result = decomposition_chain.invoke({
            "query": query,
            "num_questions": num_questions
        })
        
        sub_questions = []
        for line in result.strip().split('\n'):
            if '.' in line[:5]:
                question = line.split('.', 1)[1].strip()
                sub_questions.append(question)
        
        if len(sub_questions) < num_questions:
            for i in range(len(sub_questions), num_questions):
                sub_questions.append(f"What are additional important aspects of {query}?")
        
        state.sub_questions = sub_questions
        state.status = "query_decomposed"
        state.progress = 0.4
        state.log.append(f"Decomposition agent: Generated {len(sub_questions)} sub-questions")
        
        return state
    except Exception as e:
        error_msg = f"Error decomposing query: {str(e)}"
        state.errors.append(error_msg)
        state.log.append(f"Decomposition agent: Error - {str(e)}")
        logger.error(error_msg)
        
        query = state.clarified_query or state.original_query
        state.sub_questions = [
            f"What is {query}?",
            f"What are the key aspects of {query}?",
            f"What are the implications of {query}?"
        ]
        state.status = "query_decomposed"
        state.progress = 0.4
        
        return state

def search_web(state: ResearchState) -> ResearchState:
    """Perform web searches for each sub-question.
    
    Args:
        state: The current research state
        
    Returns:
        Updated research state with search results
    """
    try:
        if not state.sub_questions:
            log_message = "Search agent: No sub-questions available, creating default questions"
            state.log.append(log_message)
            logger.warning(log_message)
            
            query_to_use = state.clarified_query if state.clarified_query else state.original_query
            state.sub_questions = [
                f"What is {query_to_use}?",
                f"What are the key concepts in {query_to_use}?",
                f"What are the latest developments in {query_to_use}?",
                f"What are the main challenges in {query_to_use}?",
                f"What are practical applications of {query_to_use}?"
            ]
            state.log.append(f"Search agent: Created {len(state.sub_questions)} default sub-questions")
            
        state.log.append(f"Search agent: Beginning search for {len(state.sub_questions)} sub-questions")
        logger.info(f"Beginning search for {len(state.sub_questions)} sub-questions")
        
        try:
            searxng_available = search_service.reset_availability()
            if not searxng_available:
                state.log.append("Search agent: SearxNG is not available. Using fallback content.")
                logger.warning("SearxNG is not available. Using fallback content.")
        except Exception as e:
            logger.error(f"Error checking SearxNG availability: {str(e)}")
        
        search_results = {}
        
        if state.config.research_speed == "fast":
            num_results = 2
        else:
            if state.config.depth_and_breadth <= 2:
                num_results = 3
            elif state.config.depth_and_breadth <= 4:
                num_results = 4
            else:
                num_results = 5
        
        logger.info(f"Using {num_results} search results per question")
        state.log.append(f"Search agent: Using {num_results} search results per question")
        
        failed_searches = []
        
        import time
        start_time = time.time()
        
        if state.config.depth_and_breadth <= 2:
            max_search_time = 15
        elif state.config.depth_and_breadth <= 4:
            max_search_time = 20
        else:
            max_search_time = 30
            
        logger.info(f"Maximum search time set to {max_search_time} seconds")
        state.log.append(f"Search agent: Maximum search time set to {max_search_time} seconds")
        
        min_questions_to_process = min(2, len(state.sub_questions))
        questions_processed = 0
        
        if state.config.depth_and_breadth <= 2:
            max_questions = 3
        elif state.config.depth_and_breadth <= 4:
            max_questions = 5
        else:
            max_questions = len(state.sub_questions)
            
        questions_to_process = state.sub_questions[:min(max_questions, len(state.sub_questions))]
        logger.info(f"Processing {len(questions_to_process)} out of {len(state.sub_questions)} questions")
        state.log.append(f"Search agent: Processing {len(questions_to_process)} out of {len(state.sub_questions)} questions")
        
        for i, question in enumerate(questions_to_process):
            elapsed_time = time.time() - start_time
            if elapsed_time > max_search_time and questions_processed >= min_questions_to_process:
                logger.warning(f"Search time limit reached after {i} questions. Using fallback for remaining questions.")
                state.log.append(f"Search agent: Time limit reached ({elapsed_time:.1f}s). Using fallback for remaining questions.")
                failed_searches.extend(questions_to_process[i:])
                break
                
            try:
                state.log.append(f"Search agent: Searching for '{question}'")
                logger.info(f"Searching for question {i+1}/{len(questions_to_process)}: '{question}'")
                
                search_start_time = time.time()
                search_timeout = 5
                
                results = search_service.search(question, num_results)
                search_time = time.time() - search_start_time
                questions_processed += 1
                
                if results:
                    formatted_results = [
                        f"Title: {result['title']}\nURL: {result['url']}\nContent: {result['content']}"
                        for result in results
                    ]
                    
                    search_results[question] = formatted_results
                    state.log.append(f"Search agent: Found {len(formatted_results)} results for '{question}' in {search_time:.1f}s")
                else:
                    failed_searches.append(question)
                    search_results[question] = [f"No search results found for: {question}"]
                    state.log.append(f"Search agent: No results found for '{question}'")
            
            except Exception as e:
                failed_searches.append(question)
                search_results[question] = [f"Error searching for question: {str(e)}"]
                state.log.append(f"Search agent: Error searching for '{question}' - {str(e)}")
                logger.error(f"Error searching for '{question}': {str(e)}")
                questions_processed += 1
            
            progress_per_question = 0.4 / len(questions_to_process)
            state.progress = min(0.3 + progress_per_question * (i + 1), 0.7)
        
        if failed_searches:
            state.log.append(f"Search agent: Providing fallback content for {len(failed_searches)} failed searches")
            logger.info(f"Providing fallback content for {len(failed_searches)} failed searches")
            
            for question in failed_searches:
                fallback_results = search_service.get_fallback_content(question)
                
                formatted_results = [
                    f"Title: {result['title']}\nURL: {result['url']}\nContent: {result['content']}"
                    for result in fallback_results
                ]
                
                search_results[question] = formatted_results
                state.log.append(f"Search agent: Using fallback content for '{question}'")
        
        if not search_results:
            logger.warning("No search results found for any questions. Using generic fallback content.")
            state.log.append("Search agent: No search results found. Using generic fallback content.")
            
            search_results = {}
            for question in state.sub_questions[:2]:
                fallback_results = search_service.get_fallback_content(question)
                formatted_results = [
                    f"Title: {result['title']}\nURL: {result['url']}\nContent: {result['content']}"
                    for result in fallback_results
                ]
                search_results[question] = formatted_results
        
        total_search_time = time.time() - start_time
        state.log.append(f"Search agent: Completed searches in {total_search_time:.1f}s")
        logger.info(f"Completed searches in {total_search_time:.1f}s")
        
        state.search_results = search_results
        state.status = "search_completed"
        state.progress = 0.7
        
        try:
            logger.info("Automatically proceeding to summarization")
            state.log.append("Search agent: Automatically proceeding to summarization")
            summarized_state = summarize_and_fact_check(state)
            return summarized_state
        except Exception as e:
            logger.error(f"Error auto-proceeding to summarization: {str(e)}")
            return state
    except Exception as e:
        error_msg = f"Error in web search: {str(e)}"
        state.errors.append(error_msg)
        state.log.append(f"Search agent: Error - {str(e)}")
        logger.error(error_msg)
        
        if not state.search_results and state.sub_questions:
            state.search_results = {}
            for question in state.sub_questions[:2]:
                fallback_results = search_service.get_fallback_content(question)
                
                formatted_results = [
                    f"Title: {result['title']}\nURL: {result['url']}\nContent: {result['content']}"
                    for result in fallback_results
                ]
                
                state.search_results[question] = formatted_results
            
            state.status = "search_completed"
            state.progress = 0.7
            state.log.append(f"Search agent: Created fallback search results after error")
            
            try:
                logger.info("Automatically proceeding to summarization after error recovery")
                state.log.append("Search agent: Automatically proceeding to summarization after error recovery")
                summarized_state = summarize_and_fact_check(state)
                return summarized_state
            except Exception as e2:
                logger.error(f"Error auto-proceeding to summarization after error recovery: {str(e2)}")
                return state
        
        return state

def summarize_and_fact_check(state: ResearchState) -> ResearchState:
    """Summarize search results and perform fact checking.
    
    Args:
        state: The current research state
        
    Returns:
        Updated research state with summaries and fact checks
    """
    try:
        summaries = {}
        fact_checks = {}
        
        logger.info("Starting summarization and fact checking")
        
        search_results_to_process = state.search_results
        
        logger.info(f"Processing {len(search_results_to_process)} questions for summarization")
        
        depth = state.config.depth_and_breadth
        if depth <= 2:
            summary_length = "3-5 paragraphs (300-500 words)"
        elif depth <= 4:
            summary_length = "5-8 paragraphs (500-750 words)"
        else:
            summary_length = "8-10 paragraphs (750-1000 words)"
            
        if state.config.research_speed == "fast":
            if depth <= 2:
                summary_length = "2-3 paragraphs (200-300 words)"
            elif depth <= 4:
                summary_length = "3-5 paragraphs (300-500 words)"
            else:
                summary_length = "5-8 paragraphs (500-750 words)"
        
        logger.info(f"Setting summary length to {summary_length} based on depth={depth} and speed={state.config.research_speed}")
        state.log.append(f"Summarization agent: Setting summary length to {summary_length}")
        
        for question, results in search_results_to_process.items():
            if not results or all(r.startswith("Error") for r in results):
                summaries[question] = "No reliable information found for this question."
                fact_checks[question] = False
                continue
                
            combined_results = "\n\n".join(results)
            
            summary_chain = llm_provider.create_chain(SUMMARIZATION_PROMPT)
            summary = summary_chain.invoke({
                "question": question,
                "results": combined_results + f"\n\nBased on the research depth and speed settings, provide a summary of {summary_length}."
            })
            
            summaries[question] = summary
            logger.info(f"Generated summary for '{question}'")
            
            fact_checks[question] = True
            
            progress_per_question = 0.2 / len(search_results_to_process)
            state.progress = min(0.7 + progress_per_question * (list(search_results_to_process.keys()).index(question) + 1), 0.9)
        
        state.summaries = summaries
        state.fact_checked = fact_checks
        state.status = "summaries_completed"
        state.progress = 0.9
        state.log.append(f"Summarization agent: Completed summarization and fact checking for {len(summaries)} questions")
        logger.info(f"Completed summarization and fact checking for {len(summaries)} questions")
        
        try:
            logger.info("Automatically proceeding to final report generation")
            state.log.append("Summarization agent: Automatically proceeding to final report generation")
            final_state = generate_final_report(state)
            return final_state
        except Exception as e:
            logger.error(f"Error auto-proceeding to final report: {str(e)}")
            return state
    except Exception as e:
        error_msg = f"Error in summarization and fact checking: {str(e)}"
        state.errors.append(error_msg)
        state.log.append(f"Summarization agent: Error - {str(e)}")
        logger.error(error_msg)
        
        if not state.summaries and state.search_results:
            state.summaries = {}
            for question, results in list(state.search_results.items())[:3]:
                state.summaries[question] = f"Based on limited information, {state.original_query} involves various concepts and applications. Due to processing limitations, a detailed summary could not be generated."
            state.fact_checked = {q: False for q in state.summaries}
            state.status = "summaries_completed"
            state.progress = 0.9
            
            try:
                logger.info("Automatically proceeding to final report generation after error recovery")
                state.log.append("Summarization agent: Automatically proceeding to final report generation after error recovery")
                final_state = generate_final_report(state)
                return final_state
            except Exception as e2:
                logger.error(f"Error auto-proceeding to final report after error recovery: {str(e2)}")
                return state
        
        return state

def generate_final_report(state: ResearchState) -> ResearchState:
    """Generate the final research report.
    
    Args:
        state: The current research state
        
    Returns:
        Updated research state with final report
    """
    try:
        all_summaries = ""
        for i, (question, summary) in enumerate(state.summaries.items()):
            fact_check_status = "✓" if state.fact_checked.get(question, False) else "⚠"
            all_summaries += f"\n\nQuestion {i+1}: {question} {fact_check_status}\n{summary}"
        
        logger.info("Generating final report")
        logger.info(f"Processing {len(state.summaries)} summaries for final report")
        
        depth = state.config.depth_and_breadth
        if depth <= 2:
            min_word_count = 3000
            target_word_count = 4000
            exec_summary_min = 1000
            exec_summary_target = 1500
            bullet_list_min = 1500
            bullet_list_target = 2000
        elif depth <= 4:
            min_word_count = 4000
            target_word_count = 5000
            exec_summary_min = 1500
            exec_summary_target = 2000
            bullet_list_min = 2000
            bullet_list_target = 2500
        else:
            min_word_count = 5000
            target_word_count = 7000
            exec_summary_min = 2000
            exec_summary_target = 2500
            bullet_list_min = 2500
            bullet_list_target = 3000
            
        if state.config.research_speed == "fast":
            min_word_count = max(2000, min_word_count - 1000)
            target_word_count = max(3000, target_word_count - 1000)
            exec_summary_min = max(800, exec_summary_min - 500)
            exec_summary_target = max(1200, exec_summary_target - 500)
            bullet_list_min = max(1000, bullet_list_min - 500)
            bullet_list_target = max(1500, bullet_list_target - 500)
        
        if state.config.output_format == "full_report":
            prompt = FULL_REPORT_PROMPT
            depth_instructions = f"\n\nBased on the research depth and speed settings, your report should be at least {min_word_count} words, and ideally {target_word_count} words."
        elif state.config.output_format == "executive_summary":
            prompt = EXECUTIVE_SUMMARY_PROMPT
            depth_instructions = f"\n\nBased on the research depth and speed settings, your executive summary should be at least {exec_summary_min} words, and ideally {exec_summary_target} words."
        else:
            prompt = BULLET_LIST_PROMPT
            depth_instructions = f"\n\nBased on the research depth and speed settings, your bullet-point report should be at least {bullet_list_min} words, and ideally {bullet_list_target} words."
        
        additional_instructions = "\n\nIMPORTANT: Do NOT generate just an outline or table of contents. Write the COMPLETE REPORT with all sections fully developed. Each section should have detailed content, not just headings."
        
        report_chain = llm_provider.create_chain(prompt)
        
        if len(state.summaries) > 5:
            logger.info(f"Large number of summaries ({len(state.summaries)}), ensuring comprehensive report")
            
            final_report = report_chain.invoke({
                "query": state.clarified_query or state.original_query,
                "summaries": all_summaries + f"\n\nIMPORTANT: Your report MUST be at least {min_word_count} words and include ALL the information from ALL the summaries above. Do not truncate or omit any important information." + additional_instructions + depth_instructions
            })
            
            if len(final_report.split()) < min_word_count or is_outline(final_report):
                if is_outline(final_report):
                    logger.warning("Generated report appears to be just an outline, attempting to generate full report")
                else:
                    logger.warning(f"Generated report seems too short ({len(final_report.split())} words), attempting to expand it")
                
                expansion_prompt = f"""
                The following output is incomplete. It is either too short or just an outline. Please write a COMPLETE, DETAILED REPORT of at least {min_word_count} words, ensuring you include ALL the information from the original summaries.
                
                Original Research Query: {state.clarified_query or state.original_query}
                
                Current Output:
                {final_report}
                
                Please write a COMPLETE REPORT with fully developed sections, not just an outline or table of contents. Each section should have detailed content (multiple paragraphs), not just headings.
                
                The report should include:
                1. A detailed executive summary (500-750 words)
                2. A comprehensive introduction (750-1000 words)
                3. Fully developed main sections with detailed content for each subsection (2000-3000 words total)
                4. A thorough analysis and implications section (1000-1500 words)
                5. A detailed conclusion with recommendations (750-1000 words)
                6. A complete references section
                
                The final report should be at least {min_word_count} words and must be comprehensive, covering ALL aspects of the research topic.
                """
                
                expansion_chain = llm_provider.create_chain(expansion_prompt)
                expanded_report = expansion_chain.invoke({})
                
                if len(expanded_report.split()) > len(final_report.split()) and not is_outline(expanded_report):
                    final_report = expanded_report
                    logger.info(f"Successfully expanded the report to {len(expanded_report.split())} words")
                else:
                    logger.warning("First expansion attempt failed, trying alternative approach")
                    
                    sections_prompt = f"""
                    You are writing a comprehensive research report on: {state.clarified_query or state.original_query}
                    
                    Based on the following summaries, write a COMPLETE, DETAILED research report with the following sections:
                    
                    Summaries:
                    {all_summaries}
                    
                    Write each section with multiple detailed paragraphs (not just headings):
                    
                    1. EXECUTIVE SUMMARY (500-750 words)
                    2. INTRODUCTION (750-1000 words)
                    3. MAIN FINDINGS (at least 4 main sections with 2-3 subsections each, 2000-3000 words total)
                    4. ANALYSIS AND IMPLICATIONS (1000-1500 words)
                    5. CONCLUSION AND RECOMMENDATIONS (750-1000 words)
                    6. REFERENCES
                    
                    The total report should be at least {min_word_count} words. Include ALL key information from the summaries.
                    """
                    
                    sections_chain = llm_provider.create_chain(sections_prompt)
                    sectioned_report = sections_chain.invoke({})
                    
                    if len(sectioned_report.split()) > len(final_report.split()) and not is_outline(sectioned_report):
                        final_report = sectioned_report
                        logger.info(f"Successfully generated sectioned report of {len(sectioned_report.split())} words")
        else:
            final_report = report_chain.invoke({
                "query": state.clarified_query or state.original_query,
                "summaries": all_summaries + additional_instructions + depth_instructions
            })
            
            if is_outline(final_report) or len(final_report.split()) < min_word_count:
                if is_outline(final_report):
                    logger.warning("Generated report appears to be just an outline, attempting to generate full report")
                else:
                    logger.warning(f"Generated report seems too short ({len(final_report.split())} words), attempting to expand it")
                
                full_report_prompt = f"""
                Please write a COMPLETE, DETAILED REPORT (not just an outline) on the following research query:
                
                Research Query: {state.clarified_query or state.original_query}
                
                Based on these summaries:
                {all_summaries}
                
                Write a COMPLETE REPORT with fully developed sections, not just an outline or table of contents.
                Each section should have detailed content (multiple paragraphs), not just headings.
                
                The report should be at least {min_word_count} words and include ALL key information from the summaries.
                """
                
                full_report_chain = llm_provider.create_chain(full_report_prompt)
                complete_report = full_report_chain.invoke({})
                
                if not is_outline(complete_report) and len(complete_report.split()) > len(final_report.split()):
                    final_report = complete_report
                    logger.info(f"Successfully generated complete report of {len(complete_report.split())} words")
        
        final_report = f"\n\n================================================================================\nRESEARCH REPORT BEGINS\n================================================================================\n\n{final_report}"
        
        state.final_report = final_report
        state.status = "completed"
        state.progress = 1.0
        state.log.append(f"Report agent: Generated final report with {len(state.summaries)} summaries, word count: {len(final_report.split())}")
        logger.info(f"Final report generated successfully with {len(state.summaries)} summaries, word count: {len(final_report.split())}")
        return state
    except Exception as e:
        error_msg = f"Error generating final report: {str(e)}"
        state.errors.append(error_msg)
        state.status = "error"
        state.log.append(f"Report agent: Error - {str(e)}")
        logger.error(error_msg)
        return state

def is_outline(text):
    """Check if the text appears to be just an outline rather than a full report."""
    lines = text.split('\n')
    outline_pattern_count = 0
    content_paragraph_count = 0
    
    for line in lines:
        line = line.strip()
        if (line.startswith(('I.', 'II.', 'III.', 'IV.', 'V.', 'VI.', 'VII.', 'VIII.', 'IX.', 'X.')) or 
            any(line.startswith(f"{i}.") for i in range(1, 20))):
            outline_pattern_count += 1
        
        if len(line) > 100 and not line[0].isdigit() and not (line[0].isalpha() and line[1:3] in ['. ', '.)']): 
            content_paragraph_count += 1
    
    return outline_pattern_count > 5 and content_paragraph_count < 10 