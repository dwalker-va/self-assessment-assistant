"""
JiraTool: A custom tool for CrewAI agents to interact with Jira.
"""

from typing import List, Any, Callable, Optional
import os
import logging
from datetime import datetime, timedelta
from pydantic import Field, BaseModel
from atlassian import Jira
from .base_tool import BaseEvidenceTool

class JiraSearchSchema(BaseModel):
    """Schema for the Jira search tool arguments."""
    time_frame: str = Field(
        description="The time period to search (e.g., '2024', '2024-Q1', 'last 3 months')"
    )
    user: Optional[str] = Field(
        default=None,
        description="The username to search for. If not provided, uses the authenticated user."
    )

class JiraTool(BaseEvidenceTool):
    name: str = "jira_search"
    description: str = """
    Search for Jira issues, comments, and work logs for a user within a given time frame.
    Useful for finding technical contributions, project work, and collaboration.
    The tool will automatically determine the current user if none is specified.
    """
    
    args_schema: type[BaseModel] = JiraSearchSchema
    
    # Declare fields that will be set in __init__
    jira: Any = Field(default=None, exclude=True)
    current_user: str = Field(default=None)
    target_year: int = Field(default=None)

    def __init__(self, **data):
        super().__init__(**data)
        # Initialize Jira client using environment variables
        jira_server = os.getenv('JIRA_SERVER')
        jira_email = os.getenv('JIRA_EMAIL')
        jira_api_token = os.getenv('JIRA_API_TOKEN')
        self.target_year = int(os.getenv('TARGET_YEAR', datetime.now().year))
        
        if not all([jira_server, jira_email, jira_api_token]):
            raise ValueError("Missing required Jira credentials in environment variables")
        
        # Ensure the server URL is properly formatted
        if not jira_server.startswith(('http://', 'https://')):
            jira_server = f'https://{jira_server}'
        
        self.jira = Jira(
            url=jira_server,
            username=jira_email,
            password=jira_api_token,
            cloud=True
        )
        self.current_user = jira_email

    def _run(self, time_frame: str = None, user: str = None) -> str:
        """Required method for LangChain's BaseTool."""
        if time_frame is None:
            time_frame = str(self.target_year)
        return self._search_jira(time_frame, user)

    @property
    def func(self) -> Callable:
        """Required property for CrewAI's tool interface."""
        return self._search_jira

    def _save_search_results(self, time_frame: str, search_user: str, issues: list) -> str:
        """Save Jira search results to a file and return the formatted output."""
        if not issues:
            return f"No Jira activity found for user {search_user} in {time_frame}"
        
        # Create filename based on time frame and user
        safe_timeframe = time_frame.replace('/', '-')
        filename = f"jira_activity_{safe_timeframe}_{search_user.split('@')[0]}.md"
        
        # Format detailed output
        output = f"# Jira Activity for {search_user}\n"
        output += f"Time frame: {time_frame}\n"
        output += f"Found {len(issues)} items\n\n"
        
        for issue in issues:
            try:
                key = issue.get('key', 'Unknown')
                summary = issue.get('fields', {}).get('summary', 'No summary')
                status = issue.get('fields', {}).get('status', {}).get('name', 'Unknown')
                issue_type = issue.get('fields', {}).get('issuetype', {}).get('name', 'Unknown')
                project = issue.get('fields', {}).get('project', {}).get('name', 'Unknown')
                created = issue.get('fields', {}).get('created', '')[:10]
                
                # Get the URL for the issue
                issue_url = f"{self.jira.url}/browse/{key}"
                
                output += f"## [{key}] {summary}\n"
                output += f"- **Type:** {issue_type}\n"
                output += f"- **Project:** {project}\n"
                output += f"- **Status:** {status}\n"
                output += f"- **Created:** {created}\n"
                output += f"- **URL:** {issue_url}\n"
                
                # Add description if available
                description = issue.get('fields', {}).get('description')
                if description:
                    output += f"\n### Description\n{description[:200]}...\n"
                
                output += "\n---\n\n"
                
            except Exception as e:
                error_msg = f"Error processing issue: {str(e)}"
                output += f"Error: {error_msg}\n\n"
                logging.warning(error_msg)
        
        # Save the detailed output using the base class method
        try:
            filepath = self.save_evidence(output, filename)
            
            # Return a shorter version for the tool output
            summary_output = f"Found {len(issues)} Jira items for {search_user} in {time_frame}.\n"
            summary_output += f"Full results saved to: {filepath}\n\n"
            summary_output += "Summary of items:\n\n"
            
            for issue in issues:
                try:
                    key = issue.get('key', 'Unknown')
                    summary = issue.get('fields', {}).get('summary', 'No summary')
                    status = issue.get('fields', {}).get('status', {}).get('name', 'Unknown')
                    project = issue.get('fields', {}).get('project', {}).get('name', 'Unknown')
                    
                    summary_output += f"- [{key}] {summary}\n"
                    summary_output += f"  Project: {project}\n"
                    summary_output += f"  Status: {status}\n\n"
                except Exception as e:
                    summary_output += f"  Error processing issue: {str(e)}\n\n"
            
            return summary_output
            
        except Exception as e:
            error_msg = f"Failed to save results: {str(e)}"
            logging.error(error_msg)
            return error_msg

    def _search_jira(self, time_frame: str = None, user: str = None) -> str:
        """Search for Jira activity and save results to file."""
        if time_frame is None:
            time_frame = str(self.target_year)
        
        # Convert time_frame to date range
        start_date, end_date = self._parse_time_frame(time_frame)
        search_user = user if user else self.current_user
        
        try:
            # Build JQL query
            jql = f'assignee = "{search_user}" AND created >= "{start_date}" AND created <= "{end_date}"'
            logging.info(f"JQL Query: {jql}")
            
            # Search for issues
            issues = self.jira.jql(jql)
            if not isinstance(issues, dict) or 'issues' not in issues:
                return f"No Jira activity found for user {search_user} in the specified time frame"
            
            return self._save_search_results(time_frame, search_user, issues['issues'])
            
        except Exception as e:
            error_msg = f"Error searching Jira: {str(e)}"
            logging.error(error_msg)
            return error_msg

    def _parse_time_frame(self, time_frame: str) -> tuple[str, str]:
        """Convert a human-readable time frame into start and end dates for JQL."""
        today = datetime.now()
        target_year = self.target_year
        
        if time_frame == str(target_year):
            return f"{target_year}-01-01", f"{target_year}-12-31"
        
        if time_frame.lower().startswith(f"{target_year}-q"):
            quarter = int(time_frame[-1])
            if not 1 <= quarter <= 4:
                return f"{target_year}-01-01", f"{target_year}-12-31"
                
            start_month = (quarter - 1) * 3 + 1
            start_date = datetime(target_year, start_month, 1)
            
            if quarter < 4:
                end_date = datetime(target_year, start_month + 3, 1) - timedelta(days=1)
            else:
                end_date = datetime(target_year, 12, 31)
            
            return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
        
        if time_frame.lower().startswith("last"):
            parts = time_frame.lower().split()
            if len(parts) == 3 and parts[2] == "months":
                months = int(parts[1])
                start_date = today - timedelta(days=months * 30)
                return start_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
        
        return f"{target_year}-01-01", f"{target_year}-12-31" 