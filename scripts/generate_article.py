#!/usr/bin/env python3
"""
Generate articles from Bitcoin mining news events using Google Gemini API.

This script processes events from the queue (events.json), generates professional
articles using AI, and maintains proper deduplication by moving processed events
to processed_events.json and logging failed events to failed_events.json.
"""

import os
import json
import re
import sys
import signal
import argparse
import time
from datetime import datetime
from dotenv import load_dotenv
from eventregistry import EventRegistry, QueryEvent, RequestEventInfo
import google.generativeai as genai

# --- Constants and Configuration ---
# File paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVENTS_FILE = os.path.join(BASE_DIR, 'events.json')
PROCESSED_EVENTS_FILE = os.path.join(BASE_DIR, 'processed_events.json')
FAILED_EVENTS_FILE = os.path.join(BASE_DIR, 'failed_events.json')
ARTICLES_DIR = os.path.join(BASE_DIR, 'articles')

# Load API keys from .env file
load_dotenv()
EVENT_REGISTRY_API_KEY = os.getenv("EVENTREGISTRY_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Helper Functions ---

def read_json_file(file_path, default_value=None):
    """Reads a JSON file and returns its content. Returns default_value if file doesn't exist."""
    if not os.path.exists(file_path):
        return default_value if default_value is not None else []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default_value if default_value is not None else []

def write_json_file(file_path, data):
    """Writes data to a JSON file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_events_queue():
    """Load events from the queue file in the format used by fetch_news.py."""
    data = read_json_file(EVENTS_FILE, default_value={'event_uris': [], 'total_events': 0})
    return data.get('event_uris', [])

def load_cached_event_details():
    """Load cached event details from the queue file."""
    data = read_json_file(EVENTS_FILE, default_value={})
    return data.get('event_details_cache', {})

def save_events_queue(event_uris):
    """Save remaining events back to the queue in the format used by fetch_news.py."""
    data = {
        'event_uris': event_uris,
        'updated_at': datetime.now().isoformat(),
        'total_events': len(event_uris)
    }
    write_json_file(EVENTS_FILE, data)

def load_processed_events():
    """Load processed events in the format used by fetch_news.py."""
    data = read_json_file(PROCESSED_EVENTS_FILE, default_value={'processed_uris': []})
    return set(data.get('processed_uris', []))

def add_processed_event(event_uri):
    """Add an event to the processed list in the format used by fetch_news.py."""
    processed_events = load_processed_events()
    processed_events.add(event_uri)
    data = {
        'processed_uris': list(processed_events),
        'updated_at': datetime.now().isoformat(),
        'total_processed': len(processed_events)
    }
    write_json_file(PROCESSED_EVENTS_FILE, data)

def load_failed_events():
    """Load failed events list."""
    data = read_json_file(FAILED_EVENTS_FILE, default_value={'failed_uris': []})
    return data.get('failed_uris', [])

def add_failed_event(event_uri, error_message):
    """Add an event to the failed list with error details."""
    failed_events = load_failed_events()
    failed_entry = {
        'uri': event_uri,
        'error': str(error_message),
        'failed_at': datetime.now().isoformat()
    }
    failed_events.append(failed_entry)
    data = {
        'failed_uris': failed_events,
        'updated_at': datetime.now().isoformat(),
        'total_failed': len(failed_events)
    }
    write_json_file(FAILED_EVENTS_FILE, data)

def write_placeholder(path="generated_article.json"):
    """Write a placeholder article when no events were processed."""
    doc = {
        "title": "No Recent Bitcoin Mining News", 
        "headline": "No Recent Bitcoin Mining News",
        "subtitle": "The news API returned no recent Bitcoin mining events during this run.",
        "content": "We'll publish again automatically once fresh mining news becomes available.",
        "created_at": int(time.time()),
        "generated_at": datetime.now().isoformat(),
        "body": "We'll publish again automatically once fresh mining news becomes available.",
        "key_points": [
            "No recent Bitcoin mining news found in current search window",
            "Automated system will retry on next scheduled run",
            "This is normal during periods of low mining-specific news activity"
        ],
        "tags": ["bitcoin", "mining", "automated", "placeholder"],
        "model_used": "placeholder-generator",
        "source_event_uri": "placeholder"
    }
    
    # Also write to articles directory for workflow compatibility
    os.makedirs(ARTICLES_DIR, exist_ok=True)
    article_filename = os.path.join(ARTICLES_DIR, f"placeholder-article-{int(time.time())}.json")
    
    with open(path, "w") as f:
        json.dump(doc, f, indent=2)
    with open(article_filename, "w") as f:
        json.dump(doc, f, indent=2)
        
    print(f"Wrote placeholder article to {path}")
    print(f"Also wrote to {article_filename} for workflow compatibility")

def sanitize_filename(headline):
    """Sanitizes a string to be a valid filename."""
    sanitized = headline.lower()
    sanitized = re.sub(r'\s+', '-', sanitized)
    sanitized = re.sub(r'[^a-z0-9\-_]', '', sanitized)
    return f"{sanitized[:100]}.json"

def timeout_handler(signum, frame):
    """Handle timeout for API calls."""
    raise TimeoutError("API call timed out")

def fetch_event_details_with_timeout(er, event_uri, timeout_seconds=30):
    """Fetch event details with timeout and better error handling."""
    # Set up timeout handler and store original
    original_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    
    try:
        # Try different query methods for better compatibility
        print(f"    Attempting to fetch details for event URI: {event_uri}")
        
        # Method 1: Basic query with comprehensive return info
        try:
            q = QueryEvent(event_uri, requestedResult=RequestEventInfo())
            result = er.execQuery(q)
            
            if result and 'event' in result and result['event']:
                print(f"    Successfully retrieved event details")
                return result
            else:
                print(f"    Method 1: No event data in response")
                
        except Exception as e:
            print(f"    Method 1 failed: {e}")
        
        # Method 2: Simple query without specific return info
        try:
            print(f"    Trying alternative query method...")
            q = QueryEvent(event_uri)
            q.setRequestedResult(RequestEventInfo())
            result = er.execQuery(q)
            
            if result and 'event' in result and result['event']:
                print(f"    Successfully retrieved event details with method 2")
                return result
            else:
                print(f"    Method 2: No event data in response")
                
        except Exception as e:
            print(f"    Method 2 failed: {e}")
        
        # Method 3: Check if URI format needs modification
        # Sometimes URIs need to be prefixed or have different formats
        modified_uri = event_uri
        if not event_uri.startswith('eng-') and not event_uri.startswith('http'):
            modified_uri = f"eng-{event_uri}"
            print(f"    Trying with modified URI: {modified_uri}")
            try:
                q = QueryEvent(modified_uri, requestedResult=RequestEventInfo())
                result = er.execQuery(q)
                
                if result and 'event' in result and result['event']:
                    print(f"    Successfully retrieved event details with modified URI")
                    return result
                else:
                    print(f"    Method 3: No event data with modified URI")
                    
            except Exception as e:
                print(f"    Method 3 failed: {e}")
        
        # If all methods failed, raise a descriptive error
        raise ValueError(f"No event information found for URI '{event_uri}'. "
                        f"This could indicate: 1) The event has expired or been removed, "
                        f"2) The URI format is invalid, 3) API access issues, or "
                        f"4) The event is too recent and not yet fully indexed.")
        
    except TimeoutError:
        raise TimeoutError(f"EventRegistry API call timed out after {timeout_seconds} seconds")
    except Exception as e:
        raise e
    finally:
        # Always cancel the alarm and restore original handler
        signal.alarm(0)
        signal.signal(signal.SIGALRM, original_handler)

def get_event_details_from_cache(event_uri, cached_details):
    """Get event details from cache with proper format handling."""
    if event_uri not in cached_details:
        return None
    
    cached_event = cached_details[event_uri]
    print(f"    Using cached event details from fetch phase")
    
    # Extract title and summary with better handling of nested structures
    event_title = "No Title Provided"
    event_summary = "No Summary Provided"
    
    # Handle title extraction (can be string or dict)
    title_data = cached_event.get("title", {})
    if isinstance(title_data, dict):
        event_title = title_data.get("eng", title_data.get("en", 
            list(title_data.values())[0] if title_data else "No Title Provided"))
    elif isinstance(title_data, str):
        event_title = title_data
    
    # Handle summary extraction (can be string or dict)
    summary_data = cached_event.get("summary", {})
    if isinstance(summary_data, dict):
        event_summary = summary_data.get("eng", summary_data.get("en",
            list(summary_data.values())[0] if summary_data else "No Summary Provided"))
    elif isinstance(summary_data, str):
        event_summary = summary_data
    
    # If still no useful data, mark as unavailable but don't fail
    if event_title == "No Title Provided" and event_summary == "No Summary Provided":
        event_title = f"Bitcoin Mining News Event ({event_uri})"
        event_summary = "Event details not available from cache."
    
    return {
        "title": event_title,
        "summary": event_summary,
        "concepts": cached_event.get("concepts", [])
    }

def get_ai_prompt(event_details):
    """Creates a detailed prompt for the Gemini model based on event details."""
    
    event_title = event_details.get('title', 'N/A')
    event_summary = event_details.get('summary', 'N/A')
    event_concepts = [concept['label'] for concept in event_details.get('concepts', [])]
    
    prompt = f"""
    Act as a senior financial journalist with a writing style that blends the analytical depth of The Wall Street Journal with the global perspective of The Financial Times.

    Your task is to generate a comprehensive news article based on the following event data:
    - Event Title: {event_title}
    - Event Summary: {event_summary}
    - Key Concepts: {', '.join(event_concepts)}

    Generate the article in a structured JSON format. The JSON object must contain the following keys: "headline", "summary", "key_points", "body", "tags", "reflection_questions", "calls_to_action".

    Follow these specific instructions:
    1.  **Headline (`headline`):** Create a compelling, professional headline.
    2.  **Summary (`summary`):** Write a concise, one-paragraph summary that encapsulates the most critical information.
    3.  **Key Points (`key_points`):** Provide a list of 3-5 bullet points highlighting the main takeaways.
    4.  **Body (`body`):** Write a detailed, multi-paragraph article. Provide context, perspective, and link to other relevant news or market trends where appropriate. Crucially, avoid speculation. All claims should be grounded in the provided data. If you infer connections, state them cautiously (e.g., "This development could be seen in the context of...").
    5.  **Tags (`tags`):** Generate a list of relevant keywords for categorization (e.g., "mergers-and-acquisitions", "tech-industry", "market-analysis").
    6.  **Reflection Questions (`reflection_questions`):** Create a list of 2-3 thought-provoking questions that encourage the reader to think critically about the topic's implications.
    7.  **Calls to Action (`calls_to_action`):** Formulate 1-2 calls to action prompting readers to engage, such as leaving a comment with their perspective or contacting a relevant entity.

    Ensure the entire output is a single, valid JSON object. Do not include any text or formatting outside of the JSON structure.
    """
    return prompt

# --- Main Logic ---

def main():
    """Main function to generate articles from events."""
    parser = argparse.ArgumentParser(description='Generate articles from Bitcoin mining news events')
    parser.add_argument('--test-mode', action='store_true',
                       help='Run in test mode with sample data (no API calls)')
    
    args = parser.parse_args()
    
    print("Starting article generation process...")
    
    if args.test_mode:
        print("🧪 Running in TEST MODE - using sample data, no API calls")

    # Ensure API keys are set (unless in test mode)
    if not args.test_mode and (not EVENT_REGISTRY_API_KEY or not GEMINI_API_KEY):
        print("Error: API keys for Event Registry or Gemini are not set in the .env file.")
        print("Please set EVENT_REGISTRY_API_KEY and GEMINI_API_KEY environment variables.")
        print("Or use --test-mode to run with sample data.")
        sys.exit(1)

    # Initialize clients (unless in test mode)
    er = None
    model = None
    if not args.test_mode:
        try:
            er = EventRegistry(apiKey=EVENT_REGISTRY_API_KEY)
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-pro')
        except Exception as e:
            print(f"Error initializing API clients: {e}")
            sys.exit(1)

    # Ensure articles directory exists
    try:
        os.makedirs(ARTICLES_DIR, exist_ok=True)
    except OSError as e:
        print(f"Error creating articles directory at {ARTICLES_DIR}: {e}")
        sys.exit(1)

    # Load event URIs from the queue
    event_uris = load_events_queue()
    cached_event_details = load_cached_event_details()
    
    if cached_event_details:
        print(f"Loaded cached details for {len(cached_event_details)} events as fallback")

    if not event_uris:
        print("No new events to process.")
        # Check if we should write a placeholder article
        if os.getenv("ENABLE_PLACEHOLDER", "true").lower() == "true":
            print("Writing placeholder article due to no events.")
            write_placeholder()
            sys.exit(0)
        else:
            return

    print(f"Found {len(event_uris)} events to process.")
    
    remaining_events = list(event_uris)  # Copy to modify while iterating
    processed_count = 0
    failed_count = 0

    for event_uri in event_uris:
        print(f"\nProcessing event: {event_uri}")
        try:
            if args.test_mode:
                # Use sample data in test mode
                print(f"  Using sample data for testing...")
                event_details = {
                    "title": f"Bitcoin Mining Difficulty Reaches All-Time High ({event_uri})",
                    "summary": "Bitcoin mining difficulty has increased by 6.2% in the latest adjustment, marking the highest difficulty level in the network's history. This adjustment reflects the growing hash rate and increased competition among miners.",
                    "concepts": [
                        {"label": "Bitcoin mining"},
                        {"label": "Mining difficulty"},
                        {"label": "Hash rate"},
                        {"label": "Cryptocurrency"}
                    ]
                }
                print(f"  Event title: {event_details['title']}")
                
                # Generate a sample article in test mode
                article_data = {
                    "headline": f"Bitcoin Mining Difficulty Surges to Record High as Network Security Strengthens (Event {event_uri})",
                    "summary": "Bitcoin's mining difficulty has reached an unprecedented level following a 6.2% upward adjustment, signaling robust network health and continued miner confidence despite recent market volatility.",
                    "key_points": [
                        "Mining difficulty increased by 6.2% to an all-time high",
                        "Rising hash rate indicates strong network security",
                        "Miner participation remains robust despite economic pressures",
                        "Adjustment reflects growing institutional mining operations"
                    ],
                    "body": "Bitcoin's mining difficulty has reached a new milestone, climbing 6.2% in the latest bi-weekly adjustment to establish an all-time high. This development underscores the remarkable resilience and growth of the Bitcoin network's computational security infrastructure.\n\nThe difficulty adjustment, an automated mechanism that recalibrates approximately every two weeks, responds to changes in the network's total hash rate. The current increase reflects sustained growth in mining participation, suggesting that despite recent market turbulence, miners remain committed to securing the network.\n\nIndustry analysts point to several factors driving this trend. Institutional mining operations continue to expand their capacity, while improvements in mining hardware efficiency enable operators to maintain profitability even as difficulty rises. This dynamic creates a positive feedback loop that strengthens network security while demonstrating the maturation of Bitcoin's infrastructure ecosystem.",
                    "tags": ["bitcoin-mining", "cryptocurrency", "network-security", "hash-rate", "difficulty-adjustment"],
                    "reflection_questions": [
                        "What does the continuous increase in mining difficulty suggest about institutional confidence in Bitcoin's long-term value proposition?",
                        "How might sustained high mining difficulty levels impact Bitcoin's energy consumption narrative and environmental considerations?"
                    ],
                    "calls_to_action": [
                        "Share your thoughts on how mining difficulty trends might influence Bitcoin's price trajectory in the comments below.",
                        "Stay informed about Bitcoin mining developments by following our comprehensive market analysis."
                    ]
                }
                print(f"  Sample article generated successfully")
            else:
                # Real API mode
                # 1. Try to fetch event details from Event Registry with timeout
                print(f"  Fetching event details from EventRegistry...")
                event_details = None
                
                try:
                    result = fetch_event_details_with_timeout(er, event_uri, timeout_seconds=30)
                    
                    if not result or not result.get('event'):
                        print(f"    API returned no event data, trying cache fallback...")
                        event_details = get_event_details_from_cache(event_uri, cached_event_details)
                        if not event_details:
                            raise ValueError(f"No event information found via API or cache for URI: {event_uri}")
                    else:
                        event_info = result['event']
                        print(f"    Raw event info keys: {list(event_info.keys())}")
                        
                        # Extract title and summary with better handling of nested structures
                        event_title = "No Title Provided"
                        event_summary = "No Summary Provided"
                        
                        # Handle title extraction (can be string or dict)
                        title_data = event_info.get("title", {})
                        if isinstance(title_data, dict):
                            event_title = title_data.get("eng", title_data.get("en", 
                                list(title_data.values())[0] if title_data else "No Title Provided"))
                        elif isinstance(title_data, str):
                            event_title = title_data
                        
                        # Handle summary extraction (can be string or dict)
                        summary_data = event_info.get("summary", {})
                        if isinstance(summary_data, dict):
                            event_summary = summary_data.get("eng", summary_data.get("en",
                                list(summary_data.values())[0] if summary_data else "No Summary Provided"))
                        elif isinstance(summary_data, str):
                            event_summary = summary_data
                        
                        # Validate that we have minimum required information
                        if event_title == "No Title Provided" and event_summary == "No Summary Provided":
                            # Try alternative field names
                            event_title = str(event_info.get("eventTitle", event_info.get("headline", "No Title Provided")))
                            event_summary = str(event_info.get("eventSummary", event_info.get("description", 
                                                             event_info.get("snippet", "No Summary Provided"))))
                        
                        if event_title == "No Title Provided" and event_summary == "No Summary Provided":
                            print(f"    API data insufficient, trying cache fallback...")
                            event_details = get_event_details_from_cache(event_uri, cached_event_details)
                            if not event_details:
                                available_fields = list(event_info.keys())
                                print(f"    Available event fields: {available_fields}")
                                raise ValueError(f"Event found but contains insufficient information. "
                                               f"Available fields: {available_fields}. Event URI: {event_uri}")
                        else:
                            event_details = {
                                "title": event_title,
                                "summary": event_summary,
                                "concepts": event_info.get("concepts", [])
                            }
                
                except Exception as api_error:
                    print(f"    API error: {api_error}")
                    print(f"    Trying cache fallback...")
                    event_details = get_event_details_from_cache(event_uri, cached_event_details)
                    if not event_details:
                        raise ValueError(f"Failed to get event details via API ({api_error}) and no cache available for URI: {event_uri}")
                
                if not event_details:
                    raise ValueError(f"No event details available from any source for URI: {event_uri}")
                
                print(f"  Event title: {event_details['title'][:100]}...")
                print(f"  Event summary: {event_details['summary'][:100]}...")

                # 2. Generate article using Gemini
                print(f"  Generating article with Gemini AI...")
                prompt = get_ai_prompt(event_details)
                response = model.generate_content(prompt)
                
                # Clean up the response to get a valid JSON string
                cleaned_response_text = response.text.strip().replace('```json', '').replace('```', '').strip()
                article_data = json.loads(cleaned_response_text)
                print(f"  Article generated successfully")

            # 3. Save the generated article
            headline = article_data.get("headline", f"article-{event_uri}")
            # Create unique filename using headline and event URI
            base_filename = sanitize_filename(headline)
            # Remove .json extension and add URI hash for uniqueness
            uri_hash = str(hash(event_uri))[-6:]  # Last 6 chars of hash
            filename = f"{base_filename[:-5]}-{uri_hash}.json"  # Remove .json and add hash
            filepath = os.path.join(ARTICLES_DIR, filename)
            
            # Ensure the output format is easily uploadable
            final_output = {
                "source_event_uri": event_uri,
                "generated_at": datetime.now().isoformat(),
                "model_used": "gemini-pro" if not args.test_mode else "test-mode",
                **article_data
            }
            write_json_file(filepath, final_output)
            print(f"Successfully generated and saved article: {filename}")

            # 4. Move URI to processed list
            add_processed_event(event_uri)
            remaining_events.remove(event_uri)
            processed_count += 1

        except Exception as e:
            print(f"Error processing event {event_uri}: {e}")
            # Move URI to failed list
            add_failed_event(event_uri, str(e))
            remaining_events.remove(event_uri)
            failed_count += 1
            # Continue to the next event
            continue

    # 5. Update the event queue file with any remaining events
    save_events_queue(remaining_events)
    
    print(f"\nArticle generation process finished.")
    print(f"Successfully processed: {processed_count} events")
    print(f"Failed to process: {failed_count} events")
    if remaining_events:
        print(f"Remaining in queue: {len(remaining_events)} events")

    # If no events were successfully processed, handle accordingly
    if processed_count == 0 and len(event_uris) > 0:
        # Events existed but all failed to process
        if os.getenv("ENABLE_PLACEHOLDER", "true").lower() == "true":
            print(f"\nNo events successfully processed out of {len(event_uris)} events.")
            print("Writing placeholder article due to processing failures.")
            write_placeholder()
            sys.exit(0)
        else:
            print(f"\nError: Failed to process any of the {len(event_uris)} events.")
            print("This could be due to:")
            print("- Invalid or expired event URIs")
            print("- EventRegistry API issues")
            print("- Gemini API issues")
            print("- Network connectivity problems")
            print("\nCheck the failed_events.json file for detailed error information.")
            sys.exit(1)
    elif processed_count == 0:
        # No events to process at all
        if os.getenv("ENABLE_PLACEHOLDER", "true").lower() == "true":
            print("\nNo events found to process. Writing placeholder article.")
            write_placeholder()
            sys.exit(0)
        else:
            print("\nNo events found to process. This is normal if the queue is empty.")
            return
    else:
        print(f"\nSuccessfully processed {processed_count} out of {len(event_uris)} events.")

if __name__ == "__main__":
    main()