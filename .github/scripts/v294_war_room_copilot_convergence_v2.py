from pathlib import Path

source = Path('.github/scripts/v294_war_room_copilot_convergence.py')
code = compile(source.read_text(encoding='utf-8'), str(source), 'exec')
exec(code, {'__name__': '__main__'})

# git diff --check rejects the old generated blank line at EOF.
p = Path('app/src/main/assets/war-room-v294.js')
p.write_text(p.read_text(encoding='utf-8').rstrip() + '\n', encoding='utf-8')

# Android may retain the B.I.R. component in ENABLED_ACCESSIBILITY_SERVICES while
# the global accessibility switch itself is OFF (observed after emulator reboot).
# Treat that state as genuinely disabled so the queue is preserved and the user
# gets one clear re-enable action instead of an endless "reconnecting" state.
p = Path('app/src/main/java/com/profitloop/blueauto/BlueAccessibilityService.java')
s = p.read_text(encoding='utf-8')
old = '''    static boolean isEnabled(Context context) {
        String enabled = Settings.Secure.getString(
                context.getContentResolver(), Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES);
        if (enabled == null) return false;
        String expected = new ComponentName(context, BlueAccessibilityService.class).flattenToString();
        TextUtils.SimpleStringSplitter splitter = new TextUtils.SimpleStringSplitter(':');
        splitter.setString(enabled);
        while (splitter.hasNext()) {
            if (expected.equalsIgnoreCase(splitter.next())) return true;
        }
        return false;
    }
'''
new = '''    static boolean isEnabled(Context context) {
        try {
            if (Settings.Secure.getInt(context.getContentResolver(),
                    Settings.Secure.ACCESSIBILITY_ENABLED, 0) != 1) return false;
        } catch (Exception ignored) {
            return false;
        }
        return isServiceListed(context);
    }

    static boolean isServiceListed(Context context) {
        String enabled = Settings.Secure.getString(
                context.getContentResolver(), Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES);
        if (enabled == null) return false;
        String expected = new ComponentName(context, BlueAccessibilityService.class).flattenToString();
        TextUtils.SimpleStringSplitter splitter = new TextUtils.SimpleStringSplitter(':');
        splitter.setString(enabled);
        while (splitter.hasNext()) {
            if (expected.equalsIgnoreCase(splitter.next())) return true;
        }
        return false;
    }
'''
if old in s:
    s=s.replace(old,new,1)
elif 'Settings.Secure.ACCESSIBILITY_ENABLED' not in s:
    raise SystemExit('BlueAccessibilityService isEnabled anchor missing')
p.write_text(s,encoding='utf-8')

# Strengthen the v2.9.4 contract with the global-switch distinction.
t = Path('app/src/test/v294-war-room-contract.mjs')
c = t.read_text(encoding='utf-8')
if "BlueAccessibilityService.java" not in c:
    c=c.replace("const manifest=fs.readFileSync('app/src/main/AndroidManifest.xml','utf8');",
                "const manifest=fs.readFileSync('app/src/main/AndroidManifest.xml','utf8');\nconst access=fs.readFileSync('app/src/main/java/com/profitloop/blueauto/BlueAccessibilityService.java','utf8');")
    c=c.replace("need(!manifest.includes('android.permission.SEND_SMS'),'SMS invariant');",
                "need(!manifest.includes('android.permission.SEND_SMS'),'SMS invariant');\nneed(access.includes('Settings.Secure.ACCESSIBILITY_ENABLED')&&access.includes('isServiceListed'),'global accessibility distinction missing');")
t.write_text(c,encoding='utf-8')
print('BIR v2.9.4 generated EOF and Accessibility state normalized')
