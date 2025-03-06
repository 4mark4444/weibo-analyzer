#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Wrapper module for the Weibo crawler that provides a simplified interface
for our API to use.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta, date

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("weibo_wrapper")

# Make sure parent directory is in path to import weibo.py
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

class WeiboWrapper:
    """
    A wrapper around the Weibo class to provide a simplified interface for our API.
    """
    
    def __init__(self):
        """Initialize the WeiboWrapper."""
        try:
            # Try to import the Weibo class
            from weibo import Weibo
            self.Weibo = Weibo
            logger.info("Successfully imported Weibo class")
        except ImportError as e:
            logger.error(f"Failed to import Weibo class: {e}")
            logger.error("Current sys.path: %s", sys.path)
            # Define a mock Weibo class for testing
            class MockWeibo:
                def __init__(self, config):
                    self.config = config
                    logger.warning("Using MOCK Weibo class")
                
                def start(self):
                    logger.warning("MOCK start() called with config: %s", self.config)
                    # Create sample output for testing
                    output_dir = self.config.get('output_dir', './data/test')
                    os.makedirs(output_dir, exist_ok=True)
                    with open(os.path.join(output_dir, 'sample.csv'), 'w', encoding='utf-8') as f:
                        f.write("date,user,content\n")
                        f.write("2023-01-01,user123,Sample content for testing\n")
                        f.write("2023-01-02,user456,Another sample content\n")
            
            self.Weibo = MockWeibo
    
    def crawl_by_keyword(self, keyword, max_count=50, since_date='2025-03-01', output_dir=None):
        """
        Crawl Weibo posts containing the given keyword.
        
        Args:
            keyword (str): Keyword to search for.
            max_count (int): Maximum number of posts to crawl.
            since_date (str): Only crawl posts since this date (YYYY-MM-DD).
            output_dir (str): Directory to save output files.
        
        Returns:
            str: Path to the directory containing the crawled data.
        """
        if not output_dir:
            output_dir = f'./data/{keyword}'
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Prepare config for Weibo class
        config = {
            "user_id_list": [],
            "query_list": ["抑郁"],
            "since_date": since_date,
            "write_mode": ["csv"],
            "pic_download": 0,
            "video_download": 0,
            "only_crawl_original": 1,
            "remove_html_tag": 1,
            "max_count": max_count,
            "output_dir": output_dir
        }
        
        return self._run_crawler(config)
    
    def crawl_by_user_id(self, user_id, max_count=50, since_date='2023-01-01', output_dir=None):
        """
        Crawl Weibo posts from the specified user.
        
        Args:
            user_id (str): User ID to crawl posts from.
            max_count (int): Maximum number of posts to crawl.
            since_date (str): Only crawl posts since this date (YYYY-MM-DD).
            output_dir (str): Directory to save output files.
        
        Returns:
            str: Path to the directory containing the crawled data.
        """
        if not output_dir:
            output_dir = f'./data/{user_id}'
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Prepare config for Weibo class
        config = {
            "user_id_list": [user_id],
            "query_list": [],
            "since_date": since_date,
            "write_mode": ["csv"],
            "pic_download": 0,
            "video_download": 0,
            "only_crawl_original": 1,
            "remove_html_tag": 1,
            "max_count": max_count,
            "output_dir": output_dir
        }
        
        return self._run_crawler(config)
    
    def _run_crawler(self, config):
        """
        Run the Weibo crawler with the given configuration.
        
        Args:
            config (dict): Configuration for the Weibo crawler.
        
        Returns:
            str: Path to the directory containing the crawled data.
        """
        try:
            # Log information for debugging
            logger.info("Starting crawler with config: %s", json.dumps(config, ensure_ascii=False))
            
            # Add required fields if not present
            full_config = {
                "filter": 1,
                "original_pic_download": 0,
                "retweet_pic_download": 0,
                "original_video_download": 0,
                "retweet_video_download": 0,
                "download_comment": 0,
                "comment_max_download_count": 0,
                "download_repost": 0,
                "repost_max_download_count": 0,
                "user_id_as_folder_name": 0,
                "cookie": "",
            }
            full_config.update(config)
            
            # Initialize and run the Weibo crawler
            wb = self.Weibo(full_config)
            wb.start()
            
            return config["output_dir"]
        
        except Exception as e:
            logger.exception("Error running Weibo crawler: %s", e)
            raise e

# Simple test function
def test():
    """Test the WeiboWrapper."""
    wrapper = WeiboWrapper()
    output_dir = wrapper.crawl_by_keyword("测试", max_count=5)
    print(f"Output directory: {output_dir}")
    
    # Check if files were created
    if os.path.exists(output_dir):
        files = os.listdir(output_dir)
        print(f"Files created: {files}")
    else:
        print("Output directory not created")

if __name__ == "__main__":
    # If this script is run directly, run the test function
    test()
