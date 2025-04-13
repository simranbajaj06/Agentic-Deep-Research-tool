"""
Agentic Deep Research System - Main Module

This is the main entry point for the Agentic Deep Research System.
It coordinates the workflow between the Query Analysis Agent, Search & Data Collection Agent,
and Orchestration Agent to produce comprehensive research reports.
"""

import asyncio
import nest_asyncio
from pydantic_ai import Agent, RunContext
from schemas.research_report import ResearchReport, ResearchDataPoint, ResearchSubtask
from agents.query_analysis_agent import query_analyst, validate_subtasks
from agents.search_data_collection_agent import parallel_search
from agents.orchestration_agent import generate_report, validate_report
from dotenv import load_dotenv
import os
from dataclasses import dataclass
import httpx
import datetime
import logging
import constants
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

@dataclass
class ResearchDependencies:
    """Dependencies container for the research system."""
    api_key: str
    http_client: httpx.AsyncClient

def save_report_to_file(report: ResearchReport, topic: str):
    """
    Save the research report to a text file.
    
    Args:
        report: The ResearchReport object
        topic: The research topic
    """
    # Create reports directory if it doesn't exist
    os.makedirs(constants.REPORT_DIR, exist_ok=True)
    
    # Create a filename with current timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = topic.replace(' ', '_').replace('/', '_').replace('\\', '_')
    base_filename = f"{constants.REPORT_DIR}/{safe_topic}_{timestamp}"
    
    # The report content is already formatted in the synthesis
    report_content = report.synthesis
    
    # Save to text file
    text_filename = f"{base_filename}.txt"
    with open(text_filename, "w", encoding="utf-8") as f:
        f.write(report_content)
    
    print(f"\nReport saved to {text_filename}")

async def research_pipeline(topic: str) -> ResearchReport:
    """
    Execute the end-to-end research pipeline.
    
    Args:
        topic: The research topic
        
    Returns:
        ResearchReport: The generated research report
    """ 
    logger.info(f"Starting research pipeline for topic: {topic}")
    
    # Initialize HTTP client for API requests
    async with httpx.AsyncClient(timeout=60.0) as client:  # Increased timeout
        deps = ResearchDependencies(api_key=GROQ_API_KEY, http_client=client)
        
        # Step 1: Run query analysis agent
        logger.info("Analyzing query...")
        try:
            subtasks_result = await query_analyst.run(topic, deps=deps)
            subtasks = subtasks_result.data
            logger.info(f"Generated {len(subtasks)} research subtasks")
        except Exception as e:
            logger.error(f"Error in query analysis: {e}")
            raise
        
        # Validate and improve subtasks
        context = RunContext(
            model=constants.ANALYSIS_MODEL,
            usage=None,
            prompt=topic,
            deps=deps
        )
        subtasks = await validate_subtasks(context, subtasks)
        
        # Extract search terms from subtasks - use ALL search terms for better coverage
        search_terms = []
        for task in subtasks:
            if task.search_terms and isinstance(task.search_terms, list) and len(task.search_terms) > 0:
                # Use all search terms for better coverage
                for term in task.search_terms:
                    search_terms.append(f"{topic} {term}")
            else:
                search_terms.append(f"{topic} {task.objective}")
        
        logger.info(f"Generated {len(search_terms)} search terms")
        
        # Step 2: Run search and data collection
        logger.info("Collecting data from search results...")
        search_context = RunContext(
            model=constants.SEARCH_MODEL,
            usage=None,
            prompt="Extract comprehensive data points from web pages based on search terms.",
            deps=deps
        )
        
        # Process in batches to prevent timeout or overwhelming resources
        MAX_BATCH_SIZE = 3
        all_findings_lists = []
        
        for i in range(0, len(search_terms), MAX_BATCH_SIZE):
            batch = search_terms[i:i+MAX_BATCH_SIZE]
            logger.info(f"Processing batch {i//MAX_BATCH_SIZE + 1} of {(len(search_terms)-1)//MAX_BATCH_SIZE + 1} ({len(batch)} terms)")
            batch_findings = await parallel_search(search_context, batch)
            all_findings_lists.extend(batch_findings)
            logger.info(f"Completed batch {i//MAX_BATCH_SIZE + 1}")
        
        # Map findings to original subtasks
        findings_dict = {}
        for i, task in enumerate(subtasks):
            # Collect all findings related to this task
            task_findings = []
            for j, term in enumerate(search_terms):
                if j < len(all_findings_lists) and task.objective in term:
                    task_findings.extend(all_findings_lists[j])
            
            # If we have no direct matches, use findings from any relevant search term
            if not task_findings and i < len(all_findings_lists):
                task_findings = all_findings_lists[i]
                
            findings_dict[task.objective] = task_findings
            logger.info(f"Found {len(task_findings)} data points for objective: {task.objective}")
        
        # Step 3: Generate report
        logger.info("Generating research report...")
        report_context = RunContext(
            model=constants.DEFAULT_MODEL,
            usage=None,
            prompt=topic,
            deps=deps
        )
        
        # Generate the report
        report = await generate_report(report_context, findings_dict, topic)
        
        # Step 4: Validate and enhance report
        logger.info("Validating and enhancing report...")
        validation_context = RunContext(
            model=constants.DEFAULT_MODEL,
            usage=None,
            prompt=f"Validate and enhance research report on {topic}",
            deps=deps
        )
        
        # Validate the report
        validated_report = await validate_report(validation_context, report)
        
        return validated_report

async def main():
    """Main function to run the research system."""
    print("\n=== Agentic Deep Research System ===\n")
    
    # Get topic from user
    topic = input("Enter a research topic (or press Enter for 'AI in Healthcare'): ")
    if not topic:
        topic = "AI in Healthcare"
    
    print(f"\nResearching: {topic}")
    print("This may take several minutes...\n")
    
    # Start progress indicator
    progress_task = asyncio.create_task(show_progress())
    
    try:
        # Run the research pipeline
        report = await research_pipeline(topic)
        
        # Cancel progress indicator
        progress_task.cancel()
        
        # Print a summary of the report
        print("\nResearch Summary:")
        print(f"Topic: {report.topic}")
        print(f"Objectives: {len(report.findings)}")
        total_datapoints = sum(len(findings) for findings in report.findings.values())
        print(f"Total data points: {total_datapoints}")
        print(f"Report length: {len(report.synthesis)} characters")
        print(f"Sources: {len(report.sources)}")
        
        # Save the report
        save_report_to_file(report, topic)
        
        print("\nResearch complete! Your report contains comprehensive information from multiple sources.")
        print("\nThank you for using the Agentic Deep Research System!")
        
    except Exception as e:
        # Cancel progress indicator
        progress_task.cancel()
        print(f"\nError: {e}")
    
    

async def show_progress():
    """Display a simple progress indicator."""
    indicators = ['|', '/', '-', '\\']
    i = 0
    try:
        while True:
            print(f"\rResearching {indicators[i % len(indicators)]}", end="")
            await asyncio.sleep(0.5)
            i += 1
    except asyncio.CancelledError:
        print("\r                     ", end="")

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())