#!/usr/bin/env bash
set -euo pipefail

stress="${1:-12}"
package="com.profitloop.blueauto"
activity="com.profitloop.blueauto/.MainActivity"
apk="$(find apk -type f -name 'BIR-Blue-Infinity-Retail-v2.9.9.3-vc67-Qualification.apk' -print -quit)"

fail(){
  code="${1:-1}"; shift || true
  echo "BIR_SMOKE_FAILURE: $*" >&2
  adb shell dumpsys window windows 2>/dev/null | grep -E 'mCurrentFocus|mFocusedApp' >&2 || true
  adb shell dumpsys activity activities 2>/dev/null | grep -E 'mResumedActivity|ResumedActivity|com\.profitloop\.blueauto' | tail -30 >&2 || true
  adb logcat -d 2>/dev/null | grep -E 'com\.profitloop\.blueauto|chromium|crash_dump|WebView' | tail -120 >&2 || true
  exit "$code"
}

step(){ echo "BIR_SMOKE_STEP: $*"; }

bir_resumed(){
  if adb shell dumpsys window windows 2>/dev/null | grep -E 'mCurrentFocus|mFocusedApp' | grep -q "$package"; then
    return 0
  fi
  adb shell dumpsys activity activities 2>/dev/null | grep -E 'mResumedActivity|ResumedActivity' | grep -q "$package"
}

test -n "$apk" || fail 81 'qualification APK path missing'
test -s "$apk" || fail 81 'qualification APK empty'

step 'emulator ready'
adb wait-for-device
ready=0
for _ in $(seq 1 60); do
  if adb shell service check package 2>/dev/null | grep -qi found && adb shell pm path android >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 5
done
[ "$ready" = 1 ] || fail 80 'package manager never became ready'

step 'install exact candidate'
adb install --no-streaming "$apk"
adb shell dumpsys package "$package" | grep -q 'versionCode=67' || fail 82 'installed versionCode is not 67'

# google_apis emulator images are debuggable. Seed a strictly local/non-production DAE profile so
# the smoke opens the real B.I.R. WebView instead of only exercising the native pairing screen.
step 'seed local non-production profile'
adb root >/tmp/bir-adb-root.txt 2>&1 || true
adb wait-for-device
if ! adb shell id | grep -q 'uid=0(root)'; then
  fail 80 'emulator image does not allow adb root; cannot seed WebView profile safely'
fi
uid="$(adb shell dumpsys package "$package" | sed -n 's/.*userId=\([0-9]*\).*/\1/p' | head -1 | tr -d '\r')"
[ -n "$uid" ] || fail 80 'could not resolve package uid'

cat >/tmp/bir-prefs.xml <<'XML'
<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
  <string name="active_profile_id_v3">ci-dae</string>
  <string name="profiles_v3">[{"id":"ci-dae","api_url":"https://127.0.0.1/api","device_token":"ci-token-not-production","node_code":"OU3","official_node_code":"OU3","phone_number":"690000000","parent_node_code":"","official_parent_node_code":"","role":"DAE","device_mode":"REMOTE","sim_slot":0}]</string>
</map>
XML
adb push /tmp/bir-prefs.xml /data/local/tmp/bir-prefs.xml >/dev/null
adb shell "mkdir -p /data/user/0/$package/shared_prefs && cp /data/local/tmp/bir-prefs.xml /data/user/0/$package/shared_prefs/blue_magic_native_v2.xml && chown -R $uid:$uid /data/user/0/$package"

step 'launch real MainActivity/WebView'
adb shell am force-stop "$package"
adb logcat -c || true
adb shell am start -W -n "$activity" >/tmp/bir-start.txt
cat /tmp/bir-start.txt
grep -Eq 'Status: ok|Complete' /tmp/bir-start.txt || fail 83 'MainActivity did not report successful launch'
sleep 10
adb shell pidof "$package" >/dev/null || fail 84 'BIR process not alive after launch'
bir_resumed || fail 85 'BIR MainActivity is not resumed after launch'

# Prove that the real WebView renderer is active. UIAutomator output is optional because older
# providers (notably some API28 images) may fail to emit a hierarchy even while Chromium renders.
step 'prove WebView renderer exists'
adb shell uiautomator dump /sdcard/bir-window.xml >/dev/null 2>&1 || true
adb pull /sdcard/bir-window.xml /tmp/bir-window.xml >/dev/null 2>&1 || true
adb logcat -d >/tmp/bir-prestress-logcat.txt || true
adb shell ps -A 2>/dev/null >/tmp/bir-processes.txt || true
webview_evidence=0
if test -s /tmp/bir-window.xml && grep -Eq 'android\.webkit\.WebView|WebView' /tmp/bir-window.xml; then
  webview_evidence=1
fi
if grep -Ei 'WebViewFactory|chromium|webview_service|sandboxed_process' /tmp/bir-prestress-logcat.txt >/dev/null 2>&1; then
  webview_evidence=1
fi
if grep -Ei 'webview|sandboxed_process|chromium' /tmp/bir-processes.txt >/dev/null 2>&1; then
  webview_evidence=1
fi
[ "$webview_evidence" = 1 ] || fail 86 'no WebView/Chromium renderer evidence found'
adb exec-out screencap -p >/tmp/bir-initial.png
test -s /tmp/bir-initial.png || fail 87 'initial rendered screenshot missing'
initial_size="$(wc -c </tmp/bir-initial.png | tr -d ' ')"
[ "$initial_size" -gt 10000 ] || fail 87 "initial screenshot unexpectedly small: $initial_size bytes"

# Stress only scroll + process foreground/background/resume. No fixed-coordinate navigation and no
# financial button taps. This tests exactly the rendering/lifecycle regression that affected Android 11.
step "stress renderer/lifecycle cycles=$stress"
for _ in $(seq 1 "$stress"); do
  adb shell input swipe 540 1450 540 650 110 || true
  adb shell input swipe 540 650 540 1450 110 || true
  adb shell input keyevent KEYCODE_HOME || true
  adb shell am start -W -n "$activity" >/dev/null || fail 88 'MainActivity failed to resume during stress'
done
sleep 5

step 'final liveness/render/crash checks'
adb shell pidof "$package" >/dev/null || fail 89 'BIR process died during stress'
bir_resumed || fail 89 'BIR MainActivity is not resumed after stress'
adb exec-out screencap -p >/tmp/bir-final.png
test -s /tmp/bir-final.png || fail 89 'final rendered screenshot missing'
final_size="$(wc -c </tmp/bir-final.png | tr -d ' ')"
[ "$final_size" -gt 10000 ] || fail 89 "final screenshot unexpectedly small: $final_size bytes"
adb logcat -d >/tmp/bir-logcat.txt || true
if grep -E 'FATAL EXCEPTION.*com\.profitloop\.blueauto|Process: com\.profitloop\.blueauto|ANR in com\.profitloop\.blueauto|Render process.*gone|crash_dump.*webview' /tmp/bir-logcat.txt; then
  fail 1 'fatal/ANR/WebView renderer failure detected'
fi

echo "B.I.R. 2.9.9.3 unified WebView smoke: OK (stress=$stress, initial_png=$initial_size, final_png=$final_size)"
