from pathlib import Path

# Normalize Camtel labels parsed from sentence text.
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

# The old Android contract asserted the pre-scale implementation's literal startHour values.
# Validate the new contract instead: 02/03/04 hour bases, deterministic spreading, a final DAE
# sweep, and bounded retry for deferred server batches.
test_path = Path('app/src/test/finance-flow.mjs')
test = test_path.read_text(encoding='utf-8')
old = """assert.match(robotServiceV267, /startHour = 2/);\nassert.match(robotServiceV267, /startHour = 3/);\nassert.match(robotServiceV267, /startHour = 4/);\n"""
new = """assert.match(robotServiceV267, /startMinute = 2 \\* 60/);\nassert.match(robotServiceV267, /startMinute = 3 \\* 60/);\nassert.match(robotServiceV267, /startMinute = 4 \\* 60/);\nassert.match(robotServiceV267, /deterministicNightSlot/);\nassert.match(robotServiceV267, /5 \\* 60 \\+ 15/);\nassert.match(robotServiceV267, /result\\.optBoolean\\(\"complete\", false\\)/);\nassert.match(robotServiceV267, /5 \\* 60_000L/);\n"""
if test.count(old) != 1:
    raise SystemExit('old nightly Android contract not found exactly once')
test_path.write_text(test.replace(old, new, 1), encoding='utf-8')
print('Camtel labels and deterministic nightly Android contract normalized')
