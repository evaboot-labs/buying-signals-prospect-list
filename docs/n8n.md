# Run it in n8n

[`n8n/buying-signals-prospect-list.json`](../n8n/buying-signals-prospect-list.json) is the same prospect list for n8n. Evaboot sends each day's new people to a webhook, and every weekday at 8 the workflow scores them and writes the list into a Google Sheet. No AI model and no extra key: the scoring is a Code node.

## What runs

**Collect** (each time Evaboot sends a run):

1. **New people from Evaboot** (Webhook): one URL per signal, ending in `/changed_jobs`, `/viewed_profile`, `/follows_company` or `/posted`.
2. **Signal rows** (Code) and **Add to Signals**: one row per person in the Signals tab, with the signal and the date.

**List** (every weekday at 8):

1. **Signals** and **Earlier lists** read both tabs.
2. **Merge, score and tier** (Code): the people of the last 7 days who were never on a list, one row per person with all their signals, scored with `points` and put in a tier, like `score.py`.
3. **Add to List**: today's rows in the List tab, best score first.

## Set it up

1. **Make the sheet:** one Google Sheet with two tabs.
   - `Signals`, header row: `Received, Signal, Id, Name, Title, Company, Growth 1y %, Months in role, Email, Email status, LinkedIn`
   - `List`, header row: `Date, Tier, Respond, Score, Id, Name, Title, Company, Signals, Email, Reach by, LinkedIn`
2. **Import** the JSON in n8n: *Workflows > Import from file*.
3. **Add one credential:** **Google Sheets**, on the four sheet nodes.
4. **Fill in both settings nodes** (Collect settings and List settings hold the same fields): `signals_tab_url` and `list_tab_url` (each with its `gid`). `points` holds the points per signal; keep it in step with `SIGNALS.md`.
5. **Publish** the workflow. Open **New people from Evaboot** and copy its production URL. It looks like `https://<you>.app.n8n.cloud/webhook/<id>/evaboot-signals/:signal`.
6. **Connect Evaboot,** from your AI agent with the Evaboot MCP, or in Evaboot's Integrations page:
   - Add a webhook destination per signal: the URL with `:signal` replaced by `changed_jobs`, `viewed_profile`, `follows_company`, then `posted`.
   - Create a daily recurring export of each signal search and attach it to its destination.
7. **Test:** push one finished export to each destination (no credits), check the Signals tab, then click **Execute workflow** on **Every weekday at 8** and read the List tab.

## Good to know

- Each daily run spends 1 Evaboot credit per new person. Only people new to the search are exported.
- "Viewed your profile" and "Following your company" read the profile and company page of the Sales Navigator seat that runs the export.
- Add a signal by adding a destination with its own name at the end of the URL, and points for it in `points`.

Back to the [README](../README.md).
