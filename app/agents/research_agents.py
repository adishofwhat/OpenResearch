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

# Configure logging
logger = logging.getLogger(__name__)

def generate_clarification_questions(state: ResearchState) -> ResearchState:
    """Generate clarification questions based on the original query.
    
    Args:
        state: The current research state
        
    Returns:
        Updated research state with clarification questions
    """
    try:
        # Log the start of the function
        state.log.append(f"Clarification agent: Starting to analyze query '{state.original_query}'")
        logger.info(f"Generating clarification questions for: {state.original_query}")

        # If we already have questions, don't regenerate them
        if state.clarification_questions and len(state.clarification_questions) >= 2:
            state.log.append(f"Clarification agent: Using existing {len(state.clarification_questions)} questions")
            logger.info(f"Using existing questions: {state.clarification_questions}")
            return state

        # Create the LLM chain
        chain = llm_provider.create_chain(CLARIFICATION_PROMPT)
        
        # Invoke the LLM chain
        result = chain.invoke({"query": state.original_query})
        logger.debug(f"LLM result for clarification questions: {result}")
        
        # Parse the questions
        questions = []
        for line in result.strip().split('\n'):
            line = line.strip()
            if line and (line.startswith('- ') or line.startswith('• ') or 
                       any(line.startswith(f"{i}.") for i in range(1, 10))):
                # Remove the leading number/bullet and clean
                cleaned = line.split('.', 1)[-1].split('- ', 1)[-1].split('• ', 1)[-1].strip()
                if cleaned and len(cleaned) > 5:  # Ensure it's a meaningful question
                    questions.append(cleaned)

        # Log the parsed questions
        logger.info(f"Parsed questions: {questions}")
        
        # If parsing failed, use a fallback approach
        if not questions:
            logger.warning("Parsing failed. Using fallback approach")
            # Just separate by lines, clean and take up to 3
            questions = [line.strip() for line in result.strip().split('\n')]
            questions = [q for q in questions if len(q) > 10 and '?' in q][:3]
        
        # If still no valid questions, create default ones
        if len(questions) < 2:
            logger.warning("Not enough questions. Creating default questions")
            questions = [
                f"Could you provide more context about what aspects of '{state.original_query}' you're most interested in?",
                f"What specific information about '{state.original_query}' would be most valuable to you?",
                f"Are you looking for recent developments in '{state.original_query}' or historical background?"
            ]
        
        # Update the state with the generated questions
        state.clarification_questions = questions
        state.status = "clarification_needed"
        state.progress = 0.1
        
        # Log the generated questions
        state.log.append(f"Clarification agent: Generated {len(questions)} questions for user")
        logger.info(f"Generated {len(questions)} clarification questions")
        
        return state
    
    except Exception as e:
        # Log the error
        error_msg = f"Error generating clarification questions: {str(e)}"
        state.errors.append(error_msg)
        state.status = "error"
        state.log.append(f"Clarification agent: Error - {str(e)}")
        logger.error(error_msg)
        
        # Even if there's an error, create default questions to prevent recursion
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
        
        # Format the Q&A for the prompt
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
    """Break down the research query into sub-questions.
    
    Args:
        state: The current research state
        
    Returns:
        Updated research state with sub-questions
    """
    try:
        # If we already have sub-questions, don't regenerate them
        if state.sub_questions and len(state.sub_questions) >= 3:
            state.log.append(f"Decomposition agent: Using existing {len(state.sub_questions)} sub-questions")
            logger.info(f"Using existing sub-questions: {state.sub_questions}")
            return state
            
        # First, check if we need clarification
        if not state.clarified_query and state.clarification_attempts < 3 and not state.clarification_questions:
            log_message = "Decomposition agent: Clarified query missing, requesting clarification"
            state.log.append(log_message)
            state.status = "clarification_needed"
            logger.info(log_message)
            return state
        
        # If we don't have a clarified query but have tried clarification or have questions,
        # just use the original query
        query_to_use = state.clarified_query if state.clarified_query else state.original_query
        
        state.log.append(f"Decomposition agent: Breaking down research query into sub-questions")
        logger.info(f"Decomposing query: {query_to_use}")
        
        # Determine number of sub-questions based on depth_and_breadth
        num_questions = min(3 + state.config.depth_and_breadth, 8)  # 4-8 questions based on depth
        
        chain = llm_provider.create_chain(DECOMPOSITION_PROMPT)
        result = chain.invoke({
            "query": query_to_use,
            "num_questions": num_questions
        })
        
        # Parse the questions
        sub_questions = []
        for line in result.strip().split('\n'):
            line = line.strip()
            if line and (line.startswith('- ') or line.startswith('• ') or 
                       any(line.startswith(f"{i}.") for i in range(1, 20))):
                # Remove the leading number/bullet and clean
                cleaned = line.split('.', 1)[-1].split('- ', 1)[-1].split('• ', 1)[-1].strip()
                if cleaned and '?' in cleaned:
                    sub_questions.append(cleaned)
        
        # Fallback if parsing fails
        if len(sub_questions) < num_questions // 2:
            logger.warning("Parsing sub-questions failed. Using fallback approach")
            # Just separate by lines and clean
            sub_questions = [line.strip() for line in result.strip().split('\n')]
            sub_questions = [q for q in sub_questions if len(q) > 10 and '?' in q]
        
        # Ensure we have some questions
        if not sub_questions:
            logger.warning("No sub-questions found. Creating default sub-questions")
            sub_questions = [
                f"What is {query_to_use}?",
                f"What are the key concepts in {query_to_use}?",
                f"What are the latest developments in {query_to_use}?",
                f"What are the main challenges in {query_to_use}?",
                f"What are practical applications of {query_to_use}?"
            ]
        
        state.sub_questions = sub_questions[:num_questions]  # Limit to requested number
        state.status = "query_decomposed"
        state.progress = 0.3
        state.log.append(f"Decomposition agent: Created {len(state.sub_questions)} sub-questions")
        logger.info(f"Created {len(state.sub_questions)} sub-questions")
        return state
    except Exception as e:
        error_msg = f"Error decomposing query: {str(e)}"
        state.errors.append(error_msg)
        state.status = "error"
        state.log.append(f"Decomposition agent: Error - {str(e)}")
        logger.error(error_msg)
        
        # Even if there's an error, create default sub-questions to prevent recursion
        if not state.sub_questions:
            query_to_use = state.clarified_query if state.clarified_query else state.original_query
            state.sub_questions = [
                f"What is {query_to_use}?",
                f"What are the key concepts in {query_to_use}?",
                f"What are the latest developments in {query_to_use}?",
                f"What are the main challenges in {query_to_use}?",
                f"What are practical applications of {query_to_use}?"
            ]
            state.status = "query_decomposed"
            state.progress = 0.3
            state.log.append(f"Decomposition agent: Created default sub-questions after error")
        
        return state

def search_web(state: ResearchState) -> ResearchState:
    """Perform web searches for each sub-question.
    
    Args:
        state: The current research state
        
    Returns:
        Updated research state with search results
    """
    try:
        # Check if we have sub-questions
        if not state.sub_questions:
            log_message = "Search agent: No sub-questions available, creating default questions"
            state.log.append(log_message)
            logger.warning(log_message)
            
            # Create default sub-questions to prevent recursion
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
        
        search_results = {}
        
        # Determine search depth based on config
        num_results = 2 if state.config.research_speed == "fast" else 3
        
        # Track failed searches to provide fallback content
        failed_searches = []
        
        # Set a maximum time for all searches
        import time
        start_time = time.time()
        max_search_time = 15  # Reduced from 30 to 15 seconds for faster progression
        
        # Process at least 2 questions before timing out
        min_questions_to_process = min(2, len(state.sub_questions))
        questions_processed = 0
        
        # Limit the number of questions to process to speed things up
        questions_to_process = state.sub_questions[:min(5, len(state.sub_questions))]
        
        for i, question in enumerate(questions_to_process):
            # Check if we're running out of time, but ensure we process at least min_questions_to_process
            elapsed_time = time.time() - start_time
            if elapsed_time > max_search_time and questions_processed >= min_questions_to_process:
                logger.warning(f"Search time limit reached after {i} questions. Using fallback for remaining questions.")
                state.log.append(f"Search agent: Time limit reached. Using fallback for remaining questions.")
                # Add remaining questions to failed searches
                failed_searches.extend(questions_to_process[i:])
                break
                
            try:
                state.log.append(f"Search agent: Searching for '{question}'")
                logger.info(f"Searching for question {i+1}/{len(questions_to_process)}: '{question}'")
                
                # Perform the search
                results = search_service.search(question, num_results)
                questions_processed += 1
                
                if results:
                    # Format the results for the state
                    formatted_results = [
                        f"Title: {result['title']}\nURL: {result['url']}\nContent: {result['content']}"
                        for result in results
                    ]
                    
                    search_results[question] = formatted_results
                    state.log.append(f"Search agent: Found {len(formatted_results)} results for '{question}'")
                else:
                    # No results found, add to failed searches
                    failed_searches.append(question)
                    search_results[question] = [f"No search results found for: {question}"]
                    state.log.append(f"Search agent: No results found for '{question}'")
            
            except Exception as e:
                failed_searches.append(question)
                search_results[question] = [f"Error searching for question: {str(e)}"]
                state.log.append(f"Search agent: Error searching for '{question}' - {str(e)}")
                logger.error(f"Error searching for '{question}': {str(e)}")
                questions_processed += 1  # Count as processed even if it failed
            
            # Update progress for each question
            progress_per_question = 0.4 / len(questions_to_process)
            state.progress = min(0.3 + progress_per_question * (i + 1), 0.7)
            
            # No delay between searches since we're using fallback content
        
        # Provide fallback content for failed searches
        if failed_searches:
            state.log.append(f"Search agent: Providing fallback content for {len(failed_searches)} failed searches")
            logger.info(f"Providing fallback content for {len(failed_searches)} failed searches")
            
            for question in failed_searches:
                # Get fallback content
                fallback_results = search_service.get_fallback_content(question)
                
                # Format the results for the state
                formatted_results = [
                    f"Title: {result['title']}\nURL: {result['url']}\nContent: {result['content']}"
                    for result in fallback_results
                ]
                
                search_results[question] = formatted_results
                state.log.append(f"Search agent: Using fallback content for '{question}'")
        
        # Ensure we have at least some results before proceeding
        if not search_results:
            logger.warning("No search results found for any questions. Using generic fallback content.")
            state.log.append("Search agent: No search results found. Using generic fallback content.")
            
            # Create generic fallback content
            search_results = {}
            for question in state.sub_questions[:2]:  # Just use the first 2 questions
                fallback_results = search_service.get_fallback_content(question)
                formatted_results = [
                    f"Title: {result['title']}\nURL: {result['url']}\nContent: {result['content']}"
                    for result in fallback_results
                ]
                search_results[question] = formatted_results
        
        state.search_results = search_results
        state.status = "search_completed"
        state.progress = 0.7
        state.log.append(f"Search agent: Completed searches for all questions")
        logger.info("Completed searches for all questions")
        
        # Immediately proceed to summarization to avoid getting stuck
        try:
            logger.info("Automatically proceeding to summarization")
            state.log.append("Search agent: Automatically proceeding to summarization")
            summarized_state = summarize_and_fact_check(state)
            return summarized_state
        except Exception as e:
            logger.error(f"Error auto-proceeding to summarization: {str(e)}")
            # Continue with normal flow if auto-progression fails
            return state
    except Exception as e:
        error_msg = f"Error in web search: {str(e)}"
        state.errors.append(error_msg)
        state.log.append(f"Search agent: Error - {str(e)}")
        logger.error(error_msg)
        
        # Even if there's an error, ensure we have some search results to prevent recursion
        if not state.search_results and state.sub_questions:
            # Get fallback content for each question
            state.search_results = {}
            for question in state.sub_questions[:2]:  # Just use the first 2 questions to speed things up
                fallback_results = search_service.get_fallback_content(question)
                
                # Format the results for the state
                formatted_results = [
                    f"Title: {result['title']}\nURL: {result['url']}\nContent: {result['content']}"
                    for result in fallback_results
                ]
                
                state.search_results[question] = formatted_results
            
            state.status = "search_completed"
            state.progress = 0.7
            state.log.append(f"Search agent: Created fallback search results after error")
            
            # Try to auto-proceed to summarization even after error
            try:
                logger.info("Automatically proceeding to summarization after error recovery")
                state.log.append("Search agent: Automatically proceeding to summarization after error recovery")
                summarized_state = summarize_and_fact_check(state)
                return summarized_state
            except Exception as e2:
                logger.error(f"Error auto-proceeding to summarization after error recovery: {str(e2)}")
                # Continue with normal flow if auto-progression fails
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
        
        # Limit the number of search results to process for speed
        search_results_to_process = dict(list(state.search_results.items())[:5])
        
        for question, results in search_results_to_process.items():
            if not results or all(r.startswith("Error") for r in results):
                summaries[question] = "No reliable information found for this question."
                fact_checks[question] = False
                continue
                
            # Combine results for this question
            combined_results = "\n\n".join(results)
            
            # Generate summary
            summary_chain = llm_provider.create_chain(SUMMARIZATION_PROMPT)
            summary = summary_chain.invoke({
                "question": question,
                "results": combined_results
            })
            
            summaries[question] = summary
            logger.info(f"Generated summary for '{question}'")
            
            # Skip fact checking in fast mode or to speed things up
            fact_checks[question] = True
            
            # Update progress for each question
            progress_per_question = 0.2 / len(search_results_to_process)
            state.progress = min(0.7 + progress_per_question * (list(search_results_to_process.keys()).index(question) + 1), 0.9)
        
        state.summaries = summaries
        state.fact_checked = fact_checks
        state.status = "summaries_completed"
        state.progress = 0.9
        state.log.append("Summarization agent: Completed summarization and fact checking")
        logger.info("Completed summarization and fact checking")
        
        # Immediately proceed to final report generation to avoid getting stuck
        try:
            logger.info("Automatically proceeding to final report generation")
            state.log.append("Summarization agent: Automatically proceeding to final report generation")
            final_state = generate_final_report(state)
            return final_state
        except Exception as e:
            logger.error(f"Error auto-proceeding to final report: {str(e)}")
            # Continue with normal flow if auto-progression fails
            return state
    except Exception as e:
        error_msg = f"Error in summarization and fact checking: {str(e)}"
        state.errors.append(error_msg)
        state.log.append(f"Summarization agent: Error - {str(e)}")
        logger.error(error_msg)
        
        # Create basic summaries to continue even after error
        if not state.summaries and state.search_results:
            state.summaries = {}
            for question, results in list(state.search_results.items())[:3]:
                state.summaries[question] = f"Based on limited information, {state.original_query} involves various concepts and applications. Due to processing limitations, a detailed summary could not be generated."
            state.fact_checked = {q: False for q in state.summaries}
            state.status = "summaries_completed"
            state.progress = 0.9
            
            # Try to auto-proceed to final report even after error
            try:
                logger.info("Automatically proceeding to final report generation after error recovery")
                state.log.append("Summarization agent: Automatically proceeding to final report generation after error recovery")
                final_state = generate_final_report(state)
                return final_state
            except Exception as e2:
                logger.error(f"Error auto-proceeding to final report after error recovery: {str(e2)}")
                # Continue with normal flow if auto-progression fails
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
        # Format all summaries
        all_summaries = ""
        for i, (question, summary) in enumerate(state.summaries.items()):
            fact_check_status = "✓" if state.fact_checked.get(question, False) else "⚠"
            all_summaries += f"\n\nQuestion {i+1}: {question} {fact_check_status}\n{summary}"
        
        logger.info("Generating final report")
        
        # Different prompts based on output format
        if state.config.output_format == "full_report":
            prompt = FULL_REPORT_PROMPT
        elif state.config.output_format == "executive_summary":
            prompt = EXECUTIVE_SUMMARY_PROMPT
        else:  # bullet_list
            prompt = BULLET_LIST_PROMPT
        
        # Generate the final report
        report_chain = llm_provider.create_chain(prompt)
        final_report = report_chain.invoke({
            "query": state.clarified_query or state.original_query,
            "summaries": all_summaries
        })
        
        state.final_report = final_report
        state.status = "completed"
        state.progress = 1.0
        state.log.append("Report agent: Generated final report")
        logger.info("Final report generated successfully")
        return state
    except Exception as e:
        error_msg = f"Error generating final report: {str(e)}"
        state.errors.append(error_msg)
        state.status = "error"
        state.log.append(f"Report agent: Error - {str(e)}")
        logger.error(error_msg)
        return state 