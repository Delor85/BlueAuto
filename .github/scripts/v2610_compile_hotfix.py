from pathlib import Path
p=Path('app/src/main/java/com/profitloop/blueauto/BlueAccessibilityService.java')
s=p.read_text(encoding='utf-8')
old='''    static boolean isConnected() { return liveInstance != null; }\n\n    @Override\n    public void onInterrupt() {\n        if (liveInstance == this) liveInstance = null;\n    }\n\n    @Override\n    public void onDestroy() {\n        if (liveInstance == this) liveInstance = null;\n        handler.removeCallbacksAndMessages(null);\n        super.onDestroy();\n    }\n\n    static boolean isEnabled(Context context) {'''
new='''    static boolean isConnected() { return liveInstance != null; }\n\n    static boolean isEnabled(Context context) {'''
if old not in s: raise SystemExit('accessibility duplicate lifecycle anchor missing')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
