#!/usr/bin/env python3
"""
Create a Google Doc from EMAIL_SEQUENCE.md in the same Drive folder as the Neurode brief.

ONE-TIME SETUP (5 minutes):
  1. Enable APIs (same project as your YouTube key):
       https://console.cloud.google.com/apis/library/docs.googleapis.com   → Enable
       https://console.cloud.google.com/apis/library/drive.googleapis.com  → Enable

  2. Create OAuth credentials:
       https://console.cloud.google.com/apis/credentials
       → Create Credentials → OAuth client ID → Desktop app → Name it anything → Create
       → Download JSON → rename to credentials.json
       → Place credentials.json in ~/script-agent-system/

  3. Run (from ~/script-agent-system/):
       python3 tools/create_google_doc.py
       (Browser will open once for Google sign-in → auth saved to token.json)
"""

import os
import re
import sys

SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
]

BRIEF_DOC_ID    = '1_ZdPUigNRJK6utW9Yuf2by41GEeGmTfi'
SOURCE_FILE     = 'output/EMAIL_SEQUENCE.md'
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE      = 'token.json'
DOC_TITLE       = 'Neurode — 10-Email Welcome Sequence'


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
            if not os.path.exists(CREDENTIALS_FILE):
                print('\n[ERROR] credentials.json not found.\n')
                print('Setup steps:')
                print('  1. Enable Google Docs API:')
                print('     https://console.cloud.google.com/apis/library/docs.googleapis.com')
                print('  2. Enable Google Drive API:')
                print('     https://console.cloud.google.com/apis/library/drive.googleapis.com')
                print('  3. Create OAuth credentials:')
                print('     https://console.cloud.google.com/apis/credentials')
                print('     → Create Credentials → OAuth client ID → Desktop app → Download JSON')
                print('     → Save as credentials.json in ~/script-agent-system/')
                sys.exit(1)
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
    print(f"  Brief: \"{result.get('name')}\"")
    return result.get('parents', [])


def create_and_place_doc(docs_service, drive_service, title, parent_ids):
    doc = docs_service.documents().create(body={'title': title}).execute()
    doc_id = doc['documentId']

    # Move doc to the same folder as the brief
    if parent_ids:
        drive_service.files().update(
            fileId=doc_id,
            addParents=','.join(parent_ids),
            removeParents='root',
            fields='id,parents'
        ).execute()

    return doc_id


def strip_markdown(line):
    """Remove markdown syntax, keep clean text for Google Docs."""
    line = re.sub(r'\*\*(.+?)\*\*', r'\1', line)   # **bold**
    line = re.sub(r'\*(.+?)\*', r'\1', line)         # *italic*
    line = re.sub(r'`(.+?)`', r'\1', line)           # `code`
    line = re.sub(r'^#{1,6}\s+', '', line)            # # headings (text only)
    return line


def heading_style(line):
    """Return Google Docs named style if line is a markdown heading."""
    if line.startswith('# '):   return 'HEADING_1'
    if line.startswith('## '):  return 'HEADING_2'
    if line.startswith('### '): return 'HEADING_3'
    return None


def populate_doc(docs_service, doc_id, content):
    """Insert email sequence content with heading styles."""
    orig_lines = content.split('\n')

    # Build clean text (no markdown symbols)
    clean_lines = [strip_markdown(l) for l in orig_lines]
    full_text = '\n'.join(clean_lines) + '\n'

    # 1. Insert all text at once
    requests = [{
        'insertText': {
            'location': {'index': 1},
            'text': full_text
        }
    }]

    # 2. Apply heading styles
    index = 1
    for orig, clean in zip(orig_lines, clean_lines):
        char_len = len(clean) + 1  # +1 for \n
        style = heading_style(orig)
        if style and clean.strip():
            requests.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': index,
                        'endIndex': index + char_len
                    },
                    'paragraphStyle': {'namedStyleType': style},
                    'fields': 'namedStyleType'
                }
            })
        index += char_len

    # Send in batches of 500 (API limit)
    batch_size = 500
    for i in range(0, len(requests), batch_size):
        batch = requests[i:i + batch_size]
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': batch}
        ).execute()
        print(f'  Sent requests {i+1}–{min(i+batch_size, len(requests))} of {len(requests)}')


def main():
    print('=' * 60)
    print('Neurode Email Sequence → Google Docs')
    print('=' * 60)

    # Must run from script-agent-system/
    if not os.path.exists(SOURCE_FILE):
        print(f'[ERROR] {SOURCE_FILE} not found.')
        print('Run from ~/script-agent-system/: python3 tools/create_google_doc.py')
        sys.exit(1)

    with open(SOURCE_FILE) as f:
        content = f.read()
    print(f'[OK] Read {len(content):,} chars from {SOURCE_FILE}')

    print('\n[AUTH] Authenticating with Google...')
    creds = authenticate()
    print('[OK] Authenticated')

    from googleapiclient.discovery import build
    docs_service  = build('docs',  'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)

    print(f'\n[DRIVE] Finding parent folder of brief...')
    parent_ids = get_parent_folders(drive_service, BRIEF_DOC_ID)
    print(f'  Folder IDs: {parent_ids}')

    print(f'\n[DOCS] Creating "{DOC_TITLE}"...')
    doc_id = create_and_place_doc(docs_service, drive_service, DOC_TITLE, parent_ids)
    print(f'  Doc ID: {doc_id}')

    print('\n[DOCS] Writing content...')
    populate_doc(docs_service, doc_id, content)

    print(f'\n{"=" * 60}')
    print('DONE!')
    print(f'URL: https://docs.google.com/document/d/{doc_id}/edit')
    print(f'{"=" * 60}')


if __name__ == '__main__':
    main()
