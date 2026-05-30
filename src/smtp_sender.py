"""
Standalone SMTP sender — sends personalized charter outreach mailove via Gmail SMTP.

Uses app password from croatian-dmc-suite/.env (already set up for tutafranko@gmail.com).
Fail-closed: marks lead as 'sent' in sent_log.json BEFORE actually calling smtp.send().
Rate-limited: configurable seconds between sends within a run; daily cap.

Usage:
  python smtp_sender.py --self-test      # send 1 mail to tutafranko@gmail.com
  python smtp_sender.py --pilot 3        # send 3 real mailova (first 3 unsent leads)
  python smtp_sender.py --batch 20       # send up to 20 (daily cap)
  python smtp_sender.py --dry-run        # just render, no send
"""
import sys
import io
import os
import json
import smtplib
import argparse
import time
from datetime import datetime, timezone, date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import formatdate, make_msgid

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CV_PATH = os.path.join(ROOT, 'data', 'couple_cv.pdf')
LEADS_PATH = os.path.join(ROOT, 'data', 'leads.json')
SENT_LOG = os.path.join(ROOT, 'data', 'sent_log.json')
DMC_ENV = r'C:\Users\WWW\Desktop\ai\claude code\croatian-dmc-suite\.env'

RATE_LIMIT_SECONDS = 300  # 5 min between sends — safe under Gmail's anti-spam threshold
DAILY_CAP = 20


def load_env(path):
    env = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def load_sent_log():
    if os.path.exists(SENT_LOG):
        with open(SENT_LOG, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'sent': [], 'errors': []}


def save_sent_log(log):
    with open(SENT_LOG, 'w', encoding='utf-8') as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def count_sent_today(log):
    today = date.today().isoformat()
    return sum(1 for s in log['sent'] if s['date'].startswith(today))


def build_mime(from_addr, from_name, to_addr, subject, body_text, cv_bytes):
    msg = MIMEMultipart('mixed')
    msg['From'] = f'"{from_name}" <{from_addr}>'
    msg['To'] = to_addr
    msg['Subject'] = subject
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid(domain='gmail.com')
    msg['Reply-To'] = from_addr

    alt = MIMEMultipart('alternative')
    alt.attach(MIMEText(body_text, 'plain', 'utf-8'))
    msg.attach(alt)

    if cv_bytes:
        att = MIMEApplication(cv_bytes, _subtype='pdf')
        att.add_header('Content-Disposition', 'attachment', filename='Tuta_Koncan_Couple_CV.pdf')
        msg.attach(att)

    return msg


def smtp_send(msg, smtp_user, smtp_password):
    with smtplib.SMTP('smtp.gmail.com', 587, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(smtp_user, smtp_password)
        smtp.sendmail(smtp_user, [msg['To']], msg.as_string())
    return msg['Message-ID']


def render_body(lead, personal_lines=True):
    """Simple template render — keeps the same tone we used for Gmail drafts."""
    name = lead.get('company_name', lead['domain'])
    city = lead.get('city', 'your area')
    category = lead.get('category', 'charter')
    intro = lead.get('intro_line') or (
        f"My partner Vana and I are a Croatian Captain + Stewardess couple looking for "
        f"{category} work with {name} in {city}. Available immediately, ready to relocate now."
    )

    body = f"""Hi {name} team,

{intro}

- Franko Tuta (22) — Captain/Skipper. Yachtmaster, Croatian Skipper Cat C, STCW Basic, ENG1, PADI Open Water, Private Pilot License. 3 paid charter seasons in Croatia across 20+ vessels — motor yachts to 17m (Bénéteau Antares, Jeanneau Cap Camarat), RIBs (Lomac 9.0, Marlin 790, Mercan 34, Enzo Vento HT30), sport cruisers, traditional 17m wooden Blaga. Strong mechanical/electrical (mechatronics high school + ACI Marina Split boat service experience). Daily charters in Central Dalmatia incl. precision Blue Cave entries on Biševo. English C1, Italian basic.

- Vana Končan (21) — Junior Stewardess/Deckhand. STCW Basic, ENG1, Food Hygiene Lvl 2, Boat Licence Cat B. 2025 charter season as deckhand on a 12m M/Y in Split + current hostess at Croatian National Theatre Split. Strong on guest service, F&B, housekeeping, tender ops.

Both English C1, Italian basic. Couple over a year, worked same Croatian charter season together on a chase boat operation in 2025 — proven team. Available immediately for rest of 2026 + Caribbean winter 2026/27.

Joint couple-application CV attached.

Best,
Franko Tuta
+385 95 737 8710 (WhatsApp) · tutafranko@gmail.com
Vana Končan · +385 95 618 6027 · vanko555@gmail.com
"""
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true', help='Send 1 test mail to tutafranko@gmail.com')
    ap.add_argument('--pilot', type=int, help='Send N real mailova (e.g. 3 for pilot)')
    ap.add_argument('--batch', type=int, help='Send up to N (default 20 daily cap)')
    ap.add_argument('--dry-run', action='store_true', help='Render, do NOT send')
    args = ap.parse_args()

    smtp_user = os.environ.get('SMTP_USER')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    if not smtp_user or not smtp_password:
        if os.path.exists(DMC_ENV):
            env = load_env(DMC_ENV)
            smtp_user = smtp_user or env.get('SMTP_USER')
            smtp_password = smtp_password or env.get('SMTP_PASSWORD')
    if not smtp_user or not smtp_password:
        print('ERROR: SMTP_USER and SMTP_PASSWORD must be set via env vars or DMC_ENV file')
        sys.exit(1)
    smtp_password = smtp_password.replace(' ', '')  # remove spaces from app password

    print(f'Loaded SMTP: {smtp_user} (password len={len(smtp_password)})')

    # Load CV bytes
    with open(CV_PATH, 'rb') as f:
        cv_bytes = f.read()
    print(f'CV loaded: {len(cv_bytes)} bytes')

    # Self-test mode: send 1 mail to self
    if args.self_test:
        lead = {
            'domain': 'self-test.example',
            'company_name': 'Example Charter Co (SELF TEST)',
            'category': 'charter',
            'city': 'Palma de Mallorca',
            'language': 'en',
        }
        subject = 'SELF-TEST · Captain + Stewardess couple — available immediately for Example Charter Co'
        body = render_body(lead)

        if args.dry_run:
            print('--- DRY RUN ---')
            print(f'To: {smtp_user}')
            print(f'Subject: {subject}')
            print(body)
            return

        msg = build_mime(smtp_user, 'Franko Tuta', smtp_user, subject, body, cv_bytes)
        try:
            mid = smtp_send(msg, smtp_user, smtp_password)
            print(f'SELF-TEST SENT to {smtp_user} | Message-ID: {mid}')
        except Exception as e:
            print(f'SELF-TEST ERROR: {e}')
            sys.exit(1)
        return

    # Load leads
    if not os.path.exists(LEADS_PATH):
        print(f'ERROR: leads file missing at {LEADS_PATH}. Run extract_leads_from_drafts.py first.')
        sys.exit(1)

    with open(LEADS_PATH, 'r', encoding='utf-8') as f:
        leads = json.load(f)

    print(f'Loaded {len(leads)} leads')

    # Load sent log
    log = load_sent_log()
    sent_emails = {s['to'] for s in log['sent']}
    today_count = count_sent_today(log)
    print(f'Already sent today: {today_count} / {DAILY_CAP}')

    # Filter unsent
    pending = [l for l in leads if l['to'].lower() not in sent_emails]
    print(f'Pending: {len(pending)} leads')

    if not pending:
        print('No pending leads.')
        return

    # How many to send this run
    if args.pilot:
        limit = args.pilot
    elif args.batch:
        limit = args.batch
    else:
        limit = DAILY_CAP

    remaining_today = max(0, DAILY_CAP - today_count)
    limit = min(limit, remaining_today, len(pending))
    print(f'Will send {limit} this run')

    if args.dry_run:
        print('--- DRY RUN ---')
        for i, lead in enumerate(pending[:limit], 1):
            subject = lead.get('subject') or f"Captain + Stewardess couple — available for {lead.get('company_name', '')}"
            body = render_body(lead)
            print(f'\n[{i}] To: {lead["to"]}  Subject: {subject[:80]}')
        return

    # Real send loop
    for i, lead in enumerate(pending[:limit], 1):
        subject = lead.get('subject') or f"Captain + Stewardess couple — available for {lead.get('company_name', '')}"
        body = render_body(lead)
        msg = build_mime(smtp_user, 'Franko Tuta', lead['to'], subject, body, cv_bytes)

        # FAIL-CLOSED: mark sent BEFORE actual send
        now = datetime.now(timezone.utc).isoformat()
        sent_entry = {
            'to': lead['to'],
            'domain': lead.get('domain'),
            'company_name': lead.get('company_name'),
            'subject': subject,
            'date': now,
            'status': 'attempting',
        }
        log['sent'].append(sent_entry)
        save_sent_log(log)

        try:
            mid = smtp_send(msg, smtp_user, smtp_password)
            sent_entry['status'] = 'sent'
            sent_entry['message_id'] = mid
            save_sent_log(log)
            print(f'[{i}/{limit}] SENT  {lead["to"]}  |  Message-ID: {mid[:40]}...')
        except Exception as e:
            sent_entry['status'] = 'error'
            sent_entry['error'] = str(e)
            log['errors'].append(sent_entry)
            save_sent_log(log)
            print(f'[{i}/{limit}] ERROR  {lead["to"]}  |  {e}')

        if i < limit:
            print(f'   sleeping {RATE_LIMIT_SECONDS}s...')
            time.sleep(RATE_LIMIT_SECONDS)

    final_count = count_sent_today(log)
    print(f'\nDONE. Sent today: {final_count} / {DAILY_CAP}')


if __name__ == '__main__':
    main()
