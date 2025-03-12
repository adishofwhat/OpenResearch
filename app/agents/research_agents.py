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
        num_results = 3 if state.config.research_speed == "fast" else 5
        
        # Track failed searches to provide fallback content
        failed_searches = []
        
        for question in state.sub_questions:
            try:
                state.log.append(f"Search agent: Searching for '{question}'")
                
                # Perform the search
                results = search_service.search(question, num_results)
                
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
            
            # Update progress for each question
            progress_per_question = 0.4 / len(state.sub_questions)
            state.progress = min(0.3 + progress_per_question * (list(search_results.keys()).index(question) + 1), 0.7)
        
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
        
        state.search_results = search_results
        state.status = "search_completed"
        state.progress = 0.7
        state.log.append(f"Search agent: Completed searches for all questions")
        logger.info("Completed searches for all questions")
        return state
    except Exception as e:
        error_msg = f"Error in web search: {str(e)}"
        state.errors.append(error_msg)
        state.status = "error"
        state.log.append(f"Search agent: Error - {str(e)}")
        logger.error(error_msg)
        
        # Even if there's an error, ensure we have some search results to prevent recursion
        if not state.search_results and state.sub_questions:
            # Get fallback content for each question
            state.search_results = {}
            for question in state.sub_questions:
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
        
        for question, results in state.search_results.items():
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
            
            # Perform fact checking if in deep mode
            if state.config.research_speed == "deep":
                fact_check_chain = llm_provider.create_chain(FACT_CHECKING_PROMPT)
                fact_check_result = fact_check_chain.invoke({
                    "question": question,
                    "results": combined_results,
                    "summary": summary
                })
                
                # Simple check if verified
                fact_checks[question] = fact_check_result.startswith("VERIFIED")
                logger.info(f"Fact check for '{question}': {'Verified' if fact_checks[question] else 'Not verified'}")
            else:
                # Skip detailed fact checking in fast mode
                fact_checks[question] = True
            
            # Update progress for each question
            progress_per_question = 0.2 / len(state.search_results)
            state.progress = min(0.7 + progress_per_question * (list(state.search_results.keys()).index(question) + 1), 0.9)
        
        state.summaries = summaries
        state.fact_checked = fact_checks
        state.status = "summaries_completed"
        state.progress = 0.9
        state.log.append("Summarization agent: Completed summarization and fact checking")
        logger.info("Completed summarization and fact checking")
        return state
    except Exception as e:
        error_msg = f"Error in summarization and fact checking: {str(e)}"
        state.errors.append(error_msg)
        state.status = "error"
        state.log.append(f"Summarization agent: Error - {str(e)}")
        logger.error(error_msg)
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