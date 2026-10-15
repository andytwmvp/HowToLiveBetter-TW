"""僅呈現本專案條目的段落、二級標題及獨立HTTPS來源連結；不執行原始HTML。"""
import html
import re


def body_blocks(entry):
    body = entry['body']
    if not entry.get('target_path'):
        return [{'tag': 'p', 'text': body}]
    blocks = []
    for chunk in re.split(r'\n\s*\n', body.strip()):
        if chunk == '# ' + entry['title'] or chunk == '<!-- TW-ID: ' + entry['id'] + ' -->':
            continue
        if chunk.startswith('## ') and '\n' not in chunk:
            blocks.append({'tag': 'h3', 'text': chunk[3:]})
            continue
        match = re.fullmatch(r'\[([^\]\n]+)\]\((https://[^\s<>]+)\)', chunk)
        if match:
            blocks.append({'tag': 'p', 'text': match[1], 'url': match[2]})
        else:
            blocks.append({'tag': 'p', 'text': chunk})
    return blocks


def body_html(entry):
    rendered = []
    for block in body_blocks(entry):
        value = html.escape(block['text'])
        if 'url' in block:
            value = '<a href="' + html.escape(block['url'], quote=True) + '">' + value + '</a>'
        rendered.append('<' + block['tag'] + '>' + value + '</' + block['tag'] + '>')
    return ''.join(rendered)
