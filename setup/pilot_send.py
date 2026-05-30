"""
Manual pilot send. Pick first N ready leads and send (or dry-run).

Usage:
  python pilot_send.py --dry-run            # render templates and dump to stdout
  python pilot_send.py --to-self            # send 1 mail to tutafranko@gmail.com
  python pilot_send.py --live --limit 3     # send 3 real mails

DRY-RUN does NOT touch the Sheet. LIVE mode marks-sent FIRST, then sends.
"""
import sys
import io
import os
import argparse
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from renderer import load_personal_info, render_email
from gmail_sender import fetch_cv_bytes, build_mime, send_via_gmail_api, send_via_smtp
from sheet_ops import open_sheet, get_ready_leads, mark_sent, mark_send_error, append_sent_log, read_config

ROOT = r'C:\Users\WWW\Desktop\ai\claude code\job-outreach'
CONFIG_ENV = os.path.join(ROOT, 'data', 'config.env')
DOTENV = os.path.join(ROOT, '.env')


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


def make_personalization(lead):
    """Simple deterministic personalization from About snippet for pilot.
    The routine itself uses Claude to generate this; here we keep it minimal."""
    about = (lead.get('about_snippet') or '').strip()
    city = lead.get('city') or ''
    company = lead.get('company_name') or lead.get('domain', '').split('.')[0].title()
    cat = lead.get('category', '')
    if about:
        first_sentence = about.split('.')[0].strip()
        if len(first_sentence) > 220:
            first_sentence = first_sentence[:220]
        return f"I came across {company} while looking at {cat or 'charter'} operations in {city or 'the area'} — '{first_sentence}' caught my attention."
    return f"I'm reaching out to {company} as part of my search for a skipper + deckhand position in {city or 'your area'}."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true', help='Render only, do not send')
    ap.add_argument('--to-self', action='store_true', help='Send 1 test mail to tutafranko@gmail.com (ignores Leads sheet)')
    ap.add_argument('--live', action='store_true', help='Actually send to real leads')
    ap.add_argument('--limit', type=int, default=3, help='Number of mails to send (default 3)')
    ap.add_argument('--smtp', action='store_true', help='Use SMTP fallback instead of Gmail API')
    args = ap.parse_args()

    cfg = load_env(CONFIG_ENV)
    secrets = load_env(DOTENV)
    SHEET_ID = cfg.get('SHEET_ID')
    CV_FILE_ID = cfg.get('CV_DRIVE_FILE_ID')
    GMAIL_APP_PASS = secrets.get('GMAIL_APP_PASSWORD') or os.environ.get('GMAIL_APP_PASSWORD')

    if not SHEET_ID:
        print('ERROR: SHEET_ID missing. Run 01_create_sheet.py.')
        sys.exit(1)
    if not CV_FILE_ID and not args.dry_run:
        print('ERROR: CV_DRIVE_FILE_ID missing. Upload couple_cv.pdf and run find_cv_id.py.')
        sys.exit(1)

    personal = load_personal_info()
    from_addr = personal['skipper']['email']

    # Fetch CV once
    cv_bytes = None
    if not args.dry_run:
        print(f'Fetching CV from Drive (id={CV_FILE_ID})...')
        cv_bytes = fetch_cv_bytes(CV_FILE_ID)
        print(f'  CV size: {len(cv_bytes)} bytes')

    # to-self mode: build 1 fake lead
    if args.to_self:
        leads = [{
            'lead_id': 'TEST',
            'domain': 'example.com',
            'company_name': 'Example Charter Co',
            'email': from_addr,
            'category': 'charter',
            'tier': 1,
            'language': 'en',
            'city': 'Palma de Mallorca',
            'about_snippet': 'We are a family-run charter company operating in Palma since 2012, with a fleet of 8 sailing yachts.',
            '_row': None,
        }]
    else:
        sh = open_sheet(SHEET_ID)
        leads = get_ready_leads(sh, limit=args.limit)
        if not leads:
            print('No ready leads. Run seed first.')
            return

    for i, lead in enumerate(leads, 1):
        print(f'\n--- Lead {i}/{len(leads)}: {lead.get("domain")} ({lead.get("email")}) ---')
        personalization = make_personalization(lead)
        subject, body = render_email(lead, personal, personalization)
        print(f'Subject: {subject}')
        print(f'Body:\n{body}\n')

        if args.dry_run:
            continue

        msg = build_mime(
            from_addr=from_addr,
            to_addr=lead['email'],
            subject=subject,
            body_text=body,
            cv_bytes=cv_bytes,
            reply_to=from_addr,
        )

        # FAIL-CLOSED: mark sent BEFORE actual send (except in to-self mode)
        if not args.to_self and lead.get('_row'):
            mark_sent(open_sheet(SHEET_ID), lead['_row'])

        try:
            if args.smtp:
                if not GMAIL_APP_PASS:
                    print('ERROR: GMAIL_APP_PASSWORD missing for --smtp mode')
                    sys.exit(1)
                msg_id = send_via_smtp(msg, from_addr, GMAIL_APP_PASS)
            else:
                msg_id = send_via_gmail_api(msg)
            print(f'  SENT. Message-ID: {msg_id}')
            if not args.to_self:
                append_sent_log(open_sheet(SHEET_ID), lead, subject, lead.get('category', ''), personalization, msg_id, 'sent')
        except Exception as e:
            print(f'  SEND ERROR: {e}')
            if not args.to_self and lead.get('_row'):
                mark_send_error(open_sheet(SHEET_ID), lead['_row'], str(e))
                append_sent_log(open_sheet(SHEET_ID), lead, subject, lead.get('category', ''), personalization, '', 'send_error', str(e))

        if i < len(leads):
            time.sleep(20)  # rate limit between sends


if __name__ == '__main__':
    main()
