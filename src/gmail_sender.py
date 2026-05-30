"""
Gmail API send via OAuth (preferred) with SMTP app-password fallback.
"""
import os
import base64
import smtplib
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import make_msgid, formatdate

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

TOKEN_PATH = r'C:\Users\WWW\Desktop\ai\claude code\croatian-dmc-suite\token.json'


def _load_creds():
    scopes = [
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/drive.readonly',
    ]
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, scopes=scopes)
    if creds.expired:
        creds.refresh(Request())
    return creds


def fetch_cv_bytes(cv_drive_file_id):
    """Download couple_cv.pdf bytes from Drive."""
    creds = _load_creds()
    drive = build('drive', 'v3', credentials=creds)
    buf = io.BytesIO()
    req = drive.files().get_media(fileId=cv_drive_file_id)
    downloader = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _status, done = downloader.next_chunk()
    return buf.getvalue()


def build_mime(from_addr, to_addr, subject, body_text, cv_bytes, cv_filename='couple_cv.pdf', reply_to=None):
    msg = MIMEMultipart('mixed')
    msg['From'] = from_addr
    msg['To'] = to_addr
    msg['Subject'] = subject
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid(domain='gmail.com')
    if reply_to:
        msg['Reply-To'] = reply_to

    alt = MIMEMultipart('alternative')
    alt.attach(MIMEText(body_text, 'plain', 'utf-8'))
    msg.attach(alt)

    if cv_bytes:
        attach = MIMEApplication(cv_bytes, _subtype='pdf')
        attach.add_header('Content-Disposition', 'attachment', filename=cv_filename)
        msg.attach(attach)

    return msg


def send_via_gmail_api(msg):
    """Send via Gmail API. Returns Gmail message id."""
    creds = _load_creds()
    service = build('gmail', 'v1', credentials=creds)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
    result = service.users().messages().send(userId='me', body={'raw': raw}).execute()
    return result.get('id')


def send_via_smtp(msg, from_addr, app_password):
    """Fallback: send via Gmail SMTP with app password."""
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30) as smtp:
        smtp.login(from_addr, app_password)
        to = msg['To']
        smtp.sendmail(from_addr, [to], msg.as_string())
    return msg['Message-ID']
