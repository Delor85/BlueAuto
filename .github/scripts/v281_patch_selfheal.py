from pathlib import Path
import re

p = Path(__file__).with_name('v281_field_quality_patch.py')
s = p.read_text(encoding='utf-8')

# Minified ADMIN binding: use the short stable neighbour instead of a long minified span.
pattern = r"s = replace_once\(s,\n'''bind\('v280TchoSave'.*?'Admin account switch binding'\)\n"
replacement = """s = replace_once(s,\n'''bind('v280AdminRefresh',function(){request('owner_snapshot',{});});''',\n'''bind('v280AdminAccounts',function(){var b=bridge();if(b&&b.openAccounts)b.openAccounts();});bind('v280AdminRefresh',function(){request('owner_snapshot',{});});''', 'Admin account switch binding')\n"""
s, count = re.subn(pattern, replacement, s, count=1, flags=re.S)
if count != 1:
    raise SystemExit(f'Could not self-heal v281 admin binding anchor: {count}')

# Replace the whole bilingual expansion block. Triple-double quotes are intentional:
# the actual JavaScript key starts with a single quote, so no quote may be left behind
# by the search anchor and no second quote may be injected by the replacement.
pattern = r"# Expand exact-match dictionary while keeping protected operator/protocol terms unchanged\.\ns = replace_once\(s,.*?'Expanded bilingual dictionary'\)\nwrite\(p, s\)"
block = '''# Expand exact-match dictionary while keeping protected operator/protocol terms unchanged.
s = replace_once(s,
"""'Actualiser tout':'Refresh all','Aucune donnée':'No data'\\n};""",
"""'Actualiser tout':'Refresh all','Aucune donnée':'No data',\\n'En attente':'Pending','Réservée au Robot':'Leased to Robot','Composition USSD':'USSD dialing','Vérification du pop-up':'Prompt verification','PIN validé':'PIN submitted','Confirmation Blue':'Blue confirmation','Réussie':'Successful','Échec':'Failed','À vérifier':'Needs review','Annulée':'Cancelled',\\n'Compte inconnu':'Unknown account','Tous les comptes B.I.R.':'All B.I.R. accounts','Ajouter / Ouvrir':'Add / Open','Supprimer l’actif':'Delete active','Fermer':'Close','Verrouillé':'Locked','Session active':'Active session',\\n'Autorisations':'Permissions','Batterie':'Battery','Synchroniser':'Synchronize','Démarrer Robot':'Start Robot','Arrêter Robot':'Stop Robot','Changer de mode':'Change mode','Vérifier / réparer l’appairage':'Verify / repair pairing',\\n'Solde recalculé':'Recalculated balance','preuve certifiée':'certified evidence','mouvement(s) confirmé(s)':'confirmed movement(s)','Disponible':'Available','Réservé confirmé':'Confirmed reserved','Composante commission':'Commission component',\\n'Compte actif':'Active account','Tour de contrôle':'Control tower','Serveur en ligne':'Server online','Dernière synchronisation':'Last synchronization','Reprise automatique':'Automatic recovery','Aucune activité':'No activity',\\n'Gestion avancée des enfants':'Advanced child management','Demande utilisateur':'User request','Confirmation utilisateur requise':'User confirmation required','Aucune opération financière silencieuse':'No silent financial operation',\\n'Code privé MOCK':'Private MOCK code','Code privé ADMIN propriétaire':'Private owner ADMIN code','Session propriétaire verrouillée. Le code est requis après 30 minutes d’inactivité.':'Owner session is locked. The code is required after 30 minutes of inactivity.',\\n'Ouvrir MOCK':'Open MOCK','Ouvrir ADMIN':'Open ADMIN','Changer de compte':'Switch account','Comptes Blue':'Blue accounts','Tous les comptes':'All accounts'\\n};""", 'Expanded bilingual dictionary')
write(p, s)'''
s, count = re.subn(pattern, block, s, count=1, flags=re.S)
if count != 1:
    raise SystemExit(f'Could not self-heal v281 bilingual block: {count}')

legacy_old = '⚠ Accessibilité désactivée par Android • Robot conservé • achat/vente en attente'
legacy_new = '⚠ Accessibilité à activer avant achat/vente • désactivée par Android • Robot conservé • file conservée • TEST_NUMBER reste direct'
if legacy_old not in s:
    raise SystemExit('Could not preserve inherited accessibility status wording')
s = s.replace(legacy_old, legacy_new, 1)

p.write_text(s, encoding='utf-8')
print('v281 patch anchors hardened, bilingual dictionary syntax protected')
