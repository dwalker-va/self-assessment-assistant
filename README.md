# Self Assessment Assistant

An AI assistant built to help with self assessments by analyzing your Jira history and generating thoughtful, evidence-based responses.

## Features

- Analyzes Jira tickets to identify key achievements and patterns
- Generates comprehensive self-assessment responses based on concrete evidence
- Focuses on actual work completed and demonstrable impact
- Maintains professional tone while staying grounded in verifiable accomplishments

## Prerequisites

- Python 3.8 or higher
- A Jira account with API access
- An OpenAI API key

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/self-assessment-assistant.git
   cd self-assessment-assistant
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Environment Setup

Create a `.env` file in the root directory with the following variables:

```env
# Jira Configuration
JIRA_SERVER=your_jira_server_url
JIRA_EMAIL=your_jira_email
JIRA_API_TOKEN=your_jira_api_token

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL_NAME=gpt-4o  # or your preferred model

# Target Year for Assessment
TARGET_YEAR=2024  # The year you're writing the assessment for
```

### Environment Variables Explained

- **Jira Configuration**
  - `JIRA_SERVER`: Your Jira instance URL (e.g., "https://your-company.atlassian.net")
  - `JIRA_EMAIL`: Your Jira account email
  - `JIRA_API_TOKEN`: Your Jira API token (can be generated in Atlassian account settings)

- **OpenAI Configuration**
  - `OPENAI_API_KEY`: Your OpenAI API key
  - `OPENAI_MODEL_NAME`: The OpenAI model to use (default: gpt-4o)

- **Assessment Configuration**
  - `TARGET_YEAR`: The year for which you're writing the self-assessment

### How to Get API Keys

1. **Jira API Token**:
   - Go to https://id.atlassian.com/manage-profile/security/api-tokens
   - Click "Create API token"
   - Give it a name and copy the token

2. **OpenAI API Key**:
   - Visit https://platform.openai.com/api-keys
   - Create a new API key
   - Copy the key (it will only be shown once)

## Usage

1. Ensure your virtual environment is activated:
   ```bash
   source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
   ```

2. Run the assistant:
   ```bash
   python self_assessment_assistant/main.py
   ```

The program will:
1. Search through your Jira tickets for the specified year
2. Analyze the tickets to identify achievements and patterns
3. Generate thoughtful responses for each self-assessment question
4. Output the results to the console
5. Save detailed logs to the `logs` directory

## Output

- The generated self-assessment answers will be printed to the console
- Detailed execution logs will be saved in the `logs` directory with timestamps
- Each run creates a new log file for review

## Notes

- The assistant focuses on concrete, verifiable information from your Jira tickets
- It maintains authenticity by sticking to actual work completed
- The generated responses aim to present your achievements positively while remaining grounded in evidence

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
