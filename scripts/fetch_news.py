#!/usr/bin/env python3
"""
Fetch news articles related to Bitcoin-only mining using EventRegistry API.

This script fetches recent news articles related to 'Bitcoin-only mining' 
using the EventRegistry API and outputs relevant event URIs.
"""

import os
import sys
import json
from datetime import datetime, timedelta
from eventregistry import EventRegistry, QueryArticlesIter


def fetch_bitcoin_mining_news(api_key=None, max_articles=10, days_back=7):
    """
    Fetch recent news articles about Bitcoin-only mining.
    
    Args:
        api_key (str): EventRegistry API key. If None, reads from EVENTREGISTRY_API_KEY env var.
        max_articles (int): Maximum number of articles to fetch.
        days_back (int): How many days back to search for articles.
    
    Returns:
        list: List of dictionaries containing article information.
    """
    if not api_key:
        api_key = os.getenv('EVENTREGISTRY_API_KEY')
        if not api_key:
            raise ValueError("EventRegistry API key not provided. Set EVENTREGISTRY_API_KEY environment variable.")
    
    # Initialize EventRegistry
    er = EventRegistry(apiKey=api_key)
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    # Search keywords related to Bitcoin-only mining
    keywords = [
        "Bitcoin mining",
        "Bitcoin-only mining",
        "cryptocurrency mining",
        "Bitcoin hashrate",
        "mining pools",
        "Bitcoin miners"
    ]
    
    articles = []
    
    try:
        # Create query for articles
        q = QueryArticlesIter(
            keywords=" OR ".join(f'"{kw}"' for kw in keywords),
            dateStart=start_date.strftime('%Y-%m-%d'),
            dateEnd=end_date.strftime('%Y-%m-%d'),
            lang="eng"
        )
        
        # Fetch articles
        count = 0
        for article in q.execQuery(er, maxItems=max_articles):
            if count >= max_articles:
                break
                
            article_data = {
                'uri': article.get('uri'),
                'title': article.get('title'),
                'body': article.get('body', '')[:500] + '...' if len(article.get('body', '')) > 500 else article.get('body', ''),
                'url': article.get('url'),
                'source': article.get('source', {}).get('title', 'Unknown'),
                'date': article.get('date'),
                'relevance': article.get('relevance', 0)
            }
            
            # Filter for Bitcoin/mining relevance
            content = f"{article_data['title']} {article_data['body']}".lower()
            if any(term in content for term in ['bitcoin', 'mining', 'hashrate', 'cryptocurrency']):
                articles.append(article_data)
                count += 1
                
    except Exception as e:
        print(f"Error fetching articles: {e}", file=sys.stderr)
        return []
    
    return articles


def main():
    """Main function to fetch and output Bitcoin mining news."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch Bitcoin-only mining news articles')
    parser.add_argument('--max-articles', type=int, default=10, 
                       help='Maximum number of articles to fetch (default: 10)')
    parser.add_argument('--days-back', type=int, default=7,
                       help='Number of days back to search (default: 7)')
    parser.add_argument('--output-format', choices=['json', 'uris'], default='json',
                       help='Output format: json for full data, uris for just event URIs')
    
    args = parser.parse_args()
    
    try:
        articles = fetch_bitcoin_mining_news(
            max_articles=args.max_articles,
            days_back=args.days_back
        )
        
        if not articles:
            print("No relevant articles found.", file=sys.stderr)
            sys.exit(1)
        
        if args.output_format == 'uris':
            # Output just the URIs for pipeline usage
            for article in articles:
                print(article['uri'])
        else:
            # Output full JSON data
            print(json.dumps(articles, indent=2, ensure_ascii=False))
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()