# Agentic Deep Research System

A modular, end-to-end research agent framework that leverages multiple specialized agents to conduct deep web-based research and generate structured reports.

## Overview

The Agentic Deep Research System is designed to automate the process of researching topics on the web. It breaks down a research query into logical subtasks, collects relevant information from the web, and synthesizes the findings into a comprehensive, structured report.

The system uses a multi-agent architecture with specialized agents for different aspects of the research process, all coordinated by an orchestration agent. It leverages the Pydantic-ai framework for schema enforcement and validation across all components.

## System Architecture

The system consists of three primary agents:

1. **Query Analysis Agent**: Breaks down user research topics into structured sub-tasks, each with its own objective, search terms, and priority.

2. **Search & Data Collection Agent**: Conducts web searches for each subtask and extracts relevant data points from the search results.

3. **Orchestration Agent**: Manages the overall workflow and synthesizes the collected data into a comprehensive research report.

## Key Features

- **Modular Architecture**: Each agent is specialized for its specific task, allowing for easy updates and improvements.
- **Schema Enforcement**: Strict validation using Pydantic models ensures data integrity throughout the process.
- **Robust Error Handling**: Graceful degradation and fallback mechanisms ensure the system completes its task even when facing issues.
- **Parallel Processing**: The system conducts searches in parallel to optimize performance.
- **Rich Reporting**: Generates detailed reports in both human-readable text and structured JSON formats.

## Technical Details

### Tech Stack

- **Pydantic-ai**: For schema enforcement and agent interfaces
- **Groq API**: For LLM-based text processing and generation
- **BeautifulSoup**: For web scraping and content extraction
- **Asyncio**: For asynchronous processing

### Requirements

- Python 3.8 or higher
- A valid Groq API key

### Project Structure

```
agentic-deep-research/
├── agents/
│   ├── query_analysis_agent.py
│   ├── search_data_collection_agent.py
│   └── orchestration_agent.py
├── schemas/
│   └── research_report.py
├── reports/
│   └── [generated reports]
├── constants.py
├── main.py
├── requirements.txt
└── README.md
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/agentic-deep-research.git
cd agentic-deep-research
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
# Create a .env file with your API keys
echo "GROQ_API_KEY=your_groq_api_key" > .env
echo "GOOGLE_API_KEYY=your_google_api_key" > .env
echo "GOOGLE_CSE_IDY=your_google_cse_id" > .env
```

## Usage

Run the system with the following command:

```bash
python main.py
```

The system will prompt you to enter a research topic. After processing, it will save the generated report in both text and JSON formats in the `reports` directory.

## Example Output

The system generates human-readable text file with the following sections:
   - Research Topic
   - Research Objectives
   - Synthesis (the full research report)
   - References


## Customization

You can customize the system behavior by modifying constants in `constants.py`:

- `MAX_SEARCH_RESULTS`: Maximum number of search results to process
- `MIN_SUBTASKS` and `MAX_SUBTASKS`: Range of subtasks to generate
- `MIN_REPORT_WORDS`: Minimum word count for generated reports
- Model configurations for each agent


## Acknowledgements

- The project uses various open-source tools and libraries
- The implementation leverages LLM capabilities from Groq and other providers 