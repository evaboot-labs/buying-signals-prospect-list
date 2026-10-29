"""Builds n8n/buying-signals-prospect-list.json. Run: python3 n8n/build_workflow.py

Two entry points in one workflow:

1. Collect: each signal search has an Evaboot recurring export that posts its new people to
   /webhook/<id>/evaboot-signals/<signal> (changed_jobs, viewed_profile, follows_company, posted).
   The rows land in the Signals tab, dated.
2. List: every weekday at 8, the workflow reads the Signals tab, keeps the rows of the last 7 days that
   are not on an earlier list, merges them per person, scores them with the points in the settings node
   like score.py, and appends today's list, by tier, to the List tab.
"""
import json
import uuid
from pathlib import Path

SHEETS_CRED = {"googleSheetsOAuth2Api": {"id": "", "name": "Google Sheets account"}}
POINTS = {"changed_jobs": 9, "viewed_profile": 8, "fast_growth": 7, "fit": 5, "follows_company": 4, "posted": 3,
          "new_in_role": 3}

nodes, connections = [], {}


def node(name, type_, version, params, pos, creds=None, **extra):
    n = {"parameters": params, "id": str(uuid.uuid4()), "name": name, "type": type_,
         "typeVersion": version, "position": pos, **extra}
    if creds:
        n["credentials"] = creds
    nodes.append(n)


def link(a, b):
    connections.setdefault(a, {}).setdefault("main", [[]])[0].append({"node": b, "type": "main", "index": 0})


def code(name, js, pos, **extra):
    node(name, "n8n-nodes-base.code", 2, {"jsCode": js}, pos, **extra)


def sheet(name, op, url_expr, pos, executeOnce=False, **params):
    p = {"operation": op,
         "documentId": {"__rl": True, "mode": "url", "value": url_expr},
         "sheetName": {"__rl": True, "mode": "url", "value": url_expr}, "options": {}, **params}
    extra = {"alwaysOutputData": True} if op == "read" else {}
    if executeOnce:
        extra["executeOnce"] = True
    node(name, "n8n-nodes-base.googleSheets", 4.7, p, pos, SHEETS_CRED, **extra)


def settings(name, pos):
    node(name, "n8n-nodes-base.set", 3.4, {"assignments": {"assignments": [
        {"id": str(uuid.uuid4()), "name": k, "type": "string", "value": v} for k, v in [
            ("signals_tab_url", "PASTE_THE_SIGNALS_TAB_URL_WITH_GID"),
            ("list_tab_url", "PASTE_THE_LIST_TAB_URL_WITH_GID"),
            ("points", json.dumps(POINTS)),
        ]]}, "includeOtherFields": True, "options": {}}, pos)


ROWS_JS = r"""
// One row per person in the Evaboot run, tagged with the signal from the webhook path.
const signal = $json.params.signal;
const prospects = $json.body.prospects || [];
const num = v => { const n = parseFloat(String(v ?? '').replace(/[,%]/g, '')); return isNaN(n) ? '' : n; };
const now = new Date().toISOString();
return prospects.map(p => {
  const y = num(p['Years in Position']), m = num(p['Months in Position']);
  return { json: {
    'Received': now, 'Signal': signal,
    'Id': p['Linkedin URL Unique ID'] || p['Linkedin URL Public'] || p['Full Name'],
    'Name': p['Full Name'] || '', 'Title': String(p['Current Job'] || '').trim(), 'Company': p['Company Name'] || '',
    'Growth 1y %': num(p['Company Employee Growth 1 Year (%)']),
    'Months in role': (y === '' && m === '') ? '' : (y || 0) * 12 + (m || 0),
    'Email': p['Email'] || '', 'Email status': p['Email Status'] || 'not found', 'LinkedIn': p['Linkedin URL Public'] || '',
  } };
});
"""

SCORE_JS = r"""
// Same as score.py: people received in the last 7 days and never on a list, merged per person, scored, tiered.
const POINTS = JSON.parse($('List settings').first().json.points);
const LABELS = { fit: 'fits your buyer search', changed_jobs: 'changed jobs', viewed_profile: 'viewed your profile',
                 follows_company: 'follows your company', posted: 'posted on LinkedIn', new_in_role: 'under 3 months in role' };
const TIERS = [[20, 'today', 'within 1 h'], [10, '24h', 'within 24 h'], [0, 'nurture', 'nurture sequence']];
const listed = new Set($('Earlier lists').all().map(r => String(r.json['Id'] || '')).filter(Boolean));
const since = Date.now() - 7 * 24 * 3600 * 1000;
const people = {};
for (const { json: r } of $('Signals').all()) {
  if (!r['Id'] || listed.has(String(r['Id'])) || new Date(r['Received']).getTime() < since) continue;
  const p = people[r['Id']] ??= { ...r, signals: new Set(['fit']) };
  p.signals.add(r['Signal']);
}
const today = new Date().toISOString().slice(0, 10);
return Object.values(people).map(p => {
  const months = p['Months in role'] === '' ? null : Number(p['Months in role']);
  const growth = p['Growth 1y %'] === '' ? null : Number(p['Growth 1y %']);
  if (months !== null && months < 3) p.signals.add('new_in_role');
  if (growth !== null && growth >= 30) p.signals.add('fast_growth');
  const signals = [...p.signals].sort((a, b) => (POINTS[b] || 0) - (POINTS[a] || 0));
  const score = signals.reduce((s, x) => s + (POINTS[x] || 0), 0);
  const [, tier, respond] = TIERS.find(t => score >= t[0]);
  const safe = String(p['Email status']).toLowerCase() === 'safe';
  return { json: {
    'Date': today, 'Tier': tier, 'Respond': respond, 'Score': score, 'Id': p.Id, 'Name': p.Name, 'Title': p.Title,
    'Company': p.Company,
    'Signals': signals.map(s => s === 'fast_growth' ? `company +${Math.round(growth)}% in a year` : (LABELS[s] || s)).join(', '),
    'Email': safe ? p.Email : '', 'Reach by': safe ? 'email' : 'LinkedIn', 'LinkedIn': p.LinkedIn,
  } };
}).sort((a, b) => b.json.Score - a.json.Score || a.json.Name.localeCompare(b.json.Name));
"""

# 1. Collect
node("New people from Evaboot", "n8n-nodes-base.webhook", 2, {
    "httpMethod": "POST", "path": "evaboot-signals/:signal", "responseMode": "onReceived", "options": {},
}, [0, 0], webhookId=str(uuid.uuid4()))
settings("Collect settings", [220, 0])
code("Signal rows", ROWS_JS, [440, 0])
# Several runs can arrive at once (one per signal): "Use Append" keeps them all instead of overwriting rows.
sheet("Add to Signals", "append", "={{ $('Collect settings').first().json.signals_tab_url }}", [660, 0],
      columns={"mappingMode": "autoMapInputData", "value": {}, "matchingColumns": [], "schema": []})
nodes[-1]["parameters"]["options"] = {"useAppend": True}

# 2. List
node("Every weekday at 8", "n8n-nodes-base.scheduleTrigger", 1.2, {"rule": {"interval": [
    {"field": "cronExpression", "expression": "0 8 * * 1-5"}]}}, [0, 360])
settings("List settings", [220, 360])
sheet("Signals", "read", "={{ $('List settings').first().json.signals_tab_url }}", [440, 360])
sheet("Earlier lists", "read", "={{ $('List settings').first().json.list_tab_url }}", [660, 360], executeOnce=True)
code("Merge, score and tier", SCORE_JS, [880, 360], executeOnce=True)
sheet("Add to List", "append", "={{ $('List settings').first().json.list_tab_url }}", [1100, 360],
      columns={"mappingMode": "autoMapInputData", "value": {}, "matchingColumns": [], "schema": []})

for a, b in [("New people from Evaboot", "Collect settings"), ("Collect settings", "Signal rows"),
             ("Signal rows", "Add to Signals"), ("Every weekday at 8", "List settings"),
             ("List settings", "Signals"), ("Signals", "Earlier lists"), ("Earlier lists", "Merge, score and tier"),
             ("Merge, score and tier", "Add to List")]:
    link(a, b)

workflow = {"name": "Buying-signal prospect list (Evaboot)", "nodes": nodes, "connections": connections,
            "settings": {"executionOrder": "v1"}, "pinData": {}}
out = Path(__file__).with_name("buying-signals-prospect-list.json")
out.write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + "\n")
print(out, len(nodes), "nodes")
