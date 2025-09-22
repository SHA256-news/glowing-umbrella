# glowing-umbrella

Automated news pipeline for Bitcoin-only mining content generation and distribution.

## Overview

This repository contains an automated pipeline that:
1. Fetches recent news articles about Bitcoin-only mining
2. Generates comprehensive articles using AI
3. Creates Twitter thread summaries
4. Publishes content through GitHub Actions workflows

## Components

### Python Scripts (`scripts/`)

- **`fetch_news.py`**: Fetches Bitcoin mining news using EventRegistry API
- **`fetch_bitcoin_events.py`**: Fetches Bitcoin-related events using EventRegistry API
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
# Fetch news articles
python scripts/fetch_news.py --max-articles 5 --days-back 7

# Fetch Bitcoin-related events
python scripts/fetch_bitcoin_events.py --max-events 5 --days-back 7 --output-format summary

# Generate article from event URI
python scripts/generate_article.py <event_uri> --output article.json

# Create Twitter thread summary
python scripts/create_summary.py article.json --format text
```

### Automated Workflows

The workflows run automatically:
- `publish_article.yml`: Daily at 9 AM UTC
- `post_to_twitter.yml`: Triggered after article generation

Manual triggers are also available via GitHub Actions interface.

## License

MIT License - see [LICENSE](LICENSE) file for details.