"""
Template rendering. Loads templates/{lang}_{template_key}.txt and renders with Jinja.

Template file format:
  SUBJECT_VARIANTS:
  - subject 1
  - subject 2
  - subject 3
  ---
  BODY:
  <body text>
"""
import os
import random
import re
import yaml
from jinja2 import Environment, BaseLoader, StrictUndefined

ROOT = r'C:\Users\WWW\Desktop\ai\claude code\job-outreach'
TEMPLATES_DIR = os.path.join(ROOT, 'templates')
PERSONAL_INFO = os.path.join(ROOT, 'data', 'personal_info.yaml')

_jinja_env = Environment(loader=BaseLoader(), undefined=StrictUndefined, autoescape=False)


def load_personal_info():
    with open(PERSONAL_INFO, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def pick_template(language, template_key):
    """Resolve template file. EN/ES base, IT/FR fallback to EN."""
    lang = (language or 'en').lower()[:2]
    if lang not in ('en', 'es'):
        lang = 'en'  # fallback for IT/FR/other
    fname = f'{lang}_{template_key}.txt'
    path = os.path.join(TEMPLATES_DIR, fname)
    if not os.path.exists(path):
        # fallback: en_generic
        path = os.path.join(TEMPLATES_DIR, 'en_generic.txt')
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def parse_template(raw):
    """Split template into (list of subjects, body)."""
    m = re.search(r'SUBJECT_VARIANTS:\s*(.*?)\n---\s*BODY:\s*(.*)$', raw, re.DOTALL)
    if not m:
        raise ValueError('Template missing SUBJECT_VARIANTS / BODY sections')
    subjects_block = m.group(1).strip()
    body = m.group(2).strip()
    subjects = []
    for line in subjects_block.splitlines():
        line = line.strip()
        if line.startswith('- '):
            subjects.append(line[2:].strip())
    return subjects, body


def render_email(lead, personal_info, personalization_sentence):
    """
    lead = dict with keys: company_name, city, domain, language, category, contact_first_name?
    personal_info = parsed personal_info.yaml
    personalization_sentence = AI-generated 2-3 sentences specific to this lead
    Returns: (subject, body)
    """
    from lead_sources import CATEGORIES
    category = lead.get('category') or 'charter'
    cat_info = CATEGORIES.get(category, CATEGORIES['charter'])
    template_key = cat_info['template_key']
    raw = pick_template(lead.get('language'), template_key)
    subjects, body = parse_template(raw)

    skipper = personal_info['skipper']
    deckhand = personal_info['deckhand']

    ctx = {
        'company_name': lead.get('company_name') or lead.get('domain', '').split('.')[0].title(),
        'city': lead.get('city') or 'your area',
        'category_label': cat_info['label'],
        'tier_label': {1: 'Palma', 2: 'Balearic', 3: 'Italy', 4: 'French Riviera', 5: 'Caribbean'}.get(lead.get('tier'), 'Mediterranean'),
        'contact_first_name': lead.get('contact_first_name'),
        'personalization': personalization_sentence,
        'skipper_full_name': skipper['full_name'],
        'skipper_email': skipper['email'],
        'skipper_phone': skipper.get('phone', ''),
        'skipper_experience_years': skipper.get('experience_years', ''),
        'skipper_languages': ', '.join(skipper.get('languages', [])),
        'deckhand_full_name': deckhand['full_name'],
        'deckhand_first_name': deckhand['full_name'].split(' ')[0] if deckhand.get('full_name') else 'my partner',
        'deckhand_experience_years': deckhand.get('experience_years', ''),
        'deckhand_languages': ', '.join(deckhand.get('languages', [])),
        'vessel_types_short': ', '.join((skipper.get('vessel_types') or [])[:3]),
        'languages': ', '.join(set((skipper.get('languages') or []) + (deckhand.get('languages') or []))),
        'also_caribbean': lead.get('tier') in (5,),
    }

    subject_tpl = random.choice(subjects)
    subject = _jinja_env.from_string(subject_tpl).render(**ctx)
    body_text = _jinja_env.from_string(body).render(**ctx)
    return subject, body_text
