import json
import os
import time
import logging
from datetime import datetime

class QueryLogger:
    """
    A logger class that saves detailed information about each question processing step:
    - Original question
    - Classification
    - Embeddings retrieved (theory and EPD) with SQL queries
    - Generated prompt
    - Prompt length metrics
    - LLM response
    """
    
    def __init__(self, log_dir="query_logs"):
        """
        Initialize the query logger.
        
        Args:
            log_dir: Directory where log files will be saved
        """
        self.log_dir = log_dir
        
        # Create log directory if it doesn't exist
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Setup file-based logger
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s"
        )
        self.logger = logging.getLogger(__name__)
    
    def log_query(self, query_data):
        """
        Save the complete query data to a JSON file.
        
        Args:
            query_data: Dictionary containing all query information
        
        Returns:
            Path to the saved log file
        """
        try:
            # Generate filename based on timestamp
            timestamp = int(time.time())
            date_str = datetime.now().strftime("%Y%m%d")
            filename = f"query_{date_str}_{timestamp}.json"
            filepath = os.path.join(self.log_dir, filename)
            
            # Add timestamp to the data
            query_data["timestamp"] = timestamp
            query_data["datetime"] = datetime.now().isoformat()
            
            # Calculate and add prompt metrics if prompt exists
            if "prompt" in query_data and query_data["prompt"]:
                prompt = query_data["prompt"]
                query_data["prompt_metrics"] = {
                    "character_count": len(prompt),
                    "word_count": len(prompt.split()),
                    "line_count": len(prompt.splitlines())
                }
                self.logger.info(f"Prompt metrics - Characters: {len(prompt)}, Words: {len(prompt.split())}, Lines: {len(prompt.splitlines())}")
            
            # Write to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(query_data, f, indent=2, ensure_ascii=False)
                
            self.logger.info(f"Query log saved to {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"Failed to save query log: {str(e)}")
            return None