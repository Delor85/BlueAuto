from pathlib import Path
import re

changed=[]
code_chain=re.compile(r"\((?:gradle\.includes\('versionCode \d+'\)(?:\|\|)?)+\)")
name_chain=re.compile(r"\((?:gradle\.includes\('versionName [^']+'\)(?:\|\|)?)+\)")
worker_chain=re.compile(r"\((?:worker\.includes\(\"const API_VERSION = '[^']+'\"\)(?:\|\|)?)+\)")
worker_bare_chain=re.compile(r"\((?:worker\.includes\(\"[0-9.]+-cloudflare\"\)(?:\|\|)?)+\)")
code_regex=re.compile(r"versionCode \(\?:([0-9|]+)\)")

for p in Path('app/src/test').glob('*.mjs'):
    if p.name == 'bir-v293-coherence-contract.mjs':
        continue
    s=p.read_text(encoding='utf-8')
    old=s

    # Metadata-only compatibility: append the new version to existing literal OR guards.
    # No functional, finance, safety, UX, Android or Cloudflare assertion is removed or rewritten.
    def add_code(match):
        group=match.group(0)
        if "versionCode 58" in group:
            return group
        return group[:-1] + "||gradle.includes('versionCode 58'))"

    def add_name(match):
        group=match.group(0)
        if 'versionName "2.9.3"' in group:
            return group
        return group[:-1] + "||gradle.includes('versionName \"2.9.3\"'))"

    def add_worker(match):
        group=match.group(0)
        if "2.9.3-cloudflare" in group:
            return group
        return group[:-1] + "||worker.includes(\"const API_VERSION = '2.9.3-cloudflare'\"))"

    def add_worker_bare(match):
        group=match.group(0)
        if "2.9.3-cloudflare" in group:
            return group
        return group[:-1] + '||worker.includes("2.9.3-cloudflare"))'

    def add_code_regex(match):
        values=match.group(1).split('|')
        if '58' not in values:
            values.append('58')
        return 'versionCode (?:'+'|'.join(values)+')'

    s=code_chain.sub(add_code,s)
    s=name_chain.sub(add_name,s)
    s=worker_chain.sub(add_worker,s)
    s=worker_bare_chain.sub(add_worker_bare,s)
    s=code_regex.sub(add_code_regex,s)

    # finance-flow and similar historical guards use a JS RegExp rather than gradle.includes().
    finance_name='versionName "(?:2\\.7\\.(?:0|1)|2\\.8\\.(?:0|1)|2\\.9\\.0)"'
    if finance_name in s and '2\\.9\\.3' not in s:
        s=s.replace(finance_name,
                    'versionName "(?:2\\.7\\.(?:0|1)|2\\.8\\.(?:0|1)|2\\.9\\.0|2\\.9\\.3)"')

    # A few newer contracts use a single literal rather than an OR chain.
    if 'versionCode 58' not in s and "gradle.includes('versionCode 57')" in s:
        s=s.replace("gradle.includes('versionCode 57')",
                    "(gradle.includes('versionCode 57')||gradle.includes('versionCode 58'))")
    if 'versionName "2.9.3"' not in s and 'gradle.includes(\'versionName "2.9.2"\')' in s:
        s=s.replace('gradle.includes(\'versionName "2.9.2"\')',
                    '(gradle.includes(\'versionName "2.9.2"\')||gradle.includes(\'versionName "2.9.3"\'))')
    if '2.9.3-cloudflare' not in s and 'worker.includes("const API_VERSION = \'2.9.2-cloudflare\'")' in s:
        s=s.replace('worker.includes("const API_VERSION = \'2.9.2-cloudflare\'")',
                    '(worker.includes("const API_VERSION = \'2.9.2-cloudflare\'")||worker.includes("const API_VERSION = \'2.9.3-cloudflare\'"))')
    if '2.9.3-cloudflare' not in s and 'worker.includes("2.9.2-cloudflare")' in s:
        s=s.replace('worker.includes("2.9.2-cloudflare")',
                    '(worker.includes("2.9.2-cloudflare")||worker.includes("2.9.3-cloudflare"))')

    # v2611 and a few historical contracts check the JSON app_version literal in ApiClient.
    if 'api client version mismatch' in s:
        old_api="api.includes('\\\"2.9.1\\\"')"
        new_api="api.includes('\\\"2.9.3\\\"')"
        if old_api in s and new_api not in s:
            s=s.replace(old_api, "("+old_api+"||"+new_api+")", 1)

    if s!=old:
        p.write_text(s,encoding='utf-8')
        changed.append(str(p))

print('Inherited tests metadata-only widening:', len(changed))
for item in changed:
    print(' -',item)
