from pathlib import Path

p = Path('app/src/main/java/com/profitloop/blueauto/MainActivity.java')
s = p.read_text()
old = '''                + " • SIM " + (AppConfig.simSlot(this) + 1)
                + "
Actions regroupées pour rester lisibles même sur les petits téléphones.");'''
new = '''                + " • SIM " + (AppConfig.simSlot(this) + 1)
                + "\\nActions regroupées pour rester lisibles même sur les petits téléphones.");'''
if old not in s:
    raise SystemExit('MainActivity responsive intro compile anchor missing')
p.write_text(s.replace(old, new, 1))
