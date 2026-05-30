"""
One-time OAuth re-consent to extend scopes for:
  - gmail.send (send mail via Gmail API)
  - drive.readonly (fetch couple_cv.pdf from Drive)

Re-uses existing client_secret.json from croatian-dmc-suite.
Overwrites token.json with extended-scope credentials.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from google_auth_oauthlib.flow import InstalledAppFlow

CLIENT_SECRET = r'C:\Users\WWW\Desktop\ai\claude code\croatian-dmc-suite\client_secret.json'
TOKEN_PATH = r'C:\Users\WWW\Desktop\ai\claude code\croatian-dmc-suite\token.json'

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/calendar.readonly',
]

print('Opening browser for Google re-consent (gmail.send + drive.readonly)...')
flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
creds = flow.run_local_server(port=0)

with open(TOKEN_PATH, 'w') as f:
    f.write(creds.to_json())

print(f'Token saved with extended scopes to {TOKEN_PATH}')
print('Granted scopes:')
for s in SCOPES:
    print(f'  - {s}')
