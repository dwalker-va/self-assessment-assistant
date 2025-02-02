"""
Base tool class with shared functionality for file output handling.
"""

import os
import logging
from langchain.tools import BaseTool
from datetime import datetime
from pydantic import Field

class BaseEvidenceTool(BaseTool):
    """Base class for evidence gathering tools that save results to files."""
    
    # Define output directories as fields
    base_output_dir: str = Field(default="", exclude=True)
    evidence_dir: str = Field(default="", exclude=True)
    assessment_dir: str = Field(default="", exclude=True)
    
    def __init__(self, **data):
        super().__init__(**data)
        # Set up output directories
        self.base_output_dir = os.path.join(os.getcwd(), 'output')
        self.evidence_dir = os.path.join(self.base_output_dir, 'evidence')
        self.assessment_dir = os.path.join(self.base_output_dir, 'assessment')
        
        # Create all required directories
        os.makedirs(self.evidence_dir, exist_ok=True)
        os.makedirs(self.assessment_dir, exist_ok=True)
    
    def save_evidence(self, content: str, filename: str) -> str:
        """
        Save evidence to a file in the evidence directory.
        
        Args:
            content (str): The content to save
            filename (str): The filename to save to
            
        Returns:
            str: Path to the saved file
        """
        filepath = os.path.join(self.evidence_dir, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            logging.info(f"Saved evidence to {filepath}")
            return filepath
        except Exception as e:
            error_msg = f"Failed to save evidence to file: {str(e)}"
            logging.error(error_msg)
            raise
    
    def save_assessment(self, content: str, assessment_type: str) -> str:
        """
        Save assessment output.
        
        Args:
            content (str): The assessment content to save
            assessment_type (str): Type of assessment (e.g., 'quarterly', 'annual')
            
        Returns:
            str: Path to the saved file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{assessment_type}_assessment_{timestamp}.md"
        filepath = os.path.join(self.assessment_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            logging.info(f"Saved assessment to {filepath}")
            return filepath
        except Exception as e:
            error_msg = f"Failed to save assessment to file: {str(e)}"
            logging.error(error_msg)
            raise 