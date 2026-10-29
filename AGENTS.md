# Agent instructions

This repo turns buying signals into a prospect list. It runs one Sales Navigator search per signal (people who changed jobs, viewed your profile, follow your company, or posted on LinkedIn), exports the people with verified emails, scores every person with the points in `SIGNALS.md`, and sorts them into three tiers: contact today, within 24 hours, or nurture. The user does the outreach. When the user asks for a buying-signal list, signal-based prospecting, or who to contact first:

1. Follow the skill in `skills/buying-signals-prospect-list/SKILL.md` step by step.
2. Read `SIGNALS.md` for the buyers, the signal searches, the points and the tiers. If it says `Status: EXAMPLE`, ask the user and update it.
3. Use `score.py` to merge, score and write the list. The Evaboot MCP server does the Sales Navigator work (`.mcp.json`).
4. If the user is not connected yet, follow `docs/connect-your-agent.md` with them.
5. If the user wants n8n instead, follow `docs/n8n.md` with them one step at a time: you cannot click inside n8n, so say exactly what to do and wait for their confirmation.

Exports cost 1 Evaboot credit per lead. Confirm with the user before every export and before creating a recurring export. Never contact anyone yourself. Never ask for or handle an API key: the user writes it into `.env`. Never commit `.env`, `data/` or `lists/`: they hold real people's data.
