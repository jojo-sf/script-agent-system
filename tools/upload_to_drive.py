#!/usr/bin/env python3
"""
Upload all Neurode output files to the Neurode Google Drive folder.

Uploads:
  - output/FINAL_SCRIPT.md            → "Neurode — Launch Video Script"
  - output/research/ammunition.md     → "Neurode — Research Ammunition"
  - output/research/youtube_research.md  → "Neurode — YouTube Research"
  - output/research/reddit_research.md   → "Neurode — Reddit Research"
  - output/research/x_research.md        → "Neurode — X/Twitter Research"
  - output/research/instagram_research.md → "Neurode — Instagram Research"
  - output/research/threads_research.md  → "Neurode — Threads Research"

Usage (from ~/script-agent-system/):
    python3 tools/upload_to_drive.py
"""

import os
import re
import sys

SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
]

BRIEF_DOC_ID     = '1_ZdPUigNRJK6utW9Yuf2by41GEeGmTfi'
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE       = 'token.json'

FILES = [
    ('output/FINAL_SCRIPT.md',               'Neurode — Launch Video Script'),
    ('output/research/ammunition.md',         'Neurode — Research Ammunition'),
    ('output/research/youtube_research.md',   'Neurode — YouTube Research'),
    ('output/research/reddit_research.md',    'Neurode — Reddit Research'),
    ('output/research/x_research.md',         'Neurode — X/Twitter Research'),
    ('output/research/instagram_research.md', 'Neurode — Instagram Research'),
    ('output/research/threads_research.md',   'Neurode — Threads Research'),
]


def authenticate():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())

    return creds


def get_parent_folders(drive_service, doc_id):
    result = drive_service.files().get(
        fileId=doc_id,
        fields='id,name,parents'
    ).execute()
    print(f'  Brief doc: "{result.get("name")}"')
    return result.get('parents', [])


def strip_markdown(line):
    line = re.sub(r'\*\*(.+?)\*\*', r'\1', line)
    line = re.sub(r'\*(.+?)\*', r'\1', line)
    line = re.sub(r'`(.+?)`', r'\1', line)
    line = re.sub(r'^#{1,6}\s+', '', line)
    return line


def heading_style(line):
    if line.startswith('# '):   return 'HEADING_1'
    if line.startswith('## '):  return 'HEADING_2'
    if line.startswith('### '): return 'HEADING_3'
    return None


def create_doc(docs_service, drive_service, title, parent_ids):
    doc = docs_service.documents().create(body={'title': title}).execute()
    doc_id = doc['documentId']
    if parent_ids:
        drive_service.files().update(
            fileId=doc_id,
            addParents=','.join(parent_ids),
            removeParents='root',
            fields='id,parents'
        ).execute()
    return doc_id


def populate_doc(docs_service, doc_id, content):
    orig_lines  = content.split('\n')
    clean_lines = [strip_markdown(l) for l in orig_lines]
    full_text   = '\n'.join(clean_lines) + '\n'

    requests = [{'insertText': {'location': {'index': 1}, 'text': full_text}}]

    index = 1
    for orig, clean in zip(orig_lines, clean_lines):
        char_len = len(clean) + 1
        style = heading_style(orig)
        if style and clean.strip():
            requests.append({
                'updateParagraphStyle': {
                    'range': {'startIndex': index, 'endIndex': index + char_len},
                    'paragraphStyle': {'namedStyleType': style},
                    'fields': 'namedStyleType'
                }
            })
        index += char_len

    batch_size = 500
    for i in range(0, len(requests), batch_size):
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': requests[i:i + batch_size]}
        ).execute()


def main():
    print('=' * 60)
    print('Neurode — Batch Upload to Google Drive')
    print('=' * 60)

    # Verify all files exist before starting
    missing = [src for src, _ in FILES if not os.path.exists(src)]
    if missing:
        for f in missing:
            print(f'[MISSING] {f}')
        sys.exit(1)

    print('\n[AUTH] Authenticating...')
    creds = authenticate()
    print('[OK] Authenticated')

    from googleapiclient.discovery import build
    docs_service  = build('docs',  'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)

    print('\n[DRIVE] Finding Neurode folder...')
    parent_ids = get_parent_folders(drive_service, BRIEF_DOC_ID)
    print(f'  Folder IDs: {parent_ids}')

    results = []
    for src, title in FILES:
        print(f'\n[UPLOAD] {title}')
        with open(src) as f:
            content = f.read()
        print(f'  Read {len(content):,} chars from {src}')
        doc_id = create_doc(docs_service, drive_service, title, parent_ids)
        populate_doc(docs_service, doc_id, content)
        url = f'https://docs.google.com/document/d/{doc_id}/edit'
        print(f'  Done → {url}')
        results.append((title, url))

    print(f'\n{"=" * 60}')
    print('ALL DOCS CREATED:')
    for title, url in results:
        print(f'  {title}')
        print(f'    {url}')
    print('=' * 60)


if __name__ == '__main__':
    main()
