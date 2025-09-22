#!/usr/bin/env python3
"""
Fetch Bitcoin-related events using EventRegistry API.

This script fetches recent events related to Bitcoin and cryptocurrency mining
using the EventRegistry API and outputs relevant event information.
Events are aggregations of related articles about the same story/topic.
"""

import os
import sys
import json
from datetime import datetime, timedelta
from eventregistry import EventRegistry, QueryEvents, QueryEventsIter


def fetch_bitcoin_events(api_key=None, max_events=10, days_back=7):
    """
    Fetch recent events related to Bitcoin and cryptocurrency mining.
    
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
    
    # Search keywords related to Bitcoin and cryptocurrency mining
    keywords = [
        "Bitcoin",
        "cryptocurrency mining",
        "Bitcoin mining",
        "Bitcoin hashrate",
        "mining pools",
        "Bitcoin miners",
        "cryptocurrency",
        "blockchain mining"
    ]
    
    events = []
    
    try:
        # Create query for events
        q = QueryEventsIter(
            keywords=" OR ".join(f'"{kw}"' for kw in keywords),
            dateStart=start_date.strftime('%Y-%m-%d'),
            dateEnd=end_date.strftime('%Y-%m-%d'),
            lang="eng"
        )
        
        # Fetch events
        count = 0
        for event in q.execQuery(er, maxItems=max_events):
            if count >= max_events:
                break
                
            event_data = {
                'uri': event.get('uri'),
                'title': event.get('title', {}).get('eng', 'No title available'),
                'summary': event.get('summary', {}).get('eng', 'No summary available'),
                'eventDate': event.get('eventDate'),
                'articleCounts': event.get('articleCounts', {}),
                'concepts': [concept.get('label', {}).get('eng', '') for concept in event.get('concepts', [])[:5]],
                'categories': [cat.get('label', {}).get('eng', '') for cat in event.get('categories', [])[:3]],
                'location': event.get('location', {}).get('label', {}).get('eng', 'Unknown'),
                'relevance': event.get('wgt', 0)
            }
            
            # Filter for Bitcoin/mining/cryptocurrency relevance
            content = f"{event_data['title']} {event_data['summary']} {' '.join(event_data['concepts'])}".lower()
            if any(term in content for term in ['bitcoin', 'mining', 'hashrate', 'cryptocurrency', 'blockchain']):
                events.append(event_data)
                count += 1
                
    except Exception as e:
        print(f"Error fetching events: {e}", file=sys.stderr)
        return []
    
    return events


def main():
    """Main function to fetch and output Bitcoin-related events."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch Bitcoin-related events')
    parser.add_argument('--max-events', type=int, default=10, 
                       help='Maximum number of events to fetch (default: 10)')
    parser.add_argument('--days-back', type=int, default=7,
                       help='Number of days back to search (default: 7)')
    parser.add_argument('--output-format', choices=['json', 'uris', 'summary'], default='json',
                       help='Output format: json for full data, uris for just event URIs, summary for brief overview')
    
    args = parser.parse_args()
    
    try:
        events = fetch_bitcoin_events(
            max_events=args.max_events,
            days_back=args.days_back
        )
        
        if not events:
            print("No relevant events found.", file=sys.stderr)
            sys.exit(1)
        
        if args.output_format == 'uris':
            # Output just the URIs for pipeline usage
            for event in events:
                print(event['uri'])
        elif args.output_format == 'summary':
            # Output brief summary for quick overview
            print(f"Found {len(events)} Bitcoin-related events in the last {args.days_back} days:\n")
            for i, event in enumerate(events, 1):
                print(f"{i}. {event['title']}")
                print(f"   Date: {event['eventDate']}")
                print(f"   Articles: {event['articleCounts'].get('total', 'Unknown')}")
                print(f"   Location: {event['location']}")
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