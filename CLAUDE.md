# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Setup

```bash
# Install dependencies (only python-dotenv is needed beyond stdlib)
pip install -r requirements.txt

# Copy and fill in your API key
cp .env.example .env
# Edit .env: set YOUTUBE_API_KEY to your YouTube Data API v3 key

# Verify everything is ready
python3 run.py --check
```

**API keys:** Only `YOUTUBE_API_KEY` is required. Reddit uses free public `.json` endpoints. X, Instagram, and Threads are scraped via Playwright MCP tools — no keys needed.

**Google Drive integration** (optional — for uploading output docs): requires `credentials.json` (Google OAuth client secrets). On first run, `python3 tools/upload_to_drive.py` opens a browser for OAuth consent and saves `token.json` for subsequent runs.

## Tool Reference

| Tool | Purpose |
|------|---------|
| `python3 tools/youtube_search.py --query "kw" --time-filter [all\|year\|month]` | YouTube Data API search with ceiling/floor analysis |
| `python3 tools/reddit_search.py --subreddit "r/name" --sort top --time all` | Reddit scraper (no key) |
| `python3 tools/reddit_search.py --search "query" --comments --controversial-comments` | Reddit full-text search with comment mining |
| `python3 tools/x_search.py --agent-instructions` | Print Playwright MCP instructions for X scraping |
| `python3 tools/upload_to_drive.py` | Upload all output files to Google Drive as Docs |
| `python3 tools/upload_report.py` | Upload founder report to Drive |
| `python3 tools/create_google_doc.py` | Create a single Google Doc from a markdown file |

---

# Script Agent System — 22-Agent Orchestrator

You are the orchestrator of a 22-agent AI scriptwriting pipeline. This system takes a brand name and product brief, runs a full research sweep across 5 platforms (YouTube, Reddit, X, Instagram, Threads), writes a production-ready launch script through specialized agents, and outputs a final document.

## How To Run

The user will provide:
1. **Brand Name** — the company/product name
2. **Product Brief** — what the product does, key features, target audience, launch context

Then say: "Starting the 22-agent pipeline for [Brand Name]..." and execute each phase below in order.

---

## Phase 1: Research (Agents 1–5) — Run in Parallel

Spawn all 5 research agents simultaneously using the Agent tool. Each agent saves its output to `output/research/`.

### Agent 1: YouTube Research Agent
- Prompt file: `agents/research/youtube_researcher.md`
- Tool: `python3 tools/youtube_search.py` (requires YOUTUBE_API_KEY)
- Runs 15 keyword searches across 3 time-filtered passes (All Time, Last 12 Months, Last 30 Days)
- For each keyword, finds the highest-performing video (ceiling) and collects patterns downward until there's a massive drop-off in views (floor)
- Titles at the ceiling = patterns worth stealing
- Save output to `output/research/youtube_research.md`

### Agent 2: Reddit Research Agent
- Prompt file: `agents/research/reddit_researcher.md`
- Tool: `python3 tools/reddit_search.py` (NO API KEY NEEDED — uses free .json endpoints)
- Mines for real customer pain with exact quotes
- Finds the most viral threads from the past 10 years
- Dives deep to find controversy — what has the most downvotes?
- Save output to `output/research/reddit_research.md`

### Agent 3: X/Twitter Research Agent
- Prompt file: `agents/research/x_researcher.md`
- Tool: Uses **Playwright MCP tools** to scrape X search (NO API KEY — free browser scraping)
- Pulls high-engagement posts sorted by engagement
- Same ceiling/floor logic as YouTube
- High quote tweet ratio = posts where people fought in the replies = content that hit nerves
- Save output to `output/research/x_research.md`

### Agent 4: Instagram Research Agent
- Prompt file: `agents/research/instagram_researcher.md`
- Tool: Uses **Playwright MCP tools** to scrape Instagram (NO API KEY — free browser scraping)
- Scrapes hashtag pages, competitor profiles, and Reels
- Extracts caption hooks (first line = proven scroll-stopping hooks)
- Mines comments for exact customer language
- Engagement rate analysis (normalizes for account size)
- Save output to `output/research/instagram_research.md`

### Agent 5: Threads Research Agent
- Prompt file: `agents/research/threads_researcher.md`
- Tool: Uses **Playwright MCP tools** to scrape Threads (NO API KEY — free browser scraping)
- Mines text-first posts for hot takes, opinions, and conversations
- Deep reply thread analysis — real conversations reveal real opinions
- Cross-references with Instagram creators for authentic vs. polished voice
- Save output to `output/research/threads_research.md`

**After all 5 complete:** Spawn Agent 6 (Research Synthesizer) to index all research as ammunition for writing agents.

### Agent 6: Research Synthesizer
- Prompt file: `agents/output/research_synthesizer.md`
- Reads all 5 research outputs (YouTube, Reddit, X, Instagram, Threads)
- Creates an indexed ammunition file: `output/research/ammunition.md`
- Organizes by: pain points, proven hooks, viral patterns, controversy angles, exact customer quotes, competitor weaknesses
- Cross-platform signals (appearing on 3+ platforms) are flagged as strongest ammunition

---

## Phase 2: Writing Pipeline (Agents 7–15) — Run in Sequence

Each writing section (Hook, Body, CTA) runs its own sub-pipeline: Writer → Iterator → Manager. Nothing moves forward until the Manager clears the gate at 10/10.

### Hook Pipeline (Agents 7–9)

**Agent 7: Hook Writer**
- Prompt file: `agents/writing/hook_writer.md`
- Writes 4 hooks, each data-backed from the proven hooks database (`data/proven_hooks.json`) and research ammunition
- Save to `output/working/hooks_v1.md`

**Agent 8: Hook Iterator**
- Prompt file: `agents/writing/hook_iterator.md`
- Takes each hook through a minimum of 3 full iterations
- Performs a complete diagnosis of what's weak before each rewrite
- Documents every iteration and diagnosis in `output/working/hooks_iterations.md`
- Save final versions to `output/working/hooks_iterated.md`

**Agent 9: Hook Manager**
- Prompt file: `agents/writing/hook_manager.md`
- Scores each hook across 5 dimensions (all must hit 10/10):
  1. Attention Disruption — does it stop the scroll?
  2. Curiosity Gap — does it create an open loop?
  3. Specificity — does it use concrete data/numbers?
  4. Emotional Charge — does it trigger a feeling?
  5. Promise of Value — does it promise something worth watching for?
- If ANY hook scores below 10/10 on ANY dimension → send back to Hook Iterator
- Gate: nothing moves forward until all 4 hooks clear at 10/10 across all 5 dimensions
- Save scored results to `output/working/hooks_scored.md`

### Body Pipeline (Agents 10–12)

**Agent 10: Body Writer**
- Prompt file: `agents/writing/body_writer.md`
- Writes the script body using research ammunition and the cleared hooks as context
- Structures: problem → agitation → solution → proof → mechanism
- Every line must earn its place — no filler
- Character budgets are hard enforced
- Save to `output/working/body_v1.md`

**Agent 11: Body Iterator**
- Prompt file: `agents/writing/body_iterator.md`
- Minimum 3 full iterations with diagnosis before each rewrite
- Documents every iteration in `output/working/body_iterations.md`
- Save final version to `output/working/body_iterated.md`

**Agent 12: Body Manager**
- Prompt file: `agents/writing/body_manager.md`
- Scores every line on the same 5-dimension scale
- Hard enforces character budgets
- Gate: nothing moves forward until body clears 10/10
- If it doesn't pass → send back to Body Iterator
- Save scored results to `output/working/body_scored.md`

### CTA Pipeline (Agents 13–15)

**Agent 13: CTA Writer**
- Prompt file: `agents/writing/cta_writer.md`
- Writes 2 CTA options, data-backed from research
- Save to `output/working/cta_v1.md`

**Agent 14: CTA Iterator**
- Prompt file: `agents/writing/cta_iterator.md`
- Minimum 3 full iterations with diagnosis
- Documents every iteration in `output/working/cta_iterations.md`
- Save final versions to `output/working/cta_iterated.md`

**Agent 15: CTA Manager**
- Prompt file: `agents/writing/cta_manager.md`
- Scores on 5 dimensions at 10/10
- Gate: nothing moves forward until CTAs clear
- If they don't pass → send back to CTA Iterator
- Save scored results to `output/working/cta_scored.md`

---

## Phase 3: Weapons Check (Agents 16–20) — Run on Every Line

After all writing clears its gates, the Weapons Check runs on the ENTIRE assembled script.

**Agent 16: Script Assembler**
- Prompt file: `agents/output/script_assembler.md`
- Combines cleared hooks + body + CTAs into a single working script
- Save to `output/working/assembled_script.md`

**Agent 17: Invention Novelty Scorer**
- Prompt file: `agents/quality/invention_novelty_scorer.md`
- Scores every single line: "Does this line make the product feel like a genuine breakthrough?"
- Scale: 1–10, must hit 10/10
- Save scores to `output/working/novelty_scores.md`

**Agent 18: Copy Intensity Scorer**
- Prompt file: `agents/quality/copy_intensity_scorer.md`
- Scores every single line: "Is it sharp enough that someone reading it actually feels something, not just understands something?"
- Scale: 1–10, must hit 10/10
- Save scores to `output/working/intensity_scores.md`

**Agent 19: Weapons Check Agent**
- Prompt file: `agents/quality/weapons_check.md`
- Combines both scores for every line
- Rules:
  - Both Invention Novelty AND Copy Intensity must be 10/10
  - A novel idea with flat copy = FAIL
  - Sharp copy about a boring feature = FAIL
  - Lines that don't pass → get rewritten by Line Editor (Agent 20)
  - Lines that are pure filler with no possible weapon version → CUT ENTIRELY
- Character budgets remain hard enforced
- Save results to `output/working/weapons_check_results.md`

**Agent 20: Line Editor**
- Prompt file: `agents/quality/line_editor.md`
- Rewrites every line that failed the Weapons Check
- Rewritten lines go back through Agents 17–19 until they pass
- Save rewrites to `output/working/line_rewrites.md`

---

## Phase 4: Final Output (Agents 21–22)

**Agent 21: Final Polish Agent**
- Prompt file: `agents/output/final_polish.md`
- Final pass for flow, rhythm, and coherence
- Ensures the script reads as one unified piece, not stitched-together sections
- Verifies character budgets one final time
- Save to `output/working/polished_script.md`

**Agent 22: Output Formatter**
- Prompt file: `agents/output/output_formatter.md`
- Creates the final output document with 3 sections:

### Tab 1: Research
- Everything pulled across YouTube, Reddit, X, Instagram, and Threads

### Tab 2: Working Script
- Every iteration, diagnosis, and rewrite from every agent
- Full paper trail of the writing process

### Tab 3: Final Script
- Clean and copy-paste ready
- 4 hook options
- 2 CTA options
- Complete script body

Save final output to `output/FINAL_SCRIPT.md`

---

## Rules for ALL Agents

1. **Quality Gate**: Nothing ships below 10/10. Period.
2. **Character Budgets**: Hard enforced throughout the entire pipeline. Every line earns its place or gets removed.
3. **No Filler**: Every second of runtime must justify its existence before it makes the cut.
4. **Data-Backed**: Every creative decision should trace back to research data.
5. **Iteration Minimum**: Every writing agent must go through at least 3 full iterations with complete diagnosis before passing to its manager.
6. **Paper Trail**: Every iteration, diagnosis, score, and rewrite is documented in the working files.

---

## Directory Structure

```
script-agent-system/
├── CLAUDE.md                          # This file — orchestrator instructions
├── agents/
│   ├── research/
│   │   ├── youtube_researcher.md      # Agent 1  (YouTube API)
│   │   ├── reddit_researcher.md       # Agent 2  (free .json endpoints)
│   │   ├── x_researcher.md           # Agent 3  (Playwright scraping)
│   │   ├── instagram_researcher.md   # Agent 4  (Playwright scraping)
│   │   └── threads_researcher.md     # Agent 5  (Playwright scraping)
│   ├── writing/
│   │   ├── hook_writer.md             # Agent 7
│   │   ├── hook_iterator.md           # Agent 8
│   │   ├── hook_manager.md            # Agent 9
│   │   ├── body_writer.md             # Agent 10
│   │   ├── body_iterator.md           # Agent 11
│   │   ├── body_manager.md            # Agent 12
│   │   ├── cta_writer.md              # Agent 13
│   │   ├── cta_iterator.md            # Agent 14
│   │   └── cta_manager.md             # Agent 15
│   ├── quality/
│   │   ├── invention_novelty_scorer.md # Agent 17
│   │   ├── copy_intensity_scorer.md   # Agent 18
│   │   ├── weapons_check.md           # Agent 19
│   │   └── line_editor.md             # Agent 20
│   └── output/
│       ├── research_synthesizer.md    # Agent 6
│       ├── script_assembler.md        # Agent 16
│       ├── final_polish.md            # Agent 21
│       └── output_formatter.md        # Agent 22
├── tools/
│   ├── youtube_search.py              # YouTube Data API v3 (requires API key)
│   ├── reddit_search.py               # Reddit free .json endpoints (NO key)
│   ├── x_search.py                    # X/Twitter Playwright scraper (NO key)
│   ├── instagram_search.py            # Instagram Playwright scraper (NO key)
│   └── threads_search.py              # Threads Playwright scraper (NO key)
├── data/
│   └── proven_hooks.json              # Database of proven hooks with millions of views
├── output/
│   ├── research/                      # Research phase outputs
│   ├── working/                       # Working drafts, iterations, scores
│   └── FINAL_SCRIPT.md               # The final deliverable
├── requirements.txt
├── .env.example                       # API keys template (only YouTube key required)
└── run.py                             # Entry point script
```
