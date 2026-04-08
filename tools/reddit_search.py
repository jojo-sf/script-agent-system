#!/usr/bin/env python3
"""
Reddit Research Tool (NO API KEY REQUIRED)
Uses Reddit's free public .json endpoints to fetch posts and comments.
No OAuth, no API key, no rate limit worries at moderate usage.

Usage:
    python3 tools/reddit_search.py --subreddit "productivity" --sort top --time all --limit 50
    python3 tools/reddit_search.py --search "project management pain" --sort relevance --limit 100
    python3 tools/reddit_search.py --subreddit "SaaS" --sort controversial --time all --limit 50
    python3 tools/reddit_search.py --subreddit "startups" --sort top --time all --comments --controversial-comments

No environment variables needed. This uses Reddit's public JSON endpoints.
"""

import argparse
import json
import sys
import time
from urllib.parse import urlencode, quote_plus
from urllib.request import urlopen, Request
from urllib.error import HTTPError


REDDIT_BASE = "https://www.reddit.com"
USER_AGENT = "script-agent-system/1.0 (research tool)"

# Small delay between requests to be polite
REQUEST_DELAY = 1.0


def reddit_request(url, params=None):
    """Make a request to Reddit's public JSON endpoints."""
    if params:
        url += f"?{urlencode(params)}"

    req = Request(url)
    req.add_header("User-Agent", USER_AGENT)

    try:
        time.sleep(REQUEST_DELAY)
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        if e.code == 429:
            print("Rate limited. Waiting 10 seconds...", file=sys.stderr)
            time.sleep(10)
            return reddit_request(url, params)
        print(f"HTTP Error {e.code} for {url}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return None


def get_subreddit_posts(subreddit, sort="top", time_filter="all", limit=50, after=None):
    """Get posts from a subreddit using public .json endpoint."""
    url = f"{REDDIT_BASE}/r/{subreddit}/{sort}.json"
    params = {
        "t": time_filter,
        "limit": min(limit, 100),
        "raw_json": 1,
    }
    if after:
        params["after"] = after

    data = reddit_request(url, params)
    if not data:
        return [], None

    posts = []
    after_token = data.get("data", {}).get("after")

    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        posts.append({
            "id": post.get("id", ""),
            "title": post.get("title", ""),
            "selftext": post.get("selftext", "")[:500],
            "score": post.get("score", 0),
            "upvote_ratio": post.get("upvote_ratio", 0),
            "num_comments": post.get("num_comments", 0),
            "created_utc": post.get("created_utc", 0),
            "author": post.get("author", "[deleted]"),
            "url": f"https://reddit.com{post.get('permalink', '')}",
            "permalink": post.get("permalink", ""),
            "subreddit": post.get("subreddit", subreddit),
            "is_self": post.get("is_self", True),
        })

    return posts, after_token


def search_reddit(query, sort="relevance", time_filter="all", limit=100):
    """Search all of Reddit using public .json endpoint."""
    url = f"{REDDIT_BASE}/search.json"
    params = {
        "q": query,
        "sort": sort,
        "t": time_filter,
        "limit": min(limit, 100),
        "type": "link",
        "raw_json": 1,
    }

    all_posts = []
    after = None
    pages = 0
    max_pages = (limit // 100) + 1

    while pages < max_pages and len(all_posts) < limit:
        if after:
            params["after"] = after

        data = reddit_request(url, params)
        if not data:
            break

        children = data.get("data", {}).get("children", [])
        if not children:
            break

        after = data.get("data", {}).get("after")

        for child in children:
            post = child.get("data", {})
            all_posts.append({
                "id": post.get("id", ""),
                "title": post.get("title", ""),
                "selftext": post.get("selftext", "")[:500],
                "score": post.get("score", 0),
                "upvote_ratio": post.get("upvote_ratio", 0),
                "num_comments": post.get("num_comments", 0),
                "created_utc": post.get("created_utc", 0),
                "author": post.get("author", "[deleted]"),
                "url": f"https://reddit.com{post.get('permalink', '')}",
                "permalink": post.get("permalink", ""),
                "subreddit": post.get("subreddit", ""),
                "is_self": post.get("is_self", True),
            })

        pages += 1
        print(f"  Page {pages}: {len(children)} posts (total: {len(all_posts)})", file=sys.stderr)

        if not after:
            break

    return all_posts


def get_post_comments(permalink, sort="top", limit=20):
    """Get comments from a specific post using public .json endpoint."""
    # Clean permalink and build URL
    permalink = permalink.rstrip("/")
    url = f"{REDDIT_BASE}{permalink}.json"
    params = {
        "sort": sort,
        "limit": limit,
        "raw_json": 1,
    }

    data = reddit_request(url, params)
    if not data or not isinstance(data, list) or len(data) < 2:
        return []

    comments = []
    for child in data[1].get("data", {}).get("children", []):
        if child.get("kind") != "t1":
            continue
        c = child.get("data", {})
        comments.append({
            "body": c.get("body", "")[:500],
            "score": c.get("score", 0),
            "author": c.get("author", "[deleted]"),
            "controversiality": c.get("controversiality", 0),
            "replies_count": _count_replies(c.get("replies")),
        })

    return comments


def get_controversial_comments(permalink, limit=20):
    """Get the most controversial comments from a post."""
    return get_post_comments(permalink, sort="controversial", limit=limit)


def _count_replies(replies):
    if not replies or not isinstance(replies, dict):
        return 0
    return len(replies.get("data", {}).get("children", []))


def format_score(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def main():
    parser = argparse.ArgumentParser(description="Reddit Research Tool (No API Key)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--subreddit", "-r", help="Subreddit to fetch posts from")
    group.add_argument("--search", "-s", help="Search query across all of Reddit")

    parser.add_argument("--sort", choices=["top", "hot", "new", "controversial", "relevance"],
                        default="top", help="Sort order (default: top)")
    parser.add_argument("--time", choices=["all", "year", "month", "week", "day"],
                        default="all", help="Time filter (default: all)")
    parser.add_argument("--limit", "-n", type=int, default=50,
                        help="Max results (default: 50)")
    parser.add_argument("--comments", "-c", action="store_true",
                        help="Also fetch top comments for top 10 posts")
    parser.add_argument("--controversial-comments", action="store_true",
                        help="Fetch most controversial (downvoted) comments")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON")
    args = parser.parse_args()

    if args.subreddit:
        print(f"Fetching r/{args.subreddit} (sort: {args.sort}, time: {args.time})", file=sys.stderr)
        posts, _ = get_subreddit_posts(args.subreddit, args.sort, args.time, args.limit)
    else:
        print(f"Searching Reddit: \"{args.search}\" (sort: {args.sort})", file=sys.stderr)
        posts = search_reddit(args.search, args.sort, args.time, args.limit)

    if not posts:
        print("No results found.")
        return

    # Optionally fetch comments for top posts
    if args.comments or args.controversial_comments:
        print("Fetching comments for top posts...", file=sys.stderr)
        for post in posts[:10]:
            if args.comments:
                post["top_comments"] = get_post_comments(post["permalink"], sort="top")
            if args.controversial_comments:
                post["controversial_comments"] = get_controversial_comments(post["permalink"])

    if args.json:
        print(json.dumps(posts, indent=2))
    else:
        source = f"r/{args.subreddit}" if args.subreddit else f'Search: "{args.search}"'
        print(f"\n## Reddit: {source} (sort: {args.sort}, time: {args.time})")
        print(f"Results: {len(posts)}\n")

        print("| Rank | Title | Score | Comments | Upvote % | Author | Subreddit |")
        print("|------|-------|-------|----------|----------|--------|-----------|")
        for i, post in enumerate(posts, 1):
            title = post["title"][:60] + ("..." if len(post["title"]) > 60 else "")
            ratio = f"{post['upvote_ratio'] * 100:.0f}%"
            print(f"| {i} | {title} | {format_score(post['score'])} | {post['num_comments']} | {ratio} | u/{post['author']} | r/{post['subreddit']} |")

        # Print comments if fetched
        if args.comments or args.controversial_comments:
            print("\n### Comments from Top Posts\n")
            for post in posts[:10]:
                has_comments = "top_comments" in post or "controversial_comments" in post
                if has_comments:
                    print(f"**{post['title'][:80]}** ({format_score(post['score'])} score)")
                    if "top_comments" in post:
                        for c in post["top_comments"][:5]:
                            text = c["body"][:200].replace("\n", " ")
                            print(f"  - [{format_score(c['score'])} pts] u/{c['author']}: \"{text}\"")
                    if "controversial_comments" in post:
                        print("  **Controversial (most downvoted):**")
                        for c in post["controversial_comments"][:5]:
                            text = c["body"][:200].replace("\n", " ")
                            print(f"  - [{format_score(c['score'])} pts, {c['replies_count']} replies] u/{c['author']}: \"{text}\"")
                    print()

    print(f"\nDone. {len(posts)} posts retrieved.", file=sys.stderr)


if __name__ == "__main__":
    main()
