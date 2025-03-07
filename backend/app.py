#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Integrated Weibo Analyzer application.
Combines the crawler, analysis, and web interface with a more organized structure.
"""

import os
import sys
import json
import logging
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver
import threading
import io
import base64
from urllib.parse import parse_qs, urlparse
import cgi
import nltk
from nltk.util import ngrams
from collections import Counter
import jieba
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# Import our weibo_crawler
from weibo_crawler import crawl_by_keyword, crawl_by_user_id

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("integrated_app")


class WeiboAnalyzer:
    """Class to handle Weibo data analysis and visualization."""

    @staticmethod
    def analyze_ngram(data_path, n=2, top_n=20):
        """
        Generate N-gram analysis from crawled data.

        Args:
            data_path (str): Path to the crawled data.
            n (int): Size of the n-grams (1 for unigrams, 2 for bigrams, etc.).
            top_n (int): Number of top n-grams to return.

        Returns:
            list: Top n-grams with their counts.
        """
        # Define common Chinese stop words to filter out
        chinese_stop_words = set([
            '的', '了', '和', '是', '我', '有', '在', '他', '你', '们', '就', '不', '这', '也', '都',
            '说', '要', '中', '大', '为', '上', '个', '到', '以', '来', '之', '与', '被', '对', '很',
            'can', 'will', 'the', '吗', '啊', '那', '但', '去', '过', '还', '着', '全文', '让', '给',
            '所', '自', '而', '却', '么', '什', '得', '又', '…', '【', '】', '》', '《', '，', '.'
        ])

        try:
            # Load crawled text data
            text_data = ""
            for filename in os.listdir(data_path):
                if filename.endswith('.csv'):
                    # Read text column from CSV
                    with open(os.path.join(data_path, filename), 'r', encoding='utf-8') as f:
                        # Skip header
                        header = next(f)
                        headers = header.strip().split(',')
                        text_col_index = headers.index('text') if 'text' in headers else 2

                        for line in f:
                            parts = line.strip().split(',')
                            if len(parts) > text_col_index:
                                text_data += parts[text_col_index] + " "

            # If text data is empty, return an error
            if not text_data.strip():
                return []

            # Segment Chinese text
            words = list(jieba.cut(text_data))

            # Filter out stop words
            filtered_words = [word for word in words if word not in chinese_stop_words and len(word.strip()) > 0]

            # Generate n-grams
            n_grams = list(ngrams(filtered_words, n))

            # Count frequencies
            freq_dist = Counter(n_grams)

            # Get top N n-grams
            top_ngrams = freq_dist.most_common(top_n)

            # Format for response
            results = [
                {
                    "ngram": " ".join(gram),
                    "count": count
                } for gram, count in top_ngrams
            ]

            return results
        except Exception as e:
            logger.exception(f"Error analyzing n-grams: {e}")
            return []

    @staticmethod
    def generate_wordcloud(data_path):
        """
        Generate a word cloud image from crawled data.

        Args:
            data_path (str): Path to the crawled data.

        Returns:
            str: Base64-encoded image data.
        """
        try:
            # Define common Chinese stop words to filter out
            chinese_stop_words = set([
                '的', '了', '和', '是', '我', '有', '在', '他', '你', '们', '就', '不', '这', '也', '都',
                '说', '要', '中', '大', '为', '上', '个', '到', '以', '来', '之', '与', '被', '对', '很',
                'can', 'will', 'the', '吗', '啊', '那', '但', '去', '过', '还', '着', '些', '让', '给',
                '所', '自', '而', '却', '么', '什', '得', '又', '…', '【', '】', '》', '《', '，', '。',
                '一个', '可以', '没有', '因为', '如果', '所以', '只是', '这个', '那个', '现在', '知道',
                '一下', '这样', '那样', '就是', '可能', '应该', '如何', '怎么', '怎样', '已经', '比较'
            ])

            # Load crawled text data
            text_data = ""
            for filename in os.listdir(data_path):
                if filename.endswith('.csv'):
                    with open(os.path.join(data_path, filename), 'r', encoding='utf-8') as f:
                        # Skip header
                        header = next(f)
                        headers = header.strip().split(',')
                        text_col_index = headers.index('text') if 'text' in headers else 2

                        for line in f:
                            parts = line.strip().split(',')
                            if len(parts) > text_col_index:
                                text_data += parts[text_col_index] + " "

            # If text data is empty, return an empty string
            if not text_data.strip():
                return ""

            # Segment Chinese text
            words = list(jieba.cut(text_data))

            # Filter out stop words
            filtered_words = [word for word in words if word not in chinese_stop_words and len(word.strip()) > 0]

            # Join words back into text
            filtered_text = " ".join(filtered_words)

            # Check for Chinese font
            font_path = None
            possible_fonts = [
                "/System/Library/Fonts/PingFang.ttc",  # macOS
                "/System/Library/Fonts/STHeiti Light.ttc",  # macOS
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # Linux
                "C:/Windows/Fonts/simhei.ttf",  # Windows
                "./font/NotoSansSC-Regular.otf"  # Custom location
            ]

            for font in possible_fonts:
                if os.path.exists(font):
                    font_path = font
                    break

            wordcloud_params = {
                "width": 800,
                "height": 400,
                "background_color": "white",
                "max_words": 200,
                "collocations": False  # Avoid duplicate phrases
            }

            if font_path:
                wordcloud_params["font_path"] = font_path
                logger.info(f"Using font: {font_path}")

            # Generate word cloud
            wordcloud = WordCloud(**wordcloud_params).generate(filtered_text)

            # Convert to image
            img = wordcloud.to_image()

            # Save to bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)

            # Convert to base64
            img_base64 = base64.b64encode(img_bytes.getvalue()).decode('utf-8')

            return img_base64
        except Exception as e:
            logger.exception(f"Error generating wordcloud: {e}")
            return ""

    def get_time_series_data(data_path):
        """
        Generate time series data for posts from crawled data.

        Args:
            data_path (str): Path to the crawled data.

        Returns:
            list: List of date and count pairs ordered by date.
        """
        try:
            # Dictionary to hold date counts
            date_counts = {}

            for filename in os.listdir(data_path):
                if filename.endswith('.csv'):
                    with open(os.path.join(data_path, filename), 'r', encoding='utf-8') as f:
                        # Skip header
                        header = next(f)
                        headers = header.strip().split(',')
                        date_index = headers.index('created_at') if 'created_at' in headers else 8

                        for line in f:
                            parts = line.strip().split(',')
                            if len(parts) > date_index:
                                post_date = parts[date_index].strip()
                                # Validate the date format is correct (YYYY-MM-DD)
                                if post_date and re.match(r'^\d{4}-\d{2}-\d{2}', post_date):
                                    # Just use the date part if it's a datetime
                                    post_date = post_date.split('T')[0] if 'T' in post_date else post_date
                                    post_date = post_date.split(' ')[0] if ' ' in post_date else post_date
                                    # Count posts by date
                                    date_counts[post_date] = date_counts.get(post_date, 0) + 1

            # Convert to list of objects for the frontend
            time_series = [
                {"date": date, "count": count}
                for date, count in date_counts.items()
            ]

            # Sort by date
            time_series.sort(key=lambda x: x["date"])

            return time_series
        except Exception as e:
            logger.exception(f"Error generating time series data: {e}")
            return []

    @staticmethod
    def get_top_posts(data_path):
        """
        Get the top posts by engagement metrics.

        Args:
            data_path (str): Path to the crawled data.

        Returns:
            dict: Dictionary containing top posts by different metrics.
        """
        try:
            posts = []

            for filename in os.listdir(data_path):
                if filename.endswith('.csv'):
                    with open(os.path.join(data_path, filename), 'r', encoding='utf-8') as f:
                        # Skip header
                        header = next(f)
                        headers = header.strip().split(',')

                        # Get indices for relevant columns
                        text_idx = headers.index('text') if 'text' in headers else 2
                        attitudes_idx = headers.index('attitudes_count') if 'attitudes_count' in headers else 9
                        comments_idx = headers.index('comments_count') if 'comments_count' in headers else 10
                        reposts_idx = headers.index('reposts_count') if 'reposts_count' in headers else 11

                        for line in f:
                            parts = line.strip().split(',')
                            if len(parts) > max(text_idx, attitudes_idx, comments_idx, reposts_idx):
                                try:
                                    post = {
                                        "text": parts[text_idx],
                                        "attitudes_count": int(parts[attitudes_idx]) if parts[
                                            attitudes_idx].isdigit() else 0,
                                        "comments_count": int(parts[comments_idx]) if parts[
                                            comments_idx].isdigit() else 0,
                                        "reposts_count": int(parts[reposts_idx]) if parts[reposts_idx].isdigit() else 0
                                    }
                                    posts.append(post)
                                except (ValueError, IndexError) as e:
                                    continue

            # Sort posts by different metrics
            top_attitudes = sorted(posts, key=lambda x: x["attitudes_count"], reverse=True)[:3]
            top_comments = sorted(posts, key=lambda x: x["comments_count"], reverse=True)[:3]
            top_reposts = sorted(posts, key=lambda x: x["reposts_count"], reverse=True)[:3]

            return {
                "top_attitudes": top_attitudes,
                "top_comments": top_comments,
                "top_reposts": top_reposts
            }
        except Exception as e:
            logger.exception(f"Error getting top posts: {e}")
            return {"top_attitudes": [], "top_comments": [], "top_reposts": []}

            # Segment Chinese text
            words = list(jieba.cut(text_data))

            # Filter out stop words
            filtered_words = [word for word in words if word not in chinese_stop_words and len(word.strip()) > 0]

            # Join words back into text
            filtered_text = " ".join(filtered_words)

            # Check for Chinese font
            font_path = None
            possible_fonts = [
                "/System/Library/Fonts/PingFang.ttc",  # macOS
                "/System/Library/Fonts/STHeiti Light.ttc",  # macOS
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # Linux
                "C:/Windows/Fonts/simhei.ttf",  # Windows
                "./font/NotoSansSC-Regular.otf"  # Custom location
            ]

            for font in possible_fonts:
                if os.path.exists(font):
                    font_path = font
                    break

            wordcloud_params = {
                "width": 800,
                "height": 400,
                "background_color": "white",
                "max_words": 200,
                "collocations": False  # Avoid duplicate phrases
            }

            if font_path:
                wordcloud_params["font_path"] = font_path
                logger.info(f"Using font: {font_path}")

            # Generate word cloud
            wordcloud = WordCloud(**wordcloud_params).generate(filtered_text)

            # Convert to image
            img = wordcloud.to_image()

            # Save to bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)

            # Convert to base64
            img_base64 = base64.b64encode(img_bytes.getvalue()).decode('utf-8')

            return img_base64
        except Exception as e:
            logger.exception(f"Error generating wordcloud: {e}")
            return ""


class WeiboAnalyzerHandler(SimpleHTTPRequestHandler):
    """Custom HTTP request handler for the Weibo Analyzer."""

    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/' or self.path == '/index.html':
            # Serve the HTML file
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            # Read from the HTML file
            try:
                with open('templates/index.html', 'rb') as file:
                    self.wfile.write(file.read())
            except FileNotFoundError:
                # If file not found, create directories and copy default HTML content
                os.makedirs('templates', exist_ok=True)
                self.wfile.write(b"Error: templates/index.html not found")
                logger.error("templates/index.html not found")
        elif self.path == '/styles.css':
            # Serve the CSS file
            self.send_response(200)
            self.send_header('Content-type', 'text/css')
            self.end_headers()

            # Read from the CSS file
            try:
                with open('static/styles.css', 'rb') as file:
                    self.wfile.write(file.read())
            except FileNotFoundError:
                # If file not found, create directories and copy default CSS content
                os.makedirs('static', exist_ok=True)
                self.wfile.write(b"Error: static/styles.css not found")
                logger.error("static/styles.css not found")
        else:
            # Serve static files (if any)
            return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        """Handle POST requests."""
        if self.path == '/api/analyze':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            # Extract parameters
            keyword = data.get('keyword', '')
            user_id = data.get('user_id', '')
            max_count = int(data.get('max_count', 50))
            since_date = data.get('since_date', '2023-01-01')
            n = int(data.get('n', 2))

            # Create output directory
            output_dir = f'./data/{keyword or user_id}'
            os.makedirs(output_dir, exist_ok=True)

            try:
                # Crawl data
                if keyword:
                    post_count = crawl_by_keyword(
                        keyword=keyword,
                        max_count=max_count,
                        since_date=since_date,
                        output_dir=output_dir
                    )
                else:
                    post_count = crawl_by_user_id(
                        user_id=user_id,
                        max_count=max_count,
                        since_date=since_date,
                        output_dir=output_dir
                    )

                # Generate n-gram analysis
                ngrams = WeiboAnalyzer.analyze_ngram(
                    data_path=output_dir,
                    n=n,
                    top_n=20
                )

                # Generate word cloud
                wordcloud_image = WeiboAnalyzer.generate_wordcloud(
                    data_path=output_dir
                )

                # Generate time series data
                time_series = WeiboAnalyzer.get_time_series_data(
                    data_path=output_dir
                )

                # Get top posts
                top_posts = WeiboAnalyzer.get_top_posts(
                    data_path=output_dir
                )

                # Prepare response
                response = {
                    "status": "success",
                    "post_count": post_count,
                    "ngrams": ngrams,
                    "wordcloud_image": wordcloud_image,
                    "time_series": time_series,
                    "top_posts": top_posts,
                    "output_dir": output_dir
                }

                # Send response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())

            except Exception as e:
                logger.exception(f"Error processing request: {e}")

                # Send error response
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "error",
                    "message": str(e)
                }).encode())
        else:
            # Return 404 for other POST requests
            self.send_response(404)
            self.end_headers()


def run_server(port=8080):
    """
    Run the HTTP server.

    Args:
        port (int): Port to run the server on.
    """
    # Create required directories if they don't exist
    os.makedirs('./data', exist_ok=True)
    os.makedirs('./templates', exist_ok=True)
    os.makedirs('./static', exist_ok=True)

    # Initialize jieba
    jieba.initialize()

    # Create and configure the server
    server_address = ('', port)
    httpd = socketserver.ThreadingTCPServer(server_address, WeiboAnalyzerHandler)

    # Print server information
    logger.info(f"Server running at http://localhost:{port}")
    logger.info("Press Ctrl+C to stop the server")

    # Open browser automatically
    webbrowser.open(f"http://localhost:{port}")

    # Run the server
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    # Get port from command line arguments
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            logger.warning(f"Invalid port number: {sys.argv[1]}, using default port 8080")

    # Run the server
    run_server(port)