#!/usr/bin/env python3
"""
Instagram Research Tool (NO API KEY — Uses Playwright Scraping)
Scrapes Instagram hashtag pages, profiles, and Reels via browser automation.

Usage (standalone — requires Playwright):
    python3 tools/instagram_search.py --hashtag "saas" --top-posts 9
    python3 tools/instagram_search.py --profile "competitor_handle"
    python3 tools/instagram_search.py --search "product management tool"

Usage (via Claude Code agent):
    The agent uses Playwright MCP tools directly — see AGENT INSTRUCTIONS below.

Dependencies:
    pip install playwright
    playwright install chromium

AGENT INSTRUCTIONS (for Claude Code agents using Playwright MCP):
=================================================================
Use Playwright MCP tools directly for Instagram research:

## Hashtag Research
1. browser_navigate → https://www.instagram.com/explore/tags/{hashtag}/
2. browser_wait_for → time: 5
3. browser_snapshot → read the top posts grid
4. For each top post (click the thumbnail):
   - browser_click → on the post image/thumbnail
   - browser_wait_for → time: 2
   - browser_snapshot → extract: author, likes, comments, caption, post type
   - browser_press_key → key: "Escape" (close modal)
5. Repeat for top 9 posts per hashtag

## Profile Analysis
1. browser_navigate → https://www.instagram.com/{username}/
2. browser_wait_for → time: 5
3. browser_snapshot → read: bio, follower count, post count, grid
4. Click into their top posts:
   - browser_click → on post thumbnail
   - browser_snapshot → get likes, comments, caption
   - browser_press_key → key: "Escape"
5. Repeat for top 5-10 posts

## Explore/Search
1. browser_navigate → https://www.instagram.com/explore/
2. browser_wait_for → time: 3
3. browser_snapshot → see trending content
4. For keyword search, use the search bar:
   - browser_click → on search icon
   - browser_fill_form → type your query
   - browser_wait_for → time: 2
   - browser_snapshot → read results

## Reels Research
1. browser_navigate → https://www.instagram.com/reels/
2. browser_wait_for → time: 5
3. browser_snapshot → identify trending Reels
4. Click into Reels to see:
   - View count, likes, comments
   - Caption/hook text
   - Author + follower count

## Extracting Engagement Data
From each post snapshot, extract:
- Likes count (from aria-label or text)
- Comments count
- View count (Reels only)
- Caption text (especially first line = the hook)
- Author username + follower count
- Top comments (scroll comments section)

## Key Instagram Search URLs
- Hashtag: https://www.instagram.com/explore/tags/{hashtag}/
- Profile: https://www.instagram.com/{username}/
- Reels: https://www.instagram.com/{username}/reels/
- Explore: https://www.instagram.com/explore/

NOTE: Instagram often requires login. If you hit a login wall:
- Try different URL patterns
- Focus on public profiles and hashtag pages
- The Explore page is sometimes accessible without login
=================================================================
"""

import argparse
import json
import sys
import time


def check_playwright():
    try:
        import playwright
        return True
    except ImportError:
        return False


def scrape_hashtag(hashtag, max_posts=9):
    """Scrape top posts from a hashtag page."""
    from playwright.sync_api import sync_playwright

    posts = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = context.new_page()

        url = f"https://www.instagram.com/explore/tags/{hashtag}/"
        print(f"Navigating to: {url}", file=sys.stderr)
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(5000)

        # Try to extract post data from the grid
        post_data = page.evaluate("""
            () => {
                const posts = [];
                const links = document.querySelectorAll('a[href*="/p/"]');
                links.forEach(link => {
                    const href = link.getAttribute('href');
                    const img = link.querySelector('img');
                    const alt = img ? img.getAttribute('alt') : '';
                    posts.push({
                        url: href,
                        alt_text: alt,
                    });
                });
                return posts.slice(0, 20);
            }
        """)

        # Click into each post for details
        for i, post_info in enumerate(post_data[:max_posts]):
            try:
                post_url = f"https://www.instagram.com{post_info['url']}"
                page.goto(post_url, wait_until="networkidle", timeout=15000)
                page.wait_for_timeout(3000)

                details = page.evaluate("""
                    () => {
                        const result = {};

                        // Try to get likes
                        const likeEls = document.querySelectorAll('span');
                        likeEls.forEach(el => {
                            const text = el.textContent || '';
                            if (text.includes('like')) {
                                result.likes_text = text;
                            }
                        });

                        // Get caption
                        const captionEl = document.querySelector('div[class*="Caption"] span, h1 + div span');
                        result.caption = captionEl ? captionEl.textContent.substring(0, 500) : '';

                        // Get comments count from meta or page
                        const commentEls = document.querySelectorAll('ul li');
                        result.comment_count_approx = commentEls.length;

                        // Get author
                        const authorLink = document.querySelector('a[class*="author"], header a[href*="/"]');
                        result.author = authorLink ? authorLink.textContent : '';
                        result.author_url = authorLink ? authorLink.getAttribute('href') : '';

                        // Get timestamp
                        const timeEl = document.querySelector('time');
                        result.timestamp = timeEl ? timeEl.getAttribute('datetime') : '';

                        return result;
                    }
                """)

                posts.append({
                    "url": post_url,
                    "alt_text": post_info.get("alt_text", ""),
                    "caption": details.get("caption", ""),
                    "author": details.get("author", ""),
                    "timestamp": details.get("timestamp", ""),
                    "likes_text": details.get("likes_text", ""),
                    "comments_approx": details.get("comment_count_approx", 0),
                })

                print(f"  Post {i + 1}/{max_posts}: @{details.get('author', '?')}", file=sys.stderr)
            except Exception as e:
                print(f"  Error on post {i + 1}: {e}", file=sys.stderr)

        browser.close()

    return posts


def scrape_profile(username):
    """Scrape a profile's bio and top posts."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = context.new_page()

        url = f"https://www.instagram.com/{username}/"
        print(f"Navigating to: {url}", file=sys.stderr)
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(5000)

        profile_data = page.evaluate("""
            () => {
                const result = {};

                // Bio
                const bioEl = document.querySelector('div[class*="bio"] span, header section > div span');
                result.bio = bioEl ? bioEl.textContent : '';

                // Follower counts (from meta or header)
                const metaEl = document.querySelector('meta[name="description"]');
                result.meta_description = metaEl ? metaEl.getAttribute('content') : '';

                // Post links
                const postLinks = document.querySelectorAll('a[href*="/p/"]');
                result.posts = [];
                postLinks.forEach(link => {
                    const href = link.getAttribute('href');
                    const img = link.querySelector('img');
                    result.posts.push({
                        url: href,
                        alt: img ? img.getAttribute('alt') : '',
                    });
                });

                return result;
            }
        """)

        browser.close()

    return profile_data


def main():
    parser = argparse.ArgumentParser(description="Instagram Research Tool (Playwright)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--hashtag", help="Hashtag to research (without #)")
    group.add_argument("--profile", help="Profile username to analyze")
    group.add_argument("--agent-instructions", action="store_true",
                       help="Print Playwright MCP instructions for Claude Code agents")

    parser.add_argument("--top-posts", type=int, default=9,
                        help="Number of top posts to analyze (default: 9)")
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
        print("  Run: python3 tools/instagram_search.py --agent-instructions", file=sys.stderr)
        print("", file=sys.stderr)
        print("OPTION 2: Install Playwright for standalone scraping", file=sys.stderr)
        print("  pip install playwright && playwright install chromium", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        sys.exit(1)

    if args.hashtag:
        print(f"Scraping #{args.hashtag}...", file=sys.stderr)
        posts = scrape_hashtag(args.hashtag, args.top_posts)

        if args.json:
            print(json.dumps(posts, indent=2))
        else:
            print(f"\n## Instagram: #{args.hashtag}")
            print(f"Posts analyzed: {len(posts)}\n")
            for i, post in enumerate(posts, 1):
                caption_preview = post["caption"][:80] + ("..." if len(post["caption"]) > 80 else "")
                print(f"{i}. @{post['author']} — \"{caption_preview}\"")
                if post["likes_text"]:
                    print(f"   {post['likes_text']}")
                print(f"   URL: {post['url']}")
                print()

    elif args.profile:
        print(f"Analyzing @{args.profile}...", file=sys.stderr)
        data = scrape_profile(args.profile)

        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print(f"\n## Instagram Profile: @{args.profile}")
            print(f"Bio: {data.get('bio', 'N/A')}")
            print(f"Meta: {data.get('meta_description', 'N/A')}")
            print(f"Posts found: {len(data.get('posts', []))}")

    print("\nDone.", file=sys.stderr)


if __name__ == "__main__":
    main()
