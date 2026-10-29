---
name: buying-signals-prospect-list
description: Build a prospect list from real buying signals - run one Sales Navigator search per signal through Evaboot (people who changed jobs, viewed your profile, follow your company, or posted on LinkedIn), export them with verified emails, score each person with the points in SIGNALS.md, and sort them into contact today, within 24 hours, or nurture. Use when the user asks for signal-based prospecting, a buying-signal list, prospecting on job changes or trigger events, or who to contact first.
---

# Buying-signal prospect list

This skill runs inside a clone of https://github.com/evaboot-labs/buying-signals-prospect-list: it uses the repo's `score.py`, `SIGNALS.md` and `docs/`. If `score.py` is not in the working directory, clone the repo and work from there.

You do the Sales Navigator and Evaboot work through the Evaboot MCP server (`https://mcp.evaboot.com/mcp`). Every tool named below is an Evaboot MCP tool. `score.py` merges, scores and writes the list, the same way every time.

## Rules

- **You never contact anyone.** The list tells the user who to contact and when; they do it.
- Confirm with the user before `export_sn_search_or_list` and `create_recurring_export`. Show the searches and the cost (1 Evaboot credit per exported lead), then wait for a yes.
- Never invent a fact about a person. The list shows only what the export holds.
- Never ask for or paste an API key. The user writes `EVABOOT_API_KEY` into `.env` and exports it before starting the agent (`docs/connect-your-agent.md`).
- Print every Sales Navigator URL as a Markdown link with the URL in angle brackets: `[Open in Sales Navigator](<url>)`.

## Step 0: check the setup

1. If the Evaboot MCP tools are not in this session, walk the user through `docs/connect-your-agent.md`, then ask them to restart the agent from this folder.
2. Otherwise call `get_daily_export_quota`. If `has_valid_salesnav` is false, ask the user to sign in to Evaboot in Chrome, open any Sales Navigator search with the Evaboot extension, and click Export with Evaboot, then call it again.
3. Run `mkdir -p data lists`.
4. Read `SIGNALS.md`. If it says `Status: EXAMPLE`, ask the user who they sell to and who is not a fit, and whether to keep the default points. Rewrite the file and set `Status: yours`.

## Step 1: the signal searches

1. Build the buyer search with `build_sn_search_from_prompt`, **people only** (roles, seniority, country). Ask the user how many results they want and pass it as `max_results`. When it answers `building`, poll `get_search_build`.
2. Make one URL per signal: add one filter to the buyer search's filter list, before the last `))`:
   - changed jobs: `,(type:RECENTLY_CHANGED_JOBS,values:List((id:RPC,selectionType:INCLUDED)))`
   - viewed your profile: `,(type:VIEWED_YOUR_PROFILE,values:List((id:VYP,selectionType:INCLUDED)))`
   - follows your company: `,(type:FOLLOWS_YOUR_COMPANY,values:List((id:CF,selectionType:INCLUDED)))`
   - posted on LinkedIn: `,(type:POSTED_ON_LINKEDIN,values:List((id:RPOL,selectionType:INCLUDED)))`

   URL-encode the added text the same way as the rest of the URL (`:` is `%3A`, `,` is `%2C`). "Viewed your profile" and "follows your company" read the user's own LinkedIn profile and company page, so they are the user's first-party signals.
3. Show each URL as a link so the user can open it and see the count.

## Step 2: export and score

1. On a yes, export each signal search with `export_sn_search_or_list` and `max_results` (25 each to start), and poll `get_export` with `limit: 0` until it is done.
2. Save each export, one file per signal and day:

```bash
set -a; [ -n "$EVABOOT_API_KEY" ] || . ./.env; set +a
curl -s -H "Authorization: Bearer $EVABOOT_API_KEY" \
  https://api.evaboot.com/v1/extractions/<extraction_id>/ > data/<signal>-$(date +%F).json
```

3. Write the list, one `--signal` per file:

```bash
python3 score.py list --signal changed_jobs=data/changed_jobs-$(date +%F).json \
  --signal viewed_profile=data/viewed_profile-$(date +%F).json \
  --signal follows_company=data/follows_company-$(date +%F).json \
  --signal posted=data/posted-$(date +%F).json \
  --csv lists/$(date +%F).csv > lists/$(date +%F).md
```

4. Show the list: the `today` tier first. For each person in `today`, suggest one opening line that names their strongest signal, from the list only.

## Step 3: every day

Offer `create_recurring_export` on each signal export's `extraction_id` (daily). Each run returns only the people who are new to that search, and each run spends credits; say so before you create them. Each morning, get the latest run of each recurring export with `get_export_list`, then do steps 2.2 to 2.4. Or set up the n8n version (`docs/n8n.md`), which receives the runs by webhook and writes the list to a Google Sheet.
