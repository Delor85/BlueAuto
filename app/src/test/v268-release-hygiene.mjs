import fs from 'node:fs';
const build=fs.readFileSync('.github/workflows/v295-identity-balance-sync.yml','utf8');
const pkg=JSON.parse(fs.readFileSync('cloudflare/package.json','utf8'));
const lock=JSON.parse(fs.readFileSync('cloudflare/package-lock.json','utf8'));
if(!['2.6.11','2.8.0','2.9.5'].includes(pkg.version)) throw new Error('Cloudflare package version outside supported stabilized lines');
if(!['2.6.11','2.8.0','2.9.5'].includes(lock.version)||(lock.packages&&lock.packages['']&&!['2.6.11','2.8.0','2.9.5'].includes(lock.packages[''].version))) throw new Error('Cloudflare lock root version outside supported stabilized lines');
for(const required of ['permissions:','contents: read','Validate Worker and D1 migrations locally','Prepare ephemeral validation signature','versionCode=\'60\'','versionName=\'2.9.5\'','BIR-v2.9.5-identity-balance-sync-EPHEMERAL']){
  if(!build.includes(required)) throw new Error('release hygiene missing: '+required);
}
if(/wrangler\s+(?:deploy|d1\s+migrations\s+apply[^\n]*--remote)/.test(build)) throw new Error('validation workflow mutates production');
if(build.includes('BLUE_MAGIC_ANDROID_KEYSTORE_BASE64')||build.includes('BLUE_MAGIC_ANDROID_KEYSTORE_PASSWORD')) throw new Error('validation CI loads permanent signing secrets');
console.log('release hygiene: v2.9.5 source validation is read-only and APK signing is ephemeral');
