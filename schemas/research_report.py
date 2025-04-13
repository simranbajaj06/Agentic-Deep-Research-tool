from pydantic import BaseModel, Field, validator
from typing import List, Dict

class ResearchSubtask(BaseModel):
    """
    Represents a subtask in the research process.
    Each subtask has an objective, search terms, and priority.
    """
    objective: str = Field(
        ..., 
        description="The objective of the research subtask.",
        min_length=10
    )
    search_terms: List[str] = Field(
        ..., 
        description="Keywords for web search.",
        min_items=1
    )
    priority: int = Field(
        ..., 
        description="The priority of the research subtask (1 is highest).",
        ge=1
    )


class ResearchDataPoint(BaseModel):
    """
    Represents a single data point collected during research.
    Contains source URL, content, summary, and relevance score.
    """
    source: str = Field(
        ..., 
        description="Information source URL"
    )
    content: str = Field(
        ..., 
        description="Extracted relevant content with no truncation",
        min_length=1
    )
    summary: str = Field(
        ..., 
        description="Comprehensive summary of content",
        min_length=10
    )
    relevance_score: float = Field(
        ..., 
        description="Relevance score between 0 and 1",
        ge=0, 
        le=1
    )
    
    


class ResearchReport(BaseModel):
    """
    The final research report produced by the system.
    Contains the research topic, findings, synthesis, and sources.
    """
    topic: str = Field(
        ..., 
        description="The research topic"
    )
    findings: Dict[str, List[ResearchDataPoint]] = Field(
        ..., 
        description="Research findings organized by objective"
    )
    synthesis: str = Field(
        ..., 
        description="Synthesized research report content",
        min_length=100
    )
    sources: List[str] = Field(
        ..., 
        description="List of sources used in the research",
        min_items=1
    )
    
   