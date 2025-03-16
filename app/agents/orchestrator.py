"""
Orchestrator for the research workflow.

This module contains the main orchestrator that manages the research workflow,
coordinating the different research agents and maintaining the research state.
"""

import logging
from typing import Dict, Any, List, Optional
from app.models.schemas import ResearchState, ResearchConfig
from app.agents.research_agents import (
    generate_clarification_questions,
    process_clarifications,
    decompose_query,
    search_web,
    summarize_and_fact_check,
    generate_final_report
)

logger = logging.getLogger(__name__)

class ResearchOrchestrator:
    """Orchestrator for the research workflow."""
    
    def __init__(self):
        """Initialize the research orchestrator."""
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        logger.info("Research orchestrator initialized")
    
    def create_session(self, session_id: str, query: str, config: Optional[Dict[str, Any]] = None) -> ResearchState:
        """Create a new research session.
        
        Args:
            session_id: The unique session ID
            query: The research query
            config: Optional configuration for the research
            
        Returns:
            The initial research state
        """
        if config is None:
            config = {
                "research_speed": "balanced",
                "output_format": "full_report",
                "depth_and_breadth": 2,
                "skip_clarification": False
            }
        
        research_config = ResearchConfig(
            research_speed=config.get("research_speed", "balanced"),
            output_format=config.get("output_format", "full_report"),
            depth_and_breadth=config.get("depth_and_breadth", 2),
            skip_clarification=config.get("skip_clarification", False)
        )
        
        initial_state = ResearchState(
            session_id=session_id,
            original_query=query,
            config=research_config,
            status="initialized",
            progress=0.0,
            log=["Session initialized with query: " + query],
            errors=[]
        )
        
        self.active_sessions[session_id] = {
            "state": initial_state,
            "config": research_config
        }
        
        logger.info(f"Created research session {session_id} with query: {query}")
        return initial_state
    
    def get_session(self, session_id: str) -> Optional[ResearchState]:
        """Get the current state of a research session.
        
        Args:
            session_id: The unique session ID
            
        Returns:
            The current research state or None if not found
        """
        session = self.active_sessions.get(session_id)
        if session:
            return session["state"]
        return None
    
    def _run_workflow_step(self, state: ResearchState) -> ResearchState:
        """Run the appropriate workflow step based on the current state.
        
        Args:
            state: The current research state
            
        Returns:
            The updated research state
        """
        try:
            if state.status == "initialized":
                return generate_clarification_questions(state)
            elif state.status == "clarification_needed" and state.clarification_answers:
                return process_clarifications(state)
            elif state.status == "query_refined":
                return decompose_query(state)
            elif state.status == "query_decomposed":
                state.decomposition_attempts += 1
                return search_web(state)
            elif state.status == "search_completed":
                return summarize_and_fact_check(state)
            elif state.status == "summaries_completed":
                return generate_final_report(state)
            else:
                logger.warning(f"Unknown state: {state.status}, attempting to recover")
                
                if state.final_report:
                    state.status = "completed"
                    state.progress = 1.0
                elif state.summaries:
                    state.status = "summaries_completed"
                    return generate_final_report(state)
                elif state.search_results:
                    state.status = "search_completed"
                    return summarize_and_fact_check(state)
                elif state.sub_questions:
                    state.status = "query_decomposed"
                    return search_web(state)
                elif state.clarified_query:
                    state.status = "query_refined"
                    return decompose_query(state)
                elif state.clarification_answers:
                    state.status = "clarification_needed"
                    return process_clarifications(state)
                else:
                    state.status = "initialized"
                    return generate_clarification_questions(state)
        except Exception as e:
            error_msg = f"Error in workflow step: {str(e)}"
            logger.error(error_msg)
            state.errors.append(error_msg)
            
            if state.status != "error":
                state.log.append(f"Orchestrator: Error in workflow step - {str(e)}, attempting to recover")
                
                if state.status == "initialized":
                    state.status = "query_refined"
                    state.clarified_query = state.original_query
                    return decompose_query(state)
                elif state.status == "clarification_needed":
                    state.status = "query_refined"
                    state.clarified_query = state.original_query
                    return decompose_query(state)
                elif state.status == "query_refined":
                    return decompose_query(state)
                elif state.status == "query_decomposed":
                    return search_web(state)
                elif state.status == "search_completed":
                    return summarize_and_fact_check(state)
                elif state.status == "summaries_completed":
                    return generate_final_report(state)
            
            state.status = "error"
            state.log.append(f"Orchestrator: Error - {str(e)}")
            return state
    
    def start_research(self, session_id: str) -> ResearchState:
        """Start the research process for a session.
        
        Args:
            session_id: The unique session ID
            
        Returns:
            The updated research state
        """
        session = self.active_sessions.get(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            raise ValueError(f"Session {session_id} not found")
        
        state = session["state"]
        
        try:
            logger.info(f"Starting research workflow for session {session_id}")
            state.log.append("Starting research workflow")
            
            if state.config.skip_clarification:
                logger.info("Skipping clarification phase as specified in config")
                state.log.append("Skipping clarification phase as specified in config")
                state.status = "query_refined"
                state.clarified_query = state.original_query
                updated_state = decompose_query(state)
            else:
                updated_state = self._run_workflow_step(state)
                
                if updated_state.status == "clarification_needed" and state.config.research_speed == "fast":
                    logger.info("Fast research mode: auto-continuing without clarification")
                    state.log.append("Fast research mode: auto-continuing without clarification")
                    
                    default_answers = {}
                    for question in updated_state.clarification_questions:
                        default_answers[question] = "No specific preference. Please proceed with general information."
                    
                    updated_state.clarification_answers = default_answers
                    updated_state = process_clarifications(updated_state)
            
            session["state"] = updated_state
            
            logger.info(f"Research workflow started for session {session_id}, status: {updated_state.status}")
            return updated_state
        
        except Exception as e:
            error_msg = f"Error in research workflow: {str(e)}"
            logger.error(error_msg)
            state.errors.append(error_msg)
            
            if state.status == "initialized" or state.status == "":
                state.log.append(f"Orchestrator: Error during initialization - {str(e)}, attempting to recover")
                state.status = "query_refined"
                state.clarified_query = state.original_query
                
                try:
                    state = decompose_query(state)
                    session["state"] = state
                    return state
                except Exception as e2:
                    state.errors.append(f"Recovery attempt failed: {str(e2)}")
                    state.status = "error"
            else:
                state.status = "error"
                
            state.log.append(f"Orchestrator: Error - {str(e)}")
            session["state"] = state
            return state
    
    def add_clarification_answers(self, session_id: str, answers: Dict[str, str]) -> ResearchState:
        """Add clarification answers to a research session.
        
        Args:
            session_id: The unique session ID
            answers: Dictionary mapping questions to answers
            
        Returns:
            The updated research state
        """
        session = self.active_sessions.get(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            raise ValueError(f"Session {session_id} not found")
        
        state = session["state"]
        
        state.clarification_answers = answers
        state.clarification_attempts += 1
        state.log.append(f"Added {len(answers)} clarification answers")
        
        session["state"] = state
        
        logger.info(f"Added clarification answers to session {session_id}")
        return state
    
    def continue_research(self, session_id: str) -> ResearchState:
        """Continue the research process after adding clarification answers.
        
        Args:
            session_id: The unique session ID
            
        Returns:
            The updated research state
        """
        session = self.active_sessions.get(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            raise ValueError(f"Session {session_id} not found")
        
        state = session["state"]
        
        try:
            logger.info(f"Continuing research workflow for session {session_id}")
            state.log.append("Continuing research workflow")
            
            if state.status == "clarification_needed" and not state.clarification_answers:
                if state.clarification_attempts >= 3:
                    logger.info(f"Auto-continuing after {state.clarification_attempts} clarification attempts")
                    state.log.append("Auto-continuing with default answers after timeout")
                    
                    default_answers = {}
                    for question in state.clarification_questions:
                        default_answers[question] = "No specific preference. Please proceed with general information."
                    
                    state.clarification_answers = default_answers
            
            if state.status == "query_decomposed" and state.decomposition_attempts >= 2:
                logger.info(f"Auto-continuing from query_decomposed after {state.decomposition_attempts} attempts")
                state.log.append("Auto-continuing from query_decomposed state due to timeout")
                
                if not state.search_results and state.sub_questions:
                    state.search_results = {}
                    for question in state.sub_questions[:2]:
                        from app.services.search_api import search_service
                        fallback_results = search_service.get_fallback_content(question)
                        
                        formatted_results = [
                            f"Title: {result['title']}\nURL: {result['url']}\nContent: {result['content']}"
                            for result in fallback_results
                        ]
                        
                        state.search_results[question] = formatted_results
                
                state.status = "search_completed"
                state.progress = 0.7
                updated_state = state
                state.decomposition_attempts += 1
            else:
                updated_state = self._run_workflow_step(state)
                
                if updated_state.status == "query_decomposed":
                    updated_state.decomposition_attempts += 1
            
            if updated_state.status == state.status and updated_state.status != "completed":
                logger.info(f"Forcing progression from {updated_state.status} state")
                state.log.append(f"Forcing progression from {updated_state.status} state")
                
                if updated_state.status == "initialized":
                    updated_state = generate_clarification_questions(updated_state)
                elif updated_state.status == "clarification_needed":
                    if not updated_state.clarification_answers:
                        default_answers = {}
                        for question in updated_state.clarification_questions:
                            default_answers[question] = "No specific preference. Please proceed with general information."
                        updated_state.clarification_answers = default_answers
                    updated_state = process_clarifications(updated_state)
                elif updated_state.status == "query_refined":
                    updated_state = decompose_query(updated_state)
                elif updated_state.status == "query_decomposed":
                    updated_state = search_web(updated_state)
                elif updated_state.status == "search_completed":
                    updated_state = summarize_and_fact_check(updated_state)
                elif updated_state.status == "summaries_completed":
                    updated_state = generate_final_report(updated_state)
            
            session["state"] = updated_state
            
            logger.info(f"Research workflow continued for session {session_id}, new status: {updated_state.status}")
            return updated_state
        
        except Exception as e:
            error_msg = f"Error in research workflow: {str(e)}"
            logger.error(error_msg)
            state.errors.append(error_msg)
            
            if state.status != "error":
                state.log.append(f"Orchestrator: Error - {str(e)}, attempting to recover")
                
                if state.status == "initialized":
                    state.status = "query_refined"
                    state.clarified_query = state.original_query
                elif state.status == "clarification_needed":
                    state.status = "query_refined"
                    state.clarified_query = state.original_query
                elif state.status == "query_refined":
                    state = decompose_query(state)
                elif state.status == "query_decomposed":
                    state = search_web(state)
                elif state.status == "search_completed":
                    state = summarize_and_fact_check(state)
                elif state.status == "summaries_completed":
                    state = generate_final_report(state)
                else:
                    state.status = "error"
            
            session["state"] = state
            return state
    
    def run_full_research(self, session_id: str) -> ResearchState:
        """Run the full research process from start to finish.
        
        Args:
            session_id: The unique session ID
            
        Returns:
            The final research state
        """
        session = self.active_sessions.get(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            raise ValueError(f"Session {session_id} not found")
        
        state = session["state"]
        
        try:
            logger.info(f"Running full research workflow for session {session_id}")
            state.log.append("Running full research workflow")
            
            state.status = "query_refined"
            state.clarified_query = state.original_query
            
            try:
                state = decompose_query(state)
            except Exception as e:
                logger.error(f"Error in decompose_query: {str(e)}")
                state.log.append(f"Error in decompose_query: {str(e)}, attempting to continue")
                state.errors.append(f"Error in decompose_query: {str(e)}")
                if not state.sub_questions:
                    state.sub_questions = [
                        f"What is {state.original_query}?",
                        f"What are the key concepts in {state.original_query}?",
                        f"What are the latest developments in {state.original_query}?",
                        f"What are the main challenges in {state.original_query}?",
                        f"What are practical applications of {state.original_query}?"
                    ]
                state.status = "query_decomposed"
            
            if state.status == "query_decomposed" or state.status == "error":
                try:
                    state = search_web(state)
                except Exception as e:
                    logger.error(f"Error in search_web: {str(e)}")
                    state.log.append(f"Error in search_web: {str(e)}, attempting to continue")
                    state.errors.append(f"Error in search_web: {str(e)}")
                    if not state.search_results and state.sub_questions:
                        state.search_results = {}
                        for question in state.sub_questions:
                            state.search_results[question] = [
                                f"No search results available for: {question}. Using fallback content."
                            ]
                    state.status = "search_completed"
            
            if state.status == "search_completed" or state.status == "error":
                try:
                    state = summarize_and_fact_check(state)
                except Exception as e:
                    logger.error(f"Error in summarize_and_fact_check: {str(e)}")
                    state.log.append(f"Error in summarize_and_fact_check: {str(e)}, attempting to continue")
                    state.errors.append(f"Error in summarize_and_fact_check: {str(e)}")
                    if not state.summaries and state.search_results:
                        state.summaries = {}
                        for question, results in state.search_results.items():
                            state.summaries[question] = f"Based on limited information, {state.original_query} involves various concepts and applications. Due to processing limitations, a detailed summary could not be generated."
                        state.fact_checked = {q: False for q in state.summaries}
                    state.status = "summaries_completed"
            
            if state.status == "summaries_completed" or state.status == "error":
                try:
                    state = generate_final_report(state)
                except Exception as e:
                    logger.error(f"Error in generate_final_report: {str(e)}")
                    state.log.append(f"Error in generate_final_report: {str(e)}")
                    state.errors.append(f"Error in generate_final_report: {str(e)}")
                    state.final_report = f"# Research Report on {state.original_query}\n\n"
                    state.final_report += "## Executive Summary\n\n"
                    state.final_report += f"This report provides an overview of {state.original_query}. Due to processing limitations, only basic information could be compiled.\n\n"
                    
                    if state.summaries:
                        state.final_report += "## Key Findings\n\n"
                        for question, summary in state.summaries.items():
                            state.final_report += f"### {question}\n\n{summary}\n\n"
                    
                    state.final_report += "## Conclusion\n\n"
                    state.final_report += f"Further research is recommended to gain a more comprehensive understanding of {state.original_query}."
                    
                    state.status = "completed"
                    state.progress = 1.0
            
            session["state"] = state
            
            logger.info(f"Full research workflow completed for session {session_id}, status: {state.status}")
            return state
        
        except Exception as e:
            error_msg = f"Error in full research workflow: {str(e)}"
            logger.error(error_msg)
            state.errors.append(error_msg)
            state.status = "error"
            state.log.append(f"Orchestrator: Error - {str(e)}")
            session["state"] = state
            return state
    
    def cancel_session(self, session_id: str) -> bool:
        """Cancel a research session.
        
        Args:
            session_id: The unique session ID
            
        Returns:
            True if the session was cancelled, False otherwise
        """
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"Cancelled research session {session_id}")
            return True
        return False
