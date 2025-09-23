#!/bin/bash
#
# Performance-optimized wrapper for fetch_news.py
# This script provides optimized defaults for faster execution
#

set -e

# Default values optimized for performance
MAX_ARTICLES=${1:-5}
DAYS_BACK=${2:-1}  # Reduced from 7 to 1 day for much better performance
OUTPUT_FORMAT=${3:-uris}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Fetching Bitcoin news with performance optimizations..." >&2
echo "📊 Searching last $DAYS_BACK day(s) for up to $MAX_ARTICLES articles" >&2

# Use fast mode and optimized parameters
python3 "$SCRIPT_DIR/fetch_news.py" \
    --max-articles "$MAX_ARTICLES" \
    --days-back "$DAYS_BACK" \
    --output-format "$OUTPUT_FORMAT" \
    --fast-mode \
    2>/dev/null || {
        echo "⚠️  Fast fetch failed, trying with smaller time window..." >&2
        # Fallback to even smaller window if the optimized one fails
        python3 "$SCRIPT_DIR/fetch_news.py" \
            --max-articles "$MAX_ARTICLES" \
            --recency-minutes 120 \
            --output-format "$OUTPUT_FORMAT" \
            --fast-mode
    }