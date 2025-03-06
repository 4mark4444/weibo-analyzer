from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
import json
import random
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import io
import base64
import nltk
from nltk.util import ngrams
from collections import Counter
import jieba  # For Chinese word segmentation
from datetime import datetime, timedelta, date
import logging.config
import logging

# Configure logging
if not os.path.isdir("log/"):
    os.makedirs("log/")
logging_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logging.conf")
if os.path.exists(logging_path):
    logging.config.fileConfig(logging_path)
else:
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

# Add the parent directory to the path to import weibo.py
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Import the Weibo class from weibo.py
try:
    from weibo import Weibo
    logger.info("Successfully imported Weibo class from weibo.py")
except ImportError as e:
    logger.error(f"Error importing Weibo class: {e}")
    logger.error("Make sure weibo.py is in the correct location")
    # Define a mock Weibo class for testing
    class Weibo:
        def __init__(self, config):
            self.config = config
            logger.warning("Using MOCK Weibo class for testing")
        
        def start(self):
            logger.warning("MOCK Weibo.start() called with config: %s", self.config)
            # Create sample data in the output directory
            output_dir = self.config.get('output_dir', './data/test')
            os.makedirs(output_dir, exist_ok=True)
            with open(os.path.join(output_dir, 'sample.csv'), 'w', encoding='utf-8') as f:
                f.write("date,user,content\n")
                f.write("2023-01-01,user123,Sample content for testing\n")
                f.write("2023-01-02,user456,Another sample content for testing\n")
            return True

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/api/test', methods=['GET'])
def test_api():
    """Simple endpoint to test if the API is working"""
    return jsonify({
        "status": "success",
        "message": "API is working",
        "python_version": sys.version,
        "path": sys.path
    })

@app.route('/api/crawl', methods=['POST'])
def crawl_weibo():
    """
    Endpoint to trigger the Weibo crawler with user parameters
    """
    data = request.json
    keyword = data.get('keyword', '')
    user_id = data.get('user_id', '')
    max_count = data.get('max_count', 50)  # Default to 50 posts if not specified
    since_date = data.get('since_date', '2023-01-01')
    
    if not keyword and not user_id:
        return jsonify({"error": "Please provide either a keyword or user_id"}), 400
    
    # Validate max_count
    try:
        max_count = int(max_count)
        if max_count <= 0:
            return jsonify({"error": "max_count must be a positive integer"}), 400
    except ValueError:
        return jsonify({"error": "max_count must be a valid integer"}), 400
    
    # Create output directory
    output_dir = f'./data/{keyword or user_id}'
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Log information for debugging
        logger.info(f"Starting crawler with the following parameters:")
        logger.info(f"Keyword: {keyword}")
        logger.info(f"User ID: {user_id}")
        logger.info(f"Max Count: {max_count}")
        logger.info(f"Since Date: {since_date}")
        logger.info(f"Output Directory: {output_dir}")
        
        # Prepare config for Weibo class
        config = {
            "user_id_list": [user_id] if user_id else [],
            "query_list": [keyword] if keyword else [],
            "since_date": since_date,
            "write_mode": ["csv"],
            "pic_download": 0,
            "video_download": 0,
            "only_crawl_original": 1,  # Only original posts
            "remove_html_tag": 1,  # Remove HTML tags
            "max_count": max_count,  # Custom parameter
            "output_dir": output_dir  # Custom parameter
        }
        
        # Initialize and run the Weibo crawler
        wb = Weibo(config)
        wb.start()
        
        # Count the number of posts crawled
        post_count = 0
        for filename in os.listdir(output_dir):
            if filename.endswith('.csv'):
                with open(os.path.join(output_dir, filename), 'r', encoding='utf-8') as f:
                    # Subtract 1 for the header line
                    post_count = sum(1 for _ in f) - 1
        
        return jsonify({
            "status": "success",
            "message": f"Data crawled successfully for: {keyword or user_id}",
            "data_path": output_dir,
            "post_count": post_count,
            "max_requested": max_count
        })
        
    except Exception as e:
        logger.exception(f"Error during crawling: {e}")
        return jsonify({"error": str(e), "traceback": str(sys.exc_info())}), 500

@app.route('/api/analyze/ngram', methods=['POST'])
def analyze_ngram():
    """
    Generate N-gram analysis from crawled data
    """
    data = request.json
    data_path = data.get('data_path', '')
    n = data.get('n', 2)  # Default to bigrams
    top_n = data.get('top_n', 20)  # Default to top 20
    
    if not data_path or not os.path.exists(data_path):
        return jsonify({"error": "Invalid data path"}), 400
    
    try:
        # Load crawled text data
        text_data = ""
        for filename in os.listdir(data_path):
            if filename.endswith('.csv'):
                # Read text column from CSV - adjust based on actual data structure
                with open(os.path.join(data_path, filename), 'r', encoding='utf-8') as f:
                    # Skip header
                    next(f)
                    for line in f:
                        # Split by comma, but handle commas in quoted text
                        parts = line.strip().split(',')
                        if len(parts) > 2:
                            # Assuming the content is in the 3rd column, but this may need adjustment
                            text_data += parts[2] + " "
        
        # If text data is empty, return an error
        if not text_data.strip():
            return jsonify({"error": "No text data found in the provided files"}), 400
        
        # Segment Chinese text
        words = list(jieba.cut(text_data))
        
        # Generate n-grams
        n_grams = list(ngrams(words, n))
        
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
        
        return jsonify({
            "status": "success",
            "data": results,
            "total_ngrams": len(n_grams)
        })
    except Exception as e:
        logger.exception(f"Error analyzing n-grams: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/analyze/wordcloud', methods=['POST'])
def generate_wordcloud():
    """
    Generate a word cloud image from crawled data
    """
    data = request.json
    data_path = data.get('data_path', '')
    
    if not data_path or not os.path.exists(data_path):
        return jsonify({"error": "Invalid data path"}), 400
    
    try:
        # Load crawled text data
        text_data = ""
        for filename in os.listdir(data_path):
            if filename.endswith('.csv'):
                with open(os.path.join(data_path, filename), 'r', encoding='utf-8') as f:
                    next(f)
                    for line in f:
                        parts = line.strip().split(',')
                        if len(parts) > 2:
                            text_data += parts[2] + " "
        
        # If text data is empty, return an error
        if not text_data.strip():
            return jsonify({"error": "No text data found in the provided files"}), 400
        
        # Segment Chinese text
        text_data = " ".join(jieba.cut(text_data))
        
        # Generate word cloud
        # For Chinese text, you need a font that supports Chinese characters
        # Check if a Chinese font exists in the common locations
        font_path = None
        possible_fonts = [
            "/System/Library/Fonts/PingFang.ttc",  # macOS
            "/System/Library/Fonts/STHeiti Light.ttc",  # macOS
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # Linux
            "C:/Windows/Fonts/simhei.ttf",  # Windows
            "font/NotoSansSC-Regular.otf"  # Custom location (needs to be added)
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
        else:
            logger.warning("No suitable Chinese font found, wordcloud may not display Chinese characters correctly")
        
        wordcloud = WordCloud(**wordcloud_params).generate(text_data)
        
        # Convert to image
        img = wordcloud.to_image()
        
        # Save to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Convert to base64 for sending to frontend
        img_base64 = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
        
        return jsonify({
            "status": "success",
            "image": img_base64
        })
    except Exception as e:
        logger.exception(f"Error generating wordcloud: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
