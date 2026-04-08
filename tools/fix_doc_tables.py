#!/usr/bin/env python3
"""
Fix the Neurode — Threads Research Google Doc by recreating it with proper
native Google Docs tables instead of raw markdown pipe-text.

Clears the existing doc, re-parses the source markdown, and re-inserts
everything with real tables + heading styles + bold formatting.

Usage (from ~/script-agent-system/):
    python3 tools/fix_doc_tables.py
"""

import os
import re
import sys
import time

SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
]

DOC_ID = '10WoU64NqBK1gAQdeg7Ikxn9dpaDoi58qvlD8F76IYT8'
SOURCE_FILE = 'output/research/threads_research.md'
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'


# ── Auth ──────────────────────────────────────────────────────────────────────

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


# ── Markdown parsing ──────────────────────────────────────────────────────────

def strip_md_inline(text):
    """Strip bold/italic/code markers but keep the content."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    return text


def heading_level(line):
    """Return (level, clean_text) for headings, or (None, line) otherwise."""
    m = re.match(r'^(#{1,3})\s+(.*)', line)
    if m:
        return len(m.group(1)), strip_md_inline(m.group(2))
    return None, strip_md_inline(line)


def is_table_sep(line):
    return bool(re.match(r'^\s*\|[\s\-:|]+\|\s*$', line.strip()))


def parse_table_row(line):
    return [strip_md_inline(c.strip()) for c in line.strip().strip('|').split('|')]


def parse_markdown(content):
    """
    Split markdown into an ordered list of segments:
      ('text',  [line, ...])
      ('table', {'header': [...], 'rows': [[...], ...]})
    """
    lines = content.split('\n')
    segments = []
    buf_text = []
    buf_table = []
    in_table = False

    for line in lines:
        looks_like_table = (
            line.strip().startswith('|')
            and line.strip().endswith('|')
            and len(line.strip()) > 2
        )
        if looks_like_table:
            if not in_table:
                if buf_text:
                    segments.append(('text', buf_text[:]))
                    buf_text = []
                in_table = True
            if not is_table_sep(line):
                buf_table.append(line)
        else:
            if in_table:
                if buf_table:
                    hdr = parse_table_row(buf_table[0])
                    rows = [parse_table_row(r) for r in buf_table[1:]]
                    segments.append(('table', {'header': hdr, 'rows': rows}))
                    buf_table = []
                in_table = False
            buf_text.append(line)

    # flush
    if in_table and buf_table:
        hdr = parse_table_row(buf_table[0])
        rows = [parse_table_row(r) for r in buf_table[1:]]
        segments.append(('table', {'header': hdr, 'rows': rows}))
    if buf_text:
        segments.append(('text', buf_text))

    return segments


# ── Google Docs helpers ───────────────────────────────────────────────────────

def clear_doc(docs):
    """Delete all body content from the document."""
    doc = api_call(lambda: docs.documents().get(documentId=DOC_ID).execute())
    body = doc.get('body', {}).get('content', [])
    if len(body) <= 1:
        return
    end = body[-1]['endIndex'] - 1
    if end <= 1:
        return
    api_call(lambda: docs.documents().batchUpdate(
        documentId=DOC_ID,
        body={'requests': [
            {'deleteContentRange': {'range': {'startIndex': 1, 'endIndex': end}}}
        ]}
    ).execute())
    time.sleep(1.5)


def doc_end_index(docs):
    """Return the current end-of-body index (the position to append at)."""
    doc = api_call(lambda: docs.documents().get(documentId=DOC_ID).execute())
    body = doc.get('body', {}).get('content', [])
    return body[-1]['endIndex'] - 1  # -1 because endIndex is exclusive


def api_call(fn, retries=5):
    """Execute an API call with retry + backoff on 429 rate-limit errors."""
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            if '429' in str(e) or 'RATE_LIMIT' in str(e):
                wait = 15 * (attempt + 1)
                print(f'    [rate-limit] waiting {wait}s...')
                time.sleep(wait)
            else:
                raise
    raise RuntimeError('rate limit retries exhausted')


def batch(docs, requests):
    """Send requests in batches of 450 (safe under the 500 limit)."""
    for i in range(0, len(requests), 450):
        chunk = requests[i:i + 450]
        api_call(lambda c=chunk: docs.documents().batchUpdate(
            documentId=DOC_ID,
            body={'requests': c}
        ).execute())
        time.sleep(1.5)  # pace writes under 60/min quota


def insert_text_block(docs, lines):
    """Insert a block of text lines with heading + bold formatting."""
    if not lines:
        return

    # Build clean text and track heading / bold positions
    clean_parts = []
    heading_map = []   # (offset_in_block, char_len, level)

    for raw_line in lines:
        level, clean = heading_level(raw_line)
        clean_parts.append(clean)
        if level is not None:
            offset = sum(len(p) + 1 for p in clean_parts[:-1])
            heading_map.append((offset, len(clean) + 1, level))

    block = '\n'.join(clean_parts) + '\n'
    if not block.strip():
        return

    insert_at = doc_end_index(docs)
    reqs = [{'insertText': {'location': {'index': insert_at}, 'text': block}}]

    style_map = {1: 'HEADING_1', 2: 'HEADING_2', 3: 'HEADING_3'}
    for offset, clen, level in heading_map:
        s = insert_at + offset
        reqs.append({
            'updateParagraphStyle': {
                'range': {'startIndex': s, 'endIndex': s + clen},
                'paragraphStyle': {'namedStyleType': style_map[level]},
                'fields': 'namedStyleType',
            }
        })

    batch(docs, reqs)


def insert_table(docs, table_data):
    """Insert a native Google Docs table and populate its cells."""
    header = table_data['header']
    rows = table_data['rows']
    n_rows = 1 + len(rows)
    n_cols = len(header)
    all_rows = [header] + rows

    # Normalise: ensure every row has the same number of columns
    for row in all_rows:
        while len(row) < n_cols:
            row.append('')

    insert_at = doc_end_index(docs)

    # 1. Create the empty table
    api_call(lambda: docs.documents().batchUpdate(
        documentId=DOC_ID,
        body={'requests': [{
            'insertTable': {
                'location': {'index': insert_at},
                'rows': n_rows,
                'columns': n_cols,
            }
        }]}
    ).execute())
    time.sleep(1.5)

    # 2. Read back to get cell indices
    doc = api_call(lambda: docs.documents().get(documentId=DOC_ID).execute())
    body = doc.get('body', {}).get('content', [])

    # Find the table element we just inserted
    table_el = None
    for el in body:
        if 'table' in el and el.get('startIndex', 0) >= insert_at:
            table_el = el
            break

    if table_el is None:
        print('  [WARN] Could not locate table after insertion — skipping')
        return

    # 3. Collect (cell_start_index, cell_text) pairs
    fills = []   # [(index, text)]
    bolds = []   # [(start, end)]  — header row

    tbl = table_el['table']
    for r_idx, (api_row, data_row) in enumerate(
        zip(tbl.get('tableRows', []), all_rows)
    ):
        for c_idx, (api_cell, cell_text) in enumerate(
            zip(api_row.get('tableCells', []), data_row)
        ):
            cell_content = api_cell.get('content', [])
            if cell_content:
                cell_start = cell_content[0].get('startIndex')
                if cell_start is not None and cell_text:
                    fills.append((cell_start, cell_text))
                    if r_idx == 0:
                        bolds.append((cell_start, cell_text))

    # Insert cell texts in REVERSE index order so earlier indices stay valid
    fills.sort(key=lambda x: x[0], reverse=True)
    fill_reqs = [
        {'insertText': {'location': {'index': idx}, 'text': txt}}
        for idx, txt in fills
    ]
    if fill_reqs:
        batch(docs, fill_reqs)

    # 4. Bold the header row — re-read doc for updated indices
    if bolds:
        doc = api_call(lambda: docs.documents().get(documentId=DOC_ID).execute())
        body = doc.get('body', {}).get('content', [])
        for el in body:
            if 'table' in el and el.get('startIndex', 0) >= insert_at:
                first_row = el['table'].get('tableRows', [])[0]
                bold_reqs = []
                for cell in first_row.get('tableCells', []):
                    for para in cell.get('content', []):
                        for elem in para.get('paragraph', {}).get('elements', []):
                            s = elem.get('startIndex')
                            e = elem.get('endIndex')
                            run = elem.get('textRun', {}).get('content', '')
                            if run.strip():
                                bold_reqs.append({
                                    'updateTextStyle': {
                                        'range': {'startIndex': s, 'endIndex': e - 1},
                                        'textStyle': {'bold': True},
                                        'fields': 'bold',
                                    }
                                })
                if bold_reqs:
                    batch(docs, bold_reqs)
                break


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print('=' * 60)
    print('Fix: Neurode — Threads Research  (proper tables)')
    print('=' * 60)

    if not os.path.exists(SOURCE_FILE):
        print(f'[ERROR] {SOURCE_FILE} not found'); sys.exit(1)

    creds = authenticate()
    from googleapiclient.discovery import build
    docs = build('docs', 'v1', credentials=creds)

    with open(SOURCE_FILE) as f:
        content = f.read()

    segments = parse_markdown(content)
    n_tables = sum(1 for t, _ in segments if t == 'table')
    n_text   = sum(1 for t, _ in segments if t == 'text')
    print(f'\n  Parsed: {n_tables} tables, {n_text} text blocks')

    print('\n[1/3] Clearing document...')
    clear_doc(docs)

    print('[2/3] Rebuilding with native tables...')
    for i, (seg_type, seg_data) in enumerate(segments):
        if seg_type == 'text':
            insert_text_block(docs, seg_data)
            print(f'  text block {i+1}/{len(segments)}')
        else:
            n_r = 1 + len(seg_data['rows'])
            n_c = len(seg_data['header'])
            insert_table(docs, seg_data)
            print(f'  table {i+1}/{len(segments)}  ({n_r}×{n_c})')

    print(f'\n[3/3] Done!')
    print(f'  https://docs.google.com/document/d/{DOC_ID}/edit')
    print('=' * 60)


if __name__ == '__main__':
    main()
