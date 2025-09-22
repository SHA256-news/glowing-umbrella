#!/usr/bin/env python3
"""
Fetch Bitcoin-related events using EventRegistry API.

This script fetches recent events related to Bitcoin mining, cryptocurrency,
and blockchain using the EventRegistry API and outputs relevant event data.
"""

import os
import sys
import json
from datetime import datetime, timedelta
from eventregistry import EventRegistry, QueryEventsIter


def fetch_bitcoin_events(api_key=None, max_events=10, days_back=7):
    """
    Fetch recent events about Bitcoin and cryptocurrency mining.
    
    Args:
        api_key (str): EventRegistry API key. If None, reads from EVENTREGISTRY_API_KEY env var.
        max_events (int): Maximum number of events to fetch.
        days_back (int): How many days back to search for events.
    
    Returns:
        list: List of dictionaries containing event information.
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
    
    # Search keywords related to Bitcoin events
    keywords = [
        "Bitcoin",
        "Bitcoin mining",
        "cryptocurrency",
        "blockchain",
        "Bitcoin price",
        "Bitcoin adoption",
        "Bitcoin regulation",
        "mining farms",
        "Bitcoin hashrate",
        "Bitcoin network"
    ]
    
    events = []
    
    try:
        # Create query for events
        q = QueryEventsIter(
            keywords=" OR ".join(f'"{kw}"' for kw in keywords),
            dateStart=start_date.strftime('%Y-%m-%d'),
            dateEnd=end_date.strftime('%Y-%m-%d'),
            lang="eng",
            minArticlesInEvent=2  # Ensure events have multiple articles
        )
        
        # Fetch events
        count = 0
        for event in q.execQuery(er, maxItems=max_events):
            if count >= max_events:
                break
                
            event_data = {
                'uri': event.get('uri'),
                'title': event.get('title', {}).get('eng', 'No title'),
                'summary': event.get('summary', {}).get('eng', 'No summary'),
                'eventDate': event.get('eventDate'),
                'totalArticleCount': event.get('totalArticleCount', 0),
                'location': event.get('location'),
                'categories': [cat.get('label', {}).get('eng', '') for cat in event.get('categories', [])],
                'concepts': [concept.get('label', {}).get('eng', '') for concept in event.get('concepts', [])[:5]],
                'relevance': event.get('relevance', 0)
            }
            
            # Filter for Bitcoin/crypto relevance
            content = f"{event_data['title']} {event_data['summary']}".lower()
            bitcoin_terms = ['bitcoin', 'btc', 'cryptocurrency', 'crypto', 'blockchain']
            mining_terms = ['mining', 'hashrate', 'miners', 'asic', 'proof of work']
            
            # Check if content contains Bitcoin terms and is relevant
            if any(term in content for term in bitcoin_terms):
                # Add mining relevance score
                mining_score = sum(1 for term in mining_terms if term in content)
                event_data['mining_relevance_score'] = mining_score
                
                events.append(event_data)
                count += 1
                
    except Exception as e:
        print(f"Error fetching events: {e}", file=sys.stderr)
        return []
    
    # Sort by relevance and mining score
    events.sort(key=lambda x: (x.get('mining_relevance_score', 0), x.get('relevance', 0)), reverse=True)
    
    return events


def main():
    """Main function to fetch and output Bitcoin-related events."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch Bitcoin-related events from EventRegistry')
    parser.add_argument('--max-events', type=int, default=10, 
                       help='Maximum number of events to fetch (default: 10)')
    parser.add_argument('--days-back', type=int, default=7,
                       help='Number of days back to search (default: 7)')
    parser.add_argument('--output-format', choices=['json', 'uris', 'summary'], default='json',
                       help='Output format: json for full data, uris for just event URIs, summary for brief overview')
    parser.add_argument('--min-mining-relevance', type=int, default=0,
                       help='Minimum mining relevance score (0-5, default: 0)')
    
    args = parser.parse_args()
    
    try:
        events = fetch_bitcoin_events(
            max_events=args.max_events,
            days_back=args.days_back
        )
        
        if not events:
            print("No relevant events found.", file=sys.stderr)
            sys.exit(1)
        
        # Filter by minimum mining relevance if specified
        if args.min_mining_relevance > 0:
            events = [e for e in events if e.get('mining_relevance_score', 0) >= args.min_mining_relevance]
        
        if args.output_format == 'uris':
            # Output just the URIs for pipeline usage
            for event in events:
                print(event['uri'])
        elif args.output_format == 'summary':
            # Output brief summary format
            print(f"Found {len(events)} Bitcoin-related events:")
            print("-" * 50)
            for i, event in enumerate(events, 1):
                print(f"{i}. {event['title']}")
                print(f"   Date: {event['eventDate']}")
                print(f"   Articles: {event['totalArticleCount']}")
                print(f"   Mining Relevance: {event.get('mining_relevance_score', 0)}")
                print(f"   URI: {event['uri']}")
                print()
        else:
            # Output full JSON data
            print(json.dumps(events, indent=2, ensure_ascii=False))
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()