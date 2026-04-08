#!/usr/bin/env python3
"""
Threads Research Tool (NO API KEY — Uses Playwright Scraping)
Scrapes Threads.net search results, profiles, and conversations via browser automation.

Usage (standalone — requires Playwright):
    python3 tools/threads_search.py --search "keyword"
    python3 tools/threads_search.py --profile "username"

Usage (via Claude Code agent):
    The agent uses Playwright MCP tools directly — see AGENT INSTRUCTIONS below.

Dependencies:
    pip install playwright
    playwright install chromium

AGENT INSTRUCTIONS (for Claude Code agents using Playwright MCP):
=================================================================
Use Playwright MCP tools directly for Threads research:

## Search for Posts
1. browser_navigate → https://www.threads.net/search?q={query}&serp_type=default
2. browser_wait_for → time: 5
3. browser_snapshot → read search results (posts with text, author, engagement)
4. Scroll for more results:
   - browser_press_key → key: "End"
   - browser_wait_for → time: 3
   - browser_snapshot
5. Repeat scrolling 3-5 times to collect 30-50 posts per query
6. Run 10+ different queries

## Analyze Individual Posts (for detailed metrics)
1. browser_click → click on a post to open it
2. browser_wait_for → time: 2
3. browser_snapshot → get full post text, likes, replies, reposts
4. Scroll down to read reply thread:
   - browser_press_key → key: "End"
   - browser_snapshot → read replies

## Profile Research
1. browser_navigate → https://www.threads.net/@{username}
2. browser_wait_for → time: 5
3. browser_snapshot → read bio, follower count, recent posts
4. Scroll through their posts:
   - browser_press_key → key: "End"
   - browser_wait_for → time: 3
   - browser_snapshot

## Search for Users
1. browser_navigate → https://www.threads.net/search?q={name}&serp_type=user
2. browser_wait_for → time: 3
3. browser_snapshot → find relevant accounts

## Extracting Data from Snapshots
From each post in the snapshot, extract:
- Author (@username)
- Post text (full)
- Likes count
- Replies count
- Reposts count
- Timestamp
- Reply thread content (if expanded)

## Search Query Tips
- Use simple keywords: "productivity tools"
- Search for opinions: "I switched from [competitor]"
- Search for pain: "tired of [problem]", "I hate when"
- Search for hot takes: "unpopular opinion [category]"
- Search competitor names directly

NOTE: Threads usually works without login for search and public profiles.
Some content may be restricted — if blocked, focus on public profiles
and search results which are typically accessible.
=================================================================
"""

import argparse
import json
import sys


def check_playwright():
    try:
        import playwright
        return True
    except ImportError:
        return False


def scrape_search(query, max_scrolls=5):
    """Scrape Threads search results."""
    from playwright.sync_api import sync_playwright

    posts = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = context.new_page()

        url = f"https://www.threads.net/search?q={query}&serp_type=default"
        print(f"Navigating to: {url}", file=sys.stderr)
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(5000)

        for scroll in range(max_scrolls):
            print(f"  Scroll {scroll + 1}/{max_scrolls}...", file=sys.stderr)

            # Extract visible post data
            post_data = page.evaluate("""
                () => {
                    const posts = [];
                    // Threads uses div-based layout — look for post containers
                    const containers = document.querySelectorAll('[class*="post"], [class*="thread"], article');
                    containers.forEach(container => {
                        try {
                            const textEl = container.querySelector('span[dir="auto"], [class*="text"] span');
                            const text = textEl ? textEl.textContent : '';

                            const authorEl = container.querySelector('a[href*="/@"], a[class*="username"]');
                            const author = authorEl ? authorEl.textContent.replace('@', '') : '';
                            const authorUrl = authorEl ? authorEl.getAttribute('href') : '';

                            const timeEl = container.querySelector('time');
                            const timestamp = timeEl ? timeEl.getAttribute('datetime') || timeEl.textContent : '';

                            if (text && text.length > 10) {
                                posts.push({
                                    text: text.substring(0, 500),
                                    author: author,
                                    author_url: authorUrl,
                                    timestamp: timestamp,
                                });
                            }
                        } catch(e) {}
                    });
                    return posts;
                }
            """)

            for post in post_data:
                # Deduplicate
                existing_texts = {p["text"][:100] for p in posts}
                if post["text"][:100] not in existing_texts:
                    posts.append(post)

            # Scroll down
            page.keyboard.press("End")
            page.wait_for_timeout(3000)

        browser.close()

    return posts


def scrape_profile(username):
    """Scrape a Threads profile."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = context.new_page()

        url = f"https://www.threads.net/@{username}"
        print(f"Navigating to: {url}", file=sys.stderr)
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(5000)

        profile = page.evaluate("""
            () => {
                const result = {};

                // Try to get bio and follower info
                const metaEl = document.querySelector('meta[name="description"]');
                result.meta = metaEl ? metaEl.getAttribute('content') : '';

                const titleEl = document.querySelector('meta[property="og:title"]');
                result.title = titleEl ? titleEl.getAttribute('content') : '';

                // Get visible text content
                const bodyText = document.body.innerText.substring(0, 2000);
                result.page_text = bodyText;

                return result;
            }
        """)

        browser.close()

    return profile


def main():
    parser = argparse.ArgumentParser(description="Threads Research Tool (Playwright)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--search", "-s", help="Search query")
    group.add_argument("--profile", "-p", help="Profile username to analyze")
    group.add_argument("--agent-instructions", action="store_true",
                       help="Print Playwright MCP instructions for Claude Code agents")

    parser.add_argument("--scrolls", type=int, default=5,
                        help="Number of scrolls for search (default: 5)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    if args.agent_instructions:
        print(__doc__)
        return

    if not check_playwright():
        print("=" * 60, file=sys.stderr)
        print("Playwright not installed. Two options:", file=sys.stderr)
        print("", file=sys.stderr)
        print("OPTION 1 (Recommended): Use Claude Code agent with Playwright MCP", file=sys.stderr)
        print("  Run: python3 tools/threads_search.py --agent-instructions", file=sys.stderr)
        print("", file=sys.stderr)
        print("OPTION 2: Install Playwright for standalone scraping", file=sys.stderr)
        print("  pip install playwright && playwright install chromium", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        sys.exit(1)

    if args.search:
        print(f"Searching Threads: \"{args.search}\"", file=sys.stderr)
        posts = scrape_search(args.search, args.scrolls)

        if args.json:
            print(json.dumps(posts, indent=2))
        else:
            print(f"\n## Threads Search: \"{args.search}\"")
            print(f"Posts found: {len(posts)}\n")
            for i, post in enumerate(posts, 1):
                preview = post["text"][:120].replace("\n", " ")
                print(f"{i}. @{post['author']}: \"{preview}\"")
                print()

    elif args.profile:
        print(f"Analyzing @{args.profile}...", file=sys.stderr)
        data = scrape_profile(args.profile)

        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print(f"\n## Threads Profile: @{args.profile}")
            print(f"Title: {data.get('title', 'N/A')}")
            print(f"Meta: {data.get('meta', 'N/A')}")

    print("\nDone.", file=sys.stderr)


if __name__ == "__main__":
    main()
