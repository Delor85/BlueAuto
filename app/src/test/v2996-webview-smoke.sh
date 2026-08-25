#!/usr/bin/env bash
set -euo pipefail
stress="${1:-12}"
package="com.profitloop.blueauto"
activity="com.profitloop.blueauto/.MainActivity"
apk="$(find apk -type f -name 'BIR-Blue-Infinity-Retail-v2.9.9.6-vc70-Qualification.apk' -print -quit)"
fail(){ code="${1:-1}"; shift || true; echo "BIR_SMOKE_FAILURE: $*" >&2; adb logcat -d 2>/dev/null | grep -E 'com\.profitloop\.blueauto|chromium|WebView' | tail -100 >&2 || true; exit "$code"; }
bir_resumed(){ adb shell dumpsys activity activities 2>/dev/null | grep -E 'mResumedActivity|ResumedActivity' | grep -q "$package"; }
package_uid(){ local u=''; u="$(adb shell stat -c %u "/data/user/0/$package" 2>/dev/null | head -1 | tr -d '\r' || true)"; if ! printf '%s' "$u" | grep -Eq '^[0-9]+$'; then u="$(adb shell dumpsys package "$package" 2>/dev/null | sed -n 's/.*userId=\([0-9]*\).*/\1/p' | head -1 | tr -d '\r' || true)"; fi; printf '%s' "$u"; }
test -s "$apk" || fail 81 'qualification APK missing'
adb wait-for-device
ready=0
for _ in $(seq 1 60); do if adb shell pm path android >/dev/null 2>&1; then ready=1; break; fi; sleep 5; done
[ "$ready" = 1 ] || fail 80 'package manager not ready'
adb install --no-streaming "$apk"
adb shell dumpsys package "$package" | grep -q 'versionCode=70' || fail 82 'installed versionCode is not 70'
adb root >/dev/null 2>&1 || true
adb wait-for-device
uid="$(package_uid)"; printf '%s' "$uid" | grep -Eq '^[0-9]+$' || fail 80 'package uid unavailable'
cat >/tmp/bir-prefs.xml <<'XML'
<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
  <string name="active_profile_id_v3">ci-dae</string>
  <string name="profiles_v3">[{"id":"ci-dae","api_url":"https://127.0.0.1/api","device_token":"ci-token-not-production","node_code":"OU3","official_node_code":"OU3","phone_number":"690000000","parent_node_code":"","official_parent_node_code":"","role":"DAE","device_mode":"REMOTE","sim_slot":0}]</string>
</map>
XML
adb push /tmp/bir-prefs.xml /data/local/tmp/bir-prefs.xml >/dev/null
adb shell "mkdir -p /data/user/0/$package/shared_prefs && cp /data/local/tmp/bir-prefs.xml /data/user/0/$package/shared_prefs/blue_magic_native_v2.xml && chown -R $uid:$uid /data/user/0/$package"
adb shell am force-stop "$package"; adb logcat -c || true
adb shell am start -W -n "$activity" >/tmp/bir-start.txt
grep -Eq 'Status: ok|Complete' /tmp/bir-start.txt || fail 83 'MainActivity launch failed'
sleep 8
adb shell pidof "$package" >/dev/null || fail 84 'BIR process not alive'
bir_resumed || fail 85 'BIR activity not resumed'
adb exec-out screencap -p >/tmp/bir-initial.png; test "$(wc -c </tmp/bir-initial.png)" -gt 10000 || fail 87 'initial render missing'
for _ in $(seq 1 "$stress"); do adb shell input swipe 540 1450 540 650 110 || true; adb shell input swipe 540 650 540 1450 110 || true; adb shell input keyevent KEYCODE_HOME || true; adb shell am start -W -n "$activity" >/dev/null || fail 88 'resume failed'; done
sleep 4
adb shell pidof "$package" >/dev/null || fail 89 'process died during stress'
bir_resumed || fail 89 'activity not resumed after stress'
adb logcat -d >/tmp/bir-logcat.txt || true
if grep -E 'FATAL EXCEPTION.*com\.profitloop\.blueauto|Process: com\.profitloop\.blueauto|ANR in com\.profitloop\.blueauto|Render process.*gone' /tmp/bir-logcat.txt; then fail 1 'fatal/ANR/WebView failure detected'; fi
echo "B.I.R. 2.9.9.6 WebView smoke: OK (stress=$stress)"
