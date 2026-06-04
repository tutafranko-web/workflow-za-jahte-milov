"""Merge all Google Maps CSV scrapes in data/maps_scrapes/, dedupe vs already_drafted, output candidates.json."""
import csv, json, os, glob, re, sys
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRAPES = os.path.join(ROOT, 'data', 'maps_scrapes')
ALREADY = os.path.join(ROOT, 'data', 'already_drafted.json')
OUT = os.path.join(ROOT, 'data', 'candidates.json')

SOCIAL = ('facebook.','instagram.','linkedin.','tiktok.','twitter.','x.com',
          'getyourguide.','tripadvisor.','viator.','sites.google.','linktr.ee',
          'youtube.','wa.me','goo.gl')

def extract_url(row):
    for cell in row:
        c = cell.strip()
        if c.startswith('http') and 'google.com/maps' not in c and 'gstatic' not in c:
            return c
    return None

def extract_phone(row):
    for cell in row:
        c = cell.strip()
        # phone pattern: starts with + or digit, has 6+ digits
        if re.match(r'^[\+\d][\d\s\-\(\)]{6,25}$', c):
            return c
    return None

def main():
    with open(ALREADY, 'r', encoding='utf-8') as f:
        ad = json.load(f)
    contacted = set(d.lower() for d in ad['domains'])
    skip = set(d.lower() for d in ad['skip_aggregators'])

    seen, candidates, dupes, aggrs = set(), [], [], []
    csvs = sorted(glob.glob(os.path.join(SCRAPES, '*.csv')))

    for fp in csvs:
        with open(fp, 'r', encoding='utf-8') as fh:
            rdr = csv.reader(fh)
            next(rdr, None)
            for r in rdr:
                if not any(c.strip() for c in r): continue
                name = r[1].strip() if len(r)>1 else ''
                url = extract_url(r)
                phone = extract_phone(r)
                if not url: continue
                try:
                    host = (urlparse(url).hostname or '').replace('www.','').lower()
                except: continue
                if not host: continue
                if any(s in host for s in SOCIAL):
                    aggrs.append((host, name)); continue
                if host in skip:
                    aggrs.append((host, name)); continue
                if host in contacted:
                    dupes.append((host, name)); continue
                if host in seen: continue
                seen.add(host)
                candidates.append({
                    'domain': host, 'company_name': name,
                    'website': url, 'phone': phone,
                    'source_csv': os.path.basename(fp),
                })

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'count': len(candidates), 'candidates': candidates}, f, indent=2, ensure_ascii=False)

    print(f'CSVs read: {len(csvs)}')
    print(f'Already contacted (DUP): {len(dupes)}')
    print(f'Aggregator/social skip: {len(aggrs)}')
    print(f'UNIKATNI NOVI domeni: {len(candidates)}')
    print(f'Output: {OUT}')

if __name__ == '__main__':
    main()
