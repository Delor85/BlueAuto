from pathlib import Path
root=Path(__file__).resolve().parents[2]
files=[
 'app/src/test/finance-flow.mjs',
 'app/src/test/v268-field-contract.mjs',
 'app/src/test/v270-finalization-contract.mjs',
 'app/src/test/v270-owner-mock-contract.mjs',
]
for rel in files:
 p=root/rel
 s=p.read_text(encoding='utf-8')
 s=s.replace('/COMMANDE CAMTEL SENSIBLE/','/COMMANDE (?:CAMTEL|BLUE) SENSIBLE/')
 s=s.replace('/versionCode 51/','/versionCode (?:51|52)/')
 s=s.replace('/versionName "2\\.7\\.0"/','/versionName "2\\.7\\.(?:0|1)"/')
 s=s.replace('/MOCK ne crée pas d’approvisionnement ou de vente Camtel directe/','/MOCK ne crée pas d’approvisionnement ou de vente (?:Camtel|Blue) directe/')
 s=s.replace("!ui.includes('Solde Camtel : ')","!(ui.includes('Solde Camtel : ')||ui.includes('Solde Blue : '))")
 s=s.replace("!html.includes('Modifier mon PIN Camtel')","!(html.includes('Modifier mon PIN Camtel')||html.includes('Modifier mon PIN Blue'))")
 p.write_text(s,encoding='utf-8')
print('historical contracts updated for superseding v2.7.1 UI brand/version')
