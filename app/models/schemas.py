from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional, Union, Literal

class ResearchObject(BaseModel):
    """Model for a research object stored in the vector database."""
    name: str
    description: str
    tags: List[str] = []

class ResearchQuery(BaseModel):
    """Model for a research query submitted by the user."""
    query: str

class ResearchConfig(BaseModel):
    """Configuration options for the research process."""
    output_format: Literal["full_report", "executive_summary", "bullet_list"] = "full_report"
    research_speed: Literal["fast", "deep"] = "deep"
    depth_and_breadth: int = Field(default=3, ge=1, le=5, description="Depth and breadth of research on scale 1-5")

class ResearchResponse(BaseModel):
    """Response model for research initialization."""
    session_id: str
    progress: float = 0.0
    status: str = "initiated"
    message: str = "Research session created"
    
class ResearchWithConfig(BaseModel):
    """Combined model for research query with configuration."""
    query: str
    config: ResearchConfig

class ClarificationQuestion(BaseModel):
    """Model for a single clarification question."""
    question: str

class ClarificationResponse(BaseModel):
    """Response model for clarification questions."""
    session_id: str
    questions: List[str]

class ResearchState(BaseModel):
    """State schema for the research process."""
    session_id: str
    original_query: str
    clarified_query: Optional[str] = None
    config: ResearchConfig
    clarification_questions: List[str] = []
    clarification_answers: Dict[str, str] = {}
    sub_questions: List[str] = []
    search_results: Dict[str, List[str]] = {}
    summaries: Dict[str, str] = {}
    fact_checked: Dict[str, bool] = {}
    final_report: str = ""
    progress: float = 0.0
    status: str = "initiated"
    errors: List[str] = []
    log: List[str] = []  # Added field for tracking inter-agent communication
    clarification_attempts: int = 0
    decomposition_attempts: int = 0
    
    model_config = ConfigDict(arbitrary_types_allowed=True) 