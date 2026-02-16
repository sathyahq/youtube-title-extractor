#!/usr/bin/env python3
"""
YouTube Title Extractor

Extract titles from YouTube videos using three modes:
  Level 1: Direct video URL(s) → extract title(s)
  Level 2: YouTube search results URL → extract top video titles
  Level 3: Keyword → search YouTube → extract top video titles

Usage:
  python youtube_title_extractor.py --url "https://www.youtube.com/watch?v=VIDEO_ID"
  python youtube_title_extractor.py --search-url "https://www.youtube.com/results?search_query=python+tutorial"
  python youtube_title_extractor.py --keyword "python tutorial"

Options:
  --sort          Sort results by: relevance (default), views, date, rating
  --count N       Number of results to fetch (default: 30)
  --export FILE   Export results to a CSV file
"""

import argparse
import csv
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse


def check_yt_dlp():
    """Verify yt-dlp is installed."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--version"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return True
    except FileNotFoundError:
        pass
    print("ERROR: yt-dlp is not installed.")
    print("Install it by running:  pip install yt-dlp")
    sys.exit(1)


def format_number(n):
    """Format a number with commas for readability."""
    if n is None:
        return "N/A"
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def format_duration(seconds):
    """Format duration in seconds to HH:MM:SS or MM:SS."""
    if seconds is None:
        return "N/A"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_date(date_str):
    """Format YYYYMMDD to a readable date."""
    if not date_str or len(date_str) != 8:
        return "N/A"
    try:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    except (ValueError, IndexError):
        return date_str


def days_ago(date_str):
    """Return how many days ago a YYYYMMDD date was."""
    if not date_str or len(date_str) != 8:
        return None
    try:
        dt = datetime(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:]))
        delta = datetime.now() - dt
        return delta.days
    except (ValueError, IndexError):
        return None


def run_yt_dlp(args, max_retries=2):
    """Run yt-dlp with given arguments and return parsed JSON output."""
    cmd = ["yt-dlp", "--dump-json", "--no-download", "--no-warnings"] + args

    for attempt in range(max_retries + 1):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0 and result.stdout.strip():
                entries = []
                for line in result.stdout.strip().split("\n"):
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
                return entries
            if attempt < max_retries:
                print(f"  Retrying... (attempt {attempt + 2}/{max_retries + 1})")
        except subprocess.TimeoutExpired:
            if attempt < max_retries:
                print(f"  Timed out, retrying... (attempt {attempt + 2}/{max_retries + 1})")
        except Exception as e:
            print(f"  Error: {e}")
            if attempt < max_retries:
                print(f"  Retrying... (attempt {attempt + 2}/{max_retries + 1})")

    return []


def extract_video_info(entry):
    """Extract relevant fields from a yt-dlp JSON entry."""
    return {
        "title": entry.get("title", "N/A"),
        "url": entry.get("webpage_url") or entry.get("url") or entry.get("original_url", "N/A"),
        "video_id": entry.get("id", "N/A"),
        "channel": entry.get("channel") or entry.get("uploader", "N/A"),
        "channel_subscribers": entry.get("channel_follower_count"),
        "views": entry.get("view_count"),
        "likes": entry.get("like_count"),
        "comments": entry.get("comment_count"),
        "duration": entry.get("duration"),
        "upload_date": entry.get("upload_date"),
        "description": (entry.get("description") or "")[:200],
    }


def sort_videos(videos, sort_by):
    """Sort videos by the given criterion."""
    if sort_by == "views":
        return sorted(videos, key=lambda v: v.get("views") or 0, reverse=True)
    elif sort_by == "date":
        return sorted(videos, key=lambda v: v.get("upload_date") or "0", reverse=True)
    elif sort_by == "rating":
        # Approximate engagement: likes + comments relative to views
        def engagement_score(v):
            likes = v.get("likes") or 0
            comments = v.get("comments") or 0
            views = v.get("views") or 1
            return (likes + comments * 3) / views  # Comments weighted more
        return sorted(videos, key=engagement_score, reverse=True)
    elif sort_by == "subscribers":
        return sorted(videos, key=lambda v: v.get("channel_subscribers") or 0, reverse=True)
    else:
        # relevance — keep original order from YouTube
        return videos


def display_videos(videos, title="Results"):
    """Display video results in a formatted table."""
    if not videos:
        print("\nNo videos found.")
        return

    print(f"\n{'=' * 80}")
    print(f" {title}")
    print(f" Found {len(videos)} video(s)")
    print(f"{'=' * 80}\n")

    for i, v in enumerate(videos, 1):
        days = days_ago(v["upload_date"])
        days_str = f" ({days}d ago)" if days is not None else ""

        print(f"  #{i}")
        print(f"  Title:       {v['title']}")
        print(f"  Channel:     {v['channel']}", end="")
        if v["channel_subscribers"] is not None:
            print(f"  [{format_number(v['channel_subscribers'])} subs]", end="")
        print()
        print(f"  Views:       {format_number(v['views'])}", end="")
        if v["likes"] is not None:
            print(f"   |  Likes: {format_number(v['likes'])}", end="")
        if v["comments"] is not None:
            print(f"   |  Comments: {format_number(v['comments'])}", end="")
        print()
        print(f"  Duration:    {format_duration(v['duration'])}")
        print(f"  Uploaded:    {format_date(v['upload_date'])}{days_str}")
        print(f"  URL:         {v['url']}")
        print(f"  {'-' * 76}")


def display_titles_only(videos, title="Titles"):
    """Display just the titles in a numbered list."""
    if not videos:
        print("\nNo videos found.")
        return

    print(f"\n{'=' * 60}")
    print(f" {title} ({len(videos)} videos)")
    print(f"{'=' * 60}\n")

    for i, v in enumerate(videos, 1):
        print(f"  {i:>3}. {v['title']}")

    print()


def export_to_csv(videos, filepath):
    """Export video data to a CSV file."""
    if not videos:
        print("No data to export.")
        return

    fieldnames = [
        "rank", "title", "channel", "channel_subscribers",
        "views", "likes", "comments", "duration_seconds",
        "upload_date", "url",
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i, v in enumerate(videos, 1):
            writer.writerow({
                "rank": i,
                "title": v["title"],
                "channel": v["channel"],
                "channel_subscribers": v["channel_subscribers"] or "",
                "views": v["views"] or "",
                "likes": v["likes"] or "",
                "comments": v["comments"] or "",
                "duration_seconds": v["duration"] or "",
                "upload_date": format_date(v["upload_date"]),
                "url": v["url"],
            })

    print(f"\nExported {len(videos)} videos to: {filepath}")


# ---------------------------------------------------------------------------
# Level 1: Direct URL(s)
# ---------------------------------------------------------------------------

def level1_url(urls):
    """Extract titles from one or more direct YouTube video URLs."""
    print(f"\n[Level 1] Extracting titles from {len(urls)} URL(s)...")

    videos = []
    for url in urls:
        url = url.strip()
        if not url:
            continue
        print(f"  Fetching: {url}")
        entries = run_yt_dlp([url])
        for entry in entries:
            videos.append(extract_video_info(entry))

    return videos


# ---------------------------------------------------------------------------
# Level 2: YouTube search results URL
# ---------------------------------------------------------------------------

def extract_query_from_search_url(search_url):
    """Extract the search query from a YouTube search results URL."""
    parsed = urlparse(search_url)

    # https://www.youtube.com/results?search_query=python+tutorial
    if "youtube.com" in parsed.netloc and "/results" in parsed.path:
        params = parse_qs(parsed.query)
        query = params.get("search_query", [None])[0]
        if query:
            return query

    # https://www.youtube.com/hashtag/python
    if "youtube.com" in parsed.netloc and "/hashtag/" in parsed.path:
        return parsed.path.split("/hashtag/")[-1]

    return None


def level2_search_url(search_url, count=30, sort_by="relevance"):
    """Extract video titles from a YouTube search results URL."""
    query = extract_query_from_search_url(search_url)
    if not query:
        print(f"ERROR: Could not extract search query from URL: {search_url}")
        print("Expected format: https://www.youtube.com/results?search_query=YOUR+QUERY")
        return []

    print(f"\n[Level 2] Searching YouTube for: \"{query}\"")
    print(f"  Fetching top {count} results...")

    return _search_youtube(query, count, sort_by)


# ---------------------------------------------------------------------------
# Level 3: Keyword search
# ---------------------------------------------------------------------------

def level3_keyword(keyword, count=30, sort_by="relevance"):
    """Search YouTube by keyword and extract video titles."""
    print(f"\n[Level 3] Searching YouTube for keyword: \"{keyword}\"")
    print(f"  Fetching top {count} results...")

    return _search_youtube(keyword, count, sort_by)


# ---------------------------------------------------------------------------
# Shared search logic
# ---------------------------------------------------------------------------

def _search_youtube(query, count, sort_by):
    """Use yt-dlp to search YouTube and return video info."""
    # yt-dlp supports ytsearch<N>:<query> syntax
    search_term = f"ytsearch{count}:{query}"

    # Fetch basic search results
    args = [
        search_term,
        "--flat-playlist",
    ]
    entries = run_yt_dlp(args)

    if not entries:
        print("  No results found from search.")
        return []

    print(f"  Found {len(entries)} results. Fetching detailed metadata...")

    # For each result, get full metadata (views, likes, etc.)
    videos = []
    video_urls = []
    for entry in entries:
        vid_id = entry.get("id") or entry.get("url")
        if vid_id:
            # If it looks like a full URL, use as-is; otherwise construct URL
            if vid_id.startswith("http"):
                video_urls.append(vid_id)
            else:
                video_urls.append(f"https://www.youtube.com/watch?v={vid_id}")

    # Fetch detailed info in batch
    if video_urls:
        # Process in batches to avoid overwhelming yt-dlp
        batch_size = 10
        for batch_start in range(0, len(video_urls), batch_size):
            batch = video_urls[batch_start:batch_start + batch_size]
            batch_num = (batch_start // batch_size) + 1
            total_batches = (len(video_urls) + batch_size - 1) // batch_size
            print(f"  Fetching details batch {batch_num}/{total_batches}...")

            for url in batch:
                detail_entries = run_yt_dlp([url])
                for detail in detail_entries:
                    videos.append(extract_video_info(detail))

    # Sort
    videos = sort_videos(videos, sort_by)

    return videos


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="YouTube Title Extractor - Extract titles from YouTube videos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Level 1: Extract title from a video URL
  python youtube_title_extractor.py --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

  # Level 1: Multiple URLs
  python youtube_title_extractor.py --url "URL1" --url "URL2" --url "URL3"

  # Level 2: Extract titles from a YouTube search results page URL
  python youtube_title_extractor.py --search-url "https://www.youtube.com/results?search_query=python+tutorial"

  # Level 3: Search by keyword
  python youtube_title_extractor.py --keyword "python tutorial"

  # With options
  python youtube_title_extractor.py --keyword "python tutorial" --sort views --count 20
  python youtube_title_extractor.py --keyword "python tutorial" --sort date --export results.csv
  python youtube_title_extractor.py --keyword "python tutorial" --titles-only
        """,
    )

    # Input modes (mutually exclusive)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--url",
        action="append",
        metavar="VIDEO_URL",
        help="Direct YouTube video URL (can be specified multiple times)",
    )
    group.add_argument(
        "--search-url",
        metavar="SEARCH_URL",
        help="YouTube search results page URL",
    )
    group.add_argument(
        "--keyword",
        metavar="KEYWORD",
        help="Keyword to search on YouTube",
    )

    # Options
    parser.add_argument(
        "--sort",
        choices=["relevance", "views", "date", "rating", "subscribers"],
        default="relevance",
        help="Sort results by: relevance (default), views, date, rating, subscribers",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=30,
        help="Number of videos to fetch (default: 30)",
    )
    parser.add_argument(
        "--export",
        metavar="FILE.csv",
        help="Export results to a CSV file",
    )
    parser.add_argument(
        "--titles-only",
        action="store_true",
        help="Show only titles (compact output)",
    )

    args = parser.parse_args()

    # Check dependencies
    check_yt_dlp()

    # Execute the appropriate level
    videos = []

    if args.url:
        videos = level1_url(args.url)
    elif args.search_url:
        videos = level2_search_url(args.search_url, count=args.count, sort_by=args.sort)
    elif args.keyword:
        videos = level3_keyword(args.keyword, count=args.count, sort_by=args.sort)

    if not videos:
        print("\nNo videos found. Try a different query or URL.")
        sys.exit(1)

    # Display
    sort_label = f" (sorted by {args.sort})" if args.sort != "relevance" else ""
    title = f"YouTube Videos{sort_label}"

    if args.titles_only:
        display_titles_only(videos, title=title)
    else:
        display_videos(videos, title=title)

    # Export
    if args.export:
        export_to_csv(videos, args.export)

    # Summary
    print(f"Total: {len(videos)} video(s)")


if __name__ == "__main__":
    main()
