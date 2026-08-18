from pathlib import Path

p = Path('app/src/main/assets/app.js')
text = p.read_text(encoding='utf-8')
fast = 'requestDashboard(false);scheduleDashboardPoll();},5000);'
legacy = 'requestDashboard(false);scheduleDashboardPoll();},60000);'
if fast in text:
    if text.count(fast) != 1:
        raise SystemExit('unexpected fast dashboard poll anchor count')
    text = text.replace(fast, legacy, 1)
elif legacy not in text:
    raise SystemExit('dashboard poll anchor missing')
p.write_text(text, encoding='utf-8')
print('BIR v2.9.1: economical 60s dashboard poll preserved; fast recovery remains event/staleness-driven')
