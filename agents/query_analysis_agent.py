"""
Query Analysis Agent Module

This module contains the agent responsible for analyzing research queries
and breaking them down into structured subtasks. It uses LLM-based analysis
to understand the user's research needs and create appropriate subtasks.
"""

from pydantic_ai import Agent, RunContext
from schemas.research_report import ResearchSubtask
from typing import List
import logging
import constants
from dotenv import load_dotenv
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize the query analysis agent
query_analyst = Agent(
    constants.ANALYSIS_MODEL,
    result_type=List[ResearchSubtask],
    system_prompt="Analyze research queries and break them into structured subtasks"
)


@query_analyst.system_prompt
async def analysis_guidelines(ctx: RunContext) -> str:
    """System prompt for the query analysis agent"""
    return f"""Break down research topics into {constants.MIN_SUBTASKS}-{constants.MAX_SUBTASKS} logical subtasks.

    Each subtask should have:
    - A clear objective (10-200 characters)
    - 1-2 search terms
    - A priority (1 is highest)
    
    Example for "AI in Healthcare":
    [
      {{
        "objective": "Current AI applications in clinical diagnosis",
        "search_terms": ["AI medical diagnosis", "clinical AI systems"],
        "priority": 1
      }},
      {{
        "objective": "Regulatory challenges for AI in healthcare",
        "search_terms": ["healthcare AI regulation", "medical AI ethics"],
        "priority": 2
      }}
    ]
    """

@query_analyst.tool
async def validate_subtasks(ctx: RunContext, subtasks: List[ResearchSubtask]) -> List[ResearchSubtask]:
    """Validates generated subtasks"""
    logger.info(f"Validating {len(subtasks)} subtasks")
    
    # Ensure search terms are well-formed
    for i, subtask in enumerate(subtasks):
        # Ensure each subtask has at least one search term
        if not subtask.search_terms:
            subtask.search_terms = [subtask.objective]
        
        # Ensure priorities are properly set (1 to N)
        subtask.priority = i + 1
    
    # Sort by priority
    subtasks.sort(key=lambda x: x.priority)
    
    return subtasks

