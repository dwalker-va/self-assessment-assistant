# Self Assessment Assistant

A tool that helps gather evidence and generate content for self-assessments by analyzing your Jira and Confluence activity.

## Overview

This tool uses AI agents to:
1. Gather evidence of your work from Jira tickets and Confluence content
2. Analyze patterns and achievements across different data sources
3. Generate thoughtful self-assessment responses based on concrete evidence

## Features

### Evidence Gathering
- **Jira Integration**: Searches through your Jira tickets to identify:
  - Completed work and contributions
  - Project involvement
  - Task complexity and scope
  - Leadership behaviors

- **Confluence Integration**: Analyzes your Confluence content to find:
  - Knowledge sharing contributions
  - Technical documentation
  - Blog posts and articles
  - Team communications

### Output Organization
The tool organizes all gathered data and generated content in a structured output directory:
```
output/
├── evidence/              # Raw data gathered from tools
│   ├── confluence_content_*.md
│   └── jira_activity_*.md
└── assessment/           # Final generated assessments
    └── self_assessment_*.md
```

### Evidence Files
- Each evidence file contains detailed information about your work
- Includes direct links to Jira tickets and Confluence pages
- Preserves context with timestamps and metadata
- Formatted in Markdown for easy reading and reference

## Setup

1. Clone the repository
2. Create a virtual environment and install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

3. Set up your environment variables in `.env`:
```bash
# Required Jira settings
JIRA_SERVER=your-instance.atlassian.net
JIRA_EMAIL=your.email@company.com
JIRA_API_TOKEN=your-jira-api-token

# Required Confluence settings
CONFLUENCE_SERVER=your-instance.atlassian.net  # Optional if same as JIRA_SERVER
CONFLUENCE_EMAIL=your.email@company.com        # Optional if same as JIRA_EMAIL
CONFLUENCE_API_TOKEN=your-confluence-api-token # Optional if same as JIRA_API_TOKEN

# Optional: Specify additional Confluence spaces to search
CONFLUENCE_SPACE_KEYS=TEAM,PROJ               # Comma-separated list of space keys

# OpenAI settings
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL_NAME=gpt-4o                       # Optional, defaults to gpt-4o
```

## Usage

### Basic Usage
```bash
python self_assessment_assistant/main.py
```

This will:
1. Gather evidence from Jira and Confluence
2. Save detailed evidence files for reference
3. Generate a self-assessment based on the evidence
4. Save all output to the `output/` directory

### Using Evidence Files Directly
You can also use the tool just for evidence gathering:
1. Run the tool to collect evidence
2. Find detailed evidence files in `output/evidence/`
3. Use these files as reference for writing your own assessment

The evidence files contain:
- Links to all relevant tickets and pages
- Summaries of work completed
- Timestamps and context
- Organized by time period

## How It Works

1. **Evidence Gathering Agent**
   - Searches Jira for your tickets and contributions
   - Analyzes Confluence for your content and documentation
   - Organizes findings into detailed evidence files

2. **Assessment Writer Agent**
   - Reviews gathered evidence
   - Identifies patterns and achievements
   - Generates assessment responses based on concrete examples

3. **Output Organization**
   - Evidence is saved in Markdown format for easy reference
   - Final assessment is generated with links to supporting evidence
   - All output is timestamped and organized in the `output/` directory

## Tips for Best Results

1. **Confluence Space Configuration**
   - The tool always searches the R&D space (RD) by default
   - Add additional spaces in `CONFLUENCE_SPACE_KEYS` for broader coverage
   - Personal spaces are automatically included

2. **Time Periods**
   - Evidence is gathered by quarters for easy reference
   - Each evidence file is clearly labeled with its time period
   - Use the timestamped files to track changes over time

3. **Using the Evidence**
   - Review the evidence files before the final assessment
   - Use the gathered data to support your own writing
   - Reference specific examples from the evidence in your assessment

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
