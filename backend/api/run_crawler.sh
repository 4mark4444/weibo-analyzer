#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to display usage information
function show_usage {
    echo -e "${BLUE}Weibo Crawler Test Script${NC}"
    echo ""
    echo "Usage: ./run_crawler.sh [options]"
    echo ""
    echo "Options:"
    echo "  -k, --keyword KEYWORD      Search by keyword"
    echo "  -u, --user USER_ID         Search by user ID"
    echo "  -n, --num-posts NUMBER     Maximum number of posts to crawl (default: 10)"
    echo "  -s, --since-date DATE      Crawl posts since this date (YYYY-MM-DD, default: 2023-01-01)"
    echo "  -o, --output DIR           Output directory (default: ./data/test)"
    echo "  -h, --help                 Show this help message"
    echo ""
    echo "Example: ./run_crawler.sh -k \"新冠\" -n 50"
    echo "Example: ./run_crawler.sh --user \"1234567890\" --num-posts 100"
}

# Default values
KEYWORD=""
USER_ID=""
MAX_POSTS=10
SINCE_DATE="2023-01-01"
OUTPUT_DIR="./data/test"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -k|--keyword)
            KEYWORD="$2"
            shift 2
            ;;
        -u|--user)
            USER_ID="$2"
            shift 2
            ;;
        -n|--num-posts)
            MAX_POSTS="$2"
            shift 2
            ;;
        -s|--since-date)
            SINCE_DATE="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            show_usage
            exit 1
            ;;
    esac
done

# Validate inputs
if [[ -z "$KEYWORD" && -z "$USER_ID" ]]; then
    echo -e "${RED}Error: Either keyword (-k) or user ID (-u) must be provided.${NC}"
    show_usage
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Configure Python script
PYTHON_SCRIPT=$(cat << EOF
import sys
import os
sys.path.append('./backend/crawler')

try:
    from weibo_crawler import crawler

    # Set up crawler parameters
    config = {
        'filter': 1,
        'since_date': '$SINCE_DATE',
        'write_mode': ['csv'],
        'pic_download': 0,
        'video_download': 0,
        'max_count': $MAX_POSTS
    }

    # Create output directory
    os.makedirs('$OUTPUT_DIR', exist_ok=True)

    # Print configuration
    print(f"Crawler configuration:")
    print(f"  {'Keyword' if '$KEYWORD' else 'User ID'}: {'$KEYWORD' or '$USER_ID'}")
    print(f"  Max posts: {config['max_count']}")
    print(f"  Since date: {config['since_date']}")
    print(f"  Output directory: $OUTPUT_DIR")
    print("Starting crawler...")

    # Execute crawler
    if '$KEYWORD':
        crawler.crawl_by_keyword('$KEYWORD', config, '$OUTPUT_DIR')
    else:
        crawler.crawl_by_user_id('$USER_ID', config, '$OUTPUT_DIR')

    print("Crawling completed!")
except Exception as e:
    print(f"Error: {str(e)}")
    sys.exit(1)
EOF
)

# Run the Python script
echo -e "${GREEN}Starting Weibo Crawler...${NC}"
echo -e "${YELLOW}This may take some time depending on the number of posts.${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop the crawler at any time.${NC}"
echo ""

python -c "$PYTHON_SCRIPT"

# Check if the script was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Crawler completed successfully!${NC}"
    echo -e "Output saved to: ${BLUE}$OUTPUT_DIR${NC}"
    
    # Count the number of items crawled
    CSV_COUNT=$(find "$OUTPUT_DIR" -name "*.csv" | wc -l)
    
    if [ $CSV_COUNT -gt 0 ]; then
        FIRST_CSV=$(find "$OUTPUT_DIR" -name "*.csv" | head -1)
        LINES=$(wc -l < "$FIRST_CSV")
        POSTS=$((LINES - 1)) # Subtract 1 for header line
        
        echo -e "${GREEN}$POSTS posts crawled and saved to CSV.${NC}"
    else
        echo -e "${YELLOW}No CSV files found in output directory.${NC}"
    fi
else
    echo -e "${RED}Crawler failed.${NC}"
    exit 1
fi
