"""Filter candidates_enriched to those with valid email, dedupe vs leads.json, append."""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENRICHED = os.path.join(ROOT, 'data', 'candidates_enriched.json')
LEADS = os.path.join(ROOT, 'data', 'leads.json')

def pick_best_email(emails, domain):
    """Prefer info@<domain>, contact@<domain>, then any matching domain, then first."""
    if not emails: return None
    dom_clean = domain.replace('www.','').lower()
    # exact match info@
    for prefix in ['info@', 'contact@', 'hello@', 'jobs@', 'careers@', 'crew@', 'reservas@', 'booking@']:
        for e in emails:
            if e.startswith(prefix) and dom_clean in e:
                return e
    # any email at same domain
    for e in emails:
        if dom_clean in e: return e
    # fallback: first
    return emails[0]


def main():
    with open(ENRICHED, 'r', encoding='utf-8') as f:
        data = json.load(f)
    with open(LEADS, 'r', encoding='utf-8') as f:
        leads = json.load(f)

    existing_emails = {l['to'].lower() for l in leads}
    existing_domains = {l.get('domain','').lower() for l in leads}

    added = []
    skipped_no_email = 0
    skipped_dup = 0

    for c in data['enriched']:
        emails = c.get('emails', [])
        if not emails:
            skipped_no_email += 1
            continue
        best = pick_best_email(emails, c['domain'])
        if not best:
            skipped_no_email += 1
            continue
        if best.lower() in existing_emails:
            skipped_dup += 1
            continue
        if c['domain'].lower() in existing_domains:
            skipped_dup += 1
            continue
        lead = {
            'to': best,
            'domain': c['domain'],
            'company_name': c['company_name'],
            'category': 'charter',
            'city': 'Palma de Mallorca',
            'language': 'en',
            'phone': c.get('phone') or (c.get('tel_links') or [None])[0],
            'whatsapp': (c.get('whatsapp') or [None])[0],
        }
        leads.append(lead)
        existing_emails.add(best.lower())
        existing_domains.add(c['domain'].lower())
        added.append(lead)

    with open(LEADS, 'w', encoding='utf-8') as f:
        json.dump(leads, f, indent=2, ensure_ascii=False)

    print(f'Added: {len(added)}')
    print(f'Skipped no-email: {skipped_no_email}')
    print(f'Skipped dup: {skipped_dup}')
    print(f'leads.json total now: {len(leads)}')
    print()
    print('Added (first 15):')
    for l in added[:15]:
        to = l['to']
        cn = l['company_name'][:35]
        print(f'  {to:<45}  {cn}')


if __name__ == '__main__':
    main()
