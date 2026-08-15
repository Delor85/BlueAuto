from pathlib import Path

main = Path('app/src/main/java/com/profitloop/blueauto/MainActivity.java')
s = main.read_text()
old = '''                + " • SIM " + (AppConfig.simSlot(this) + 1)
                + "
Actions regroupées pour rester lisibles même sur les petits téléphones.");'''
new = '''                + " • SIM " + (AppConfig.simSlot(this) + 1)
                + "\\nActions regroupées pour rester lisibles même sur les petits téléphones.");'''
if old not in s:
    raise SystemExit('MainActivity responsive intro compile anchor missing')
main.write_text(s.replace(old, new, 1))

obsolete = Path('app/src/main/java/com/profitloop/blueauto/InsecureKeyguardDismissActivity.java')
if obsolete.exists():
    obsolete.unlink()
