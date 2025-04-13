# orchestration_agent.py
from pydantic_ai import Agent, RunContext
from schemas.research_report import ResearchReport, ResearchDataPoint
import logging
from typing import Dict, List
import constants
from dotenv import load_dotenv
import os
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

async def generate_report(ctx: RunContext, research_data: Dict[str, List[ResearchDataPoint]], original_query: str) -> ResearchReport:
    """Generate a research report from collected data points"""
    logger.info(f"Generating report for: {original_query}")
    
    try:
        # Create a dictionary to store subtask content
        subtask_content = {}
        sources = []
        
        # Process each objective and summarize its content
        for objective, data_points in research_data.items():
            logger.info(f"Processing content for objective: {objective}")
            
            if not data_points:
                subtask_content[objective] = "No data found for this objective."
                continue
                
            # Format all content from data points
            combined_content = ""
            
            # Process each data point to extract content and sources
            for i, data_point in enumerate(data_points):
                # Extract source
                source = getattr(data_point, 'source', "Unknown source")
                
                # Only add valid sources that don't start with @
                if source and not source.startswith('@') and source not in sources:
                    sources.append(source)
                
                # Extract content
                content = getattr(data_point, 'content', "")
                if content:
                    combined_content += f"{content}\n\n"
            
            # Create a summarization agent for this subtask
            summarizer = Agent(
                constants.DEFAULT_MODEL,
                result_type=str,
                system_prompt=f"""You are an expert research analyst.
                Create a comprehensive synthesis of the provided content related to: {objective}
                Your synthesis should be thorough, factual, and include all key information.
                DO NOT include phrases like "In summary" or "This section summarizes" - 
                simply present the information as a cohesive section of a research report.
                DO NOT include introductions or conclusions within this section.
                """
            )
            
            # Generate synthesis for this objective
            try:
                # If content is very long, we'll need to truncate
                if len(combined_content) > 10000:
                    # Create a more balanced preview
                    combined_content = combined_content[:10000] + "\n[Content truncated for length]\n"
                
                summary_result = await summarizer.run(combined_content)
                section_content = summary_result.data if hasattr(summary_result, 'data') else str(summary_result)
                subtask_content[objective] = section_content
                logger.info(f"Generated {len(section_content)} character content for objective: {objective}")
            except Exception as e:
                logger.error(f"Error generating content for objective {objective}: {e}")
                subtask_content[objective] = f"Error processing content: {str(e)}"
        
        # Create a full report structure using a dedicated agent
        report_agent = Agent(
            constants.DEFAULT_MODEL,
            result_type=str,
            system_prompt=f"""You are an expert research report writer.
            Create a comprehensive, professionally-formatted research report following standard academic structure.
            The report should include:
            1. An engaging title
            2. A proper introduction to the overall topic
            3. Clearly labeled sections for each research objective with smooth transitions between them
            4. A comprehensive conclusion that ties the research together
            5. A properly formatted references section with ALL valid source URLs listed
            
            The references section MUST be the final section of the report.
            DO NOT label sections as "summaries" - they are integral parts of the report.
            Ensure the report flows as a cohesive whole rather than disconnected sections.
            """
        )
        
        # Filter out invalid sources (those starting with @)
        valid_sources = [src for src in sources if not src.startswith('@')]
        
        # Format the valid sources for reference
        formatted_sources = ""
        for i, source in enumerate(valid_sources):
            formatted_sources += f"[{i+1}] {source}\n"
        
        # Format data for the report generation agent
        report_prompt = f"""
        Create a comprehensive research report on: {original_query}
        
        Use the following sections and content to create a cohesive, professional report:
        
        Topic: {original_query}
        
        Section content:
        {json.dumps(subtask_content, indent=2)}
        
        Sources to be cited (MUST be included in a References section at the end):
        {formatted_sources}
        
        Guidelines:
        1. Create a proper title and introduction for the topic
        2. Incorporate ALL the section content under appropriate headings
        3. Add a comprehensive conclusion that synthesizes the findings
        4. MUST include a References section at the end with ALL sources listed
        5. Ensure the report reads as a cohesive document with proper transitions
        6. The report should be at least {constants.MIN_REPORT_WORDS} words
        
        IMPORTANT: The final section of the report MUST be a References section that includes a numbered list of ALL the source URLs provided above.
        """
        
        # Generate the complete report
        result = await report_agent.run(report_prompt)
        final_report = result.data if hasattr(result, 'data') else str(result)
        
        # Verify that the report contains a references section
        if "References" not in final_report and "REFERENCES" not in final_report:
            # If references section is missing, append it manually
            final_report += "\n\n## References\n\n"
            for i, source in enumerate(valid_sources):
                final_report += f"{i+1}. {source}\n"
        
        # Create the final report object
        return ResearchReport(
            topic=original_query,
            findings=research_data,
            synthesis=final_report,
            sources=valid_sources if valid_sources else ["No valid sources found"]
        )
        
    except Exception as e:
        logger.error(f"Report generation error: {e}")
        # Create a minimal report with references, filtering out invalid sources
        valid_sources = [src for src in sources if not src.startswith('@')]
        minimal_report = f"Error generating report: {str(e)}\n\n## References\n\n"
        for i, source in enumerate(valid_sources):
            minimal_report += f"{i+1}. {source}\n"
            
        return ResearchReport(
            topic=original_query,
            findings=research_data,
            synthesis=minimal_report,
            sources=valid_sources if valid_sources else ["Error collecting sources"]
        )
async def validate_report(ctx: RunContext, report: ResearchReport) -> ResearchReport:
    """
    Validate and enhance a generated research report.
    """
    logger.info(f"Validating report for topic: {report.topic}")
    
    try:
        # Check if synthesis exists and is not too short
        if not report.synthesis or len(report.synthesis) < constants.MIN_REPORT_WORDS * 2:
            logger.error("Report synthesis is missing or too short")
            
            # If we have findings data, try to regenerate the synthesis
            if report.findings and sum(len(points) for points in report.findings.values()) > 0:
                logger.info("Attempting to regenerate report structure")
                
                try:
                    # Create a minimal report structure
                    minimal_synthesis = f"# Research Report: {report.topic}\n\n"
                    
                    # Add each objective with whatever content we can gather
                    for objective, data_points in report.findings.items():
                        minimal_synthesis += f"## {objective}\n\n"
                        
                        if not data_points:
                            minimal_synthesis += "No data found for this objective.\n\n"
                            continue
                            
                        # Add a brief summary for each source
                        for i, data_point in enumerate(data_points):
                            source = getattr(data_point, 'source', "Unknown source")
                            content = getattr(data_point, 'content', "")
                            
                            minimal_synthesis += f"### Information from {source}\n\n"
                            if content:
                                # Include a preview of the content
                                content_preview = content[:300] + "..." if len(content) > 300 else content
                                minimal_synthesis += f"{content_preview}\n\n"
                                
                    # Add sources
                    minimal_synthesis += "## References\n\n"
                    for objective, data_points in report.findings.items():
                        for data_point in data_points:
                            source = getattr(data_point, 'source', "Unknown source")
                            minimal_synthesis += f"- {source}\n"
                    
                    report.synthesis = minimal_synthesis
                    logger.info("Generated minimal report structure")
                    
                except Exception as e:
                    logger.error(f"Error generating minimal report: {e}")
        
        return report
        
    except Exception as e:
        logger.error(f"Error validating report: {e}")
        return report