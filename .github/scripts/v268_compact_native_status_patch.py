from pathlib import Path

p = Path('app/src/main/java/com/profitloop/blueauto/MainActivity.java')
s = p.read_text()
old = '''    private void refreshNativeStatus() {
        if (nativeStatus == null) return;
        boolean simRequired = AppConfig.isRobotMode(this);
        SimIdentityManager.Verification sim = simRequired
                ? SimIdentityManager.verify(this, AppConfig.profileId(this)) : null;
        if (AppConfig.robotEnabled(this) && sim != null && !sim.valid) {
            AppConfig.setRobotEnabled(this, false);
            RobotService.stop(this);
        }
        nativeStatus.setText(AppConfig.nodeCode(this)
                + " • " + AppConfig.displayMode(AppConfig.mode(this))
                + " • SIM " + (AppConfig.simSlot(this) + 1)
                + (!simRequired ? " NON REQUISE" : sim.valid ? " VÉRIFIÉE" : " BLOQUÉE")
                + " • Robot " + (AppConfig.robotEnabled(this) ? "ACTIF" : "ARRÊTÉ")
                + "\\nAccessibilité " + (BlueAccessibilityService.isEnabled(this) ? "OK" : "À ACTIVER")
                + " • Robots actifs : " + AppConfig.enabledRobotCount(this)
                + (DeviceLockState.isSecurelyLocked(this)
                ? "\\n🔒 VERROU SÉCURISÉ : aucune tentative automatique; déverrouillage humain requis"
                : DeviceLockState.isInsecurelyLocked(this)
                ? "\\n✨ VERROU SIMPLE : assistance ponctuelle autorisée seulement au moment d’une commande" : "")
                + (sim != null && !sim.valid ? "\\n⛔ " + sim.message : "")
                + (AppConfig.pinBlocked(this) ? "\\n⛔ PIN BLOQUÉ : corriger avant toute nouvelle transaction" : ""));
    }
'''
new = '''    private void refreshNativeStatus() {
        if (nativeStatus == null) return;
        boolean robotMode = AppConfig.isRobotMode(this);
        if (!robotMode) {
            // A Remote is a control terminal. SIM verification and Accessibility are Robot-only
            // requirements and showing them here was both confusing and wasteful on short screens.
            nativeStatus.setText(AppConfig.nodeCode(this)
                    + " • REMOTE • Télécommande prête"
                    + (AppConfig.profileCount(this) > 1
                    ? " • " + AppConfig.profileCount(this) + " comptes sur ce téléphone" : ""));
            nativeStatus.setTextColor(CYAN);
            return;
        }

        String profileId = AppConfig.profileId(this);
        SimIdentityManager.Verification sim = SimIdentityManager.verify(this, profileId);
        boolean robotEnabled = AppConfig.robotEnabled(this);
        boolean accessibility = BlueAccessibilityService.isEnabled(this);
        if (robotEnabled && !sim.valid) {
            AppConfig.setRobotEnabled(this, false);
            RobotService.stop(this);
            robotEnabled = false;
        }

        StringBuilder status = new StringBuilder();
        status.append(AppConfig.nodeCode(this))
                .append(" • ROBOT • SIM ").append(AppConfig.simSlot(this) + 1)
                .append(sim.valid ? " VÉRIFIÉE" : " BLOQUÉE")
                .append(" • ").append(robotEnabled ? "ACTIF" : "ARRÊTÉ");
        int activeCount = AppConfig.enabledRobotCount(this);
        if (activeCount > 1) status.append(" • ").append(activeCount).append(" Robots locaux");

        if (sim != null && !sim.valid) {
            status.append("\\n⛔ ").append(sim.message);
        } else if (AppConfig.pinBlocked(this)) {
            status.append("\\n⛔ PIN BLOQUÉ : corriger avant toute nouvelle transaction");
        } else if (robotEnabled && !accessibility) {
            status.append("\\n⚠ Accessibilité à activer avant achat/vente • TEST_NUMBER reste direct");
        } else if (robotEnabled && DeviceLockState.isSecurelyLocked(this)) {
            status.append("\\n🔒 Écran sécurisé : déverrouillage humain requis avant USSD");
        } else if (robotEnabled && DeviceLockState.isInsecurelyLocked(this)) {
            status.append("\\n✨ Verrou simple : assistance ponctuelle uniquement si une commande arrive");
        }

        nativeStatus.setText(status.toString());
        nativeStatus.setTextColor((!sim.valid || AppConfig.pinBlocked(this)
                || (robotEnabled && !accessibility)) ? GOLD : CYAN);
    }
'''
if old not in s:
    raise SystemExit('native status anchor missing')
p.write_text(s.replace(old, new, 1))

contract = r'''import fs from 'node:fs';
const main=fs.readFileSync('app/src/main/java/com/profitloop/blueauto/MainActivity.java','utf8');
if(!main.includes('REMOTE • Télécommande prête')) throw new Error('compact Remote status missing');
const remoteStart=main.indexOf('if (!robotMode)');
const remoteEnd=main.indexOf('String profileId',remoteStart);
const remoteBlock=main.slice(remoteStart,remoteEnd);
if(remoteBlock.includes('BlueAccessibilityService')||remoteBlock.includes('SimIdentityManager.verify')) throw new Error('Remote still performs Robot-only status checks');
for(const text of ['Accessibilité à activer avant achat/vente','TEST_NUMBER reste direct','Écran sécurisé : déverrouillage humain requis','Verrou simple : assistance ponctuelle']){
  if(!main.includes(text)) throw new Error('Robot actionable status missing: '+text);
}
if(!main.includes('activeCount > 1')) throw new Error('multi-Robot count is not compacted');
if(main.includes('• Robots actifs : ')) throw new Error('legacy always-visible Robot counter remains');
console.log('v2.6.8 native status: compact Remote and actionable Robot-only alerts OK');
'''
Path('app/src/test/v268-native-status.mjs').write_text(contract)
