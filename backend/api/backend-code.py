from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
import json
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import io
import base64
import nltk
from nltk.util import ngrams
from collections import Counter
import jieba  # For Chinese word segmentation

# Add crawler to path - adjust path as needed
# Option 1: Using absolute path (more reliable)
crawler_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'crawler')
sys.path.append(crawler_path)
try:
    from weibo_crawler import crawler
except ImportError:
    print("Error importing weibo_crawler. Make sure the path is correct.")
    print(f"Current crawler path: {crawler_path}")
    print(f"Current sys.path: {sys.path}")


    # Fallback for development
    class MockCrawler:
        @staticmethod
        def crawl_by_keyword(keyword, config, output_dir):
            print(f"Mock crawling for keyword: {keyword}")
            # Create a sample file for testing
            with open(os.path.join(output_dir, 'sample.csv'), 'w', encoding='utf-8') as f:
                f.write("date,user,content\n")
                f.write(f"2023-01-01,user123,Sample content about {keyword}\n")

        @staticmethod
        def crawl_by_user_id(user_id, config, output_dir):
            print(f"Mock crawling for user_id: {user_id}")
            # Create a sample file for testing
            with open(os.path.join(output_dir, 'sample.csv'), 'w', encoding='utf-8') as f:
                f.write("date,user,content\n")
                f.write(f"2023-01-01,{user_id},Sample content from user\n")


    crawler = MockCrawler

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


@app.route('/api/crawl', methods=['POST'])
def crawl_weibo():
    """
    Endpoint to trigger the Weibo crawler with user parameters
    """
    data = request.json
    keyword = data.get('keyword', '')
    user_id = data.get('user_id', '')

    if not keyword and not user_id:
        return jsonify({"error": "Please provide either a keyword or user_id"}), 400

    # Set up crawler parameters
    config = {
        'filter': 1,
        'since_date': '2023-01-01',
        'write_mode': ['csv'],
        'pic_download': 0,
        'video_download': 0,
    }

    # Create output directory
    output_dir = f'./data/{keyword or user_id}'
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Execute crawler (simplified - modify based on actual weibo-crawler API)
        if keyword:
            crawler.crawl_by_keyword(keyword, config, output_dir)
        elif user_id:
            crawler.crawl_by_user_id(user_id, config, output_dir)

        return jsonify({
            "status": "success",
            "message": f"Data crawled successfully for: {keyword or user_id}",
            "data_path": output_dir
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
                        # Assume 3rd column is text content - adjust as needed
                        parts = line.strip().split(',')
                        if len(parts) > 2:
                            text_data += parts[2] + " "

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

        # Segment Chinese text
        text_data = " ".join(jieba.cut(text_data))

        # Generate word cloud
        wordcloud = WordCloud(
            width=800,
            height=400,
            background_color='white',
            font_path='path/to/chinese/font.ttf'  # Use a font that supports Chinese
        ).generate(text_data)

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
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)