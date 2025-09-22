# glowing-umbrella

Automated news pipeline for Bitcoin-only mining content generation and distribution.

## Overview

This repository contains an automated pipeline that:
1. Fetches recent news events about Bitcoin-only mining with deduplication
2. Generates comprehensive articles using AI
3. Creates Twitter thread summaries
4. Publishes content through GitHub Actions workflows

## Components

### Python Scripts (`scripts/`)

- **`fetch_news.py`**: Fetches Bitcoin mining news events using EventRegistry API with robust deduplication system
- **`generate_article.py`**: Generates articles from news events using Google Gemini API  
- **`create_summary.py`**: Creates Twitter thread summaries from generated articles

### GitHub Actions Workflows (`.github/workflows/`)

- **`publish_article.yml`**: Daily scheduled workflow for news fetching and article generation
- **`post_to_twitter.yml`**: Workflow for creating and posting Twitter summaries

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure API keys as repository secrets:
   - `EVENTREGISTRY_API_KEY`: EventRegistry API key
   - `GEMINI_API_KEY`: Google Gemini API key
   - Twitter API credentials (for posting functionality)

## Usage

### Manual Script Usage

```bash
# Fetch Bitcoin mining news events (saves to events.json)
python scripts/fetch_news.py --max-articles 5 --recency-minutes 90

# Fetch with custom options
python scripts/fetch_news.py --max-articles 10 --recency-minutes 1440 --output custom_events.json

# Generate article from event URI
python scripts/generate_article.py <event_uri> --output article.json

# Create Twitter thread summary
python scripts/create_summary.py article.json --format text
```

### Deduplication System

The `fetch_news.py` script implements a robust deduplication system:

1. **Event Clustering**: Uses EventRegistry's event clustering to get unique news stories rather than duplicate articles
2. **Temporal Deduplication**: Maintains `processed_events.json` to track previously processed events
3. **Queue Management**: Uses `events.json` as a queue for new events to be processed
4. **Bitcoin-Only Filtering**: Focuses on Bitcoin mining while excluding other cryptocurrencies

**Files used by the system:**
- `events.json`: Queue of event URIs waiting to be processed
- `processed_events.json`: Long-term memory of all events that have been published

### Automated Workflows

The workflows run automatically:
- `publish_article.yml`: Daily at 9 AM UTC
- `post_to_twitter.yml`: Triggered after article generation

Manual triggers are also available via GitHub Actions interface.

## License

MIT License - see [LICENSE](LICENSE) file for details.