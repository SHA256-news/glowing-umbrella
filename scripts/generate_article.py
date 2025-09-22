#!/usr/bin/env python3
"""
Generate articles from news event URIs using Google Gemini API.

This script accepts a news event URI as input and uses the Google Gemini API
to research the event and generate a full, well-structured article.
"""

import os
import sys
import json
import argparse
from datetime import datetime
import google.generativeai as genai
from eventregistry import EventRegistry


def configure_gemini(api_key=None):
    """
    Configure Google Gemini API.
    
    Args:
        api_key (str): Gemini API key. If None, reads from GEMINI_API_KEY env var.
    """
    if not api_key:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("Gemini API key not provided. Set GEMINI_API_KEY environment variable.")
    
    genai.configure(api_key=api_key)


def get_event_details(event_uri, eventregistry_api_key=None):
    """
    Fetch detailed information about a news event.
    
    Args:
        event_uri (str): EventRegistry event URI.
        eventregistry_api_key (str): EventRegistry API key.
    
    Returns:
        dict: Event details including articles, concepts, and metadata.
    """
    if not eventregistry_api_key:
        eventregistry_api_key = os.getenv('EVENTREGISTRY_API_KEY')
        if not eventregistry_api_key:
            raise ValueError("EventRegistry API key not provided. Set EVENTREGISTRY_API_KEY environment variable.")
    
    er = EventRegistry(apiKey=eventregistry_api_key)
    
    try:
        # Get event details
        event_info = er.getEvent(event_uri)
        return event_info
    except Exception as e:
        print(f"Error fetching event details: {e}", file=sys.stderr)
        return None


def generate_article_content(event_data, model_name="gemini-1.5-flash"):
    """
    Generate a full article using Gemini AI based on event data.
    
    Args:
        event_data (dict): Event information from EventRegistry.
        model_name (str): Gemini model to use.
    
    Returns:
        dict: Generated article with title, content, and metadata.
    """
    model = genai.GenerativeModel(model_name)
    
    # Extract key information from event data
    event_title = event_data.get('title', {}).get('eng', 'Bitcoin Mining News')
    event_summary = event_data.get('summary', {}).get('eng', '')
    
    # Get articles associated with the event
    articles = event_data.get('articles', {}).get('results', [])
    article_excerpts = []
    
    for i, article in enumerate(articles[:3]):  # Use top 3 articles
        title = article.get('title', '')
        body = article.get('body', '')[:1000]  # First 1000 chars
        source = article.get('source', {}).get('title', 'Unknown')
        article_excerpts.append(f"Source {i+1} ({source}): {title}\n{body}")
    
    # Create comprehensive prompt
    prompt = f"""
    You are a professional cryptocurrency and Bitcoin mining journalist. Based on the following news event and source articles, write a comprehensive, well-structured article about Bitcoin mining.

    Event Title: {event_title}
    Event Summary: {event_summary}

    Source Articles:
    {chr(10).join(article_excerpts)}

    Please write a professional article that:
    1. Has an engaging headline (different from the event title)
    2. Includes a compelling introduction
    3. Covers the key facts and developments
    4. Explains the implications for Bitcoin mining industry
    5. Provides context about Bitcoin-only mining operations
    6. Concludes with potential future impacts
    7. Is approximately 800-1200 words
    8. Uses professional journalism style
    9. Includes relevant technical details about mining when appropriate
    10. Maintains objectivity while being informative

    Format the response as a JSON object with the following structure:
    {{
        "headline": "Article headline",
        "subtitle": "Brief subtitle or summary",
        "content": "Full article content with proper paragraphs",
        "key_points": ["List of 3-5 key takeaways"],
        "tags": ["relevant", "tags", "for", "the", "article"]
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        
        # Try to parse JSON response
        try:
            article_json = json.loads(response.text)
            return article_json
        except json.JSONDecodeError:
            # If not JSON, create structured response
            return {
                "headline": event_title,
                "subtitle": "Bitcoin Mining Industry Update",
                "content": response.text,
                "key_points": ["Industry development", "Market impact", "Technical advancement"],
                "tags": ["bitcoin", "mining", "cryptocurrency", "blockchain"]
            }
            
    except Exception as e:
        print(f"Error generating article: {e}", file=sys.stderr)
        return None


def main():
    """Main function to generate article from event URI."""
    parser = argparse.ArgumentParser(description='Generate article from news event URI')
    parser.add_argument('event_uri', help='EventRegistry event URI')
    parser.add_argument('--model', default='gemini-1.5-flash',
                       help='Gemini model to use (default: gemini-1.5-flash)')
    parser.add_argument('--output', help='Output file path (default: stdout)')
    
    args = parser.parse_args()
    
    try:
        # Configure APIs
        configure_gemini()
        
        # Fetch event details
        print(f"Fetching event details for: {args.event_uri}", file=sys.stderr)
        event_data = get_event_details(args.event_uri)
        
        if not event_data:
            print("Failed to fetch event details.", file=sys.stderr)
            sys.exit(1)
        
        # Generate article
        print("Generating article with Gemini AI...", file=sys.stderr)
        article = generate_article_content(event_data, args.model)
        
        if not article:
            print("Failed to generate article.", file=sys.stderr)
            sys.exit(1)
        
        # Add metadata
        article['generated_at'] = datetime.now().isoformat()
        article['source_event_uri'] = args.event_uri
        article['model_used'] = args.model
        
        # Output article
        output_content = json.dumps(article, indent=2, ensure_ascii=False)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_content)
            print(f"Article saved to: {args.output}", file=sys.stderr)
        else:
            print(output_content)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()