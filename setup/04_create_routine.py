"""
Prepares the routine prompt with config values embedded and prints it.

The actual CronCreate call happens via Claude Code: I (Claude) call the
CronCreate tool after this script outputs the final embed-ready prompt.

Usage:
  python setup/04_create_routine.py
"""
import sys
import io
import os
import yaml

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = r'C:\Users\WWW\Desktop\ai\claude code\job-outreach'
CONFIG_ENV = os.path.join(ROOT, 'data', 'config.env')
PROMPT_PATH = os.path.join(ROOT, 'routine_prompts', 'daily_outreach.md')
PERSONAL_INFO = os.path.join(ROOT, 'data', 'personal_info.yaml')
OUTPUT_PATH = os.path.join(ROOT, 'routine_prompts', 'daily_outreach_FINAL.md')


def load_env(path):
    env = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env


cfg = load_env(CONFIG_ENV)
SHEET_ID = cfg.get('SHEET_ID')
CV_FILE_ID = cfg.get('CV_DRIVE_FILE_ID')

assert SHEET_ID, 'config.env missing SHEET_ID. Run 01_create_sheet.py.'
assert CV_FILE_ID, 'config.env missing CV_DRIVE_FILE_ID. Run find_cv_id.py.'

with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
    prompt = f.read()

with open(PERSONAL_INFO, 'r', encoding='utf-8') as f:
    personal_yaml = f.read()

prompt = prompt.replace('{{SHEET_ID}}', SHEET_ID)
prompt = prompt.replace('{{CV_DRIVE_FILE_ID}}', CV_FILE_ID)

# Append personal info embed
prompt += '\n\n## Embedded personal_info.yaml\n\n```yaml\n' + personal_yaml + '\n```\n'

with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    f.write(prompt)

print(f'Final embed-ready prompt written to: {OUTPUT_PATH}')
print(f'Length: {len(prompt)} chars')
print()
print('NEXT: tell Claude (in this conversation) to call CronCreate with:')
print(f'  - cron schedule: "0 8 * * *"   # 08:00 UTC = 09:00/10:00 CET')
print(f'  - prompt file: {OUTPUT_PATH}')
print(f'  - name: "charter-outreach-daily"')
