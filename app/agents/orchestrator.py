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

# Configure logging
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
        # Create default config if not provided
        if config is None:
            config = {
                "research_speed": "balanced",
                "output_format": "full_report",
                "depth_and_breadth": 2
            }
        
        # Create the research config
        research_config = ResearchConfig(
            research_speed=config.get("research_speed", "balanced"),
            output_format=config.get("output_format", "full_report"),
            depth_and_breadth=config.get("depth_and_breadth", 2)
        )
        
        # Create the initial state
        initial_state = ResearchState(
            session_id=session_id,
            original_query=query,
            config=research_config,
            status="initialized",
            progress=0.0,
            log=["Session initialized with query: " + query],
            errors=[]
        )
        
        # Store the session
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
            # Determine which step to run based on the current status
            if state.status == "initialized":
                return generate_clarification_questions(state)
            elif state.status == "clarification_needed" and state.clarification_answers:
                return process_clarifications(state)
            elif state.status == "query_refined":
                return decompose_query(state)
            elif state.status == "query_decomposed":
                return search_web(state)
            elif state.status == "search_completed":
                return summarize_and_fact_check(state)
            elif state.status == "summaries_completed":
                return generate_final_report(state)
            else:
                # If we don't know what to do, just return the state
                return state
        except Exception as e:
            error_msg = f"Error in workflow step: {str(e)}"
            logger.error(error_msg)
            state.errors.append(error_msg)
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
        
        # Get the initial state
        state = session["state"]
        
        # Start the workflow
        try:
            logger.info(f"Starting research workflow for session {session_id}")
            state.log.append("Starting research workflow")
            
            # Run the first step (generate clarification questions)
            updated_state = self._run_workflow_step(state)
            
            # Update the session state
            session["state"] = updated_state
            
            logger.info(f"Research workflow started for session {session_id}")
            return updated_state
        
        except Exception as e:
            error_msg = f"Error in research workflow: {str(e)}"
            logger.error(error_msg)
            state.errors.append(error_msg)
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
        
        # Get the current state
        state = session["state"]
        
        # Add the answers
        state.clarification_answers = answers
        state.clarification_attempts += 1
        state.log.append(f"Added {len(answers)} clarification answers")
        
        # Update the session state
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
        
        # Get the current state
        state = session["state"]
        
        # Continue the workflow
        try:
            logger.info(f"Continuing research workflow for session {session_id}")
            state.log.append("Continuing research workflow")
            
            # Run the next step in the workflow
            updated_state = self._run_workflow_step(state)
            
            # If the status hasn't changed, run the next step
            if updated_state.status == state.status and updated_state.status != "completed":
                # Try to advance to the next step
                if updated_state.status == "clarification_needed":
                    # We need user input, so just return
                    pass
                elif updated_state.status == "query_refined":
                    updated_state = decompose_query(updated_state)
                elif updated_state.status == "query_decomposed":
                    updated_state = search_web(updated_state)
                elif updated_state.status == "search_completed":
                    updated_state = summarize_and_fact_check(updated_state)
                elif updated_state.status == "summaries_completed":
                    updated_state = generate_final_report(updated_state)
            
            # Update the session state
            session["state"] = updated_state
            
            logger.info(f"Research workflow continued for session {session_id}")
            return updated_state
        
        except Exception as e:
            error_msg = f"Error in research workflow: {str(e)}"
            logger.error(error_msg)
            state.errors.append(error_msg)
            state.status = "error"
            state.log.append(f"Orchestrator: Error - {str(e)}")
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
        
        # Get the initial state
        state = session["state"]
        
        # Run the full workflow
        try:
            logger.info(f"Running full research workflow for session {session_id}")
            state.log.append("Running full research workflow")
            
            # Skip clarification and run all steps in sequence
            state.status = "query_refined"  # Skip clarification
            state.clarified_query = state.original_query  # Use original query
            
            # Run each step in sequence
            state = decompose_query(state)
            if state.status == "query_decomposed":
                state = search_web(state)
            if state.status == "search_completed":
                state = summarize_and_fact_check(state)
            if state.status == "summaries_completed":
                state = generate_final_report(state)
            
            # Update the session state
            session["state"] = state
            
            logger.info(f"Full research workflow completed for session {session_id}")
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
