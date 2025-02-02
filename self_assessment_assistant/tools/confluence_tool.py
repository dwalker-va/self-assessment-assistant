"""
ConfluenceTool: A custom tool for CrewAI agents to interact with Confluence.
"""

from typing import List, Any, Callable, Optional
from langchain.tools import BaseTool
from atlassian import Confluence
import os
import logging
from datetime import datetime, timedelta
from pydantic import Field, BaseModel
import re

class ConfluenceSearchSchema(BaseModel):
    """Schema for the Confluence search tool arguments."""
    time_frame: str = Field(
        description="The time period to search (e.g., '2024', '2024-Q1', 'last 3 months')"
    )
    user: Optional[str] = Field(
        default=None,
        description="The username to search for. If not provided, uses the authenticated user."
    )

class ConfluenceTool(BaseTool):
    name: str = "confluence_search"
    description: str = """
    Search for Confluence pages and blog posts authored by a user within a given time frame.
    Useful for finding documentation, knowledge sharing, and technical contributions.
    The tool will automatically determine the current user if none is specified.
    Searches in the user's personal space, the R&D space (RD), and any additional spaces specified in CONFLUENCE_SPACE_KEYS.
    """
    
    args_schema: type[BaseModel] = ConfluenceSearchSchema
    
    # Declare fields that will be set in __init__
    confluence: Any = Field(default=None, exclude=True)
    current_user: str = Field(default=None)
    target_year: int = Field(default=None)
    space_keys: List[str] = Field(default_factory=list)

    def __init__(self, **data):
        super().__init__(**data)
        # Initialize Confluence client using environment variables
        confluence_server = os.getenv('CONFLUENCE_SERVER', os.getenv('JIRA_SERVER'))  # Fallback to JIRA_SERVER
        confluence_email = os.getenv('CONFLUENCE_EMAIL', os.getenv('JIRA_EMAIL'))  # Fallback to JIRA_EMAIL
        confluence_api_token = os.getenv('CONFLUENCE_API_TOKEN', os.getenv('JIRA_API_TOKEN'))  # Fallback to JIRA_API_TOKEN
        self.target_year = int(os.getenv('TARGET_YEAR', datetime.now().year))
        
        if not all([confluence_server, confluence_email, confluence_api_token]):
            raise ValueError("Missing required Confluence credentials in environment variables")
        
        # Always include RD space and any additional spaces from environment
        self.space_keys = ['RD']  # R&D space is always included
        space_keys_str = os.getenv('CONFLUENCE_SPACE_KEYS', '')
        if space_keys_str:
            # Add additional spaces from env var, avoiding duplicates
            additional_spaces = [key.strip() for key in space_keys_str.split(',')]
            self.space_keys.extend([key for key in additional_spaces if key != 'RD'])
            logging.info(f"Configured to search in spaces: RD (default), {', '.join(key for key in self.space_keys if key != 'RD')}")
        else:
            logging.info("No additional CONFLUENCE_SPACE_KEYS provided. Will search in RD space and personal space.")
        
        # Ensure the server URL is properly formatted
        if not confluence_server.startswith(('http://', 'https://')):
            confluence_server = f'https://{confluence_server}'
        
        # Ensure we're using the /wiki endpoint for cloud instances
        if not confluence_server.endswith('/wiki'):
            confluence_server = f"{confluence_server.rstrip('/')}/wiki"
        
        self.confluence = Confluence(
            url=confluence_server,
            username=confluence_email,
            password=confluence_api_token,
            cloud=True  # Set to True for cloud instances
        )
        self.current_user = confluence_email

    def _run(self, time_frame: str = None, user: str = None) -> str:
        """
        Required method for LangChain's BaseTool.
        """
        if time_frame is None:
            time_frame = str(self.target_year)
        return self._search_confluence(time_frame, user)

    @property
    def func(self) -> Callable:
        """
        Required property for CrewAI's tool interface.
        Returns a callable that will be used by CrewAI to execute the tool.
        """
        return self._search_confluence

    def _search_confluence(self, time_frame: str = None, user: str = None) -> str:
        """
        Search for Confluence content created by a user within the specified time frame.
        
        Args:
            time_frame (str): The time period to search (e.g., "2023", "2023-Q1", "last 3 months")
            user (str, optional): The username to search for. If None, uses the authenticated user.
            
        Returns:
            str: A formatted string containing the found pages and their details.
        """
        if time_frame is None:
            time_frame = str(self.target_year)

        # Convert time_frame to date range
        start_date, end_date = self._parse_time_frame(time_frame)
        
        # Use current user if none specified
        search_user = user if user else self.current_user
        
        content_items = []
        
        try:
            # Try to get space info first to verify access
            spaces_to_search = set(self.space_keys)  # Start with configured spaces
            accessible_spaces = set()
            
            logging.info(f"Verifying access to {len(spaces_to_search)} spaces...")
            for space_key in spaces_to_search:
                try:
                    space_info = self.confluence.get_space(space_key, expand='permissions')
                    if space_info:
                        accessible_spaces.add(space_key)
                        space_name = space_info.get('name', 'Unknown')
                        logging.info(f"Have access to space {space_key} ({space_name})")
                except Exception as e:
                    if "permission" in str(e).lower():
                        logging.warning(f"No access to space {space_key}, skipping")
                    else:
                        logging.warning(f"Error checking space {space_key}: {str(e)}")
            
            if not accessible_spaces:
                logging.warning("No accessible spaces found!")
                return f"No accessible Confluence spaces found for user {search_user}"
            
            logging.info(f"Will search in {len(accessible_spaces)} accessible spaces: {', '.join(accessible_spaces)}")
            
            # Try different search approaches
            
            # 1. Try CQL search first (fastest method)
            logging.info("Attempting CQL search...")
            try:
                # Build space clause if we have spaces to search
                space_conditions = []
                for key in accessible_spaces:
                    space_conditions.append(f'space = "{key}"')
                space_clause = f"({' OR '.join(space_conditions)})" if space_conditions else ""
                
                # Build creator clause using currentUser() function
                creator_clause = 'creator = currentUser()'
                
                # Build date clause with time component (using ISO 8601 format)
                date_clause = f'created >= "{start_date} 00:00" AND created <= "{end_date} 23:59"'
                
                # Add type clause to filter for pages and blog posts only
                type_clause = 'type in ("page", "blogpost")'
                
                # Combine clauses
                cql_parts = [creator_clause, date_clause, type_clause]
                if space_clause:
                    cql_parts.append(space_clause)
                
                cql = " AND ".join(cql_parts)
                logging.info(f"CQL Query: {cql}")
                
                results = self.confluence.cql(cql, limit=100, expand='space,history,version,type')
                if results and isinstance(results, dict) and results.get('results'):
                    content_items.extend(results['results'])
                    # Log content types for debugging
                    type_counts = {}
                    for item in results['results']:
                        # Get type from content object
                        content_type = (item.get('content', {}).get('type', 'Unknown')).title()
                        type_counts[content_type] = type_counts.get(content_type, 0) + 1
                    logging.info(f"Content type distribution: {type_counts}")
                    logging.info(f"CQL search found {len(results['results'])} items")
                else:
                    logging.info("CQL search found no results")
                    # Log the full response for debugging
                    logging.info(f"CQL response: {results}")
            except Exception as e:
                logging.warning(f"CQL search failed: {str(e)}")
            
            # 2. Try content search if CQL didn't find anything
            if not content_items:
                logging.info("Trying space-by-space content search...")
                try:
                    for space_key in accessible_spaces:
                        try:
                            logging.info(f"Searching space: {space_key}")
                            pages = self.confluence.get_all_pages_from_space(
                                space=space_key,
                                start=0,
                                limit=100,
                                status='current',
                                expand='version,history,space'
                            )
                            
                            if isinstance(pages, list):
                                # Filter by date and creator
                                space_matches = []
                                for page in pages:
                                    if not isinstance(page, dict):
                                        continue
                                    
                                    creator = (page.get('history', {}).get('createdBy', {}).get('email') or 
                                             page.get('history', {}).get('createdBy', {}).get('username', ''))
                                    created_date = (page.get('history', {}).get('createdDate', '') or 
                                                  page.get('version', {}).get('when', ''))[:10]
                                    
                                    if (creator == search_user and 
                                        start_date <= created_date <= end_date):
                                        space_matches.append(page)
                                
                                if space_matches:
                                    content_items.extend(space_matches)
                                    logging.info(f"Found {len(space_matches)} matching pages in space {space_key}")
                                else:
                                    logging.info(f"No matching content found in space {space_key}")
                            
                        except Exception as e:
                            logging.warning(f"Error searching space {space_key}: {str(e)}")
                except Exception as e:
                    logging.warning(f"Content search failed: {str(e)}")

            # Process results
            if not content_items:
                no_results_msg = f"No Confluence content found for user {search_user} in the specified time frame. Searched between {start_date} and {end_date}"
                logging.info(no_results_msg)
                return no_results_msg
            
            logging.info(f"Processing {len(content_items)} found items...")
            output = f"Found {len(content_items)} Confluence items for {search_user} between {start_date} and {end_date}:\n\n"
            
            for item in content_items:
                try:
                    # Get content type from content object
                    content_type = (item.get('content', {}).get('type', 'Unknown')).title()
                    logging.debug(f"Processing item of type: {content_type}")
                    
                    # Get space info from resultGlobalContainer
                    space_info = item.get('resultGlobalContainer', {})
                    space_name = space_info.get('title', 'Unknown')
                    # Extract space key from displayUrl
                    space_url = space_info.get('displayUrl', '')
                    space_key = space_url.split('/')[-1] if space_url else 'Unknown'
                    
                    # Fallback to expandable space if needed
                    if space_key == 'Unknown' and 'content' in item:
                        space_path = item['content'].get('_expandable', {}).get('space', '')
                        if space_path:
                            space_key = space_path.split('/')[-1]
                    
                    title = item.get('content', {}).get('title', 'Untitled')
                    created_date = item.get('lastModified', '')[:10]  # Use lastModified from the root
                    
                    output += f"- [{content_type}] {title}\n"
                    output += f"  Created: {created_date}\n"
                    output += f"  Space: {space_key} ({space_name})\n"
                    
                    # Add excerpt if available
                    if 'excerpt' in item and item['excerpt']:
                        excerpt = item['excerpt'][:200]  # Take first 200 chars
                        output += f"  Preview: {excerpt}...\n"
                    
                    output += "\n"
                except Exception as e:
                    error_msg = f"Error retrieving content details: {str(e)}"
                    output += f"  {error_msg}\n\n"
                    logging.warning(error_msg)
            
            return output
            
        except Exception as e:
            error_msg = f"Error searching Confluence: {str(e)}"
            logging.error(error_msg)
            return error_msg

    def _parse_time_frame(self, time_frame: str) -> tuple[str, str]:
        """
        Convert a human-readable time frame into start and end dates for CQL.
        
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