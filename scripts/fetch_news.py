import os
import json
from datetime import datetime, timedelta
from eventregistry import EventRegistry, QueryEventsIter

# --- Configuration ---
EVENTREGISTRY_API_KEY = os.getenv("EVENTREGISTRY_API_KEY")
EVENTS_JSON_PATH = "events.json"
PROCESSED_EVENTS_JSON_PATH = "processed_events.json"

def load_json_file(filepath):
    """Safely load a JSON file, returning an empty list if it doesn't exist or is invalid."""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        # If file is empty or corrupt, treat it as empty
        return []

def save_json_file(filepath, data):
    """Save data to a JSON file."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def fetch_bitcoin_events(api_key):
    """
    Fetches unique Bitcoin-related news events from EventRegistry based on a predefined query.
    """
    if not api_key:
        print("Error: EVENTREGISTRY_API_KEY environment variable not set.")
        return []

    er = EventRegistry(apiKey=api_key)

    # --- Define the Query ---
    # Core topic: Bitcoin
    bitcoin_concept_uri = er.getConceptUri("Bitcoin")
    
    # Keywords to ensure we capture the right context
    include_keywords = [
        "bitcoin mining", "hashrate", "ASIC", "mining pools", "foundry", 
        "block subsidy", "difficulty adjustment", "price", "trading", 
        "ETF", "investment", "speculation"
    ]
    
    # Keywords to strictly filter out noise from other cryptocurrencies
    exclude_keywords = [
        "XRP", "Ripple", "ETH", "Ethereum", "SOL", "Solana", "DODGE", "Dogecoin"
    ]

    # Build the query for events
    q = QueryEventsIter(
        conceptUri=bitcoin_concept_uri,
        keywords=" OR ".join(include_keywords),
        ignoreKeywords=" OR ".join(exclude_keywords),
        lang="eng",
        dateStart=datetime.utcnow() - timedelta(minutes=90),
        sortBy="rel" # Sort by relevance
    )

    # Execute the query, getting a maximum of 5 events
    events = []
    for event in q.execQuery(er, returnInfo=None, maxItems=5):
        events.append(event['uri'])
        
    return events

def main():
    """
    Main function to fetch news, deduplicate, and save new event URIs.
    """
    print("Starting news fetching process...")

    # 1. Load existing event URIs from both queues
    pending_events = load_json_file(EVENTS_JSON_PATH)
    processed_events = load_json_file(PROCESSED_EVENTS_JSON_PATH)
    existing_uris = set(pending_events + processed_events)
    print(f"Found {len(pending_events)} events in the queue and {len(processed_events)} processed events.")

    # 2. Fetch the latest events from the API
    newly_fetched_events = fetch_bitcoin_events(EVENTREGISTRY_API_KEY)
    if not newly_fetched_events:
        print("No new events returned from the API.")
        return
    
    print(f"Fetched {len(newly_fetched_events)} potential new events from the API.")

    # 3. Deduplicate and identify unique events
    unique_new_events = []
    for event_uri in newly_fetched_events:
        if event_uri not in existing_uris:
            unique_new_events.append(event_uri)
            existing_uris.add(event_uri) # Add to set to prevent duplicate additions in the same run

    # 4. Save the unique new events to the queue
    if unique_new_events:
        # Append new unique events to the existing queue
        updated_events_queue = pending_events + unique_new_events
        save_json_file(EVENTS_JSON_PATH, updated_events_queue)
        print(f"Success: Added {len(unique_new_events)} new unique events to '{EVENTS_JSON_PATH}'.")
    else:
        print("No new unique events to add to the queue.")

if __name__ == "__main__":
    main()