"""
Google Sheet read/write operations.
"""
import os
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import gspread

TOKEN_PATH = r'C:\Users\WWW\Desktop\ai\claude code\croatian-dmc-suite\token.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


def get_gc():
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, scopes=SCOPES)
    if creds.expired:
        creds.refresh(Request())
    return gspread.authorize(creds)


def open_sheet(sheet_id):
    gc = get_gc()
    return gc.open_by_key(sheet_id)


def read_config(sh):
    """Returns dict {key: value} from Config tab."""
    ws = sh.worksheet('Config')
    rows = ws.get_all_records()
    return {r['key']: r['value'] for r in rows}


def write_config(sh, key, value):
    ws = sh.worksheet('Config')
    cell = ws.find(key)
    if cell:
        ws.update_cell(cell.row, 2, str(value))


def get_ready_leads(sh, limit=20):
    """Read Leads where status=ready AND sent_at empty."""
    ws = sh.worksheet('Leads')
    rows = ws.get_all_records()
    ready = []
    for i, r in enumerate(rows, start=2):  # rows are 1-indexed, +1 for header
        if r.get('status') == 'ready' and not r.get('sent_at') and not r.get('send_error'):
            r['_row'] = i
            ready.append(r)
    # oldest first
    ready.sort(key=lambda x: x.get('discovered_at', ''))
    return ready[:limit]


def count_ready_leads(sh):
    ws = sh.worksheet('Leads')
    statuses = ws.col_values(12)[1:]  # column L = status
    sent_ats = ws.col_values(14)[1:]  # column N = sent_at
    count = 0
    for s, sa in zip(statuses, sent_ats):
        if s == 'ready' and not sa:
            count += 1
    return count


def mark_sent(sh, row, message_id=''):
    """Fail-closed: mark BEFORE actual send. row = sheet row number."""
    ws = sh.worksheet('Leads')
    now = datetime.now(timezone.utc).isoformat()
    ws.update_cell(row, 12, 'sent')      # status
    ws.update_cell(row, 14, now)         # sent_at


def mark_send_error(sh, row, error):
    ws = sh.worksheet('Leads')
    ws.update_cell(row, 12, 'send_error')
    ws.update_cell(row, 15, str(error)[:500])


def append_sent_log(sh, lead, subject, template_key, personalization, message_id, status, error=''):
    ws = sh.worksheet('Sent')
    now = datetime.now(timezone.utc).isoformat()
    ws.append_row([
        now,
        lead.get('lead_id', ''),
        lead.get('domain', ''),
        lead.get('email', ''),
        subject,
        template_key,
        lead.get('language', ''),
        lead.get('category', ''),
        personalization,
        message_id,
        status,
        str(error)[:500],
    ], value_input_option='RAW')
