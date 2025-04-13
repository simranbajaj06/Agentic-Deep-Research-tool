"""
Constants for the Agentic Deep Research System.
"""

# Search engine URL
SEARCH_URL = "https://html.duckduckgo.com/html"

# Model configurations
DEFAULT_MODEL = "groq:llama-3.1-8b-instant"
ANALYSIS_MODEL = "groq:llama-3.3-70b-versatile"
SEARCH_MODEL = "groq:llama-3.3-70b-versatile"

# Research configuration
MAX_SEARCH_RESULTS = 3
MIN_SUBTASKS = 3
MAX_SUBTASKS = 5
MIN_REPORT_WORDS = 1000
REPORT_DIR = "reports"