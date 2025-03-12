"""
API routes for the research functionality.

This module contains the FastAPI routes for the research functionality,
including creating research sessions, getting research status, and
handling clarification answers.
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from app.models.schemas import ResearchState, ResearchConfig
from app.agents.orchestrator import ResearchOrchestrator

# Configure logging
logger = logging.getLogger(__name__)

# Create the router
router = APIRouter(prefix="/research", tags=["research"])

# Create the orchestrator
orchestrator = ResearchOrchestrator()

# Request and response models
class ResearchRequest(BaseModel):
    """Request model for creating a research session."""
    query: str = Field(..., description="The research query")
    config: Optional[Dict[str, Any]] = Field(None, description="Optional research configuration")

class ClarificationAnswersRequest(BaseModel):
    """Request model for submitting clarification answers."""
    answers: Dict[str, str] = Field(..., description="Answers to clarification questions")

class ResearchResponse(BaseModel):
    """Response model for research operations."""
    session_id: str = Field(..., description="The unique session ID")
    status: str = Field(..., description="The current status of the research")
    progress: float = Field(..., description="The progress of the research (0.0 to 1.0)")
    clarification_questions: Optional[List[str]] = Field(None, description="Clarification questions if needed")
    final_report: Optional[str] = Field(None, description="The final research report if completed")
    errors: List[str] = Field([], description="Any errors that occurred during the research")

@router.post("/create", response_model=ResearchResponse)
async def create_research_session(request: ResearchRequest, background_tasks: BackgroundTasks):
    """Create a new research session.
    
    Args:
        request: The research request
        background_tasks: FastAPI background tasks
        
    Returns:
        The research response
    """
    try:
        # Generate a unique session ID
        session_id = str(uuid.uuid4())
        
        # Create the session
        state = orchestrator.create_session(session_id, request.query, request.config)
        
        # Start the research in the background
        background_tasks.add_task(orchestrator.start_research, session_id)
        
        # Return the initial response
        return ResearchResponse(
            session_id=session_id,
            status=state.status,
            progress=state.progress,
            errors=state.errors
        )
    
    except Exception as e:
        logger.error(f"Error creating research session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating research session: {str(e)}")

@router.get("/{session_id}", response_model=ResearchResponse)
async def get_research_status(session_id: str):
    """Get the status of a research session.
    
    Args:
        session_id: The unique session ID
        
    Returns:
        The research response
    """
    try:
        # Get the session state
        state = orchestrator.get_session(session_id)
        
        if not state:
            raise HTTPException(status_code=404, detail=f"Research session {session_id} not found")
        
        # Return the response
        return ResearchResponse(
            session_id=session_id,
            status=state.status,
            progress=state.progress,
            clarification_questions=state.clarification_questions if state.status == "clarification_needed" else None,
            final_report=state.final_report if state.status == "completed" else None,
            errors=state.errors
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting research status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting research status: {str(e)}")

@router.post("/{session_id}/clarify", response_model=ResearchResponse)
async def submit_clarification_answers(session_id: str, request: ClarificationAnswersRequest, background_tasks: BackgroundTasks):
    """Submit answers to clarification questions.
    
    Args:
        session_id: The unique session ID
        request: The clarification answers request
        background_tasks: FastAPI background tasks
        
    Returns:
        The research response
    """
    try:
        # Get the session state
        state = orchestrator.get_session(session_id)
        
        if not state:
            raise HTTPException(status_code=404, detail=f"Research session {session_id} not found")
        
        if state.status != "clarification_needed":
            raise HTTPException(status_code=400, detail="Research session is not waiting for clarification")
        
        # Add the answers
        state = orchestrator.add_clarification_answers(session_id, request.answers)
        
        # Continue the research in the background
        background_tasks.add_task(orchestrator.continue_research, session_id)
        
        # Return the response
        return ResearchResponse(
            session_id=session_id,
            status=state.status,
            progress=state.progress,
            errors=state.errors
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting clarification answers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error submitting clarification answers: {str(e)}")

@router.delete("/{session_id}", response_model=Dict[str, bool])
async def cancel_research_session(session_id: str):
    """Cancel a research session.
    
    Args:
        session_id: The unique session ID
        
    Returns:
        Success status
    """
    try:
        # Cancel the session
        success = orchestrator.cancel_session(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Research session {session_id} not found")
        
        # Return success
        return {"success": True}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling research session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error cancelling research session: {str(e)}") 