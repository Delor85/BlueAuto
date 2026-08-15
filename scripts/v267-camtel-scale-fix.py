from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{path}: expected one occurrence, found {count}: {old!r}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')

# Camtel node names are underscore/hyphen identifiers; punctuation after the label belongs
# to the sentence and must never become part of the canonical identity.
replace_once('cloudflare/src/blue-message.mjs',
    "([A-Za-z0-9_.-]+))?/i.exec(segment);",
    "([A-Za-z0-9_-]+))?/i.exec(segment);")
replace_once('cloudflare/src/blue-message.mjs',
    "([A-Za-z0-9_.-]+))?/i.exec(text);",
    "([A-Za-z0-9_-]+))?/i.exec(text);")
# There are two top-level source/target expressions with identical character classes.
text = Path('cloudflare/src/blue-message.mjs').read_text(encoding='utf-8')
text = text.replace("([A-Za-z0-9_.-]+))?/i.exec(text);", "([A-Za-z0-9_-]+))?/i.exec(text);")
Path('cloudflare/src/blue-message.mjs').write_text(text, encoding='utf-8')

print('Camtel message labels normalized without sentence punctuation')
