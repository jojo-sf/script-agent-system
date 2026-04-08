#!/usr/bin/env python3
"""
Script Agent System — Entry Point

This script sets up the environment and provides instructions for running
the 20-agent pipeline in Claude Code.

Usage:
    1. Set up API keys in .env file (copy from .env.example)
    2. Open Claude Code in this directory
    3. Give Claude a brand name and product brief
    4. Claude reads CLAUDE.md and orchestrates all 20 agents

You can also use this script to verify your setup:
    python3 run.py --check
"""

import argparse
import os
import sys
import json


def check_env():
    """Check that all required environment variables are set."""
    # Try loading .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("[OK] .env file loaded")
    except ImportError:
        print("[WARN] python-dotenv not installed. Using system environment variables.")
        if os.path.exists(".env"):
            print("       Install with: pip install python-dotenv")

    required_vars = {
        "YOUTUBE_API_KEY": "YouTube Data API v3 (REQUIRED)",
    }

    optional_vars = {
        "REDDIT_CLIENT_ID": "Reddit API (optional — free .json endpoints work without it)",
        "REDDIT_CLIENT_SECRET": "Reddit API (optional)",
        "X_BEARER_TOKEN": "X/Twitter API (optional — Playwright scraping works without it)",
    }

    all_set = True
    for var, service in required_vars.items():
        value = os.environ.get(var)
        if value and value != f"your_{var.lower()}_here":
            print(f"[OK] {var} is set ({service})")
        else:
            print(f"[MISSING] {var} — {service}")
            all_set = False

    print("\n  Free scraping (no API key needed):")
    print("  [FREE] Reddit — uses public .json endpoints")
    print("  [FREE] X/Twitter — uses Playwright browser scraping")
    print("  [FREE] Instagram — uses Playwright browser scraping")
    print("  [FREE] Threads — uses Playwright browser scraping")

    return all_set


def check_files():
    """Check that all required files exist."""
    required_files = [
        "CLAUDE.md",
        "agents/research/youtube_researcher.md",
        "agents/research/reddit_researcher.md",
        "agents/research/x_researcher.md",
        "agents/research/instagram_researcher.md",
        "agents/research/threads_researcher.md",
        "agents/writing/hook_writer.md",
        "agents/writing/hook_iterator.md",
        "agents/writing/hook_manager.md",
        "agents/writing/body_writer.md",
        "agents/writing/body_iterator.md",
        "agents/writing/body_manager.md",
        "agents/writing/cta_writer.md",
        "agents/writing/cta_iterator.md",
        "agents/writing/cta_manager.md",
        "agents/quality/invention_novelty_scorer.md",
        "agents/quality/copy_intensity_scorer.md",
        "agents/quality/weapons_check.md",
        "agents/quality/line_editor.md",
        "agents/output/research_synthesizer.md",
        "agents/output/script_assembler.md",
        "agents/output/final_polish.md",
        "agents/output/output_formatter.md",
        "tools/youtube_search.py",
        "tools/reddit_search.py",
        "tools/x_search.py",
        "tools/instagram_search.py",
        "tools/threads_search.py",
        "data/proven_hooks.json",
    ]

    all_exist = True
    for f in required_files:
        if os.path.exists(f):
            print(f"[OK] {f}")
        else:
            print(f"[MISSING] {f}")
            all_exist = False

    return all_exist


def check_output_dirs():
    """Ensure output directories exist."""
    dirs = ["output", "output/research", "output/working"]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        print(f"[OK] {d}/")
    return True


def verify_hooks_db():
    """Verify the proven hooks database is valid."""
    try:
        with open("data/proven_hooks.json") as f:
            data = json.load(f)
        count = len(data.get("hook_patterns", []))
        print(f"[OK] Proven hooks database: {count} patterns loaded")
        return True
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"[ERROR] Proven hooks database: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Script Agent System")
    parser.add_argument("--check", action="store_true",
                        help="Verify setup and environment")
    args = parser.parse_args()

    if args.check:
        print("=" * 60)
        print("Script Agent System — Setup Check")
        print("=" * 60)

        print("\n--- Checking Files ---")
        files_ok = check_files()

        print("\n--- Checking Output Directories ---")
        dirs_ok = check_output_dirs()

        print("\n--- Checking Hooks Database ---")
        hooks_ok = verify_hooks_db()

        print("\n--- Checking API Keys ---")
        env_ok = check_env()

        print("\n" + "=" * 60)
        if files_ok and dirs_ok and hooks_ok:
            print("Core system: READY")
        else:
            print("Core system: INCOMPLETE — fix missing files above")

        if env_ok:
            print("API keys: ALL SET")
        else:
            print("API keys: MISSING — research tools won't work without them")
            print("\nTo set up API keys:")
            print("  1. cp .env.example .env")
            print("  2. Fill in your API keys in .env")

        print("\n--- How to Run ---")
        print("  1. cd script-agent-system")
        print("  2. Open Claude Code: claude")
        print("  3. Tell Claude: 'Run the 20-agent pipeline for [Brand Name]'")
        print("  4. Provide the product brief when asked")
        print("  5. Claude reads CLAUDE.md and orchestrates all 20 agents")
        print("=" * 60)
    else:
        print("Script Agent System — 20-Agent Scriptwriting Pipeline")
        print()
        print("Usage:")
        print("  python3 run.py --check    Verify your setup")
        print()
        print("To run the pipeline:")
        print("  1. cd script-agent-system")
        print("  2. Open Claude Code: claude")
        print("  3. Tell Claude: 'Run the 20-agent pipeline for [Brand Name]'")
        print("  4. Provide the product brief when asked")
        print()
        print("For setup instructions, run: python3 run.py --check")


if __name__ == "__main__":
    main()
