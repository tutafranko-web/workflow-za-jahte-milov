"""
Load curated leads from data/bootstrap_leads.json into the Sheet.

This is a fallback for when Firecrawl key isn't available — the 14 leads
in bootstrap_leads.json were hand-curated via Claude WebSearch+WebFetch
during setup.

Run AFTER 01_create_sheet.py.
"""
import sys
import io
import os
import json
import hashlib
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from sheet_ops import open_sheet

ROOT = r'C:\Users\WWW\Desktop\ai\claude code\job-outreach'
CONFIG_ENV = os.path.join(ROOT, 'data', 'config.env')
BOOTSTRAP = os.path.join(ROOT, 'data', 'bootstrap_leads.json')


def load_env(path):
    env = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env


cfg = load_env(CONFIG_ENV)
SHEET_ID = cfg['SHEET_ID']

with open(BOOTSTRAP, 'r', encoding='utf-8') as f:
    data = json.load(f)

sh = open_sheet(SHEET_ID)
ws = sh.worksheet('Leads')
existing = set(d.lower().strip() for d in ws.col_values(2)[1:] if d)

rows = []
now = datetime.now(timezone.utc).isoformat()
for lead in data['leads']:
    domain = lead['domain'].lower()
    if domain in existing:
        continue
    email = lead.get('email', '')
    # Treat TBD/FORM_ONLY as unreachable until Firecrawl pass fills them
    has_real_email = email and not email.startswith('TBD')
    status = 'ready' if has_real_email else 'unreachable'

    lead_id = hashlib.sha1(domain.encode()).hexdigest()[:10]
    rows.append([
        lead_id,
        domain,
        lead.get('company_name', ''),
        email if has_real_email else '',
        lead.get('category', 'charter'),
        lead.get('tier', 1),
        lead.get('language', 'en'),
        lead.get('country', 'Spain'),
        lead.get('city', ''),
        (lead.get('about_snippet') or '')[:500],
        lead.get('website', ''),
        status,
        now,
        '',  # sent_at
        '',  # send_error
        lead.get('note', ''),
    ])

if rows:
    ws.append_rows(rows, value_input_option='RAW')
    ready = sum(1 for r in rows if r[11] == 'ready')
    print(f'Inserted {len(rows)} bootstrap leads ({ready} ready, {len(rows) - ready} need email).')
else:
    print('No new bootstrap leads to insert.')
