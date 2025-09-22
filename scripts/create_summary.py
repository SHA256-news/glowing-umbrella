#!/usr/bin/env python3
"""
Create Twitter thread summaries from generated articles.

This script takes a generated article as input and creates a concise,
multi-tweet thread summary suitable for posting on Twitter.
"""

import os
import sys
import json
import argparse
import re
from datetime import datetime


def split_text_for_twitter(text, max_length=280):
    """
    Split text into Twitter-compatible chunks.
    
    Args:
        text (str): Text to split.
        max_length (int): Maximum characters per tweet (default: 280).
    
    Returns:
        list: List of text chunks suitable for Twitter.
    """
    # Reserve space for thread numbering (e.g., "1/5 ")
    effective_length = max_length - 10
    
    # Split by sentences first
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        # If adding this sentence would exceed the limit
        if len(current_chunk) + len(sentence) + 1 > effective_length:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                # Single sentence is too long, split it
                words = sentence.split()
                for word in words:
                    if len(current_chunk) + len(word) + 1 > effective_length:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                            current_chunk = word
                        else:
                            # Single word is too long, truncate
                            chunks.append(word[:effective_length])
                    else:
                        current_chunk = f"{current_chunk} {word}".strip()
        else:
            current_chunk = f"{current_chunk} {sentence}".strip()
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


def create_twitter_thread(article_data, max_tweets=10):
    """
    Create a Twitter thread from article data.
    
    Args:
        article_data (dict): Article data with headline, content, and key_points.
        max_tweets (int): Maximum number of tweets in the thread.
    
    Returns:
        list: List of tweets for the thread.
    """
    tweets = []
    
    # Tweet 1: Headline and hook
    headline = article_data.get('headline', 'Bitcoin Mining Update')
    subtitle = article_data.get('subtitle', '')
    
    first_tweet = f"🧵 THREAD: {headline}"
    if subtitle and len(first_tweet) + len(subtitle) + 3 < 270:
        first_tweet += f"\n\n{subtitle}"
    
    tweets.append(first_tweet)
    
    # Extract key points for the thread
    key_points = article_data.get('key_points', [])
    content = article_data.get('content', '')
    
    # Create summary of key points
    if key_points:
        key_points_text = "Key takeaways:\n\n" + "\n".join([f"• {point}" for point in key_points[:4]])
        key_points_chunks = split_text_for_twitter(key_points_text)
        tweets.extend(key_points_chunks[:2])  # Limit key points to 2 tweets max
    
    # Extract interesting excerpts from content
    content_paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    
    # Find the most informative paragraphs (avoiding introduction/conclusion)
    informative_paragraphs = []
    for para in content_paragraphs[1:-1]:  # Skip first and last paragraphs
        if len(para) > 100 and any(keyword in para.lower() for keyword in 
                                  ['mining', 'bitcoin', 'hashrate', 'blockchain', 'cryptocurrency']):
            informative_paragraphs.append(para)
    
    # Add selected content chunks
    remaining_tweets = max_tweets - len(tweets) - 1  # Reserve last tweet for conclusion
    content_tweets = 0
    
    for para in informative_paragraphs[:remaining_tweets]:
        para_chunks = split_text_for_twitter(para)
        if content_tweets + len(para_chunks) <= remaining_tweets:
            tweets.extend(para_chunks)
            content_tweets += len(para_chunks)
        else:
            # Add partial content
            remaining_space = remaining_tweets - content_tweets
            tweets.extend(para_chunks[:remaining_space])
            break
    
    # Final tweet with tags and call to action
    tags = article_data.get('tags', ['bitcoin', 'mining', 'cryptocurrency'])
    hashtags = ' '.join([f'#{tag}' for tag in tags[:3]])
    
    final_tweet = f"That's a wrap! 🎯\n\nWhat are your thoughts on these developments in Bitcoin mining?\n\n{hashtags}"
    tweets.append(final_tweet)
    
    # Number the tweets
    numbered_tweets = []
    total = len(tweets)
    
    for i, tweet in enumerate(tweets, 1):
        if total > 1:
            numbered_tweet = f"{i}/{total} {tweet}"
        else:
            numbered_tweet = tweet
        numbered_tweets.append(numbered_tweet)
    
    return numbered_tweets


def main():
    """Main function to create Twitter thread summary from article."""
    parser = argparse.ArgumentParser(description='Create Twitter thread summary from article')
    parser.add_argument('article_file', help='JSON file containing the generated article')
    parser.add_argument('--max-tweets', type=int, default=8,
                       help='Maximum number of tweets in thread (default: 8)')
    parser.add_argument('--output', help='Output file path (default: stdout)')
    parser.add_argument('--format', choices=['json', 'text'], default='json',
                       help='Output format (default: json)')
    
    args = parser.parse_args()
    
    try:
        # Load article data
        if args.article_file == '-':
            article_data = json.load(sys.stdin)
        else:
            with open(args.article_file, 'r', encoding='utf-8') as f:
                article_data = json.load(f)
        
        # Create Twitter thread
        tweets = create_twitter_thread(article_data, args.max_tweets)
        
        if not tweets:
            print("Failed to create Twitter thread.", file=sys.stderr)
            sys.exit(1)
        
        # Prepare output
        if args.format == 'json':
            output_data = {
                'thread': tweets,
                'total_tweets': len(tweets),
                'created_at': datetime.now().isoformat(),
                'source_article': {
                    'headline': article_data.get('headline', ''),
                    'generated_at': article_data.get('generated_at', ''),
                    'source_event_uri': article_data.get('source_event_uri', '')
                }
            }
            output_content = json.dumps(output_data, indent=2, ensure_ascii=False)
        else:
            # Text format for easy copy-paste
            output_lines = []
            for i, tweet in enumerate(tweets, 1):
                output_lines.append(f"Tweet {i}:")
                output_lines.append(tweet)
                output_lines.append("")  # Empty line between tweets
            output_content = "\n".join(output_lines)
        
        # Output result
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_content)
            print(f"Twitter thread saved to: {args.output}", file=sys.stderr)
        else:
            print(output_content)
            
    except FileNotFoundError:
        print(f"Error: Article file '{args.article_file}' not found.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in article file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()