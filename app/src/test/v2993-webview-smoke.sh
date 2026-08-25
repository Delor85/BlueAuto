#!/usr/bin/env bash
set -euo pipefail

stress="${1:-12}"
package="com.profitloop.blueauto"
activity="com.profitloop.blueauto/.MainActivity"
apk="$(find apk -type f -name 'BIR-Blue-Infinity-Retail-v2.9.9.3-vc67-Qualification.apk' -print -quit)"

test -n "$apk"
test -s "$apk"

adb wait-for-device
ready=0
for _ in $(seq 1 60); do
  if adb shell service check package 2>/dev/null | grep -qi found && adb shell pm path android >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 5
done
test "$ready" = 1

adb install --no-streaming "$apk"
adb shell dumpsys package "$package" | grep -q 'versionCode=67'

# google_apis emulator images are debuggable. Seed a strictly local/non-production DAE profile so
# the smoke opens the real B.I.R. WebView instead of only exercising the native pairing screen.
adb root >/tmp/bir-adb-root.txt 2>&1 || true
adb wait-for-device
if ! adb shell id | grep -q 'uid=0(root)'; then
  echo 'BIR_CI_INFRA: emulator image does not allow adb root; cannot seed WebView profile safely.' >&2
  exit 80
fi
uid="$(adb shell dumpsys package "$package" | sed -n 's/.*userId=\([0-9]*\).*/\1/p' | head -1 | tr -d '\r')"
test -n "$uid"

cat >/tmp/bir-prefs.xml <<'XML'
<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
  <string name="active_profile_id_v3">ci-dae</string>
  <string name="profiles_v3">[{"id":"ci-dae","api_url":"https://127.0.0.1/api","device_token":"ci-token-not-production","node_code":"OU3","official_node_code":"OU3","phone_number":"690000000","parent_node_code":"","official_parent_node_code":"","role":"DAE","device_mode":"REMOTE","sim_slot":0}]</string>
</map>
XML
adb push /tmp/bir-prefs.xml /data/local/tmp/bir-prefs.xml >/dev/null
adb shell "mkdir -p /data/user/0/$package/shared_prefs && cp /data/local/tmp/bir-prefs.xml /data/user/0/$package/shared_prefs/blue_magic_native_v2.xml && chown -R $uid:$uid /data/user/0/$package"

adb shell am force-stop "$package"
adb logcat -c || true
adb shell am start -W -n "$activity" >/tmp/bir-start.txt
grep -Eq 'Status: ok|Complete' /tmp/bir-start.txt
sleep 8

# The same v2.9.7-derived modern cockpit must exist on every API.
# Open Home using only the bottom navigation; never tap a financial action during stress.
adb shell input tap 108 1760 || true
sleep 2
adb shell uiautomator dump /sdcard/bir-home.xml >/dev/null 2>&1 || true
adb pull /sdcard/bir-home.xml /tmp/bir-home.xml >/dev/null 2>&1 || true
test -s /tmp/bir-home.xml
grep -q 'COCKPIT ADAPTATIF' /tmp/bir-home.xml

# Open Network and prove the current 2.9.9.3 child War Room is present on the same UI path.
adb shell input tap 324 1760 || true
sleep 2
adb shell uiautomator dump /sdcard/bir-network.xml >/dev/null 2>&1 || true
adb pull /sdcard/bir-network.xml /tmp/bir-network.xml >/dev/null 2>&1 || true
test -s /tmp/bir-network.xml
grep -q 'WAR ROOM DES ENFANTS' /tmp/bir-network.xml

# Stress only navigation, scrolling and background/resume. No random central taps, no finance.
for _ in $(seq 1 "$stress"); do
  adb shell input swipe 540 1450 540 650 120 || true
  adb shell input swipe 540 650 540 1450 120 || true
  adb shell input tap 108 1760 || true
  adb shell input tap 324 1760 || true
  adb shell input keyevent KEYCODE_HOME || true
  adb shell am start -W -n "$activity" >/dev/null || true
done
sleep 4

adb shell pidof "$package" >/dev/null
adb exec-out screencap -p >/tmp/bir-final.png
test -s /tmp/bir-final.png
adb logcat -d >/tmp/bir-logcat.txt || true
if grep -E 'FATAL EXCEPTION.*com\.profitloop\.blueauto|Process: com\.profitloop\.blueauto|ANR in com\.profitloop\.blueauto|Render process.*gone|crash_dump.*webview' /tmp/bir-logcat.txt; then
  echo 'BIR_APP_FAILURE: fatal/ANR/WebView renderer failure detected.' >&2
  exit 1
fi

echo "B.I.R. 2.9.9.3 unified WebView smoke: OK (stress=$stress)"
