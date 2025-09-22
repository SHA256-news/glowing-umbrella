#!/usr/bin/env python3
"""
Fetch Bitcoin mining news events using EventRegistry API with deduplication.

This script fetches recent Bitcoin mining news events from EventRegistry,
implements robust deduplication using event clustering, and maintains
a queue system to prevent reprocessing of events.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional
from eventregistry import EventRegistry, QueryEvents, RequestEventsInfo, QueryEventsIter, QueryItems


def load_processed_events(file_path: str = "processed_events.json") -> Set[str]:
    """
    Load previously processed event URIs from file.
    
    Args:
        file_path (str): Path to the processed events file.
    
    Returns:
        Set[str]: Set of previously processed event URIs.
    """
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get('processed_uris', []))
        return set()
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not load processed events file: {e}", file=sys.stderr)
        return set()


def load_existing_queue(file_path: str = "events.json") -> List[str]:
    """
    Load existing event URIs from the queue file.
    
    Args:
        file_path (str): Path to the events queue file.
    
    Returns:
        List[str]: List of event URIs currently in queue.
    """
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('event_uris', [])
        return []
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not load events queue file: {e}", file=sys.stderr)
        return []


def save_events_queue(event_uris: List[str], file_path: str = "events.json") -> None:
    """
    Save event URIs to the queue file.
    
    Args:
        event_uris (List[str]): List of event URIs to save.
        file_path (str): Path to the events queue file.
    """
    try:
        data = {
            'event_uris': event_uris,
            'updated_at': datetime.now().isoformat(),
            'total_events': len(event_uris)
        }
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(event_uris)} events to queue: {file_path}", file=sys.stderr)
    except IOError as e:
        print(f"Error saving events queue: {e}", file=sys.stderr)
        sys.exit(1)


def build_bitcoin_mining_query(recency_minutes: int = 90) -> QueryEvents:
    """
    Build EventRegistry query for Bitcoin mining news events.
    
    Args:
        recency_minutes (int): How far back to look for events in minutes.
    
    Returns:
        QueryEvents: Configured query for Bitcoin mining events.
    """
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(minutes=recency_minutes)
    
    # Keywords to include (Bitcoin mining related)
    include_keywords = [
        "bitcoin mining", "hashrate", "ASIC", "mining pools", "foundry",
        "block subsidy", "difficulty adjustment", "bitcoin price", 
        "bitcoin trading", "bitcoin ETF", "bitcoin investment", 
        "bitcoin speculation", "mining hardware", "mining farm",
        "bitcoin miner", "proof of work", "mining difficulty"
    ]
    
    # Build query with Bitcoin mining focus
    query = QueryEvents(
        keywords=QueryItems.AND(include_keywords[:5]),  # Use first 5 main keywords
        dateStart=start_date.date(),
        dateEnd=end_date.date(),
        lang="eng",  # English language
        minArticlesInEvent=2,  # Ensure it's a real event with multiple sources
        maxArticlesInEvent=50,  # Reasonable upper bound
        requestedResult=RequestEventsInfo(
            page=1,
            count=20,  # Get more events to filter from
            sortBy="relevance",
            returnInfo=None  # Use default return info
        )
    )
    
    return query


def filter_bitcoin_mining_events(events: List[Dict], exclude_other_cryptos: bool = True) -> List[Dict]:
    """
    Filter events to focus on Bitcoin-only mining, excluding other cryptocurrencies.
    
    Args:
        events (List[Dict]): List of events from EventRegistry.
        exclude_other_cryptos (bool): Whether to exclude other cryptocurrency mentions.
    
    Returns:
        List[Dict]: Filtered events focused on Bitcoin mining.
    """
    # Other cryptocurrency names and tickers to exclude
    exclude_crypto_terms = [
        "ethereum", "ETH", "litecoin", "LTC", "dogecoin", "DOGE", 
        "cardano", "ADA", "polygon", "MATIC", "solana", "SOL",
        "ripple", "XRP", "chainlink", "LINK", "polkadot", "DOT",
        "avalanche", "AVAX", "cosmos", "ATOM", "algorand", "ALGO",
        "stellar", "XLM", "monero", "XMR", "zcash", "ZEC",
        "dash", "DASH", "bitcoin cash", "BCH", "bitcoin SV", "BSV"
    ]
    
    # Bitcoin mining specific terms that should be present
    bitcoin_mining_terms = [
        "bitcoin", "mining", "hash", "ASIC", "miner", "pool",
        "difficulty", "subsidy", "proof of work", "SHA-256"
    ]
    
    filtered_events = []
    
    for event in events:
        title = event.get('title', {}).get('eng', '').lower()
        summary = event.get('summary', {}).get('eng', '').lower()
        combined_text = f"{title} {summary}"
        
        # Check if it mentions Bitcoin mining concepts
        has_bitcoin_mining = any(term.lower() in combined_text for term in bitcoin_mining_terms)
        
        if not has_bitcoin_mining:
            continue
        
        # Exclude if it mentions other cryptocurrencies (unless it's clearly Bitcoin-focused)
        if exclude_other_cryptos:
            bitcoin_mentions = combined_text.count('bitcoin')
            other_crypto_mentions = sum(1 for term in exclude_crypto_terms 
                                      if term.lower() in combined_text)
            
            # Skip if other cryptos are mentioned more than Bitcoin
            if other_crypto_mentions > 0 and bitcoin_mentions <= other_crypto_mentions:
                continue
        
        filtered_events.append(event)
    
    return filtered_events


def fetch_bitcoin_mining_events(api_key: Optional[str] = None, 
                               recency_minutes: int = 90,
                               max_events: int = 5) -> List[str]:
    """
    Fetch Bitcoin mining events from EventRegistry API.
    
    Args:
        api_key (Optional[str]): EventRegistry API key.
        recency_minutes (int): How far back to look for events in minutes.
        max_events (int): Maximum number of events to fetch.
    
    Returns:
        List[str]: List of event URIs.
    """
    if not api_key:
        api_key = os.getenv('EVENTREGISTRY_API_KEY')
        if not api_key:
            raise ValueError("EventRegistry API key not provided. Set EVENTREGISTRY_API_KEY environment variable.")
    
    try:
        er = EventRegistry(apiKey=api_key)
        
        # Build and execute query
        query = build_bitcoin_mining_query(recency_minutes)
        print(f"Fetching Bitcoin mining events from last {recency_minutes} minutes...", file=sys.stderr)
        
        # Execute query
        result = er.execQuery(query)
        
        if not result or 'events' not in result:
            print("No events found in API response", file=sys.stderr)
            return []
        
        events = result['events']['results']
        print(f"Found {len(events)} raw events from EventRegistry", file=sys.stderr)
        
        # Filter for Bitcoin-only mining events
        filtered_events = filter_bitcoin_mining_events(events)
        print(f"Filtered to {len(filtered_events)} Bitcoin mining events", file=sys.stderr)
        
        # Extract event URIs and limit to max_events
        event_uris = []
        for event in filtered_events[:max_events]:
            uri = event.get('uri')
            if uri:
                event_uris.append(uri)
                title = event.get('title', {}).get('eng', 'No title')
                print(f"  - {uri}: {title[:100]}...", file=sys.stderr)
        
        return event_uris
        
    except Exception as e:
        print(f"Error fetching events from EventRegistry: {e}", file=sys.stderr)
        return []


def main():
    """Main function to fetch news events with deduplication."""
    parser = argparse.ArgumentParser(description='Fetch Bitcoin mining news events with deduplication')
    parser.add_argument('--max-articles', type=int, default=5,
                       help='Maximum number of events to fetch (default: 5)')
    parser.add_argument('--recency-minutes', type=int, default=90,
                       help='How far back to look for events in minutes (default: 90)')
    parser.add_argument('--days-back', type=int,
                       help='Number of days back to search (converted to minutes)')
    parser.add_argument('--output', default='events.json',
                       help='Output file for event queue (default: events.json)')
    parser.add_argument('--output-format', choices=['json', 'uris'], default='json',
                       help='Output format: json (default) or uris (one URI per line)')
    parser.add_argument('--processed-file', default='processed_events.json',
                       help='File tracking processed events (default: processed_events.json)')
    parser.add_argument('--force', action='store_true',
                       help='Skip deduplication and fetch events anyway')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be fetched without making API calls')
    
    args = parser.parse_args()
    
    # Convert days-back to recency-minutes if provided
    if args.days_back is not None:
        args.recency_minutes = args.days_back * 24 * 60  # Convert days to minutes
    
    try:
        # Load existing processed events for deduplication
        processed_events = set()
        if not args.force:
            processed_events = load_processed_events(args.processed_file)
            print(f"Loaded {len(processed_events)} previously processed events", file=sys.stderr)
        
        # Load existing queue
        existing_queue = load_existing_queue(args.output)
        existing_queue_set = set(existing_queue)
        print(f"Found {len(existing_queue)} events already in queue", file=sys.stderr)
        
        # Fetch new events
        print(f"Fetching up to {args.max_articles} events from last {args.recency_minutes} minutes...", file=sys.stderr)
        
        if args.dry_run:
            print("🧪 DRY RUN MODE: No API calls will be made", file=sys.stderr)
            # Simulate some events for dry run
            new_event_uris = [f"dry-run-event-{i}" for i in range(1, min(args.max_articles + 1, 4))]
            print(f"Simulated {len(new_event_uris)} events for dry run", file=sys.stderr)
        else:
            new_event_uris = fetch_bitcoin_mining_events(
                recency_minutes=args.recency_minutes,
                max_events=args.max_articles
            )
        
        if not new_event_uris:
            print("No new events found", file=sys.stderr)
            if args.output_format == 'uris':
                # For uris format, output existing queue URIs if no new events
                for uri in existing_queue:
                    print(uri)
            return
        
        # Deduplicate against processed events and existing queue
        unique_new_events = []
        for uri in new_event_uris:
            if uri not in processed_events and uri not in existing_queue_set:
                unique_new_events.append(uri)
            else:
                print(f"Skipping already processed/queued event: {uri}", file=sys.stderr)
        
        if not unique_new_events:
            print("All fetched events were already processed or queued", file=sys.stderr)
            if args.output_format == 'uris':
                # For uris format, output existing queue URIs if no new events
                for uri in existing_queue:
                    print(uri)
            return
        
        # Combine with existing queue and save
        updated_queue = existing_queue + unique_new_events
        save_events_queue(updated_queue, args.output)
        
        print(f"✅ Added {len(unique_new_events)} new events to queue", file=sys.stderr)
        print(f"📊 Total events in queue: {len(updated_queue)}", file=sys.stderr)
        
        # Output based on format
        if args.output_format == 'uris':
            # For uris format, output all URIs in the queue (one per line)
            for uri in updated_queue:
                print(uri)
        else:
            # Default JSON format for pipeline integration
            summary = {
                'new_events_added': len(unique_new_events),
                'total_events_in_queue': len(updated_queue),
                'fetch_time': datetime.now().isoformat(),
                'new_event_uris': unique_new_events
            }
            print(json.dumps(summary, indent=2))
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()