"""
Find couple_cv.pdf in the Charter_CVs Drive folder and write file ID
to data/config.env + Sheet Config tab cv_drive_file_id.

Run this AFTER you upload couple_cv.pdf to the Charter_CVs folder.
"""
import sys
import io
import os
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import gspread

TOKEN_PATH = r'C:\Users\WWW\Desktop\ai\claude code\croatian-dmc-suite\token.json'
CONFIG_ENV = r'C:\Users\WWW\Desktop\ai\claude code\job-outreach\data\config.env'

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.readonly',
]


def load_env(path):
    env = {}
    if not os.path.exists(path):
        return env
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env


def save_env(path, env):
    with open(path, 'w', encoding='utf-8') as f:
        for k, v in env.items():
            f.write(f'{k}={v}\n')


env = load_env(CONFIG_ENV)
folder_id = env.get('CV_DRIVE_FOLDER_ID')
sheet_id = env.get('SHEET_ID')
if not folder_id or not sheet_id:
    print('ERROR: config.env missing CV_DRIVE_FOLDER_ID or SHEET_ID. Run 01_create_sheet.py first.')
    sys.exit(1)

creds = Credentials.from_authorized_user_file(TOKEN_PATH, scopes=SCOPES)
if creds.expired:
    creds.refresh(Request())

drive = build('drive', 'v3', credentials=creds)

print(f'Listing files in folder {folder_id}...')
result = drive.files().list(
    q=f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false",
    fields='files(id,name,modifiedTime)',
    orderBy='modifiedTime desc',
).execute()
files = result.get('files', [])
if not files:
    print('ERROR: No PDF found in Charter_CVs folder. Upload couple_cv.pdf first.')
    sys.exit(1)

# Prefer couple_cv.pdf, otherwise most recent PDF
target = None
for f in files:
    if re.search(r'couple', f['name'], re.IGNORECASE):
        target = f
        break
if not target:
    target = files[0]
    print(f'WARN: no couple_cv.pdf found; using most recent: {target["name"]}')

print(f'Selected CV: {target["name"]} (id={target["id"]})')

env['CV_DRIVE_FILE_ID'] = target['id']
save_env(CONFIG_ENV, env)
print(f'Updated {CONFIG_ENV} with CV_DRIVE_FILE_ID')

# Update Sheet Config tab
print('Updating Sheet Config tab...')
gc = gspread.authorize(creds.with_scopes(SCOPES + ['https://www.googleapis.com/auth/spreadsheets']))
# Need spreadsheets scope; re-load with combined scope
combined_scopes = list(set(SCOPES + ['https://www.googleapis.com/auth/spreadsheets']))
creds2 = Credentials.from_authorized_user_file(TOKEN_PATH, scopes=combined_scopes)
if creds2.expired:
    creds2.refresh(Request())
gc = gspread.authorize(creds2)
sh = gc.open_by_key(sheet_id)
ws = sh.worksheet('Config')
# Find row with key=cv_drive_file_id
cell = ws.find('cv_drive_file_id')
if cell:
    ws.update_cell(cell.row, 2, target['id'])
    print(f'  Wrote cv_drive_file_id={target["id"]} to Config row {cell.row}')
else:
    print('  WARN: cv_drive_file_id row not found in Config tab')

print('Done.')
