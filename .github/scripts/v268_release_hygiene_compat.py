from pathlib import Path

# Markdown line breaks must not rely on trailing whitespace because git diff --check is mandatory.
p = Path('README.md')
s = p.read_text()
p.write_text('\n'.join(line.rstrip() for line in s.splitlines()) + '\n')

# The permanent job must execute the same v2.6.8 application contracts as ordinary CI.
p = Path('.github/workflows/build.yml')
s = p.read_text()
marker = '  android-permanent-apk:'
start = s.index(marker)
old = '''      - name: Compiler le vrai APK Release permanent
        if: steps.signing-availability.outputs.available == 'true'
        run: |
          node app/src/test/finance-flow.mjs
          gradle --no-daemon :app:testDebugUnitTest :app:assembleRelease
'''
new = '''      - name: Compiler le vrai APK Release permanent
        if: steps.signing-availability.outputs.available == 'true'
        run: |
          set -euo pipefail
          node app/src/test/finance-flow.mjs
          node app/src/test/v268-field-contract.mjs
          node app/src/test/v268-responsive-management.mjs
          node app/src/test/v268-ux-performance.mjs
          node app/src/test/v268-platform-compat.mjs
          node app/src/test/v268-transaction-ux.mjs
          node app/src/test/v268-control-plane.mjs
          node app/src/test/v268-native-status.mjs
          node app/src/test/v268-release-hygiene.mjs
          node --check app/src/main/assets/app.js
          node --check app/src/main/assets/platform-v267.js
          gradle --no-daemon :app:testDebugUnitTest :app:assembleRelease
'''
tail = s[start:]
if old not in tail:
    raise SystemExit('permanent compile block missing')
s = s[:start] + tail.replace(old, new, 1)
p.write_text(s)
