"""
Initial lead discovery batch.

Strategy:
  - Tier 1 (Palma) — 8 categories x ~12 leads each ≈ 100 leads
  - Tier 5 (Caribbean) — 4 categories x ~8 leads each ≈ 30 leads
  - Per lead: Serper search → top result domain → Firecrawl scrape /contact + homepage → email regex
  - Dedup by domain
  - Append rows to Leads tab in Sheet

Costs (approx):
  - Serper: ~80 queries × $0.001 = $0.08
  - Firecrawl: ~250 page fetches × $0.005 = $1.25
  - Total: ~$1.40 for full seed batch
"""
import sys
import io
import os
import re
import time
import json
import hashlib
import requests
from urllib.parse import urlparse
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from lead_sources import TIERS, CATEGORIES

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import gspread

ROOT = r'C:\Users\WWW\Desktop\ai\claude code\job-outreach'
TOKEN_PATH = r'C:\Users\WWW\Desktop\ai\claude code\croatian-dmc-suite\token.json'
CONFIG_ENV = os.path.join(ROOT, 'data', 'config.env')
DOTENV = os.path.join(ROOT, '.env')

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

EMAIL_RX = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')
GENERIC_EMAIL_PREFIXES = {'noreply', 'no-reply', 'donotreply', 'mailer-daemon', 'postmaster'}

# Domains we don't email (job boards we use for lead discovery, social sites, etc.)
SKIP_DOMAINS = {
    'facebook.com', 'instagram.com', 'twitter.com', 'linkedin.com', 'youtube.com',
    'tripadvisor.com', 'getyourguide.com', 'viator.com',
    'wikipedia.org', 'reddit.com',
    # Big aggregators where listing != hiring company:
    'samboat.com', 'clickandboat.com', 'getmyboat.com', 'boatbookings.com',
}


def load_env(path):
    env = {}
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    k, v = line.split('=', 1)
                    env[k.strip()] = v.strip()
    return env


def main():
    cfg = load_env(CONFIG_ENV)
    secrets = load_env(DOTENV)

    SHEET_ID = cfg.get('SHEET_ID')
    SERPER_KEY = secrets.get('SERPER_API_KEY') or os.environ.get('SERPER_API_KEY')
    FIRECRAWL_KEY = secrets.get('FIRECRAWL_API_KEY') or os.environ.get('FIRECRAWL_API_KEY')

    if not SHEET_ID:
        print('ERROR: SHEET_ID missing in config.env. Run 01_create_sheet.py first.')
        sys.exit(1)
    if not SERPER_KEY:
        print('ERROR: SERPER_API_KEY missing in .env')
        sys.exit(1)
    if not FIRECRAWL_KEY:
        print('ERROR: FIRECRAWL_API_KEY missing in .env')
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(TOKEN_PATH, scopes=SCOPES)
    if creds.expired:
        creds.refresh(Request())

    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)
    ws_leads = sh.worksheet('Leads')

    # Existing domains to skip
    print('Loading existing leads for dedup...')
    existing = ws_leads.col_values(2)[1:]  # column B = domain, skip header
    seen_domains = set(d.lower().strip() for d in existing if d)
    print(f'  {len(seen_domains)} existing domains')

    # Plan:
    # Tier 1 (Palma): 8 categories
    # Tier 5 (Caribbean): 4 categories
    plan = []
    tier1_categories = ['charter', 'crew_agency', 'broker', 'daytour', 'school', 'flotilla', 'jobboard_lead', 'superyacht']
    tier5_categories = ['charter', 'crew_agency', 'flotilla', 'broker']

    for cat in tier1_categories:
        plan.append((1, cat))
    for cat in tier5_categories:
        plan.append((5, cat))

    new_rows = []
    skipped = 0

    for tier_num, cat_name in plan:
        tier = TIERS[tier_num]
        category = CATEGORIES[cat_name]
        print(f'\n=== Tier {tier_num} ({tier["label"]}) — {cat_name} ===')

        for query_template in category['queries'][:3]:  # first 3 queries per cat
            for city in tier['cities'][:3]:  # first 3 cities per tier
                if '{city}' not in query_template:
                    # global query (e.g. "Bluewater yacht crew")
                    query = query_template
                    city_use = ''
                else:
                    query = query_template.replace('{city}', city)
                    city_use = city

                print(f'  Q: {query}')
                results = serper_search(SERPER_KEY, query, limit=5)

                for r in results:
                    link = r.get('link') or ''
                    title = r.get('title') or ''
                    snippet = r.get('snippet') or ''
                    domain = extract_domain(link)
                    if not domain:
                        continue
                    if domain in seen_domains:
                        skipped += 1
                        continue
                    if any(domain.endswith(d) for d in SKIP_DOMAINS):
                        skipped += 1
                        continue

                    seen_domains.add(domain)

                    # Try to scrape email
                    email, about, lang = scrape_lead(FIRECRAWL_KEY, link)
                    status = 'enriched' if email else 'unreachable'

                    lead_id = hashlib.sha1(domain.encode()).hexdigest()[:10]
                    row = [
                        lead_id,
                        domain,
                        clean_company_name(title),
                        email or '',
                        cat_name,
                        tier_num,
                        lang or tier['languages'][0],
                        tier['country'],
                        city_use,
                        (about or snippet)[:500],
                        link,
                        'ready' if email else 'unreachable',
                        datetime.now(timezone.utc).isoformat(),
                        '',  # sent_at
                        '',  # send_error
                        '',  # notes
                    ]
                    new_rows.append(row)
                    print(f'    + {domain} | {email or "(no email)"}')

                    if not email:
                        continue

                time.sleep(1)  # serper rate limit

            if len(new_rows) >= 130:
                break
        if len(new_rows) >= 130:
            break

    print(f'\nAppending {len(new_rows)} new leads to Sheet (skipped {skipped} dupes)...')
    if new_rows:
        ws_leads.append_rows(new_rows, value_input_option='RAW')

    ready_count = sum(1 for r in new_rows if r[11] == 'ready')
    print(f'Done. ready={ready_count}, unreachable={len(new_rows) - ready_count}')


def serper_search(api_key, query, limit=10):
    try:
        resp = requests.post(
            'https://google.serper.dev/search',
            headers={'X-API-KEY': api_key, 'Content-Type': 'application/json'},
            json={'q': query, 'num': limit},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get('organic', [])
    except Exception as e:
        print(f'    serper error: {e}')
        return []


def scrape_lead(api_key, url):
    """Scrape homepage + /contact. Returns (email, about_snippet, lang)."""
    urls_to_try = [url]
    parsed = urlparse(url)
    base = f'{parsed.scheme}://{parsed.netloc}'
    if not url.rstrip('/').endswith(('contact', 'contact-us', 'kontakt')):
        urls_to_try.append(f'{base}/contact')

    best_email = None
    best_about = None
    best_lang = None

    for u in urls_to_try:
        try:
            resp = requests.post(
                'https://api.firecrawl.dev/v1/scrape',
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                json={'url': u, 'formats': ['markdown'], 'onlyMainContent': False, 'timeout': 20000},
                timeout=30,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            md = (data.get('data') or {}).get('markdown') or ''
            if not md:
                continue

            emails = EMAIL_RX.findall(md)
            for e in emails:
                local = e.split('@')[0].lower()
                if local in GENERIC_EMAIL_PREFIXES:
                    continue
                if 'sentry' in e or 'example.com' in e or 'wixpress' in e:
                    continue
                best_email = e.lower()
                break

            if best_email is None and emails:
                # fallback to first email even if generic (info@, contact@)
                best_email = emails[0].lower()

            if not best_about:
                # First 500 chars of markdown body as about snippet
                stripped = re.sub(r'^[#\s>\-*]+', '', md, flags=re.MULTILINE)
                stripped = re.sub(r'\n+', ' ', stripped).strip()
                best_about = stripped[:500]

            if best_email:
                break
        except Exception as e:
            print(f'    firecrawl error on {u}: {e}')
            continue

    # Language detection
    if best_about:
        try:
            from langdetect import detect
            best_lang = detect(best_about)
        except Exception:
            pass

    return best_email, best_about, best_lang


def extract_domain(url):
    try:
        netloc = urlparse(url).netloc.lower()
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return None


def clean_company_name(title):
    # strip " - blah" and " | blah" suffixes
    for sep in [' - ', ' | ', ' – ', ' — ']:
        if sep in title:
            title = title.split(sep)[0]
    return title.strip()[:120]


if __name__ == '__main__':
    main()
