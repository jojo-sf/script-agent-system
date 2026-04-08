#!/usr/bin/env python3
"""
YouTube Research Tool
Searches YouTube using the Data API v3 and returns video data for analysis.
Supports time-filtered searches and ceiling/floor pattern analysis.

Usage:
    python3 tools/youtube_search.py --query "keyword" --time-filter all --max-results 20
    python3 tools/youtube_search.py --query "keyword" --time-filter year --max-results 20
    python3 tools/youtube_search.py --query "keyword" --time-filter month --max-results 20

Environment:
    YOUTUBE_API_KEY - YouTube Data API v3 key (required)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError


YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


def get_api_key():
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        print("ERROR: YOUTUBE_API_KEY environment variable not set.", file=sys.stderr)
        print("Get one at: https://console.cloud.google.com/apis/credentials", file=sys.stderr)
        print("Enable: YouTube Data API v3", file=sys.stderr)
        sys.exit(1)
    return key


def api_request(endpoint, params):
    url = f"{YOUTUBE_API_BASE}/{endpoint}?{urlencode(params)}"
    req = Request(url)
    try:
        with urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        error_body = e.read().decode()
        print(f"API Error {e.code}: {error_body}", file=sys.stderr)
        sys.exit(1)


def get_time_filter(filter_type):
    """Returns ISO 8601 publishedAfter date string for the given filter."""
    now = datetime.utcnow()
    if filter_type == "all":
        return None
    elif filter_type == "year":
        return (now - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
    elif filter_type == "month":
        return (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        print(f"ERROR: Unknown time filter: {filter_type}", file=sys.stderr)
        sys.exit(1)


def search_videos(api_key, query, time_filter="all", max_results=20):
    """Search YouTube for videos matching the query."""
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "order": "viewCount",
        "maxResults": min(max_results, 50),
        "key": api_key,
    }

    published_after = get_time_filter(time_filter)
    if published_after:
        params["publishedAfter"] = published_after

    data = api_request("search", params)
    return data.get("items", [])


def get_video_stats(api_key, video_ids):
    """Get detailed statistics for a list of video IDs."""
    if not video_ids:
        return {}

    params = {
        "part": "statistics,contentDetails",
        "id": ",".join(video_ids),
        "key": api_key,
    }

    data = api_request("videos", params)
    stats = {}
    for item in data.get("items", []):
        vid = item["id"]
        s = item.get("statistics", {})
        stats[vid] = {
            "views": int(s.get("viewCount", 0)),
            "likes": int(s.get("likeCount", 0)),
            "comments": int(s.get("commentCount", 0)),
            "duration": item.get("contentDetails", {}).get("duration", ""),
        }
    return stats


def get_channel_stats(api_key, channel_ids):
    """Get subscriber counts for channels."""
    if not channel_ids:
        return {}

    unique_ids = list(set(channel_ids))
    params = {
        "part": "statistics",
        "id": ",".join(unique_ids[:50]),
        "key": api_key,
    }

    data = api_request("channels", params)
    stats = {}
    for item in data.get("items", []):
        cid = item["id"]
        s = item.get("statistics", {})
        stats[cid] = {
            "subscribers": int(s.get("subscriberCount", 0)),
            "hidden": s.get("hiddenSubscriberCount", False),
        }
    return stats


def get_top_comments(api_key, video_id, max_results=10):
    """Get top comments for a video."""
    params = {
        "part": "snippet",
        "videoId": video_id,
        "order": "relevance",
        "maxResults": max_results,
        "key": api_key,
    }

    try:
        data = api_request("commentThreads", params)
        comments = []
        for item in data.get("items", []):
            snippet = item["snippet"]["topLevelComment"]["snippet"]
            comments.append({
                "text": snippet.get("textDisplay", ""),
                "likes": snippet.get("likeCount", 0),
                "author": snippet.get("authorDisplayName", ""),
            })
        return comments
    except SystemExit:
        return []


def ceiling_floor_analysis(videos_with_stats):
    """Identify ceiling and floor in the video list based on view count drop-off."""
    if not videos_with_stats:
        return None, None, []

    sorted_videos = sorted(videos_with_stats, key=lambda v: v["views"], reverse=True)

    ceiling = sorted_videos[0] if sorted_videos else None
    floor = None
    in_range = []

    for i, video in enumerate(sorted_videos):
        in_range.append(video)
        if i > 0:
            prev_views = sorted_videos[i - 1]["views"]
            curr_views = video["views"]
            if prev_views > 0 and curr_views / prev_views < 0.3:
                floor = video
                break

    if floor is None and len(sorted_videos) > 1:
        floor = sorted_videos[-1]

    return ceiling, floor, in_range


def format_views(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def main():
    parser = argparse.ArgumentParser(description="YouTube Research Tool")
    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument("--time-filter", "-t", choices=["all", "year", "month"],
                        default="all", help="Time filter: all, year, month")
    parser.add_argument("--max-results", "-n", type=int, default=20,
                        help="Max results per search (default: 20)")
    parser.add_argument("--comments", "-c", action="store_true",
                        help="Also fetch top comments for ceiling videos")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON instead of formatted text")
    args = parser.parse_args()

    api_key = get_api_key()

    print(f"Searching YouTube: \"{args.query}\" (filter: {args.time_filter})", file=sys.stderr)

    # Search for videos
    search_results = search_videos(api_key, args.query, args.time_filter, args.max_results)

    if not search_results:
        print("No results found.")
        return

    # Get video IDs and channel IDs
    video_ids = [item["id"]["videoId"] for item in search_results]
    channel_ids = [item["snippet"]["channelId"] for item in search_results]

    # Fetch stats
    video_stats = get_video_stats(api_key, video_ids)
    channel_stats = get_channel_stats(api_key, channel_ids)

    # Combine data
    videos = []
    for item in search_results:
        vid = item["id"]["videoId"]
        snippet = item["snippet"]
        cid = snippet["channelId"]
        stats = video_stats.get(vid, {})
        ch_stats = channel_stats.get(cid, {})

        videos.append({
            "video_id": vid,
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "channel_id": cid,
            "published": snippet.get("publishedAt", ""),
            "description": snippet.get("description", ""),
            "views": stats.get("views", 0),
            "likes": stats.get("likes", 0),
            "comments_count": stats.get("comments", 0),
            "duration": stats.get("duration", ""),
            "subscribers": ch_stats.get("subscribers", 0),
            "url": f"https://www.youtube.com/watch?v={vid}",
        })

    # Ceiling/Floor analysis
    ceiling, floor, in_range = ceiling_floor_analysis(videos)

    if args.json:
        output = {
            "query": args.query,
            "time_filter": args.time_filter,
            "total_results": len(videos),
            "ceiling": ceiling,
            "floor": floor,
            "videos": in_range,
        }
        if args.comments and ceiling:
            output["ceiling_comments"] = get_top_comments(api_key, ceiling["video_id"])
        print(json.dumps(output, indent=2))
    else:
        # Formatted text output
        print(f"\n## YouTube Search: \"{args.query}\" ({args.time_filter})")
        print(f"Results: {len(videos)}\n")

        if ceiling:
            print(f"**CEILING:** {ceiling['title']}")
            print(f"  Views: {format_views(ceiling['views'])} | Channel: {ceiling['channel']} ({format_views(ceiling['subscribers'])} subs)")
            print(f"  URL: {ceiling['url']}")
            print()

        if floor:
            print(f"**FLOOR:** {floor['title']}")
            print(f"  Views: {format_views(floor['views'])} | Channel: {floor['channel']}")
            print()

        print("| Rank | Title | Views | Channel | Subs | Published |")
        print("|------|-------|-------|---------|------|-----------|")
        for i, v in enumerate(in_range, 1):
            label = ""
            if v == ceiling:
                label = " [CEILING]"
            elif v == floor:
                label = " [FLOOR]"
            title = v["title"][:60] + ("..." if len(v["title"]) > 60 else "")
            print(f"| {i} | {title}{label} | {format_views(v['views'])} | {v['channel']} | {format_views(v['subscribers'])} | {v['published'][:10]} |")

        if args.comments and ceiling:
            print(f"\n### Top Comments on Ceiling Video")
            comments = get_top_comments(api_key, ceiling["video_id"])
            for c in comments:
                text = c["text"][:150] + ("..." if len(c["text"]) > 150 else "")
                print(f"- [{c['likes']} likes] {text}")

    print(f"\nDone. {len(in_range)} videos in ceiling-floor range.", file=sys.stderr)


if __name__ == "__main__":
    main()
