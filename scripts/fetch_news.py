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


class APITimeoutError(Exception):
    """Custom exception for API timeout errors to distinguish from other errors."""
    pass


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


def build_simple_bitcoin_query(recency_minutes: int = 30, max_events: int = 5) -> QueryEvents:
    """
    Build a simplified EventRegistry query for Bitcoin news when standard mining queries fail.
    
    Args:
        recency_minutes (int): How far back to look for events in minutes.
        max_events (int): Maximum number of events needed (to optimize API request).
    
    Returns:
        QueryEvents: Simplified query for Bitcoin events.
    """
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(minutes=recency_minutes)
    
    # Use very simple query strategy for better API reliability
    query = QueryEvents(
        keywords="bitcoin",  # Single keyword for fastest search
        dateStart=start_date.date(),
        dateEnd=end_date.date(),
        lang="eng",  # English language
        minArticlesInEvent=1,  # Allow single-article events
        maxArticlesInEvent=10,  # Smaller upper bound for speed
        requestedResult=RequestEventsInfo(
            page=1,
            count=min(max_events * 2, 10),  # Request only 2x what we need, max 10
            sortBy="date",  # Sort by date for most recent first
            returnInfo=None  # Use default return info
        )
    )
    
    return query


def build_bitcoin_mining_query(recency_minutes: int = 90, max_events: int = 5) -> QueryEvents:
    """
    Build EventRegistry query for Bitcoin mining news events.
    
    Args:
        recency_minutes (int): How far back to look for events in minutes.
        max_events (int): Maximum number of events needed (to optimize API request).
    
    Returns:
        QueryEvents: Configured query for Bitcoin mining events.
    """
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(minutes=recency_minutes)
    
    # Limit very large time windows for performance
    max_days = 30  # Maximum 30 days for performance
    max_minutes = max_days * 24 * 60
    if recency_minutes > max_minutes:
        print(f"Warning: Large time window ({recency_minutes} minutes = {recency_minutes//1440} days). "
              f"Limiting to {max_days} days for performance.", file=sys.stderr)
        recency_minutes = max_minutes
        start_date = end_date - timedelta(minutes=recency_minutes)
    
    # Use simpler keyword strategy for better performance
    # Focus on most specific terms first
    query = QueryEvents(
        keywords=QueryItems.OR([
            "bitcoin mining",    # Most specific term
            "bitcoin miner",     # Second most specific
            QueryItems.AND(["bitcoin", "hashrate"]),    # Bitcoin + mining indicator
            QueryItems.AND(["bitcoin", "ASIC"]),        # Bitcoin + mining hardware
        ]),
        dateStart=start_date.date(),
        dateEnd=end_date.date(),
        lang="eng",  # English language
        minArticlesInEvent=1,  # Allow single-article events
        maxArticlesInEvent=20,  # Reduced upper bound for performance
        requestedResult=RequestEventsInfo(
            page=1,
            count=min(max_events * 3, 15),  # Request only ~3x what we need, max 15
            sortBy="date",  # Sort by date for most recent first
            returnInfo=None  # Use default return info
        )
    )
    
    return query


def filter_bitcoin_mining_events(events: List[Dict], exclude_other_cryptos: bool = True, max_events: int = 5) -> List[Dict]:
    """
    Filter events to focus on Bitcoin-only mining, excluding other cryptocurrencies.
    Optimized to stop processing once we have enough events.
    
    Args:
        events (List[Dict]): List of events from EventRegistry.
        exclude_other_cryptos (bool): Whether to exclude other cryptocurrency mentions.
        max_events (int): Maximum number of events needed (for early termination).
    
    Returns:
        List[Dict]: Filtered events focused on Bitcoin mining.
    """
    # Prioritized other cryptocurrency terms to exclude (most common first)
    exclude_crypto_terms = [
        "ethereum", "ETH", "bitcoin cash", "BCH", "litecoin", "LTC", 
        "dogecoin", "DOGE", "solana", "SOL", "cardano", "ADA",
        "ripple", "XRP", "polygon", "MATIC", "avalanche", "AVAX"
    ]
    
    # Essential Bitcoin mining terms (simplified for performance)
    bitcoin_terms = ["bitcoin", "mining", "miner", "hashrate", "ASIC"]
    
    filtered_events = []
    
    for event in events:
        # Early termination if we have enough events
        if len(filtered_events) >= max_events * 2:  # Get 2x to allow for further filtering
            break
            
        title = event.get('title', {}).get('eng', '').lower()
        summary = event.get('summary', {}).get('eng', '').lower()
        combined_text = f"{title} {summary}"
        
        # Quick Bitcoin check first (most efficient)
        if 'bitcoin' not in combined_text:
            continue
            
        # Check for mining relevance
        has_mining_context = any(term in combined_text for term in ['mining', 'miner', 'hashrate', 'asic'])
        if not has_mining_context:
            continue
        
        # Quick exclusion check (only if needed)
        if exclude_other_cryptos:
            bitcoin_count = combined_text.count('bitcoin')
            # Check only most common competing cryptos for performance
            other_crypto_count = sum(1 for term in exclude_crypto_terms[:8] 
                                   if term.lower() in combined_text)
            
            # Skip if other cryptos dominate
            if other_crypto_count > 0 and bitcoin_count <= other_crypto_count:
                continue
        
        filtered_events.append(event)
    
    return filtered_events


def fetch_bitcoin_mining_events_with_fallback(api_key: Optional[str] = None,
                                             recency_minutes: int = 90,
                                             max_events: int = 5) -> List[str]:
    """
    Fetch Bitcoin mining events with progressive fallback to smaller time windows and simpler queries.
    
    Args:
        api_key (Optional[str]): EventRegistry API key.
        recency_minutes (int): Initial time window to try.
        max_events (int): Maximum number of events to fetch.
    
    Returns:
        List[str]: List of event URIs.
    """
    # Progressive fallback windows (in minutes) - more granular fallbacks
    fallback_windows = [
        recency_minutes,  # Original requested window
        min(recency_minutes, 240),  # 4 hours max
        min(recency_minutes, 120),  # 2 hours max
        min(recency_minutes, 60),   # 1 hour max
        30,  # 30 minutes
        15,  # 15 minutes - very recent news only
        5,   # 5 minutes - ultra-recent fallback
    ]
    
    # Remove duplicates while preserving order
    fallback_windows = list(dict.fromkeys(fallback_windows))
    
    # First try standard mining queries
    for i, window_minutes in enumerate(fallback_windows):
        try:
            print(f"Attempting standard mining query with {window_minutes} minute window...", file=sys.stderr)
            return fetch_bitcoin_mining_events(api_key, window_minutes, max_events, use_simple_query=False)
        except APITimeoutError:
            if i < len(fallback_windows) - 1:  # Not the last attempt
                next_window = fallback_windows[i + 1]
                print(f"API timeout with {window_minutes} minutes. Trying {next_window} minutes...", file=sys.stderr)
                continue
            else:  # Last standard attempt failed
                print(f"All standard mining query attempts failed. Trying simplified Bitcoin queries...", file=sys.stderr)
                break
    
    # If all standard queries failed, try simplified queries with smaller windows
    simple_windows = [30, 15, 5]  # Only try small windows for simple queries
    
    for i, window_minutes in enumerate(simple_windows):
        try:
            print(f"Attempting simplified Bitcoin query with {window_minutes} minute window...", file=sys.stderr)
            return fetch_bitcoin_mining_events(api_key, window_minutes, max_events, use_simple_query=True)
        except APITimeoutError:
            if i < len(simple_windows) - 1:  # Not the last attempt
                next_window = simple_windows[i + 1]
                print(f"Simple query timeout with {window_minutes} minutes. Trying {next_window} minutes...", file=sys.stderr)
                continue
            else:  # Last attempt failed
                print(f"All fallback attempts failed. API appears to be having performance issues.", file=sys.stderr)
                raise APITimeoutError("All progressive fallback attempts timed out")
    
    return []  # Should never reach here


def fetch_bitcoin_mining_events(api_key: Optional[str] = None, 
                               recency_minutes: int = 90,
                               max_events: int = 5,
                               use_simple_query: bool = False) -> List[str]:
    """
    Fetch Bitcoin mining events from EventRegistry API.
    
    Args:
        api_key (Optional[str]): EventRegistry API key.
        recency_minutes (int): How far back to look for events in minutes.
        max_events (int): Maximum number of events to fetch.
        use_simple_query (bool): Use simplified query for better reliability.
    
    Returns:
        List[str]: List of event URIs.
    """
    if not api_key:
        api_key = os.getenv('EVENTREGISTRY_API_KEY')
        if not api_key:
            raise ValueError("EventRegistry API key not provided. Set EVENTREGISTRY_API_KEY environment variable.")
    
    # Performance warning for large time windows
    if recency_minutes > 1440:  # More than 1 day
        print(f"Warning: Large time window ({recency_minutes//1440} days) may cause slow performance", file=sys.stderr)
    
    # Set a dynamic timeout based on time window size
    # More realistic timeouts - EventRegistry API needs more time for Bitcoin mining queries
    if recency_minutes <= 60:   # 1 hour or less
        timeout_seconds = 25
    elif recency_minutes <= 120:  # 2 hours or less
        timeout_seconds = 30
    elif recency_minutes <= 240:  # 4 hours or less
        timeout_seconds = 35
    elif recency_minutes <= 480:  # 8 hours or less  
        timeout_seconds = 40
    else:  # Larger windows
        timeout_seconds = 45
    
    try:
        er = EventRegistry(apiKey=api_key)
        
        # Build query based on strategy
        if use_simple_query:
            query = build_simple_bitcoin_query(recency_minutes, max_events)
            print(f"Using simplified Bitcoin query for last {recency_minutes} minutes...", file=sys.stderr)
        else:
            query = build_bitcoin_mining_query(recency_minutes, max_events)
            print(f"Fetching Bitcoin mining events from last {recency_minutes} minutes...", file=sys.stderr)
            
        print(f"Query optimization: requesting up to {min(max_events * (2 if use_simple_query else 3), 15)} events for {max_events} target", file=sys.stderr)
        
        # Execute query with timeout handling
        import signal
        def timeout_handler(signum, frame):
            raise TimeoutError("API query timed out")
        
        print(f"Setting API timeout to {timeout_seconds} seconds for {recency_minutes} minute window", file=sys.stderr)
        # Store original handler to restore later
        original_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)
        
        try:
            result = er.execQuery(query)
        finally:
            # Cancel the alarm and restore original handler
            signal.alarm(0)
            signal.signal(signal.SIGALRM, original_handler)
        
        if not result or 'events' not in result:
            print("No events found in API response", file=sys.stderr)
            return []
        
        events = result['events']['results']
        print(f"Found {len(events)} raw events from EventRegistry", file=sys.stderr)
        
        # Filter for Bitcoin-only mining events with early termination
        # For simple queries, be more lenient with filtering
        if use_simple_query:
            # For simple queries, apply basic Bitcoin filtering
            filtered_events = []
            for event in events[:max_events * 2]:  # Check more events for simple queries
                title = event.get('title', {}).get('eng', '').lower()
                summary = event.get('summary', {}).get('eng', '').lower()
                
                # Basic Bitcoin mining relevance check
                if ('bitcoin' in title or 'bitcoin' in summary) and \
                   ('mining' in title or 'mining' in summary or 'miner' in title or 'miner' in summary or 
                    'hashrate' in title or 'hashrate' in summary or 'hash rate' in title or 'hash rate' in summary):
                    filtered_events.append(event)
                elif 'bitcoin' in title:  # At least Bitcoin-related
                    filtered_events.append(event)
                    
                if len(filtered_events) >= max_events:
                    break
        else:
            filtered_events = filter_bitcoin_mining_events(events, exclude_other_cryptos=True, max_events=max_events)
            
        print(f"Filtered to {len(filtered_events)} Bitcoin{'mining' if not use_simple_query else ''} events", file=sys.stderr)
        
        # Extract event URIs and limit to max_events
        event_uris = []
        for event in filtered_events[:max_events]:
            uri = event.get('uri')
            if uri:
                event_uris.append(uri)
                title = event.get('title', {}).get('eng', 'No title')
                print(f"  - {uri}: {title[:100]}...", file=sys.stderr)
        
        return event_uris
        
    except TimeoutError:
        print(f"Error: API query timed out (>{timeout_seconds} seconds). Try reducing the time window or number of articles.", file=sys.stderr)
        raise APITimeoutError("API query timed out")
    except Exception as e:
        print(f"Error fetching events from EventRegistry: {e}", file=sys.stderr)
        # For non-timeout errors, return empty list instead of crashing
        return []
    finally:
        # Ensure alarm is always canceled
        try:
            signal.alarm(0)
        except:
            pass


def main():
    """Main function to fetch news events with deduplication."""
    parser = argparse.ArgumentParser(description='Fetch Bitcoin mining news events with deduplication')
    parser.add_argument('--max-articles', type=int, default=5,
                       help='Maximum number of events to fetch (default: 5)')
    parser.add_argument('--recency-minutes', type=int, default=90,
                       help='How far back to look for events in minutes (default: 90)')
    parser.add_argument('--days-back', type=int,
                       help='Number of days back to search (converted to minutes). Warning: Large values cause slow performance!')
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
    parser.add_argument('--fast-mode', action='store_true',
                       help='Use faster performance settings (smaller time window, fewer API requests)')
    
    args = parser.parse_args()
    
    # Convert days-back to recency-minutes if provided
    if args.days_back is not None:
        args.recency_minutes = args.days_back * 24 * 60  # Convert days to minutes
    
    # Apply fast mode optimizations
    if args.fast_mode:
        print("🚀 FAST MODE: Using performance optimizations", file=sys.stderr)
        # Limit to more reasonable time windows for speed
        if args.recency_minutes > 1440:  # More than 1 day
            original_minutes = args.recency_minutes
            args.recency_minutes = 1440  # Limit to 1 day
            print(f"Fast mode: Reduced time window from {original_minutes//1440} days to 1 day", file=sys.stderr)
        
        # Additional optimization: if still experiencing timeouts, start even smaller
        # Based on recent API performance issues, limit to 2 hours for ultra-fast mode
        if args.recency_minutes > 120:  # More than 2 hours
            original_minutes = args.recency_minutes
            args.recency_minutes = 120  # Limit to 2 hours for better reliability
            print(f"Fast mode: Further reduced time window from {original_minutes} minutes ({original_minutes//60} hours) to 2 hours for better API reliability", file=sys.stderr)
        
        # Limit max articles for faster processing
        if args.max_articles > 10:
            original_max = args.max_articles
            args.max_articles = 10
            print(f"Fast mode: Reduced max articles from {original_max} to 10", file=sys.stderr)
    
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
            try:
                new_event_uris = fetch_bitcoin_mining_events_with_fallback(
                    recency_minutes=args.recency_minutes,
                    max_events=args.max_articles
                )
            except APITimeoutError:
                print("All progressive fallback attempts failed - falling back to existing queue if available", file=sys.stderr)
                new_event_uris = []
        
        if not new_event_uris:
            print("No new events found from API", file=sys.stderr)
            if args.output_format == 'uris':
                # For uris format, output existing queue URIs if no new events
                if existing_queue:
                    print("Using existing events from queue", file=sys.stderr)
                    for uri in existing_queue:
                        print(uri)
                    return
                else:
                    print("No existing events in queue either", file=sys.stderr)
                    # Exit gracefully - let the workflow handle empty output
                    return
            else:
                # For JSON format, provide empty but valid response
                summary = {
                    'new_events_added': 0,
                    'total_events_in_queue': len(existing_queue),
                    'fetch_time': datetime.now().isoformat(),
                    'new_event_uris': [],
                    'existing_queue_uris': existing_queue
                }
                print(json.dumps(summary, indent=2))
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
                # For uris format, output existing queue URIs if no new unique events
                if existing_queue:
                    print("Using existing events from queue", file=sys.stderr)
                    for uri in existing_queue:
                        print(uri)
                    return
                else:
                    print("No events available in queue", file=sys.stderr)
                    # Exit gracefully - let the workflow handle empty output
                    return
            else:
                # For JSON format, provide info about existing queue
                summary = {
                    'new_events_added': 0,
                    'total_events_in_queue': len(existing_queue),
                    'fetch_time': datetime.now().isoformat(),
                    'new_event_uris': [],
                    'existing_queue_uris': existing_queue
                }
                print(json.dumps(summary, indent=2))
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