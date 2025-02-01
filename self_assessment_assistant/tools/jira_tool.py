"""
JiraTool: A custom tool for CrewAI agents to interact with Jira.
"""

from typing import List, Any, Callable, Optional
from langchain.tools import BaseTool
from jira import JIRA
import os
from datetime import datetime, timedelta
from pydantic import Field, BaseModel

class JiraSearchSchema(BaseModel):
    """Schema for the Jira search tool arguments."""
    time_frame: str = Field(
        description="The time period to search (e.g., '2024', '2024-Q1', 'last 3 months')"
    )
    user: Optional[str] = Field(
        default=None,
        description="The username to search for. If not provided, uses the authenticated user."
    )

class JiraTool(BaseTool):
    name: str = "jira_search"
    description: str = """
    Search for Jira issues assigned to a specific user within a given time frame.
    Useful for finding work items, achievements, and contributions made by a user.
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
        
        self.jira = JIRA(
            server=jira_server,
            basic_auth=(jira_email, jira_api_token)
        )
        self.current_user = jira_email

    def _run(self, time_frame: str = None, user: str = None) -> str:
        """
        Required method for LangChain's BaseTool.
        """
        if time_frame is None:
            time_frame = str(self.target_year)
        return self._search_jira(time_frame, user)

    @property
    def func(self) -> Callable:
        """
        Required property for CrewAI's tool interface.
        Returns a callable that will be used by CrewAI to execute the tool.
        """
        return self._search_jira

    def _search_jira(self, time_frame: str = None, user: str = None) -> str:
        """
        Search for Jira issues assigned to a user within the specified time frame.
        
        Args:
            time_frame (str): The time period to search (e.g., "2023", "2023-Q1", "last 3 months")
            user (str, optional): The username to search for. If None, uses the authenticated user.
            
        Returns:
            str: A formatted string containing the found issues and their details.
        """
        if time_frame is None:
            time_frame = str(self.target_year)

        # Convert time_frame to JQL date format
        start_date, end_date = self._parse_time_frame(time_frame)
        
        # Use current user if none specified
        search_user = user if user else self.current_user
        
        # Construct JQL query
        jql = f"""
            assignee = '{search_user}' 
            AND created >= '{start_date}' 
            AND created <= '{end_date}' 
            ORDER BY created DESC
        """
        
        # Search for issues
        issues = self.jira.search_issues(jql, maxResults=100)
        
        # Format results
        if not issues:
            return f"No issues found for user {search_user} in the specified time frame."
        
        result = f"Found {len(issues)} issues for {search_user} between {start_date} and {end_date}:\n\n"
        for issue in issues:
            result += f"- [{issue.key}] {issue.fields.summary}\n"
            result += f"  Status: {issue.fields.status.name}\n"
            result += f"  Created: {issue.fields.created[:10]}\n"
            if hasattr(issue.fields, 'resolution') and issue.fields.resolution:
                result += f"  Resolution: {issue.fields.resolution.name}\n"
            result += "\n"
        
        return result

    def _parse_time_frame(self, time_frame: str) -> tuple[str, str]:
        """
        Convert a human-readable time frame into start and end dates for JQL.
        
        Args:
            time_frame (str): Time frame specification (e.g., "2023", "2023-Q1", "last 3 months")
            
        Returns:
            tuple[str, str]: Start and end dates in YYYY-MM-DD format
        """
        today = datetime.now()
        target_year = self.target_year
        
        if time_frame == str(target_year):
            return f"{target_year}-01-01", f"{target_year}-12-31"
        
        if time_frame.lower().startswith(f"{target_year}-q"):
            quarter = int(time_frame[-1])
            if not 1 <= quarter <= 4:
                return f"{target_year}-01-01", f"{target_year}-12-31"
                
            # Calculate start date
            start_month = (quarter - 1) * 3 + 1
            start_date = datetime(target_year, start_month, 1)
            
            # Calculate end date (start of next quarter minus 1 day)
            if quarter < 4:
                end_date = datetime(target_year, start_month + 3, 1) - timedelta(days=1)
            else:
                end_date = datetime(target_year, 12, 31)
            
            return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
        
        if time_frame.lower().startswith("last"):
            parts = time_frame.lower().split()
            if len(parts) == 3 and parts[2] == "months":
                months = int(parts[1])
                start_date = today - timedelta(days=months * 30)  # Approximate
                return start_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
        
        # Default to target year if format not recognized
        return f"{target_year}-01-01", f"{target_year}-12-31" 