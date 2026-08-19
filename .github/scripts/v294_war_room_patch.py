from pathlib import Path

root = Path('.')
index = root/'app/src/main/assets/index.html'
text = index.read_text(encoding='utf-8')
needle = '<script src="pilotage-v292.js"></script>'
insert = needle + '\n<script src="war-room-v294.js"></script>'
if 'war-room-v294.js' not in text:
    if needle not in text:
        raise SystemExit('pilotage anchor not found')
    text = text.replace(needle, insert, 1)
index.write_text(text, encoding='utf-8')

# Commission strategy is owned by each DAE/DSM. Keep computation/audit, simplify only the wording.
ct = root/'app/src/main/assets/control-tower-v2611.js'
s = ct.read_text(encoding='utf-8')
repls = {
    "Taux par défaut, personnalisés et envoi ponctuel.": "Vos règles, taux par enfant et envoi ponctuel.",
    "Le taux par défaut s\\'applique automatiquement. Une exception enfant remplace seulement ce taux.": "Votre taux habituel s\\'applique automatiquement. Un taux enfant remplace seulement votre taux habituel pour cet enfant.",
    "<label>Taux par défaut (%)</label>": "<label>Mon taux habituel (%)</label>",
    "REVENIR AU DÉFAUT": "REVENIR À MON TAUX HABITUEL",
    "à remettre au taux par défaut.": "à remettre à votre taux habituel.",
}
for old,new in repls.items():
    if old in s:
        s=s.replace(old,new)
# Remove role-prescribed examples from this UX; free competition remains explicit.
s=s.replace("placeholder=\"Ex. '+(r==='DAE'?'10':'8')+'\"", "placeholder=\"Ex. 9,5\"")
ct.write_text(s, encoding='utf-8')

# Bump only after additive UX patch is applied.
gradle = root/'app/build.gradle'
g = gradle.read_text(encoding='utf-8')
g = g.replace('versionCode 58','versionCode 59',1).replace('versionName "2.9.3"','versionName "2.9.4"',1)
gradle.write_text(g, encoding='utf-8')

print('BIR v2.9.4 War Room patch applied')
