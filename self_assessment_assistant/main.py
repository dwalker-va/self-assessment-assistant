#!/usr/bin/env python3
"""
Main entry point for self_assessment_assistant.
This script uses CrewAI to coordinate agents that help generate a self-assessment
by gathering evidence and answering questions.
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from tools.jira_tool import JiraTool
from tools.confluence_tool import ConfluenceTool
from typing import Any

# Configure logging
def setup_logging():
    """Configure logging to write to both file and console."""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"crew_execution_{timestamp}.log")
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # This will maintain console output
        ]
    )
    return log_file

def save_output(content: Any) -> str:
    """Save the crew's output to a file.
    
    Args:
        content: The content to save (can be str or CrewOutput)
        
    Returns:
        str: Path to the saved file
    """
    # Create output directory structure
    output_dir = os.path.join(os.getcwd(), 'output', 'assessment')
    os.makedirs(output_dir, exist_ok=True)
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"self_assessment_{timestamp}.md"
    filepath = os.path.join(output_dir, filename)
    
    try:
        # Convert CrewOutput to string if needed
        content_str = str(content) if content is not None else ""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content_str)
        logging.info(f"Saved assessment to {filepath}")
        return filepath
    except Exception as e:
        error_msg = f"Failed to save assessment to file: {str(e)}"
        logging.error(error_msg)
        raise

# Load environment variables from .env file
load_dotenv()

def load_self_assessment(file_path: str) -> str:
    """Load the self assessment document from file."""
    with open(file_path, "r") as f:
        return f.read()

def main():
    # Setup logging
    log_file = setup_logging()
    logging.info("Starting self assessment assistant...")

    # Load the assessment template
    assessment_file = "assessment_template.txt"
    logging.info("Loading self assessment document...")
    assessment_text = load_self_assessment(assessment_file)

    # Initialize tools
    jira_tool = JiraTool()
    confluence_tool = ConfluenceTool()

    # Configure the LLM
    llm = ChatOpenAI(
        model=os.getenv('OPENAI_MODEL_NAME', 'gpt-4o'),
        temperature=0.7
    )

    # Create the evidence gathering agent
    evidence_agent = Agent(
        role='Evidence Gatherer',
        goal='Collect and analyze work evidence from Jira tickets and Confluence content',
        backstory="""You are an expert at analyzing work history through various data sources.
        Your strength lies in identifying patterns of achievement and impact from both:
        1. Jira tickets showing completed work and contributions
        2. Confluence content demonstrating knowledge sharing and technical expertise
        
        You know how to extract meaningful narratives by looking at:
        1. The types and complexity of work completed
        2. Documentation and knowledge sharing contributions
        3. Patterns of collaboration and leadership
        4. Technical depth and expertise in content
        You focus on concrete, verifiable information from all sources.""",
        verbose=True,
        allow_delegation=False,
        tools=[jira_tool, confluence_tool],
        llm=llm
    )

    # Create the question answering agent
    qa_agent = Agent(
        role='Assessment Writer',
        goal='Generate thoughtful and well-supported answers based on concrete evidence',
        backstory="""You are a skilled writer with expertise in performance reviews and self-assessments.
        You excel at crafting clear, specific responses that highlight achievements and growth areas.
        You understand that while metrics and KPIs are valuable when available, many impactful contributions
        can be demonstrated through:
        1. The nature, scope, and consistency of work completed (from Jira)
        2. Knowledge sharing and documentation efforts (from Confluence)
        3. Technical depth and expertise shown in written content
        
        You focus on telling compelling stories about impact through:
        1. Patterns of successful project completion
        2. Examples of complex problem-solving
        3. Demonstrations of leadership behaviors
        4. Knowledge sharing and mentorship
        You maintain honesty and authenticity by sticking to concrete evidence.""",
        verbose=True,
        allow_delegation=False,
        llm=llm
    )

    # Define the evidence gathering task
    evidence_task = Task(
        description="""Gather and analyze evidence from both Jira and Confluence to identify key achievements and patterns.
        For each quarter of the target year:
        1. Search Jira tickets to identify:
           - Types and complexity of work completed
           - Patterns in task completion and approach
           - Examples of leadership behaviors
           - Notable achievements and contributions
        
        2. Search Confluence content to identify:
           - Knowledge sharing and documentation efforts
           - Technical expertise and depth
           - Contributions to team and organizational knowledge
           - Evidence of mentorship and leadership
        
        Use both the jira_search and confluence_search tools to gather comprehensive evidence.
        Analyze all sources to identify:
        - The scope and complexity of work
        - Patterns of behavior and approach
        - Examples of leadership principles in action
        - Knowledge sharing and technical expertise
        - Concrete achievements and contributions""",
        expected_output="""A detailed report containing:
        1. Key achievements and completed work from each quarter, supported by specific examples
        2. Examples of leadership behaviors demonstrated through actual work
        3. Knowledge sharing and documentation contributions
        4. Patterns and themes that show consistent positive impact
        The report should focus on concrete, verifiable information from all sources.""",
        agent=evidence_agent
    )

    # Define the answer generation task
    answer_task = Task(
        description=f"""Using the gathered evidence from both Jira and Confluence, generate comprehensive answers for the self-assessment questions.
        The assessment template is as follows:
        
        {assessment_text}
        
        When writing answers:
        1. Focus on concrete achievements and completed work from all sources
        2. Highlight both technical contributions and knowledge sharing
        3. Use specific examples to illustrate leadership behaviors
        4. Maintain authenticity by sticking to verifiable information
        5. When metrics or KPIs aren't available, focus instead on:
           - The nature, scope, and quality of work completed
           - Knowledge sharing and documentation efforts
           - Technical depth and expertise demonstrated
        
        Remember that impactful contributions can be demonstrated through:
        - The complexity and scope of completed work
        - Patterns of successful project delivery
        - Documentation and knowledge sharing
        - Examples of problem-solving and leadership
        - Consistent themes in work quality""",
        expected_output="""A complete self-assessment document with:
        1. Thoughtful answers grounded in concrete evidence from all sources
        2. Specific examples of achievements, leadership, and knowledge sharing
        3. Focus on verifiable accomplishments and patterns
        4. Professional and authentic tone throughout
        The answers should present achievements positively while maintaining credibility through concrete evidence.""",
        agent=qa_agent
    )

    # Create the crew with a sequential process
    crew = Crew(
        agents=[evidence_agent, qa_agent],
        tasks=[evidence_task, answer_task],
        process=Process.sequential,
        verbose=True,
        function_calling="auto"
    )

    # Run the crew
    result = crew.kickoff()
    
    # Save the output to a file
    try:
        output_file = save_output(result)
        logging.info(f"Assessment complete! Results saved to: {output_file}")
        print(f"\nAssessment complete! Results saved to: {output_file}")
    except Exception as e:
        logging.error(f"Failed to save assessment: {e}")
        print("\nFailed to save results to file, but here they are:")
        print(result)
    
    return result

if __name__ == "__main__":
    main() 