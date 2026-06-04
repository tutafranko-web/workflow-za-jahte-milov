"""For each candidate website, fetch homepage + common contact paths, extract email/tel/WhatsApp.

Outputs data/candidates_enriched.json with verified contact info.
Per 'no blind guesses' rule: only emails found via regex on actual HTML, no guessing info@<domain>.
"""
import json, os, re, sys, time, urllib.request, urllib.error, ssl
from urllib.parse import urljoin, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATES = os.path.join(ROOT, 'data', 'candidates.json')
OUT = os.path.join(ROOT, 'data', 'candidates_enriched.json')

PATHS = ['', 'contact', 'contacto', 'contatti', 'contatto', 'kontakt', 'about',
         'about-us', 'impressum', 'en/contact', 'es/contacto', 'de/kontakt',
         'contact-us', 'careers', 'jobs', 'crew', 'sobre-nosotros', 'chi-siamo']

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
TEL_RE = re.compile(r'tel:([+\d][\d\s\-\(\)]{6,25})', re.I)
WA_RE = re.compile(r'(?:wa\.me/|whatsapp\.com/send\?phone=|api\.whatsapp\.com/send\?phone=)(\+?\d{6,15})', re.I)
WA_TEXT = re.compile(r'whatsapp[^a-z]+(\+?[\d\s\-\(\)]{8,20})', re.I)
# Cloudflare email-protection: data-cfemail="abcd1234..."
CF_RE = re.compile(r'data-cfemail="([0-9a-f]+)"', re.I)


def cf_decode(enc):
    """Decode Cloudflare-protected email. enc is hex string."""
    try:
        r = int(enc[:2], 16)
        return ''.join(chr(int(enc[i:i+2], 16) ^ r) for i in range(2, len(enc), 2))
    except Exception:
        return ''

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36'
TIMEOUT = 15
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def fetch(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html,*/*'})
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as r:
            ctype = r.headers.get('Content-Type', '')
            if 'text/html' not in ctype and 'text' not in ctype:
                return ''
            data = r.read(500_000)
            try: return data.decode('utf-8', errors='ignore')
            except: return data.decode('latin-1', errors='ignore')
    except Exception:
        return ''


def clean_email(e):
    e = e.lower().strip().strip('.,;:"\'<>')
    if any(x in e for x in ['example.com', 'example.', 'sentry.', 'andromedant',
                            '.png', '.jpg', '.gif', '.webp', '.svg', '.ico',
                            'wixpress.com', 'godaddy.com', 'cookieinfo', '@2x',
                            'u003e', 'u003c', 'sentry-next', 'mail.com', 'correo.es',
                            'email.com', 'domain.com', 'yourdomain', 'youremail',
                            'test@', 'foo@', 'bar@', 'name@', 'firstname',
                            'lastname', 'username', 'noreply@', 'no-reply@']):
        return None
    if e.endswith(('.png','.jpg','.webp','.svg','.gif','.ico','.css','.js')):
        return None
    if len(e) > 80: return None
    if '@' not in e or e.count('@') != 1: return None
    local, dom = e.split('@')
    if len(local) < 1 or len(dom) < 4: return None
    return e


def scrape_one(cand):
    base = cand['website'].rstrip('/')
    p = urlparse(base)
    root = f'{p.scheme}://{p.netloc}'
    emails, tels, was = set(), set(), set()
    pages_seen = 0

    for path in PATHS:
        url = root if path == '' else f'{root}/{path}'
        if path and not path.startswith('en/') and not path.startswith('es/'):
            # only try root + first-level paths
            pass
        html = fetch(url)
        if not html: continue
        pages_seen += 1

        for m in EMAIL_RE.findall(html):
            e = clean_email(m)
            if e: emails.add(e)
        # Cloudflare-protected emails
        for cf in CF_RE.findall(html):
            decoded = cf_decode(cf)
            if decoded:
                e = clean_email(decoded)
                if e: emails.add(e)
        for m in TEL_RE.findall(html):
            tels.add(re.sub(r'\s+', ' ', m).strip())
        for m in WA_RE.findall(html):
            d = re.sub(r'\D', '', m)
            if 8 <= len(d) <= 15: was.add('+' + d)

        if pages_seen >= 4 and emails: break  # enough

    return {
        **cand,
        'emails': sorted(emails)[:5],
        'tel_links': sorted(tels)[:3],
        'whatsapp': sorted(was)[:2],
        'pages_scraped': pages_seen,
    }


def main():
    with open(CANDIDATES, 'r', encoding='utf-8') as f:
        data = json.load(f)
    cands = data['candidates']
    out = []
    start = time.time()
    for i, c in enumerate(cands, 1):
        try:
            res = scrape_one(c)
        except Exception as e:
            res = {**c, 'emails': [], 'tel_links': [], 'whatsapp': [], 'error': str(e)}
        out.append(res)
        em = ','.join(res.get('emails', [])) or '-'
        print(f'[{i}/{len(cands)}] {c["domain"]:<40}  emails={em[:60]}')
        # save snapshot every 10
        if i % 10 == 0:
            with open(OUT, 'w', encoding='utf-8') as f:
                json.dump({'count': len(out), 'enriched': out}, f, indent=2, ensure_ascii=False)

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'count': len(out), 'enriched': out}, f, indent=2, ensure_ascii=False)

    elapsed = time.time() - start
    with_email = sum(1 for r in out if r.get('emails'))
    print(f'\nDONE in {elapsed:.0f}s. {with_email}/{len(out)} have email ({100*with_email/len(out):.0f}%).')


if __name__ == '__main__':
    main()
