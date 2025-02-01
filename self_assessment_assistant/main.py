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

    # Configure the LLM
    llm = ChatOpenAI(
        model=os.getenv('OPENAI_MODEL_NAME', 'gpt-4o'),
        temperature=0.7
    )

    # Create the evidence gathering agent
    evidence_agent = Agent(
        role='Evidence Gatherer',
        goal='Collect and analyze Jira tickets to identify key achievements and contributions',
        backstory="""You are an expert at analyzing work history through Jira tickets.
        Your strength lies in identifying patterns of achievement and impact from ticket data.
        You know how to extract meaningful narratives from Jira tickets by looking at:
        1. The types of work completed
        2. The complexity and scope of tasks
        3. Patterns of collaboration and leadership
        4. Consistent themes in the work
        You focus on concrete, verifiable information from the tickets themselves.""",
        verbose=True,
        allow_delegation=False,
        tools=[jira_tool],
        llm=llm
    )

    # Create the question answering agent
    qa_agent = Agent(
        role='Assessment Writer',
        goal='Generate thoughtful and well-supported answers based on concrete Jira evidence',
        backstory="""You are a skilled writer with expertise in performance reviews and self-assessments.
        You excel at crafting clear, specific responses that highlight achievements and growth areas.
        You understand that while metrics and KPIs are valuable when available, many impactful contributions
        can be demonstrated through the nature, scope, and consistency of work completed.
        You focus on telling compelling stories about impact through:
        1. Patterns of successful project completion
        2. Examples of complex problem-solving
        3. Demonstrations of leadership behaviors
        4. Consistent themes in work quality and approach
        You maintain honesty and authenticity by sticking to concrete evidence.""",
        verbose=True,
        allow_delegation=False,
        llm=llm
    )

    # Define the evidence gathering task
    evidence_task = Task(
        description="""Gather and analyze Jira tickets to identify key achievements and patterns.
        For each quarter of the target year, search for and analyze the user's Jira tickets.
        Focus on collecting information about:
        1. Types and complexity of work completed
        2. Patterns in task completion and approach
        3. Examples of leadership behaviors
        4. Notable achievements and contributions
        
        Use the jira_search tool to find tickets for each quarter.
        Analyze the tickets to identify:
        - The scope and complexity of work
        - Patterns of behavior and approach
        - Examples of leadership principles in action
        - Concrete achievements and contributions""",
        expected_output="""A detailed report containing:
        1. Key achievements and completed work from each quarter, supported by specific Jira tickets
        2. Examples of leadership behaviors demonstrated through actual work
        3. Patterns and themes in the work that show consistent positive impact
        The report should focus on concrete, verifiable information from the tickets.""",
        agent=evidence_agent
    )

    # Define the answer generation task
    answer_task = Task(
        description=f"""Using the gathered Jira evidence, generate comprehensive answers for the self-assessment questions.
        The assessment template is as follows:
        
        {assessment_text}
        
        When writing answers:
        1. Focus on concrete achievements and completed work from the Jira evidence
        2. Highlight patterns and themes that demonstrate consistent positive impact
        3. Use specific examples to illustrate leadership behaviors
        4. Maintain authenticity by sticking to verifiable information
        5. When metrics or KPIs aren't available in the evidence, focus instead on the nature,
           scope, and quality of work completed
        
        Remember that impactful contributions can be demonstrated through:
        - The complexity and scope of completed work
        - Patterns of successful project delivery
        - Examples of problem-solving and leadership
        - Consistent themes in work quality""",
        expected_output="""A complete self-assessment document with:
        1. Thoughtful answers grounded in concrete Jira evidence
        2. Specific examples of achievements and leadership behaviors
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
        verbose=True
    )

    # Kick off the process
    logging.info("Starting the self-assessment process...")
    result = crew.kickoff()
    
    # Log the final result
    logging.info("Self assessment process completed")
    logging.info(f"Results have been written to: {log_file}")
    
    print("\nGenerated Self Assessment Answers:")
    print(result)

if __name__ == "__main__":
    main() 