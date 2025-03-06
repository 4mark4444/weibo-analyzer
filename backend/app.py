#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Integrated Weibo Analyzer application.
Combines the crawler, analysis, and web interface in a single file.
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

# HTML Template for the application
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Weibo Analysis Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f8f9fa;
        }
        .dashboard-header {
            background-color: #ff8c00;
            color: white;
            padding: 20px 0;
            margin-bottom: 30px;
        }
        .card {
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
            transition: transform 0.3s;
        }
        .card:hover {
            transform: translateY(-5px);
        }
        .card-header {
            background-color: #ff8c00;
            color: white;
            border-radius: 10px 10px 0 0 !important;
        }
        .btn-primary {
            background-color: #ff8c00;
            border-color: #ff8c00;
        }
        .btn-primary:hover {
            background-color: #e67e00;
            border-color: #e67e00;
        }
        .loader {
            border: 5px solid #f3f3f3;
            border-radius: 50%;
            border-top: 5px solid #ff8c00;
            width: 50px;
            height: 50px;
            animation: spin 2s linear infinite;
            margin: 20px auto;
            display: none;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        #wordcloud-img {
            max-width: 100%;
            height: auto;
        }
        .result-container {
            display: none;
        }
        .ngram-item {
            background-color: #f8f9fa;
            border-radius: 5px;
            padding: 10px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
        }
        .ngram-count {
            background-color: #ff8c00;
            color: white;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .progress {
            height: 20px;
            margin-top: 10px;
            margin-bottom: 10px;
        }
        .progress-bar {
            background-color: #ff8c00;
        }
        #status-details {
            margin-top: 10px;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="dashboard-header">
        <div class="container">
            <h1><i class="bi bi-bar-chart-fill"></i> Weibo Analysis Dashboard</h1>
            <p class="lead">Analyze Weibo content with N-grams and word clouds</p>
        </div>
    </div>

    <div class="container">
        <div class="row">
            <!-- Input Form -->
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="bi bi-search"></i> Search Parameters</h5>
                    </div>
                    <div class="card-body">
                        <form id="search-form">
                            <div class="mb-3">
                                <label for="search-type" class="form-label">Search By</label>
                                <select class="form-select" id="search-type">
                                    <option value="keyword">Keyword</option>
                                    <option value="user">User ID</option>
                                </select>
                            </div>
                            <div class="mb-3" id="keyword-input">
                                <label for="keyword" class="form-label">Keyword</label>
                                <input type="text" class="form-control" id="keyword" placeholder="Enter a keyword">
                            </div>
                            <div class="mb-3 d-none" id="user-input">
                                <label for="user-id" class="form-label">Weibo User ID</label>
                                <input type="text" class="form-control" id="user-id" placeholder="Enter a Weibo user ID">
                            </div>
                            <div class="mb-3">
                                <label for="max-count" class="form-label">Maximum Posts to Crawl</label>
                                <input type="number" class="form-control" id="max-count" min="1" max="500" value="50" placeholder="Enter max number of posts">
                                <small class="text-muted">Higher values will take longer to crawl</small>
                            </div>
                            <div class="mb-3">
                                <label for="since-date" class="form-label">Posts Since Date</label>
                                <input type="date" class="form-control" id="since-date" value="2023-01-01">
                            </div>
                            <div class="mb-3">
                                <label for="n-value" class="form-label">N-gram Size</label>
                                <select class="form-select" id="n-value">
                                    <option value="1">Unigrams</option>
                                    <option value="2" selected>Bigrams</option>
                                    <option value="3">Trigrams</option>
                                </select>
                            </div>
                            <button type="submit" class="btn btn-primary w-100">
                                <i class="bi bi-search"></i> Analyze
                            </button>
                        </form>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <h5><i class="bi bi-info-circle"></i> Instructions</h5>
                    </div>
                    <div class="card-body">
                        <p>1. Enter a keyword or Weibo user ID</p>
                        <p>2. Set the maximum number of posts to crawl</p>
                        <p>3. Select the date range and N-gram size</p>
                        <p>4. Click "Analyze" to start the process</p>
                        <p>5. View the word cloud and N-gram analysis</p>
                        <p class="text-muted"><small>Note: Crawling may take some time for popular topics or users with many posts.</small></p>
                    </div>
                </div>
            </div>

            <!-- Results Section -->
            <div class="col-md-8">
                <!-- Loading Indicator -->
                <div id="loading" class="text-center" style="display: none;">
                    <div class="loader" style="display: block;"></div>
                    <p id="status-message">Preparing to analyze...</p>
                    <div class="progress" id="progress-container">
                        <div class="progress-bar" id="progress-bar" role="progressbar" style="width: 0%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">0%</div>
                    </div>
                    <p id="status-details" class="text-muted"></p>
                </div>

                <!-- Results Container -->
                <div id="results" class="result-container">
                    <!-- Crawl Summary -->
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="bi bi-list-check"></i> Crawl Summary</h5>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <strong>Search Term:</strong>
                                        <span id="summary-search-term"></span>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <strong>Posts Crawled:</strong>
                                        <span id="summary-post-count"></span>
                                    </div>
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <strong>Date Range:</strong>
                                        <span id="summary-date-range"></span>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <strong>Analysis Type:</strong>
                                        <span id="summary-ngram-type"></span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Word Cloud -->
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="bi bi-cloud"></i> Word Cloud</h5>
                        </div>
                        <div class="card-body text-center">
                            <img id="wordcloud-img" src="" alt="Word Cloud">
                        </div>
                    </div>

                    <!-- N-gram Analysis -->
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="bi bi-graph-up"></i> Top N-grams</h5>
                        </div>
                        <div class="card-body">
                            <div id="ngram-results"></div>
                        </div>
                    </div>
                </div>

                <!-- Error Messages -->
                <div id="error" class="alert alert-danger" style="display: none;" role="alert">
                    <i class="bi bi-exclamation-triangle-fill"></i> <span id="error-message"></span>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Elements
            const searchForm = document.getElementById('search-form');
            const searchType = document.getElementById('search-type');
            const keywordInput = document.getElementById('keyword-input');
            const userInput = document.getElementById('user-input');
            const keywordField = document.getElementById('keyword');
            const userIdField = document.getElementById('user-id');
            const maxCountField = document.getElementById('max-count');
            const sinceDateField = document.getElementById('since-date');
            const nValue = document.getElementById('n-value');
            const loading = document.getElementById('loading');
            const statusMessage = document.getElementById('status-message');
            const statusDetails = document.getElementById('status-details');
            const progressContainer = document.getElementById('progress-container');
            const progressBar = document.getElementById('progress-bar');
            const results = document.getElementById('results');
            const wordcloudImg = document.getElementById('wordcloud-img');
            const ngramResults = document.getElementById('ngram-results');
            const errorDiv = document.getElementById('error');
            const errorMessage = document.getElementById('error-message');

            // Summary elements
            const summarySearchTerm = document.getElementById('summary-search-term');
            const summaryPostCount = document.getElementById('summary-post-count');
            const summaryDateRange = document.getElementById('summary-date-range');
            const summaryNgramType = document.getElementById('summary-ngram-type');

            // URL for API requests - now points to our local server
            const API_BASE_URL = window.location.origin;

            // Toggle between keyword and user ID inputs
            searchType.addEventListener('change', function() {
                if (this.value === 'keyword') {
                    keywordInput.classList.remove('d-none');
                    userInput.classList.add('d-none');
                } else {
                    keywordInput.classList.add('d-none');
                    userInput.classList.remove('d-none');
                }
            });

            // Form submission
            searchForm.addEventListener('submit', async function(e) {
                e.preventDefault();

                // Get search parameters
                const isKeywordSearch = searchType.value === 'keyword';
                const keyword = keywordField.value.trim();
                const userId = userIdField.value.trim();
                const maxCount = parseInt(maxCountField.value);
                const sinceDate = sinceDateField.value;
                const n = parseInt(nValue.value);

                // Validate input
                if (isKeywordSearch && !keyword) {
                    showError('Please enter a keyword');
                    return;
                } else if (!isKeywordSearch && !userId) {
                    showError('Please enter a Weibo user ID');
                    return;
                }

                if (isNaN(maxCount) || maxCount <= 0) {
                    showError('Please enter a valid number for maximum posts');
                    return;
                }

                // Reset UI
                resetUI();

                // Show loading state
                loading.style.display = 'block';
                statusMessage.textContent = 'Starting to crawl Weibo data...';
                statusDetails.textContent = `This will crawl up to ${maxCount} posts since ${sinceDate}`;

                // Artificial progress simulation for better UX
                let progress = 0;
                const progressInterval = setInterval(() => {
                    // Slowly increase progress, but never reach 100% until we get the actual response
                    if (progress < 90) {
                        progress += (90 - progress) / 50;
                        progressBar.style.width = `${progress}%`;
                        progressBar.textContent = `${Math.round(progress)}%`;
                        progressBar.setAttribute('aria-valuenow', Math.round(progress));
                    }
                }, 500);

                try {
                    // Step 1: Crawl data
                    const crawlData = {
                        keyword: isKeywordSearch ? keyword : '',
                        user_id: isKeywordSearch ? '' : userId,
                        max_count: maxCount,
                        since_date: sinceDate,
                        n: n
                    };

                    statusMessage.textContent = 'Crawling and analyzing Weibo data...';
                    statusDetails.textContent = `Searching for ${isKeywordSearch ? 'keyword: ' + keyword : 'user ID: ' + userId}`;

                    // Send the request to our local API endpoint
                    const response = await fetch(`${API_BASE_URL}/api/analyze`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(crawlData)
                    });

                    if (!response.ok) {
                        throw new Error(`Failed to analyze data: ${response.statusText}`);
                    }

                    const result = await response.json();

                    // Update progress to 100%
                    progress = 100;
                    progressBar.style.width = `${progress}%`;
                    progressBar.textContent = `${Math.round(progress)}%`;
                    progressBar.setAttribute('aria-valuenow', Math.round(progress));

                    // Clear progress interval
                    clearInterval(progressInterval);

                    // Display results
                    displayResults(
                        result.ngrams, 
                        result.wordcloud_image, 
                        {
                            searchTerm: isKeywordSearch ? keyword : userId,
                            searchType: isKeywordSearch ? 'Keyword' : 'User ID',
                            postCount: result.post_count,
                            maxRequested: maxCount,
                            sinceDate: sinceDate,
                            ngramType: n === 1 ? 'Unigrams' : (n === 2 ? 'Bigrams' : 'Trigrams')
                        }
                    );

                } catch (error) {
                    clearInterval(progressInterval);
                    showError(error.message);
                } finally {
                    // Hide loading state
                    loading.style.display = 'none';
                }
            });

            // Display results
            function displayResults(ngrams, wordcloudImage, summary) {
                // Update summary information
                summarySearchTerm.textContent = `${summary.searchType}: ${summary.searchTerm}`;
                summaryPostCount.textContent = `${summary.postCount} / ${summary.maxRequested} requested`;
                summaryDateRange.textContent = `Since ${summary.sinceDate}`;
                summaryNgramType.textContent = summary.ngramType;

                // Display word cloud
                wordcloudImg.src = `data:image/png;base64,${wordcloudImage}`;

                // Display N-grams
                ngramResults.innerHTML = '';
                ngrams.forEach((item, index) => {
                    const ngramItem = document.createElement('div');
                    ngramItem.className = 'ngram-item';
                    ngramItem.innerHTML = `
                        <div class="ngram-text">${item.ngram}</div>
                        <div class="ngram-count">${item.count}</div>
                    `;
                    ngramResults.appendChild(ngramItem);
                });

                // Show results container
                results.style.display = 'block';
            }

            // Show error message
            function showError(message) {
                errorMessage.textContent = message;
                errorDiv.style.display = 'block';
                setTimeout(() => {
                    errorDiv.style.display = 'none';
                }, 8000);
            }

            // Reset UI
            function resetUI() {
                errorDiv.style.display = 'none';
                results.style.display = 'none';
                wordcloudImg.src = '';
                ngramResults.innerHTML = '';
                progressBar.style.width = '0%';
                progressBar.textContent = '0%';
                progressBar.setAttribute('aria-valuenow', 0);
            }
        });
    </script>
</body>
</html>
"""


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

            # If text data is empty, return an error
            if not text_data.strip():
                return ""

            # Segment Chinese text
            text_data = " ".join(jieba.cut(text_data))

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
            wordcloud = WordCloud(**wordcloud_params).generate(text_data)

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
            # Serve the main HTML page
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode())
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

                # Prepare response
                response = {
                    "status": "success",
                    "post_count": post_count,
                    "ngrams": ngrams,
                    "wordcloud_image": wordcloud_image
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
    # Create data directory if it doesn't exist
    os.makedirs('./data', exist_ok=True)

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