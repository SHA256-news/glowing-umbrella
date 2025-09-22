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
EVENT_REGISTRY_API_KEY = os.getenv("EVENT_REGISTRY_API_KEY")
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

def sanitize_filename(headline):
    """Sanitizes a string to be a valid filename."""
    sanitized = headline.lower()
    sanitized = re.sub(r'\s+', '-', sanitized)
    sanitized = re.sub(r'[^a-z0-9\-_]', '', sanitized)
    return f"{sanitized[:100]}.json"

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
    print("Starting article generation process...")

    # Ensure API keys are set
    if not EVENT_REGISTRY_API_KEY or not GEMINI_API_KEY:
        print("Error: API keys for Event Registry or Gemini are not set in the .env file.")
        print("Please set EVENT_REGISTRY_API_KEY and GEMINI_API_KEY environment variables.")
        sys.exit(1)

    # Initialize clients
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

    if not event_uris:
        print("No new events to process.")
        return

    print(f"Found {len(event_uris)} events to process.")
    
    remaining_events = list(event_uris)  # Copy to modify while iterating
    processed_count = 0
    failed_count = 0

    for event_uri in event_uris:
        print(f"\nProcessing event: {event_uri}")
        try:
            # 1. Fetch event details from Event Registry
            q = QueryEvent(event_uri, requestedResult=RequestEventInfo())
            result = er.execQuery(q)
            
            if not result or not result.get('event'):
                raise ValueError("No event information found for this event URI.")
            
            event_info = result['event']
            event_details = {
                "title": event_info.get("title", {}).get("eng", "No Title Provided"),
                "summary": event_info.get("summary", {}).get("eng", "No Summary Provided"),
                "concepts": event_info.get("concepts", [])
            }

            # 2. Generate article using Gemini
            prompt = get_ai_prompt(event_details)
            response = model.generate_content(prompt)
            
            # Clean up the response to get a valid JSON string
            cleaned_response_text = response.text.strip().replace('```json', '').replace('```', '').strip()
            article_data = json.loads(cleaned_response_text)

            # 3. Save the generated article
            headline = article_data.get("headline", f"article-{event_uri}")
            filename = sanitize_filename(headline)
            filepath = os.path.join(ARTICLES_DIR, filename)
            
            # Ensure the output format is easily uploadable
            final_output = {
                "source_event_uri": event_uri,
                "generated_at": datetime.now().isoformat(),
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

if __name__ == "__main__":
    main()