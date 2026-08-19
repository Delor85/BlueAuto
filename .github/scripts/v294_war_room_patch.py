from pathlib import Path

root = Path('.')

# Load the War Room after the validated v2.9.2 pilotage module.
index = root/'app/src/main/assets/index.html'
text = index.read_text(encoding='utf-8')
needle = '<script src="pilotage-v292.js"></script>'
insert = needle + '\n<script src="war-room-v294.js"></script>'
if 'war-room-v294.js' not in text:
    if needle not in text:
        raise SystemExit('pilotage anchor not found')
    text = text.replace(needle, insert, 1)
index.write_text(text, encoding='utf-8')

# Commission strategy is owned by each DAE/DSM. Keep calculations/audit unchanged;
# simplify only the commercial wording and remove role-prescribed examples.
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
    s = s.replace(old,new)
s = s.replace("placeholder=\"Ex. '+(r==='DAE'?'10':'8')+'\"", "placeholder=\"Ex. 9,5\"")
ct.write_text(s, encoding='utf-8')

# Every fresh application opening begins on Accueil/War Room. Navigation remains free afterwards.
appjs = root/'app/src/main/assets/app.js'
a = appjs.read_text(encoding='utf-8')
a = a.replace("var saved=localStorage.getItem('bir_active_module_v269')||'reports';", "var saved='reports'; // v2.9.4: ouverture = War Room; navigation ensuite libre.", 1)
a = a.replace('Stock hors commission : ', 'Solde réel hors commission : ')
a = a.replace(' • part taux par défaut : ', ' • part commission : ')
a = a.replace("+' • taux '+escapeHtml(String(Number(n.default_commission_bps||0)/100).replace('.',','))+' %</small>';", "+' • taux appliqué '+escapeHtml(String(Number(n.default_commission_bps||0)/100).replace('.',','))+' %</small>';", 1)
if "var saved='reports'; // v2.9.4" not in a:
    raise SystemExit('War Room opening route missing')
appjs.write_text(a, encoding='utf-8')

# Telemetry identifies the APK; the production Worker remains 2.9.3-cloudflare.
api = root/'app/src/main/java/com/profitloop/blueauto/ApiClient.java'
ap = api.read_text(encoding='utf-8')
ap = ap.replace('payload.put("app_version", "2.9.3");','payload.put("app_version", "2.9.4");')
if ap.count('payload.put("app_version", "2.9.4");') < 2:
    raise SystemExit('v2.9.4 telemetry missing')
api.write_text(ap, encoding='utf-8')

# Bump only after the additive UX patch is ready.
gradle = root/'app/build.gradle'
g = gradle.read_text(encoding='utf-8')
g = g.replace('versionCode 58','versionCode 59',1).replace('versionName "2.9.3"','versionName "2.9.4"',1)
if 'versionCode 59' not in g or 'versionName "2.9.4"' not in g:
    raise SystemExit('v2.9.4 metadata missing')
gradle.write_text(g, encoding='utf-8')

# Explicit non-mutation guard for this UX-only release.
worker = (root/'cloudflare/src/index.js').read_text(encoding='utf-8')
if "const API_VERSION = '2.9.3-cloudflare'" not in worker:
    raise SystemExit('Worker must remain 2.9.3-cloudflare for v2.9.4 UX-only release')
if "effective_modes: ['REMOTE','ROBOT']" not in worker:
    raise SystemExit('REMOTE/ROBOT invariant missing')

print('BIR v2.9.4 War Room UI-only patch applied')
