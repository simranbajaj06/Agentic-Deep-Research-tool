"""
Search and Data Collection Agent Module

This module contains the agent responsible for conducting web searches,
scraping content, and extracting relevant data points based on research subtasks.
It uses web search APIs and content processing to collect information.
"""

import asyncio
from pydantic_ai import Agent, RunContext
from schemas.research_report import ResearchDataPoint
import requests
from bs4 import BeautifulSoup
import constants
import logging
from typing import List
import re
from dotenv import load_dotenv
import os
import random

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)   

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # Add this to your .env file
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")    # Add this to your .env file

# Initialize the search agent
search_agent = Agent(
    model=constants.SEARCH_MODEL,
    result_type=List[ResearchDataPoint],
    system_prompt="""Extract relevant data points from web pages based on search terms.
    Be thorough and comprehensive in your analysis of content.
    Include ALL relevant information in your data points."""
)
@search_agent.system_prompt
async def search_guidelines(ctx: RunContext) -> str:
    """System prompt for the search agent"""
    return """You are an expert web researcher. Extract full content from search results that address the research objective.

    Your task is to:
    1. Search for information related to the query
    2. Extract COMPLETE relevant content from search results
    3. Provide source attribution

    Return a list of data points with:
    - source: URL or reference
    - content: FULL extracted content (not just excerpts)
    - relevance_score: How relevant the information is (0-1)
    
    Focus on gathering comprehensive content - don't worry about summarizing.
    """

@search_agent.tool
async def web_search(ctx: RunContext, query: str) -> List[dict]:
    """Perform a web search using Google Custom Search API and fetch full webpage content"""
    logger.info(f"Searching for: {query}")
    
    try:
        await asyncio.sleep(random.uniform(1, 3))
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'q': query,
            'key': GOOGLE_API_KEY,
            'cx': GOOGLE_CSE_ID,
            'num': constants.MAX_SEARCH_RESULTS  # Number of results (max 10 per request)
        }
        
        # Make the request
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Search failed with status code: {response.status_code}")
            return [{
                'source': f"https://example.com/search?q={query}",
                'content': f"Search failed with status code: {response.status_code}",
                'title': 'Error', 
                'summary': f"Search error: status code {response.status_code}"
            }]
        
        # Parse JSON response
        search_results = response.json()
        logger.info(f"Search response keys: {list(search_results.keys())}")
       
        if 'items' not in search_results:
            logger.warning(f"No results found for query: {query}")
            return [{
                'source': f"https://example.com/search?q={query}",
                'content': f"No results found for query: {query}",
                'title': 'No results',
                'summary': f"No search results found for: {query}"
            }]
        
        # Extract results from JSON and fetch full content for each page
        results = []
        for item in search_results['items']:
            # Get basic info from search result
            source_url = item['link']
            snippet = item.get('snippet', item.get('title', 'No content available'))
            title = item.get('title', 'No title')
            
            # Add search snippet as preliminary content
            result = {
                'source': source_url,
                'content': snippet,  # Will be replaced with full content if fetch is successful
                'title': title,
                'summary': f"Snippet: {snippet}"  # Default summary from snippet
            }
            
            # Try to fetch full content
            try:
                logger.info(f"Fetching full content for: {source_url}")
                full_content = await fetch_webpage_content(ctx, source_url)
                
                # Only update if we got meaningful content
                if full_content and len(full_content) > len(snippet):
                    result['content'] = full_content
                    # Generate a summary of the content
                    result['summary'] = ""
                    logger.info(f"Successfully fetched and summarized {len(full_content)} characters from {source_url}")
                else:
                    logger.warning(f"Fetched content was too short, keeping snippet for {source_url}")
            except Exception as e:
                logger.error(f"Error fetching content from {source_url}: {e}")
                # Keep the original snippet if fetch fails
            
            results.append(result)
            logger.info(f"Processed result: {source_url}")
            
            # Add delay between fetches to avoid overwhelming servers
            await asyncio.sleep(random.uniform(1, 3))
        
        return results
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        return [{
            'source': f"https://example.com/error?q={query}",
            'content': f"Error during search: {str(e)}",
            'title': 'Error',
            'summary': f"Search error: {str(e)}"
        }]
    

@search_agent.tool
async def fetch_webpage_content(ctx: RunContext, url: str) -> str:
    """Fetch content from a webpage given its URL"""
    logger.info(f"Fetching webpage content: {url}")
    try:
        # More comprehensive headers for better compatibility
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Increase timeout for large pages
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return f"Failed to fetch content from {url} (Status code: {response.status_code})"
        
        # Use BeautifulSoup to parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script, style, and other non-content elements
        for element in soup(["script", "style", "nav", "footer", "head", "header"]):
            element.extract()
        
        # Try to get the main content
        main_content = None
        
        # Look for common content containers
        for container in ['article', 'main', '.content', '#content', '.post', '.entry']:
            if main_content:
                break
                
            if container.startswith('.'):
                # This is a class selector
                elements = soup.select(container)
                if elements:
                    main_content = elements[0].get_text(separator=' ', strip=True)
            elif container.startswith('#'):
                # This is an ID selector
                element = soup.select_one(container)
                if element:
                    main_content = element.get_text(separator=' ', strip=True)
            else:
                # This is a tag name
                elements = soup.find_all(container)
                if elements:
                    main_content = elements[0].get_text(separator=' ', strip=True)
        
        # If we couldn't find main content, fall back to the whole page text
        if not main_content or len(main_content) < 200:
            # Get text from body
            body = soup.find('body')
            if body:
                main_content = body.get_text(separator=' ', strip=True)
            else:
                main_content = soup.get_text(separator=' ', strip=True)
        
        # Clean up text
        lines = (line.strip() for line in main_content.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Limit length for very large pages to avoid token issues
        if len(text) > 12000:
            logger.info(f"Trimming very long content from {url} ({len(text)} characters)")
            text = text[:12000] + "... [content truncated for length]"
            
        return text
        
    except requests.exceptions.Timeout:
        return f"Timeout while fetching content from {url}"
    except requests.exceptions.TooManyRedirects:
        return f"Too many redirects while fetching content from {url}"
    except requests.exceptions.RequestException as e:
        return f"Error fetching content: {str(e)}"
    except Exception as e:
        return f"Unexpected error fetching content: {str(e)}"
    


async def parallel_search(ctx: RunContext, queries: List[str]) -> List[List[ResearchDataPoint]]:
    """Perform searches in parallel for multiple queries using the search agent"""
    logger.info(f"Searching for {len(queries)} queries")
    
    async def process_query_with_retry(query: str, max_retries=5) -> List[ResearchDataPoint]:
        """Process a single query with robust retry logic"""
        for attempt in range(max_retries + 1):
            try:
                # Add delay between API calls that increases with each attempt
                delay = 2 + (attempt * 3) + random.uniform(0, 2)
                await asyncio.sleep(delay)
                
                logger.info(f"Processing query: {query} (attempt {attempt+1}/{max_retries+1})")
                
                # Have the agent directly perform the search and prepare results
                prompt = f"""
                Search for information about: "{query}"
                
                1. Search the web for this topic
                2. Extract and compile all relevant information
                3. Create comprehensive summaries of the findings
                4. Include FULL content in your data points
                5. Organize the information into a set of ResearchDataPoint objects
                
                Return a list of ResearchDataPoint objects with:
                - source: The URL or reference for the information
                - content: COMPLETE relevant content (not truncated)
                - summary: Detailed 3-5 paragraph summary of key information
                - relevance_score: A score between 0-1 indicating relevance
                """
                
                # Run the search agent to handle the entire process
                result = await search_agent.run(prompt, deps=ctx.deps)
                data_points = result.data if hasattr(result, 'data') else []
                
                logger.info(f"Generated {len(data_points)} data points for query: {query}")
                
                # Ensure we have at least one data point
                if not data_points:
                    data_points = [ResearchDataPoint(
                        source=f"https://example.com/search?q={query}",
                        content=f"No valid results for '{query}'",
                        summary=f"No information available for '{query}'",
                        relevance_score=0.1
                    )]
                
                return data_points
                
            except Exception as e:
                error_str = str(e)
                if "429" in error_str:
                    # Rate limited - use exponential backoff
                    wait_time = min(30, (2 ** attempt) + random.uniform(1, 5))
                    logger.warning(f"Rate limited (429). Retrying in {wait_time:.2f} seconds... (Attempt {attempt+1}/{max_retries+1})")
                    
                    if attempt < max_retries:
                        await asyncio.sleep(wait_time)
                        continue
                
                # Either not a 429 error or we've reached max retries
                logger.error(f"Error in search agent for query '{query}': {e}")
                return [ResearchDataPoint(
                    source=f"https://example.com/error?q={query}",
                    content=f"Error during search for '{query}'",
                    summary=f"Search error for '{query}'",
                    relevance_score=0.1
                )]
    
    # Process queries SEQUENTIALLY 
    all_results = []
    for query in queries:
        result = await process_query_with_retry(query)
        all_results.append(result)
        await asyncio.sleep(8 + random.uniform(0, 4))
    
    return all_results