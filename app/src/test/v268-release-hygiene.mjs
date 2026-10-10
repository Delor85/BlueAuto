import fs from 'node:fs';
const build=fs.readFileSync('.github/workflows/build.yml','utf8');
const pkg=JSON.parse(fs.readFileSync('cloudflare/package.json','utf8'));
const lock=JSON.parse(fs.readFileSync('cloudflare/package-lock.json','utf8'));
if(pkg.version!=='2.6.8') throw new Error('Cloudflare package version not 2.6.8');
if(lock.version!=='2.6.8'||(lock.packages&&lock.packages['']&&lock.packages[''].version!=='2.6.8')) throw new Error('Cloudflare lock root version not 2.6.8');
for(const required of ['publish_permanent','authorized_sha','inputs.authorized_sha == github.sha','Préparer une signature éphémère de validation','v268-native-status.mjs','Blue-Magic-v2.6.8-Stabilisation-Ergonomie-Release.apk','versionName=2.6.8']){
  if(!build.includes(required)) throw new Error('release hygiene missing: '+required);
}
if(build.includes("github.event_name == 'workflow_dispatch' ||")) throw new Error('manual dispatch can still publish without explicit guard');
if(build.includes('release: authorized Blue Magic v2.6.7 permanent APK once')) throw new Error('old v2.6.7 trigger remains');
const normal=build.slice(build.indexOf('android-debug-apk:'),build.indexOf('android-permanent-apk:'));
if(normal.includes('BLUE_MAGIC_ANDROID_KEYSTORE_BASE64')||normal.includes('BLUE_MAGIC_ANDROID_KEYSTORE_PASSWORD')) throw new Error('normal CI still loads permanent signing secrets');
console.log('v2.6.8 release hygiene: metadata aligned, normal CI ephemeral and permanent delivery SHA-gated OK');
