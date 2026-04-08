#!/usr/bin/env python3
"""Upload the Founder Report to Google Drive in the same folder as the Neurode brief."""

import os, sys

SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
]

BRIEF_DOC_ID     = '1_ZdPUigNRJK6utW9Yuf2by41GEeGmTfi'
SOURCE_FILE      = 'output/FOUNDER_REPORT.md'
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE       = 'token.json'
DOC_TITLE        = 'Neurode — Research & Deliverables Report'

import re

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


def populate_doc(docs_service, doc_id, content):
    orig_lines = content.split('\n')
    clean_lines = [strip_markdown(l) for l in orig_lines]
    full_text = '\n'.join(clean_lines) + '\n'

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
        batch = requests[i:i + batch_size]
        docs_service.documents().batchUpdate(
            documentId=doc_id, body={'requests': batch}
        ).execute()
        print(f'  Sent requests {i+1}-{min(i+batch_size, len(requests))} of {len(requests)}')


def main():
    print('=' * 60)
    print('Neurode Founder Report -> Google Docs')
    print('=' * 60)

    if not os.path.exists(SOURCE_FILE):
        print(f'[ERROR] {SOURCE_FILE} not found.')
        sys.exit(1)

    with open(SOURCE_FILE) as f:
        content = f.read()
    print(f'[OK] Read {len(content):,} chars from {SOURCE_FILE}')

    print('\n[AUTH] Authenticating...')
    creds = authenticate()
    print('[OK] Authenticated')

    from googleapiclient.discovery import build
    docs_service  = build('docs',  'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)

    # Find parent folder
    print('\n[DRIVE] Finding Neurode folder...')
    result = drive_service.files().get(fileId=BRIEF_DOC_ID, fields='id,name,parents').execute()
    parent_ids = result.get('parents', [])
    print(f'  Brief: "{result.get("name")}"')

    # Create doc
    print(f'\n[DOCS] Creating "{DOC_TITLE}"...')
    doc = docs_service.documents().create(body={'title': DOC_TITLE}).execute()
    doc_id = doc['documentId']

    if parent_ids:
        drive_service.files().update(
            fileId=doc_id,
            addParents=','.join(parent_ids),
            removeParents='root',
            fields='id,parents'
        ).execute()

    print(f'  Doc ID: {doc_id}')

    print('\n[DOCS] Writing content...')
    populate_doc(docs_service, doc_id, content)

    print(f'\n{"=" * 60}')
    print('DONE!')
    print(f'URL: https://docs.google.com/document/d/{doc_id}/edit')
    print(f'{"=" * 60}')


if __name__ == '__main__':
    main()
