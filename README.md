# Script Agent System

A 22-agent AI scriptwriting pipeline powered by [Claude Code](https://claude.ai/code). It runs a full research sweep across 5 platforms (YouTube, Reddit, X, Instagram, Threads), then writes a production-ready launch script through specialized writing, iteration, and quality-gate agents.

## How It Works

The pipeline has 4 phases:

1. **Research (Agents 1-6)** — 5 parallel research agents scrape YouTube, Reddit, X, Instagram, and Threads. A synthesizer agent combines findings into an indexed ammunition file.
2. **Writing (Agents 7-15)** — Three sub-pipelines (Hook, Body, CTA) each run Writer → Iterator → Manager. Nothing advances until the Manager scores every dimension at 10/10.
3. **Weapons Check (Agents 16-20)** — Every line is scored for Invention Novelty and Copy Intensity. Lines that fail get rewritten or cut.
4. **Final Output (Agents 21-22)** — Polish pass for flow and rhythm, then formatted into the final deliverable.

## Prerequisites

- **Python 3.8+**
- **[Claude Code](https://claude.ai/code)** CLI installed
- **Node.js** (for Playwright-based browser scraping)
- **No API keys required** — all 5 platforms are scraped via Playwright or free public endpoints

## Setup

```bash
# Clone
git clone https://github.com/jojo-sf/script-agent-system.git
cd script-agent-system

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright (for browser-based scraping)
npm install

# Verify everything is ready
python3 run.py --check
```

### Platform Scraping — Zero API Keys

| Platform  | Method |
|-----------|--------|
| YouTube   | Playwright browser scraping |
| Reddit    | Free public `.json` endpoints |
| X/Twitter | Playwright browser scraping |
| Instagram | Playwright browser scraping |
| Threads   | Playwright browser scraping |

### Google Drive Upload (Optional)

To upload output docs to Google Drive, place a `credentials.json` (Google OAuth client secrets) in the project root. On first run of `python3 tools/upload_to_drive.py`, a browser will open for OAuth consent.

## Usage

1. Open Claude Code in the project directory:
   ```bash
   claude
   ```

2. Give Claude a brand name and product brief:
   ```
   Run the 22-agent pipeline for [Brand Name].

   Product brief: [what it does, key features, target audience, launch context]
   ```

3. Claude reads `CLAUDE.md`, orchestrates all 22 agents, and outputs the final script to `output/FINAL_SCRIPT.md`.

## Tools

| Tool | Purpose |
|------|---------|
| `python3 tools/youtube_search.py --query "kw" --time-filter [all\|year\|month]` | YouTube search with ceiling/floor analysis |
| `python3 tools/reddit_search.py --subreddit "r/name" --sort top --time all` | Reddit scraper |
| `python3 tools/reddit_search.py --search "query" --comments --controversial-comments` | Reddit full-text search with comment mining |
| `python3 tools/x_search.py --agent-instructions` | Print Playwright instructions for X scraping |
| `python3 tools/upload_to_drive.py` | Upload output files to Google Drive |
| `python3 tools/create_google_doc.py` | Create a Google Doc from a markdown file |

## Project Structure

```
script-agent-system/
├── CLAUDE.md              # Orchestrator instructions (Claude reads this)
├── agents/
│   ├── research/          # Agents 1-5: platform research
│   ├── writing/           # Agents 7-15: hook/body/CTA pipelines
│   ├── quality/           # Agents 17-20: scoring & line editing
│   └── output/            # Agents 6, 16, 21-22: synthesis & formatting
├── tools/                 # Python/JS tools for scraping & uploads
├── data/
│   └── proven_hooks.json  # Database of proven hooks with millions of views
├── run.py                 # Setup verification script
├── requirements.txt
└── .env.example           # API key template
```

## Output

After a run, results are saved to `output/`:

- `output/research/` — Raw research from all 5 platforms + synthesized ammunition
- `output/working/` — Every iteration, diagnosis, score, and rewrite (full paper trail)
- `output/FINAL_SCRIPT.md` — The final deliverable with 4 hook options, script body, and 2 CTA options
