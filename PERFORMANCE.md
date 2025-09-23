# Performance Optimization Guide

## Problem
The `fetch_news.py` script was running slowly, especially with large time windows like `--days-back 7` (10,080 minutes).

## Root Causes Identified

1. **Massive Time Windows**: Default 7-day search window causes slow EventRegistry API queries
2. **Over-fetching**: Requesting 30 events from API when only needing 5
3. **Inefficient Filtering**: Processing all events before limiting to desired count
4. **No Timeout Protection**: Scripts could hang on slow API responses
5. **Complex Queries**: Multiple OR/AND keyword combinations causing slower searches

## Optimizations Implemented

### 1. Smart Time Window Management
- **Fast Mode**: Automatically limits large time windows (>1 day) to 1 day for performance
- **Performance Warnings**: Alerts users when using slow configurations
- **Time Window Limits**: Maximum 30-day limit to prevent extremely slow queries

### 2. Optimized API Requests
- **Reduced Count**: Request only 3x needed events (max 15) instead of 30
- **Simplified Keywords**: Use most specific terms first, fewer OR/AND combinations
- **Sort by Date**: Get most recent events first instead of "relevance" sorting

### 3. Efficient Filtering
- **Early Termination**: Stop processing when enough events found
- **Priority Filtering**: Check most common exclusions first
- **Optimized String Operations**: Reduce text processing overhead

### 4. Timeout and Error Handling
- **30-second API Timeout**: Prevents hanging on slow queries
- **Graceful Fallbacks**: Multiple retry strategies with smaller windows
- **Clear Error Messages**: Better guidance for performance issues

### 5. Performance-Optimized Modes
- **`--fast-mode`**: Automatic performance optimizations
- **Shell Wrapper**: `fetch_btc_news.sh` with optimized defaults
- **Updated Workflows**: Default to 1-day windows instead of 7-day

## Performance Improvements

### Workflow Changes
- **Default Time Window**: Reduced from 7 days to 1 day (7x faster API queries)
- **Fallback Strategy**: Automatic retry with 8-hour window if 1-day fails
- **Fast Mode Integration**: All automation uses optimized settings

### API Efficiency
- **Request Size**: Reduced from 30 to 15 events max (~50% fewer API calls)
- **Query Complexity**: Simplified keyword matching for faster searches
- **Processing Speed**: Early termination and optimized filtering

### Expected Results
- **Typical Speed**: 1-day searches should complete in seconds instead of minutes
- **Large Queries**: Even 7-day searches now limited to 1-day with fast mode
- **Reliability**: Timeout protection prevents indefinite hangs

## Usage Recommendations

### For Manual Use
```bash
# Fast (recommended)
python scripts/fetch_news.py --fast-mode --days-back 1 --max-articles 5

# Ultra-fast using wrapper
scripts/fetch_btc_news.sh 5 1

# Avoid slow configurations
python scripts/fetch_news.py --days-back 30 --max-articles 50  # This will be slow!
```

### For Automation
- Use `--fast-mode` flag always
- Limit `--days-back` to 1-2 days maximum
- Keep `--max-articles` under 10 for best performance
- Use the optimized shell wrapper when possible

## Implementation Files Modified

1. **`scripts/fetch_news.py`**: Core optimizations and fast mode
2. **`scripts/fetch_btc_news.sh`**: Performance-optimized wrapper (NEW)
3. **`.github/workflows/publish_article.yml`**: Updated workflow defaults
4. **`README.md`**: Added performance guidelines and examples

## Monitoring Performance

The script now provides better feedback:
- Warnings for large time windows
- Query optimization details
- Performance timing in logs
- Clear error messages for timeouts