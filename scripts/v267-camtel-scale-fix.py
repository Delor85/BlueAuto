from pathlib import Path

path = Path('cloudflare/src/blue-message.mjs')
text = path.read_text(encoding='utf-8')
old_segment = "([A-Za-z0-9_.-]+))?/i.exec(segment);"
old_text = "([A-Za-z0-9_.-]+))?/i.exec(text);"
segment_count = text.count(old_segment)
text_count = text.count(old_text)
if segment_count != 1 or text_count != 2:
    raise SystemExit(f'unexpected Camtel label patterns: segment={segment_count}, text={text_count}')
text = text.replace(old_segment, "([A-Za-z0-9_-]+))?/i.exec(segment);")
text = text.replace(old_text, "([A-Za-z0-9_-]+))?/i.exec(text);")
path.write_text(text, encoding='utf-8')
print('Camtel message labels normalized without sentence punctuation')
