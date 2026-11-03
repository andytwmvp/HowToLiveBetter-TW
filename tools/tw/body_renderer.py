"""僅呈現本專案條目的段落、標題及安全來源／內文連結；不執行原始HTML。"""
import html
import re


def _markdown_segments(value, strip_bullet=False):
    value = value.strip()
    if strip_bullet:
        value = re.sub(r'^[-*]\s+', '', value, count=1)
    segments = []
    output_cursor = 0
    search_cursor = 0
    link_count = 0
    while search_cursor < len(value):
        start = value.find('[', search_cursor)
        if start < 0:
            break
        label_end = value.find('](', start + 1)
        if label_end < 0:
            search_cursor = start + 1
            continue
        label = value[start + 1:label_end]
        url_start = label_end + 2
        if not label:
            search_cursor = start + 1
            continue
        url_end = url_start
        parentheses = 0
        invalid = False
        while url_end < len(value):
            char = value[url_end]
            if char.isspace() or char in '<>':
                invalid = True
                break
            if char == '(':
                parentheses += 1
            elif char == ')':
                if parentheses == 0:
                    break
                parentheses -= 1
            url_end += 1
        if invalid or url_end >= len(value) or value[url_end] != ')' or parentheses:
            search_cursor = start + 1
            continue
        if start > output_cursor:
            segments.append({'text': value[output_cursor:start]})
        destination = value[url_start:url_end]
        segment = {'text': label}
        if destination.startswith('https://'):
            segment['url'] = destination
        else:
            target = (
                not destination.startswith('/')
                and re.fullmatch(r'(?:\.\.?/)*[A-Za-z0-9_./-]+\.md', destination)
            )
            target_id = re.search(r'(TW-(?:NAV-\d{3}|\d{2}-\d{3}))\.md$', destination)
            if target and target_id:
                segment['href'] = '#' + target_id[1]
        segments.append(segment)
        link_count += 1
        output_cursor = url_end + 1
        search_cursor = url_end + 1
    if not link_count:
        return None
    if output_cursor < len(value):
        segments.append({'text': value[output_cursor:]})
    return segments


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
        lines = chunk.splitlines()
        rows = [
            _markdown_segments(line, strip_bullet=True) if re.match(r'^[-*]\s+', line.strip()) else None
            for line in lines
        ]
        parsed_rows = rows if rows and all(rows) else [_markdown_segments(chunk)]
        if parsed_rows and all(parsed_rows):
            for segments in parsed_rows:
                links = [segment for segment in segments if 'url' in segment or 'href' in segment]
                if len(segments) == 1 and not links:
                    blocks.append({'tag': 'p', 'text': segments[0]['text']})
                elif len(links) == 1 and segments[0] is links[0]:
                    link = links[0]
                    block = {'tag': 'p', 'text': link['text']}
                    block.update({key: link[key] for key in ('url', 'href') if key in link})
                    suffix = ''.join(segment['text'] for segment in segments[1:])
                    if suffix:
                        block['suffix'] = suffix
                    blocks.append(block)
                else:
                    blocks.append({
                        'tag': 'p',
                        'text': ''.join(segment['text'] for segment in segments),
                        'segments': segments,
                    })
        else:
            blocks.append({'tag': 'p', 'text': chunk})
    return blocks


def _segment_html(segment, internal_link_mode):
    label = html.escape(segment['text'])
    if 'url' in segment:
        return '<a href="' + html.escape(segment['url'], quote=True) + '">' + label + '</a>'
    if 'href' in segment:
        if internal_link_mode == 'anki':
            target = re.fullmatch(r'#(TW-(?:NAV-\d{3}|\d{2}-\d{3}))', segment['href'])
            if target:
                return label + ' <small>（請在 Anki 中搜尋「' + target[1] + '」）</small>'
        return '<a href="' + html.escape(segment['href'], quote=True) + '">' + label + '</a>'
    return label


def body_html(entry, *, internal_link_mode='anchor'):
    if internal_link_mode not in {'anchor', 'anki'}:
        raise ValueError('不支援的內部連結呈現方式')
    rendered = []
    for block in body_blocks(entry):
        if 'segments' in block:
            value = ''.join(_segment_html(segment, internal_link_mode) for segment in block['segments'])
        else:
            value = html.escape(block['text'])
        if 'url' in block or 'href' in block:
            value = _segment_html({key: block[key] for key in ('text', 'url', 'href') if key in block}, internal_link_mode)
            value += html.escape(block.get('suffix', ''))
        rendered.append('<' + block['tag'] + '>' + value + '</' + block['tag'] + '>')
    return ''.join(rendered)
