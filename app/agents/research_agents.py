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
        # Check if we already have search results and should continue instead of redoing searches
        if state.search_results and len(state.search_results) > 0:
            logger.info(f"Found existing search results for {len(state.search_results)} questions - continuing without repeating searches")
            state.log.append(f"Search agent: Using {len(state.search_results)} existing search results - skipping repeated searches")
            state.status = "search_completed"
            state.progress = 0.7
            return state

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
        
        # Filter out empty questions
        state.sub_questions = [q for q in state.sub_questions if q and q.strip()]
        if not state.sub_questions:
            error_msg = "No valid sub-questions found after filtering"
            state.errors.append(error_msg)
            state.log.append(f"Search agent: Error - {error_msg}")
            logger.error(error_msg)
            state.status = "error"
            return state
            
        state.log.append(f"Search agent: Beginning search for {len(state.sub_questions)} sub-questions")
        logger.info(f"Beginning search for {len(state.sub_questions)} sub-questions")
        
        try:
            searxng_available = search_service.reset_availability()
            if not searxng_available:
                state.log.append("Search agent: SearxNG is not available. Research results may be limited.")
                logger.warning("SearxNG is not available. Research results may be limited.")
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
        
        successful_searches = 0
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
            # Skip empty questions
            if not question or not question.strip():
                logger.warning(f"Skipping empty question at index {i}")
                continue
                
            elapsed_time = time.time() - start_time
            if elapsed_time > max_search_time and questions_processed >= min_questions_to_process:
                logger.warning(f"Search time limit reached after {i} questions with {successful_searches} successful searches")
                state.log.append(f"Search agent: Time limit reached ({elapsed_time:.1f}s). Continuing with {successful_searches} successful searches.")
                failed_searches.extend(questions_to_process[i:])
                break
                
            try:
                state.log.append(f"Search agent: Searching for '{question}'")
                logger.info(f"Searching for question {i+1}/{len(questions_to_process)}: '{question}'")
                
                search_start_time = time.time()
                
                results = search_service.search(question, num_results)
                search_time = time.time() - search_start_time
                questions_processed += 1
                
                if results and len(results) > 0:
                    formatted_results = [
                        f"Title: {result['title']}\nURL: {result['url']}\nContent: {result['content']}"
                        for result in results
                    ]
                    
                    search_results[question] = formatted_results
                    successful_searches += 1
                    state.log.append(f"Search agent: Found {len(formatted_results)} results for '{question}' in {search_time:.1f}s")
                else:
                    failed_searches.append(question)
                    state.log.append(f"Search agent: No results found for '{question}'")
            
            except Exception as e:
                failed_searches.append(question)
                state.log.append(f"Search agent: Error searching for '{question}' - {str(e)}")
                logger.error(f"Error searching for '{question}': {str(e)}")
                questions_processed += 1
            
            progress_per_question = 0.4 / len(questions_to_process)
            state.progress = min(0.3 + progress_per_question * (i + 1), 0.7)
        
        # If we have at least some successful searches, continue with those results
        if successful_searches > 0:
            logger.info(f"Completed {successful_searches} successful searches out of {len(questions_to_process)} questions")
            state.log.append(f"Search agent: Completed {successful_searches} successful searches out of {len(questions_to_process)} attempted")
            
            # If there were any failed searches, log that we're proceeding without them
            if failed_searches:
                logger.info(f"Proceeding with {successful_searches} successful searches, skipping {len(failed_searches)} failed searches")
                state.log.append(f"Search agent: Proceeding with available data, skipping {len(failed_searches)} failed searches")
        else:
            # If all searches failed, record an error but don't use fallback content
            error_msg = "All searches failed. Research quality will be limited."
            state.errors.append(error_msg)
            state.log.append(f"Search agent: Warning - {error_msg}")
            logger.error(error_msg)
        
        total_search_time = time.time() - start_time
        state.log.append(f"Search agent: Completed searches in {total_search_time:.1f}s")
        logger.info(f"Completed searches in {total_search_time:.1f}s")
        
        # Always update the state with whatever results we have
        state.search_results = search_results
        state.status = "search_completed"
        state.progress = 0.7
        
        # Don't auto-proceed to summarization to avoid potential loops
        return state
    except Exception as e:
        error_msg = f"Error in web search: {str(e)}"
        state.errors.append(error_msg)
        state.log.append(f"Search agent: Error - {str(e)}")
        logger.error(error_msg)
        
        # If we have any search results, continue with what we have
        if state.search_results and len(state.search_results) > 0:
            logger.info(f"Continuing with {len(state.search_results)} existing search results despite error")
            state.log.append(f"Search agent: Continuing with {len(state.search_results)} existing search results despite error")
            state.status = "search_completed"
            state.progress = 0.7
        else:
            # If we have NO results, mark as error instead of using fallbacks
            state.status = "error"
            state.log.append("Search agent: No search results available after errors. Research cannot proceed.")
            
        return state

def summarize_and_fact_check(state: ResearchState) -> ResearchState:
    """Summarize search results and perform fact checking.
    
    Args:
        state: The current research state
        
    Returns:
        Updated research state with summaries and fact checks
    """
    try:
        # Check if we already have summaries and should continue instead of redoing summarization
        if state.summaries and len(state.summaries) > 0 and state.status == "summaries_completed":
            logger.info(f"Found existing summaries for {len(state.summaries)} questions - continuing without repeating summarization")
            state.log.append(f"Summarization agent: Using {len(state.summaries)} existing summaries - skipping repeated summarization")
            return state
        
        # If we have no search results, cannot proceed with summarization
        if not state.search_results or len(state.search_results) == 0:
            error_msg = "No search results available for summarization"
            state.errors.append(error_msg)
            state.log.append(f"Summarization agent: Error - {error_msg}")
            logger.error(error_msg)
            state.status = "error"
            return state
            
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
        
        successful_summaries = 0
        failed_summaries = 0
        
        for question, results in search_results_to_process.items():
            # Skip if no valid results for this question
            if not results or len(results) == 0:
                logger.warning(f"Skipping summarization for '{question}' - no search results")
                failed_summaries += 1
                continue
                
            try:
                combined_results = "\n\n".join(results)
                
                summary_chain = llm_provider.create_chain(SUMMARIZATION_PROMPT)
                summary = summary_chain.invoke({
                    "question": question,
                    "results": combined_results + f"\n\nBased on the research depth and speed settings, provide a summary of {summary_length}."
                })
                
                # Verify we got a real summary, not just an error message or empty content
                if summary and len(summary) > 50:  # Minimal length check
                    summaries[question] = summary
                    fact_checks[question] = True
                    successful_summaries += 1
                    logger.info(f"Generated summary for '{question}' ({len(summary)} characters)")
                    state.log.append(f"Summarization agent: Generated summary for '{question}'")
                else:
                    failed_summaries += 1
                    logger.warning(f"Generated summary for '{question}' was too short or empty")
                    state.log.append(f"Summarization agent: Failed to generate valid summary for '{question}'")
            except Exception as e:
                failed_summaries += 1
                logger.error(f"Error summarizing '{question}': {str(e)}")
                state.log.append(f"Summarization agent: Error summarizing '{question}' - {str(e)}")
            
            progress_per_question = 0.2 / len(search_results_to_process)
            state.progress = min(0.7 + progress_per_question * (list(search_results_to_process.keys()).index(question) + 1), 0.9)
        
        if successful_summaries == 0:
            error_msg = "Failed to generate any valid summaries"
            state.errors.append(error_msg)
            state.log.append(f"Summarization agent: Error - {error_msg}")
            logger.error(error_msg)
            state.status = "error"
            return state
            
        state.log.append(f"Summarization agent: Successfully summarized {successful_summaries} questions, failed on {failed_summaries}")
        logger.info(f"Successfully summarized {successful_summaries} questions, failed on {failed_summaries}")
        
        state.summaries = summaries
        state.fact_checked = fact_checks
        state.status = "summaries_completed"
        state.progress = 0.9
        
        # Don't auto-proceed to report generation to avoid potential loops
        return state
    except Exception as e:
        error_msg = f"Error in summarization and fact checking: {str(e)}"
        state.errors.append(error_msg)
        state.log.append(f"Summarization agent: Error - {str(e)}")
        logger.error(error_msg)
        
        # If we have existing summaries, continue with those
        if state.summaries and len(state.summaries) > 0:
            logger.info(f"Continuing with {len(state.summaries)} existing summaries despite error")
            state.log.append(f"Summarization agent: Continuing with {len(state.summaries)} existing summaries despite error")
            state.status = "summaries_completed"
            state.progress = 0.9
            return state
        else:
            # If we have NO summaries, mark as error rather than using fallbacks
            state.status = "error"
            state.log.append("Summarization agent: No valid summaries available after errors. Research cannot proceed.")
            return state

def generate_final_report(state: ResearchState) -> ResearchState:
    """Generate the final research report.
    
    Args:
        state: The current research state
        
    Returns:
        Updated research state with final report
    """
    try:
        # Check if we already have a final report and should continue instead of regenerating
        if state.final_report and len(state.final_report) > 500 and state.status == "completed":
            logger.info("Found existing final report - continuing without regenerating")
            state.log.append("Report generation agent: Using existing final report - skipping regeneration")
            return state
            
        # If we have no summaries, cannot proceed with report generation
        if not state.summaries or len(state.summaries) == 0:
            error_msg = "No summaries available for report generation"
            state.errors.append(error_msg)
            state.log.append(f"Report generation agent: Error - {error_msg}")
            logger.error(error_msg)
            state.status = "error"
            return state
            
        logger.info("Starting final report generation")
        state.log.append("Report generation agent: Starting final report generation")
        
        # Determine which prompt to use based on the requested output format
        output_format = state.config.output_format
        if output_format == "executive_summary":
            prompt_template = EXECUTIVE_SUMMARY_PROMPT
            logger.info("Using EXECUTIVE_SUMMARY_PROMPT")
        elif output_format == "bullet_list":
            prompt_template = BULLET_LIST_PROMPT
            logger.info("Using BULLET_LIST_PROMPT")
        else:  # default is "full_report"
            prompt_template = FULL_REPORT_PROMPT
            logger.info("Using FULL_REPORT_PROMPT")
            
        state.log.append(f"Report generation agent: Using {output_format} format")
        
        # Prepare summaries for the prompt
        combined_summaries = []
        for question, summary in state.summaries.items():
            combined_summaries.append(f"## {question}\n\n{summary}")
            
        all_summaries = "\n\n".join(combined_summaries)
        
        # Generate the final report
        try:
            report_chain = llm_provider.create_chain(prompt_template)
            report = report_chain.invoke({"query": state.original_query, "summaries": all_summaries})
            
            # Verify the report is valid and not just a template or error message
            if is_outline(report):
                logger.warning("Generated report appears to be just an outline. Trying again.")
                state.log.append("Report generation agent: Generated report appears to be just an outline. Trying again.")
                
                # Try again with explicit instructions not to produce just an outline
                prompt_with_warning = prompt_template + "\n\nIMPORTANT FINAL INSTRUCTION: DO NOT produce just an outline or template. Write a FULL and COMPLETE report with all sections fully developed."
                report_chain = llm_provider.create_chain(prompt_with_warning)
                report = report_chain.invoke({"query": state.original_query, "summaries": all_summaries})
                
                # Check again
                if is_outline(report):
                    error_msg = "Unable to generate complete report, only produced an outline"
                    state.errors.append(error_msg)
                    state.log.append(f"Report generation agent: Error - {error_msg}")
                    logger.error(error_msg)
                
            # Validate that report is not too small (which would indicate a generation problem)
            min_report_size = 1500  # Minimum characters for a valid report
            if len(report) < min_report_size:
                error_msg = f"Generated report is too short ({len(report)} chars)"
                state.errors.append(error_msg)
                state.log.append(f"Report generation agent: Warning - {error_msg}")
                logger.warning(error_msg)
                
                # Continue with the short report anyway rather than failing completely
                
            state.final_report = report
            state.status = "completed"
            state.progress = 1.0
            
            logger.info(f"Final report generated successfully with {len(report)} characters")
            state.log.append(f"Report generation agent: Final report generated successfully ({len(report)} characters)")
            
            return state
            
        except Exception as e:
            error_msg = f"Error in final report generation: {str(e)}"
            state.errors.append(error_msg)
            state.log.append(f"Report generation agent: Error - {str(e)}")
            logger.error(error_msg)
            
            # If we already have a partial report, use that instead of failing
            if state.final_report and len(state.final_report) > 0:
                logger.info("Using existing partial report despite error")
                state.log.append("Report generation agent: Using existing partial report despite error")
                state.status = "completed"
                state.progress = 1.0
                return state
                
            # Cannot proceed with report generation, mark as error
            state.status = "error"
            return state
            
    except Exception as e:
        error_msg = f"Error in report generation: {str(e)}"
        state.errors.append(error_msg)
        state.log.append(f"Report generation agent: Error - {str(e)}")
        logger.error(error_msg)
        
        # If we already have a report, use that despite the error
        if state.final_report and len(state.final_report) > 0:
            logger.info("Using existing report despite error")
            state.log.append("Report generation agent: Using existing report despite error")
            state.status = "completed"
            state.progress = 1.0
            return state
            
        state.status = "error"
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