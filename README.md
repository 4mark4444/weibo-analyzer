# Weibo Analysis Dashboard

An integrated application for crawling, analyzing, and visualizing Weibo data.

## Overview

This project provides a web-based dashboard for analyzing Weibo content through N-gram analysis, word clouds, and engagement metrics. It consists of a Python backend with a simple HTTP server and an interactive HTML/JavaScript frontend.

## Features

- **Crawl Weibo data** by keyword or user ID
- **Generate word clouds** to visualize frequently used terms
- **N-gram analysis** to identify common phrases
- **Time series visualization** of post frequency
- **Engagement metrics** showing top posts by likes, comments, and reposts
- **Responsive web interface** for easy analysis

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/weibo-analysis-dashboard.git
   cd weibo-analysis-dashboard
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Make sure you have a Chinese font installed on your system for proper word cloud rendering.

## Usage

1. Run the application:
   ```
   python backend/app.py [port]
   ```
   Default port is 8080 if not specified.

2. A browser window will automatically open with the dashboard.

3. Enter a keyword or Weibo user ID, set the parameters, and click "Analyze" to start the crawling and analysis process.

4. Navigate through the analysis tabs to view different visualizations and insights.

## Credits

The Weibo crawler functionality is based on the [weibo-crawler](https://github.com/dataabc/weibo-crawler) project by dataabc, modified to integrate with the dashboard application.

## Note

This application is for educational and research purposes only. Please respect Weibo's terms of service and API rate limits when using this tool.