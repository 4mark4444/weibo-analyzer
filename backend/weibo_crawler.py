#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A simplified Weibo crawler based on the original weibo-crawler project
but modified to work as a standalone module without external dependencies.
"""

import os
import sys
import csv
import json
import logging
import random
import re
import time
import codecs
import requests
from datetime import datetime, timedelta, date
from requests.exceptions import RequestException
from collections import OrderedDict
from lxml import etree

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("weibo_crawler")

class WeiboCrawler:
    """
    Simplified Weibo crawler class that can be easily integrated with other applications.
    """
    
    def __init__(self, keyword=None, user_id=None, max_count=50, since_date=None, output_dir=None):
        """
        Initialize the crawler with parameters.
        
        Args:
            keyword (str): Keyword to search for. Either keyword or user_id must be provided.
            user_id (str): User ID to crawl posts from. Either keyword or user_id must be provided.
            max_count (int): Maximum number of posts to crawl.
            since_date (str): Only crawl posts since this date (YYYY-MM-DD).
            output_dir (str): Directory to save output files.
        """
        # Validate parameters
        if not keyword and not user_id:
            raise ValueError("Either keyword or user_id must be provided")
        
        self.keyword = keyword
        self.user_id = user_id
        self.max_count = max_count
        
        # Handle since_date
        if since_date:
            if isinstance(since_date, int):
                self.since_date = (date.today() - timedelta(since_date)).strftime("%Y-%m-%d")
            elif re.match(r'^\d{4}-\d{2}-\d{2}$', since_date):
                self.since_date = since_date
            else:
                raise ValueError("since_date must be an integer or in YYYY-MM-DD format")
        else:
            self.since_date = (date.today() - timedelta(365)).strftime("%Y-%m-%d")  # Default to 1 year ago
        
        # Set output directory
        if output_dir:
            self.output_dir = output_dir
        else:
            self.output_dir = f"./data/{self.keyword or self.user_id}"
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Default headers for requests
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36",
            "Cookie": ""  # Add your cookie here if needed
        }
        
        # Initialize state variables
        self.weibo_list = []
        self.got_count = 0
        self.page_count = 1
        self.user_info = {}
    
    def start(self):
        """
        Start the crawling process.
        
        Returns:
            int: Number of posts crawled.
        """
        logger.info("Starting Weibo crawler")
        logger.info(f"Parameters: keyword={self.keyword}, user_id={self.user_id}, max_count={self.max_count}, since_date={self.since_date}")
        
        try:
            if self.user_id:
                # Get user info and posts by user ID
                self.get_user_info()
                self.get_user_posts()
            elif self.keyword:
                # Get posts by keyword
                self.get_keyword_posts()
            
            # Write results to CSV
            self.write_to_csv()
            
            logger.info(f"Crawling completed. Got {self.got_count} posts.")
            return self.got_count
            
        except Exception as e:
            logger.exception(f"Error during crawling: {e}")
            return 0
    
    def get_user_info(self):
        """
        Get user information by user ID.
        """
        logger.info(f"Getting user info for user ID: {self.user_id}")
        
        url = "https://m.weibo.cn/api/container/getIndex"
        params = {"containerid": "100505" + str(self.user_id)}
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('ok') == 1 and 'data' in data and 'userInfo' in data['data']:
                user_info = data['data']['userInfo']
                self.user_info = {
                    "id": self.user_id,
                    "screen_name": user_info.get('screen_name', ''),
                    "statuses_count": user_info.get('statuses_count', 0),
                    "followers_count": user_info.get('followers_count', 0),
                    "follow_count": user_info.get('follow_count', 0),
                    "description": user_info.get('description', '')
                }
                logger.info(f"Got user info: {self.user_info['screen_name']}, {self.user_info['statuses_count']} posts")
                
                # Calculate page count based on statuses_count
                page_count = (self.user_info['statuses_count'] + 9) // 10  # 10 posts per page, rounded up
                self.page_count = min(page_count, (self.max_count + 9) // 10)
                
            else:
                logger.error(f"Failed to get user info: {data.get('msg', 'Unknown error')}")
        
        except Exception as e:
            logger.exception(f"Error getting user info: {e}")
    
    def get_user_posts(self):
        """
        Get posts from the specified user.
        """
        logger.info(f"Getting posts for user ID: {self.user_id}")
        
        url = "https://m.weibo.cn/api/container/getIndex"
        
        for page in range(1, self.page_count + 1):
            if self.got_count >= self.max_count:
                break
                
            logger.info(f"Getting page {page}/{self.page_count}")
            
            params = {
                "containerid": "230413" + str(self.user_id),
                "page": page
            }
            
            try:
                # Add a random delay to avoid being blocked
                time.sleep(random.uniform(1, 3))
                
                response = requests.get(url, params=params, headers=self.headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if data.get('ok') == 1 and 'data' in data and 'cards' in data['data']:
                    cards = data['data']['cards']
                    
                    for card in cards:
                        if card.get('card_type') == 9 and 'mblog' in card:
                            weibo = self.parse_weibo(card['mblog'])
                            
                            if weibo:
                                weibo_date = datetime.strptime(weibo['created_at'], "%Y-%m-%d")
                                since_date = datetime.strptime(self.since_date, "%Y-%m-%d")
                                
                                if weibo_date < since_date:
                                    logger.info(f"Reached posts older than {self.since_date}, stopping.")
                                    return
                                
                                self.weibo_list.append(weibo)
                                self.got_count += 1
                                
                                if self.got_count >= self.max_count:
                                    logger.info(f"Reached maximum count of {self.max_count}, stopping.")
                                    return
                
                else:
                    logger.warning(f"Failed to get page {page}: {data.get('msg', 'Unknown error')}")
                    
            except Exception as e:
                logger.exception(f"Error getting page {page}: {e}")
                
            # Add a longer delay between pages
            time.sleep(random.uniform(3, 5))
    
    def get_keyword_posts(self):
        """
        Get posts containing the specified keyword.
        """
        logger.info(f"Getting posts for keyword: {self.keyword}")
        
        url = "https://m.weibo.cn/api/container/getIndex"
        
        # For keywords, we don't know total count in advance, so start with page 1
        page = 1
        
        while True:
            if self.got_count >= self.max_count:
                break
                
            logger.info(f"Getting page {page}")
            
            params = {
                "containerid": "100103type=1&q=" + self.keyword,
                "page_type": "searchall",
                "page": page
            }
            
            try:
                # Add a random delay to avoid being blocked
                time.sleep(random.uniform(1, 3))
                
                response = requests.get(url, params=params, headers=self.headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if data.get('ok') == 1 and 'data' in data and 'cards' in data['data']:
                    cards = data['data']['cards']
                    
                    if len(cards) == 0:
                        logger.info("No more posts found.")
                        break
                    
                    # For keywords, the cards structure is different
                    for card in cards:
                        if card.get('card_type') == 11 and 'card_group' in card:
                            for item in card['card_group']:
                                if item.get('card_type') == 9 and 'mblog' in item:
                                    weibo = self.parse_weibo(item['mblog'])
                                    
                                    if weibo:
                                        weibo_date = datetime.strptime(weibo['created_at'], "%Y-%m-%d")
                                        since_date = datetime.strptime(self.since_date, "%Y-%m-%d")
                                        
                                        if weibo_date < since_date:
                                            logger.info(f"Reached posts older than {self.since_date}, stopping.")
                                            return
                                        
                                        self.weibo_list.append(weibo)
                                        self.got_count += 1
                                        
                                        if self.got_count >= self.max_count:
                                            logger.info(f"Reached maximum count of {self.max_count}, stopping.")
                                            return
                
                else:
                    logger.warning(f"Failed to get page {page}: {data.get('msg', 'Unknown error')}")
                    if page > 50:  # Limit to 50 pages to avoid infinite loop
                        break
                    
                page += 1
                
            except Exception as e:
                logger.exception(f"Error getting page {page}: {e}")
                if page > 50:  # Limit to 50 pages to avoid infinite loop
                    break
                page += 1
                
            # Add a longer delay between pages
            time.sleep(random.uniform(3, 5))
    
    def parse_weibo(self, mblog):
        """
        Parse a Weibo post from the API response.
        
        Args:
            mblog (dict): The mblog data from the API response.
            
        Returns:
            dict: Parsed Weibo post data.
        """
        try:
            # Basic information
            weibo = {
                "id": mblog.get('id', ''),
                "user_id": mblog.get('user', {}).get('id', ''),
                "screen_name": mblog.get('user', {}).get('screen_name', ''),
                "text": self.remove_html_tags(mblog.get('text', '')),
                "pics": self.get_pics(mblog),
                "video_url": self.get_video_url(mblog),
                "created_at": self.standardize_date(mblog.get('created_at', '')),
                "source": mblog.get('source', ''),
                "attitudes_count": mblog.get('attitudes_count', 0),
                "comments_count": mblog.get('comments_count', 0),
                "reposts_count": mblog.get('reposts_count', 0),
                "topics": self.get_topics(mblog.get('text', '')),
                "at_users": self.get_at_users(mblog.get('text', ''))
            }
            
            # Get full text for long weibos
            if mblog.get('isLongText', False) and weibo['id']:
                full_text = self.get_long_weibo(weibo['id'])
                if full_text:
                    weibo['text'] = full_text
            
            return weibo
            
        except Exception as e:
            logger.exception(f"Error parsing weibo: {e}")
            return None
    
    def remove_html_tags(self, text):
        """
        Remove HTML tags from text.
        
        Args:
            text (str): Text with HTML tags.
            
        Returns:
            str: Clean text without HTML tags.
        """
        if not text:
            return ""
            
        # Parse HTML
        selector = etree.HTML(text)
        if selector is not None:
            # Extract all text nodes
            text_list = selector.xpath('//text()')
            # Join text nodes
            clean_text = ' '.join([t.strip() for t in text_list if t.strip()])
            return clean_text
        
        # Fallback: use regex to remove HTML tags
        return re.sub(r'<[^>]+>', '', text)
    
    def get_pics(self, mblog):
        """
        Get image URLs from a Weibo post.
        
        Args:
            mblog (dict): The mblog data from the API response.
            
        Returns:
            str: Comma-separated image URLs.
        """
        if mblog.get('pics'):
            pic_info = mblog['pics']
            pic_list = [pic.get('large', {}).get('url', '') for pic in pic_info]
            return ','.join([url for url in pic_list if url])
        return ""
    
    def get_video_url(self, mblog):
        """
        Get video URL from a Weibo post.
        
        Args:
            mblog (dict): The mblog data from the API response.
            
        Returns:
            str: Video URL.
        """
        if mblog.get('page_info') and mblog['page_info'].get('type') == 'video':
            media_info = mblog['page_info'].get('media_info', {})
            video_url = media_info.get('mp4_720p_mp4', '')
            if not video_url:
                video_url = media_info.get('mp4_hd_url', '')
            if not video_url:
                video_url = media_info.get('mp4_sd_url', '')
            return video_url
        return ""
    
    def get_topics(self, text):
        """
        Extract hashtags/topics from text.
        
        Args:
            text (str): Text to extract topics from.
            
        Returns:
            str: Comma-separated topics.
        """
        if not text:
            return ""
            
        topics = re.findall(r'#(.*?)#', text)
        return ','.join(topics)
    
    def get_at_users(self, text):
        """
        Extract @mentions from text.
        
        Args:
            text (str): Text to extract mentions from.
            
        Returns:
            str: Comma-separated user mentions.
        """
        if not text:
            return ""
            
        at_users = re.findall(r'@([a-zA-Z0-9_\u4e00-\u9fa5]+)', text)
        return ','.join(at_users)
    
    def get_long_weibo(self, weibo_id):
        """
        Get the full text of a long Weibo post.
        
        Args:
            weibo_id (str): ID of the Weibo post.
            
        Returns:
            str: Full text of the Weibo post.
        """
        try:
            url = f"https://m.weibo.cn/detail/{weibo_id}"
            response = requests.get(url, headers=self.headers, timeout=10)
            html = response.text
            
            # Extract the weibo content JSON
            json_text = re.search(r'"status":(.*?),"ok"', html)
            if json_text:
                js = json.loads('{' + json_text.group(0) + '}')
                if 'status' in js:
                    weibo_info = js['status']
                    text = weibo_info.get('text', '')
                    return self.remove_html_tags(text)
            
            return None
            
        except Exception as e:
            logger.warning(f"Error getting long weibo {weibo_id}: {e}")
            return None
    
    def standardize_date(self, created_at):
        """
        Standardize the date format from Weibo API.
        
        Args:
            created_at (str): Date string from Weibo API.
            
        Returns:
            str: Standardized date in YYYY-MM-DD format.
        """
        try:
            if created_at.startswith('刚刚'):
                return datetime.now().strftime('%Y-%m-%d')
            
            elif '分钟前' in created_at:
                minutes = int(created_at.split('分钟前')[0].strip())
                return (datetime.now() - timedelta(minutes=minutes)).strftime('%Y-%m-%d')
            
            elif '小时前' in created_at:
                hours = int(created_at.split('小时前')[0].strip())
                return (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d')
            
            elif '昨天' in created_at:
                return (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
            elif created_at.count('-') == 1:  # Only month and day, like "11-12"
                # Add current year
                current_year = datetime.now().year
                return f"{current_year}-{created_at}"
            
            elif re.match(r'\d{1,2}-\d{1,2} \d{1,2}:\d{1,2}', created_at):
                # Format like "11-12 10:15"
                current_year = datetime.now().year
                return f"{current_year}-{created_at.split(' ')[0]}"
                
            elif re.match(r'\d{4}-\d{1,2}-\d{1,2}', created_at):
                # Already in YYYY-MM-DD format
                return created_at.split(' ')[0]
                
            else:
                # Try to parse with multiple formats
                for fmt in ['%a %b %d %H:%M:%S +0800 %Y', '%Y-%m-%d']:
                    try:
                        dt = datetime.strptime(created_at, fmt)
                        return dt.strftime('%Y-%m-%d')
                    except:
                        continue
                
                # Fallback to current date
                return datetime.now().strftime('%Y-%m-%d')
                
        except Exception as e:
            logger.warning(f"Error parsing date {created_at}: {e}")
            return datetime.now().strftime('%Y-%m-%d')
    
    def write_to_csv(self):
        """
        Write crawled posts to a CSV file.
        """
        if not self.weibo_list:
            logger.warning("No posts to write to CSV")
            return
        
        file_path = os.path.join(self.output_dir, f"{self.keyword or self.user_id}.csv")
        logger.info(f"Writing {len(self.weibo_list)} posts to {file_path}")
        
        try:
            # Define the headers for the CSV file
            headers = [
                "id", "user_id", "screen_name", "text", "topics", "at_users",
                "pics", "video_url", "created_at", "source",
                "attitudes_count", "comments_count", "reposts_count"
            ]
            
            # Prepare the data for writing
            data = []
            for weibo in self.weibo_list:
                row = [weibo.get(key, '') for key in headers]
                data.append(row)
            
            # Write to CSV
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(data)
            
            logger.info(f"Successfully wrote to {file_path}")
            
        except Exception as e:
            logger.exception(f"Error writing to CSV: {e}")

def crawl_by_keyword(keyword, max_count=50, since_date=None, output_dir=None):
    """
    Crawl Weibo posts by keyword.
    
    Args:
        keyword (str): Keyword to search for.
        max_count (int): Maximum number of posts to crawl.
        since_date (str): Only crawl posts since this date (YYYY-MM-DD).
        output_dir (str): Directory to save output files.
        
    Returns:
        int: Number of posts crawled.
    """
    crawler = WeiboCrawler(
        keyword=keyword,
        max_count=max_count,
        since_date=since_date,
        output_dir=output_dir
    )
    return crawler.start()

def crawl_by_user_id(user_id, max_count=50, since_date=None, output_dir=None):
    """
    Crawl Weibo posts by user ID.
    
    Args:
        user_id (str): User ID to crawl posts from.
        max_count (int): Maximum number of posts to crawl.
        since_date (str): Only crawl posts since this date (YYYY-MM-DD).
        output_dir (str): Directory to save output files.
        
    Returns:
        int: Number of posts crawled.
    """
    crawler = WeiboCrawler(
        user_id=user_id,
        max_count=max_count,
        since_date=since_date,
        output_dir=output_dir
    )
    return crawler.start()

# Example usage
if __name__ == "__main__":
    # Test with keyword
    # crawl_by_keyword("Python", max_count=10)
    
    # Test with user ID
    # crawl_by_user_id("1669879400", max_count=10)
    
    print("Run this script with parameters to test crawling.")
    print("Example: python weibo_crawler.py keyword Python 10")
    print("Example: python weibo_crawler.py user_id 1669879400 10")
    
    if len(sys.argv) >= 4:
        crawl_type = sys.argv[1]
        value = sys.argv[2]
        max_count = int(sys.argv[3])
        
        if crawl_type == "keyword":
            print(f"Crawling by keyword: {value}, max_count: {max_count}")
            crawl_by_keyword(value, max_count)
        elif crawl_type == "user_id":
            print(f"Crawling by user ID: {value}, max_count: {max_count}")
            crawl_by_user_id(value, max_count)
        else:
            print(f"Unknown crawl type: {crawl_type}")
