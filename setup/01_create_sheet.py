"""
One-time bootstrap: create Google Sheet 'Charter_Outreach' with 3 tabs.

Tabs:
  - Leads: discovered companies (one row per company)
  - Sent: log of every send attempt (one row per attempted send)
  - Config: knobs (current_tier, pilot_approved, paused, daily_cap, ratios)

After creation, prints SHEET_ID and Drive folder ID for couple_cv.pdf.
Writes both into data/config.env.
"""
import sys
import io
import os
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import gspread
from googleapiclient.discovery import build

TOKEN_PATH = r'C:\Users\WWW\Desktop\ai\claude code\croatian-dmc-suite\token.json'
CONFIG_ENV = r'C:\Users\WWW\Desktop\ai\claude code\job-outreach\data\config.env'

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]

LEADS_HEADERS = [
    'lead_id', 'domain', 'company_name', 'email', 'category', 'tier',
    'language', 'country', 'city', 'about_snippet', 'website',
    'status', 'discovered_at', 'sent_at', 'send_error', 'notes',
]
# status values: discovered | enriched | ready | sent | send_error | bounced | replied | blacklist

SENT_HEADERS = [
    'sent_at', 'lead_id', 'domain', 'email', 'subject', 'template_key',
    'language', 'category', 'personalization', 'message_id', 'status', 'error',
]

CONFIG_ROWS = [
    ['key', 'value', 'note'],
    ['current_tier', '1', 'Active geo tier: 1=Palma, 2=Balearic, 3=Italy, 4=France, 5=Caribbean'],
    ['pilot_approved', 'FALSE', 'Set TRUE after pilot 3 mailova verified. Routine sends 20/day only when TRUE.'],
    ['paused', 'FALSE', 'Manual kill switch. TRUE = routine refuses to send.'],
    ['daily_cap', '20', 'Max mailova per fire.'],
    ['pilot_size', '3', 'Mailova in pilot mode (when pilot_approved=FALSE).'],
    ['med_caribbean_ratio', '3:1', 'Tier 1-4 (Med) vs Tier 5 (Caribbean) send ratio.'],
    ['min_ready_threshold', '40', 'Trigger discovery top-up when ready<this.'],
    ['min_tier_threshold', '30', 'Escalate tier when ready in current tier<this.'],
    ['rate_limit_seconds', '30', 'Pause between sends within same fire.'],
    ['cv_drive_file_id', '', 'FILL IN: couple_cv.pdf file ID from Drive'],
    ['sheet_id', '', 'AUTO-FILLED below'],
]

print('Loading credentials...')
creds = Credentials.from_authorized_user_file(TOKEN_PATH, scopes=SCOPES)
if creds.expired:
    creds.refresh(Request())

gc = gspread.authorize(creds)
drive = build('drive', 'v3', credentials=creds)

print('Creating spreadsheet Charter_Outreach...')
sh = gc.create('Charter_Outreach')
sheet_id = sh.id
print(f'  Sheet ID: {sheet_id}')

print('Renaming default sheet to Leads and adding headers...')
ws_leads = sh.sheet1
ws_leads.update_title('Leads')
ws_leads.update(values=[LEADS_HEADERS], range_name='A1', value_input_option='RAW')
ws_leads.format('A1:Z1', {'textFormat': {'bold': True}})
ws_leads.freeze(rows=1)
time.sleep(1)

print('Creating Sent tab...')
ws_sent = sh.add_worksheet('Sent', rows=2000, cols=len(SENT_HEADERS))
ws_sent.update(values=[SENT_HEADERS], range_name='A1', value_input_option='RAW')
ws_sent.format('A1:Z1', {'textFormat': {'bold': True}})
ws_sent.freeze(rows=1)
time.sleep(1)

print('Creating Config tab...')
ws_config = sh.add_worksheet('Config', rows=50, cols=3)
config_with_sheet_id = []
for row in CONFIG_ROWS:
    if row[0] == 'sheet_id':
        config_with_sheet_id.append(['sheet_id', sheet_id, 'Auto-filled by 01_create_sheet.py'])
    else:
        config_with_sheet_id.append(row)
ws_config.update(values=config_with_sheet_id, range_name='A1', value_input_option='RAW')
ws_config.format('A1:C1', {'textFormat': {'bold': True}})
ws_config.freeze(rows=1)
time.sleep(1)

print('Creating Charter_CVs Drive folder...')
folder_metadata = {
    'name': 'Charter_CVs',
    'mimeType': 'application/vnd.google-apps.folder',
}
folder = drive.files().create(body=folder_metadata, fields='id').execute()
folder_id = folder['id']
print(f'  Folder ID: {folder_id}')

print(f'Writing {CONFIG_ENV}...')
os.makedirs(os.path.dirname(CONFIG_ENV), exist_ok=True)
with open(CONFIG_ENV, 'w', encoding='utf-8') as f:
    f.write(f'SHEET_ID={sheet_id}\n')
    f.write(f'CV_DRIVE_FOLDER_ID={folder_id}\n')
    f.write('CV_DRIVE_FILE_ID=\n')  # to be filled after user uploads PDF
    f.write('# Fill these from .env (do NOT commit secrets):\n')
    f.write('# GMAIL_APP_PASSWORD=\n')
    f.write('# SERPER_API_KEY=\n')
    f.write('# FIRECRAWL_API_KEY=\n')

print()
print('=' * 60)
print(f'DONE.')
print(f'Sheet URL:  https://docs.google.com/spreadsheets/d/{sheet_id}/edit')
print(f'CV folder:  https://drive.google.com/drive/folders/{folder_id}')
print()
print('NEXT STEPS:')
print(f'  1. Upload couple_cv.pdf to the Charter_CVs folder above')
print(f'  2. Copy the file ID from the URL and paste into Config tab cv_drive_file_id')
print(f'     (or run setup/find_cv_id.py to do it automatically)')
print(f'  3. Fill data/personal_info.yaml')
print(f'  4. Add secrets to job-outreach/.env (Gmail app password, Serper, Firecrawl)')
print(f'  5. Run setup/03_seed_initial_leads.py')
print('=' * 60)
