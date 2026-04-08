#!/usr/bin/env python3
"""
X/Twitter Research Tool (NO API KEY — Uses Playwright Scraping)
Scrapes X search results using browser automation via Playwright.
No API key needed. No $100/mo subscription.

This tool is designed to be called by Claude Code agents, which have access
to Playwright MCP tools. It can also run standalone with Playwright installed.

Usage (standalone):
    python3 tools/x_search.py --query "keyword" --max-results 100
    python3 tools/x_search.py --query "keyword" --min-likes 1000
    python3 tools/x_search.py --query "keyword" --mode nerves

Usage (via Claude Code agent):
    The agent reads the instructions below and uses Playwright MCP tools directly.

Dependencies:
    pip install playwright
    playwright install chromium

AGENT INSTRUCTIONS (for Claude Code agents using Playwright MCP):
=================================================================
Instead of running this Python script, use the Playwright MCP tools directly:

1. Navigate to X search:
   browser_navigate → https://x.com/search?q={query}&src=typed_query&f=top

2. Wait for results to load:
   browser_wait_for → time: 5

3. Take a snapshot to read the posts:
   browser_snapshot

4. Scroll down for more results:
   browser_press_key → key: "End"
   browser_wait_for → time: 3
   browser_snapshot

5. Repeat scrolling 5-10 times to collect ~50-100 posts per query

6. For each interesting post, navigate to it directly to get full engagement data:
   browser_navigate → https://x.com/{author}/status/{post_id}
   browser_snapshot

7. Extract from each post:
   - Author + follower count
   - Full post text
   - Likes, retweets, quotes, replies, bookmarks, views
   - Calculate QT ratio: quotes / (likes + retweets + quotes + replies) * 100

8. Run 10+ different queries to accumulate ~500+ posts total

SEARCH QUERY TIPS:
- "keyword" min_faves:1000  → only posts with 1000+ likes
- "keyword" min_retweets:100 → only posts with 100+ retweets
- "keyword" -filter:replies  → exclude replies, only original posts
- from:username             → posts from specific user
- "keyword" until:2026-03-23 since:2025-03-23 → date range
- "keyword" lang:en         → English only
=================================================================
"""

import argparse
import json
import subprocess
import sys
import re


def check_playwright():
    """Check if Playwright is installed."""
    try:
        import playwright
        return True
    except ImportError:
        return False


def scrape_x_search(query, max_results=100, scroll_count=10):
    """Scrape X search results using Playwright (standalone mode)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: Playwright not installed.", file=sys.stderr)
        print("Install with: pip install playwright && playwright install chromium", file=sys.stderr)
        print("", file=sys.stderr)
        print("OR: If running inside Claude Code, the agent should use", file=sys.stderr)
        print("Playwright MCP tools directly instead of this script.", file=sys.stderr)
        sys.exit(1)

    posts = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = context.new_page()

        # Navigate to X search
        search_url = f"https://x.com/search?q={query}&src=typed_query&f=top"
        print(f"Navigating to: {search_url}", file=sys.stderr)
        page.goto(search_url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(5000)

        # Scroll and collect posts
        for scroll in range(scroll_count):
            print(f"  Scroll {scroll + 1}/{scroll_count}...", file=sys.stderr)

            # Extract post data from the page
            tweet_data = page.evaluate("""
                () => {
                    const tweets = [];
                    const articles = document.querySelectorAll('article[data-testid="tweet"]');
                    articles.forEach(article => {
                        try {
                            const textEl = article.querySelector('[data-testid="tweetText"]');
                            const text = textEl ? textEl.innerText : '';

                            const authorEl = article.querySelector('a[role="link"][href*="/"]');
                            const authorHref = authorEl ? authorEl.getAttribute('href') : '';
                            const author = authorHref ? authorHref.split('/').pop() : '';

                            const timeEl = article.querySelector('time');
                            const datetime = timeEl ? timeEl.getAttribute('datetime') : '';

                            const linkEl = article.querySelector('a[href*="/status/"]');
                            const statusUrl = linkEl ? linkEl.getAttribute('href') : '';

                            // Try to get engagement metrics
                            const metricEls = article.querySelectorAll('[data-testid$="count"]');
                            const metrics = {};
                            metricEls.forEach(el => {
                                const testId = el.getAttribute('data-testid');
                                const value = el.innerText;
                                if (testId) metrics[testId] = value;
                            });

                            // Alternative: get from aria-labels on buttons
                            const buttons = article.querySelectorAll('button[aria-label]');
                            buttons.forEach(btn => {
                                const label = btn.getAttribute('aria-label') || '';
                                if (label.includes('repl')) metrics.replies = label;
                                if (label.includes('repost') || label.includes('Repost')) metrics.reposts = label;
                                if (label.includes('like') || label.includes('Like')) metrics.likes = label;
                                if (label.includes('bookmark') || label.includes('Bookmark')) metrics.bookmarks = label;
                                if (label.includes('view')) metrics.views = label;
                            });

                            if (text || statusUrl) {
                                tweets.push({
                                    text: text.substring(0, 500),
                                    author: author,
                                    datetime: datetime,
                                    status_url: statusUrl,
                                    metrics: metrics
                                });
                            }
                        } catch(e) {}
                    });
                    return tweets;
                }
            """)

            for tweet in tweet_data:
                # Deduplicate by URL
                urls_seen = {p.get("status_url") for p in posts}
                if tweet.get("status_url") and tweet["status_url"] not in urls_seen:
                    posts.append(tweet)

            if len(posts) >= max_results:
                break

            # Scroll down
            page.keyboard.press("End")
            page.wait_for_timeout(3000)

        browser.close()

    return posts[:max_results]


def parse_metric_label(label):
    """Parse a metric value from an aria-label like '1,234 Likes. Like' or '5.2K reposts'."""
    if not label:
        return 0

    # Extract number from the label
    match = re.search(r'([\d,.]+[KMB]?)', label)
    if not match:
        return 0

    num_str = match.group(1).replace(",", "")

    multiplier = 1
    if num_str.endswith("K"):
        multiplier = 1000
        num_str = num_str[:-1]
    elif num_str.endswith("M"):
        multiplier = 1000000
        num_str = num_str[:-1]
    elif num_str.endswith("B"):
        multiplier = 1000000000
        num_str = num_str[:-1]

    try:
        return int(float(num_str) * multiplier)
    except ValueError:
        return 0


def enrich_posts(posts):
    """Calculate engagement metrics and QT ratios."""
    enriched = []
    for post in posts:
        metrics = post.get("metrics", {})

        likes = parse_metric_label(metrics.get("likes", ""))
        reposts = parse_metric_label(metrics.get("reposts", ""))
        replies = parse_metric_label(metrics.get("replies", ""))
        bookmarks = parse_metric_label(metrics.get("bookmarks", ""))
        views = parse_metric_label(metrics.get("views", ""))

        total_engagement = likes + reposts + replies
        qt_ratio = 0  # Can't distinguish quotes from reposts in scrape
        ratio_flag = replies > likes  # More replies than likes = ratio'd

        enriched.append({
            "text": post.get("text", ""),
            "author": post.get("author", ""),
            "datetime": post.get("datetime", ""),
            "url": f"https://x.com{post.get('status_url', '')}",
            "likes": likes,
            "reposts": reposts,
            "replies": replies,
            "bookmarks": bookmarks,
            "views": views,
            "total_engagement": total_engagement,
            "ratio_flag": ratio_flag,
        })

    return enriched


def ceiling_floor_analysis(posts):
    """Identify ceiling and floor based on engagement drop-off."""
    if not posts:
        return None, None, []

    sorted_posts = sorted(posts, key=lambda p: p["total_engagement"], reverse=True)

    ceiling = sorted_posts[0]
    floor = None
    in_range = []

    for i, post in enumerate(sorted_posts):
        in_range.append(post)
        if i > 0:
            prev = sorted_posts[i - 1]["total_engagement"]
            curr = post["total_engagement"]
            if prev > 0 and curr / prev < 0.3:
                floor = post
                break

    if floor is None and len(sorted_posts) > 1:
        floor = sorted_posts[-1]

    return ceiling, floor, in_range


def format_num(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def main():
    parser = argparse.ArgumentParser(description="X/Twitter Research Tool (Playwright Scraper)")
    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument("--max-results", "-n", type=int, default=100,
                        help="Target number of results (default: 100)")
    parser.add_argument("--scrolls", type=int, default=10,
                        help="Number of page scrolls (default: 10)")
    parser.add_argument("--min-likes", type=int, default=0,
                        help="Filter: minimum likes")
    parser.add_argument("--mode", choices=["top", "nerves", "ratio"],
                        default="top",
                        help="Analysis mode: top (highest engagement), nerves (high controversy), ratio (more replies than likes)")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON")
    parser.add_argument("--agent-instructions", action="store_true",
                        help="Print instructions for Claude Code agents using Playwright MCP")
    args = parser.parse_args()

    if args.agent_instructions:
        print("""
AGENT INSTRUCTIONS: Using Playwright MCP Tools for X Research
=============================================================

Instead of running this script, use Playwright MCP tools directly in Claude Code:

1. Build your search URL:
   query = "{query}"
   For high-engagement posts add: min_faves:1000
   URL: https://x.com/search?q={query} min_faves:1000&src=typed_query&f=top

2. Navigate:
   → mcp__playwright__browser_navigate(url)

3. Wait 5 seconds:
   → mcp__playwright__browser_wait_for(time=5)

4. Snapshot to read posts:
   → mcp__playwright__browser_snapshot()

5. Scroll for more:
   → mcp__playwright__browser_press_key(key="End")
   → mcp__playwright__browser_wait_for(time=3)
   → mcp__playwright__browser_snapshot()

6. Repeat scrolling 5-10 times per query, run 10+ queries.

7. For detailed metrics, click into individual posts:
   → mcp__playwright__browser_navigate(url=post_url)
   → mcp__playwright__browser_snapshot()

SEARCH OPERATORS:
   "keyword" min_faves:1000    → 1000+ likes only
   "keyword" min_retweets:100  → 100+ retweets only
   "keyword" -filter:replies   → exclude replies
   from:username               → specific user's posts
   since:2025-01-01            → date range
   lang:en                     → English only
""")
        return

    if not check_playwright():
        print("=" * 60, file=sys.stderr)
        print("Playwright not installed. Two options:", file=sys.stderr)
        print("", file=sys.stderr)
        print("OPTION 1 (Recommended): Use Claude Code agents with Playwright MCP", file=sys.stderr)
        print("  Run: python3 tools/x_search.py --agent-instructions", file=sys.stderr)
        print("", file=sys.stderr)
        print("OPTION 2: Install Playwright for standalone scraping", file=sys.stderr)
        print("  pip install playwright", file=sys.stderr)
        print("  playwright install chromium", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        sys.exit(1)

    # Add search operators based on mode/filters
    query = args.query
    if args.min_likes > 0:
        query += f" min_faves:{args.min_likes}"

    print(f"Scraping X: \"{query}\" (target: {args.max_results} posts)", file=sys.stderr)

    raw_posts = scrape_x_search(query, args.max_results, args.scrolls)

    if not raw_posts:
        print("No results found. X may require login for some searches.", file=sys.stderr)
        print("Try using --agent-instructions for the Playwright MCP approach.", file=sys.stderr)
        return

    enriched = enrich_posts(raw_posts)

    # Filter by min likes
    if args.min_likes > 0:
        enriched = [p for p in enriched if p["likes"] >= args.min_likes]

    # Apply mode
    if args.mode == "nerves":
        enriched = [p for p in enriched if p["replies"] > p["likes"] * 0.3]
        enriched.sort(key=lambda p: p["replies"], reverse=True)
    elif args.mode == "ratio":
        enriched = [p for p in enriched if p["ratio_flag"]]
        enriched.sort(key=lambda p: p["replies"] - p["likes"], reverse=True)
    else:
        enriched.sort(key=lambda p: p["total_engagement"], reverse=True)

    ceiling, floor, in_range = ceiling_floor_analysis(enriched)

    if args.json:
        output = {
            "query": args.query,
            "mode": args.mode,
            "total_collected": len(enriched),
            "ceiling": ceiling,
            "floor": floor,
            "posts": enriched[:50],
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\n## X Search: \"{args.query}\" (mode: {args.mode})")
        print(f"Total posts collected: {len(enriched)}\n")

        if ceiling:
            print(f"**CEILING:** @{ceiling['author']}")
            print(f"  \"{ceiling['text'][:200]}\"")
            print(f"  Likes: {format_num(ceiling['likes'])} | Reposts: {format_num(ceiling['reposts'])} | Replies: {format_num(ceiling['replies'])} | Views: {format_num(ceiling['views'])}")
            print()

        if floor:
            print(f"**FLOOR:** @{floor['author']} — {format_num(floor['total_engagement'])} total engagement")
            print()

        print("### Top Posts")
        print("| # | Author | Preview | Likes | Reposts | Replies | Views | Ratio'd? |")
        print("|---|--------|---------|-------|---------|---------|-------|----------|")
        for i, p in enumerate(enriched[:30], 1):
            preview = p["text"][:50].replace("\n", " ") + ("..." if len(p["text"]) > 50 else "")
            ratio = "YES" if p["ratio_flag"] else ""
            print(f"| {i} | @{p['author']} | {preview} | {format_num(p['likes'])} | {format_num(p['reposts'])} | {format_num(p['replies'])} | {format_num(p['views'])} | {ratio} |")

        # Ratio'd posts (more replies than likes)
        ratiod = [p for p in enriched if p["ratio_flag"]]
        if ratiod:
            print(f"\n### Ratio'd Posts (More Replies Than Likes = Hit a Nerve)")
            for p in ratiod[:10]:
                print(f"- @{p['author']}: \"{p['text'][:150]}...\"")
                print(f"  Likes: {format_num(p['likes'])} vs Replies: {format_num(p['replies'])}")

    print(f"\nDone. {len(enriched)} posts analyzed.", file=sys.stderr)


if __name__ == "__main__":
    main()
