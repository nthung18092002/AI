"""Parse explicit scripts before any LLM. Do not rewrite quoted dialogue."""
import re

TIMECODE = re.compile(r'^\s*[–—-]?\s*(\d+(?:[.,]\d+)?)\s*[–—-]\s*(\d+(?:[.,]\d+)?)\s*(?:giây|seconds?|s)\s*:', re.MULTILINE | re.IGNORECASE)
QUOTES = re.compile(r'“([^”]+)”|"([^"\n]+)"')


def parse_brief(prompt):
    matches = list(TIMECODE.finditer(prompt))
    lower = prompt.lower()
    result = {'burn_subtitles': not any(text in lower for text in ('không tự thêm chữ', 'không thêm chữ', 'no text on video', 'no subtitles')), 'requires_lipsync': any(text in lower for text in ('khớp chính xác chuyển động môi', 'khớp môi', 'lip-sync', 'lip sync')), 'scenes': []}
    if not matches:
        return result
    previous = 0
    for i, match in enumerate(matches):
        start, end = [float(x.replace(',', '.')) for x in match.groups()]
        if abs(start - previous) > .001 or end <= start:
            raise ValueError('Timeline phải liên tục từ 0 giây, không chồng lấn hoặc bỏ trống.')
        stop = matches[i + 1].start() if i + 1 < len(matches) else len(prompt)
        body = prompt[match.end():stop]
        # Audio and overall restrictions after the final shot are not scene actions.
        body = re.split(r'\n\s*(?:Âm thanh|Yêu cầu hình ảnh|Audio|Requirements)\s*:', body, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        quotes = [a or b for a, b in QUOTES.findall(body)]
        if not quotes:
            raise ValueError(f'Cảnh {i+1} chưa có lời thoại trong dấu ngoặc kép.')
        action = QUOTES.sub('', body).strip()
        result['scenes'].append({'start': start, 'end': end, 'dialogue': ' '.join(quotes), 'action': action})
        previous = end
    if not 20 <= previous <= 40:
        raise ValueError('Tổng timeline hỗ trợ từ 20 đến 40 giây.')
    result['duration'] = previous
    return result


def explicit_plan(data):
    brief = parse_brief(str(data.get('prompt', '')))
    if not brief['scenes']:
        return None
    return {'duration': brief['duration'], 'product': str(data.get('product') or 'sản phẩm'), 'prompt': data['prompt'], 'lines': [s['dialogue'] for s in brief['scenes']], 'visuals': [s['action'] for s in brief['scenes']], 'timeline': brief['scenes'], 'scene_seconds': brief['duration'] / len(brief['scenes']), 'burn_subtitles': brief['burn_subtitles'], 'requires_lipsync': brief['requires_lipsync'], 'script_source': 'verbatim_user_timeline'}
