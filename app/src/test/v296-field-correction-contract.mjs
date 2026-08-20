import fs from 'node:fs';

const read=p=>fs.readFileSync(p,'utf8');
const must=(condition,message)=>{if(!condition)throw new Error(message);};
const main=read('app/src/main/java/com/profitloop/blueauto/MainActivity.java');
const sim=read('app/src/main/java/com/profitloop/blueauto/SimIdentityManager.java');
const identity=read('app/src/main/java/com/profitloop/blueauto/CamtelIdentity.java');
const attempts=read('app/src/main/java/com/profitloop/blueauto/PairingAttemptGuard.java');
const secure=read('app/src/main/java/com/profitloop/blueauto/SecurePairingStore.java');
const manifest=read('app/src/main/AndroidManifest.xml');
const gradle=read('app/build.gradle');
const api=read('app/src/main/java/com/profitloop/blueauto/ApiClient.java');
const worker=read('cloudflare/src/index.js');
const permanent=read('.github/workflows/v296-permanent-upgrade.yml');

must(gradle.includes('versionCode 61')&&gradle.includes('versionName "2.9.6"'),'2.9.6 Android identity missing');
must(api.includes('payload.put("app_version", "2.9.6");'),'2.9.6 telemetry missing');
must(worker.includes("const API_VERSION = '2.9.6-cloudflare'"),'2.9.6 Worker identity missing');
must(main.includes('PIN Blue exact à 4 chiffres est obligatoire en Remote et en Robot')
  &&main.includes('SecurePinStore.save(this, pin);'),'PIN must be captured for Remote and Robot');
must(main.includes('Afficher le code pendant la saisie')&&attempts.includes('MAX_ATTEMPTS = 5')
  &&main.includes('PairingAttemptGuard.recordDenied')&&secure.includes('static synchronized void clear'),
  'activation reveal/retry recovery missing');
must(identity.includes('Pour un PoS abrégé, le supérieur doit être complet')
  &&main.includes('pairWithLegacyRecovery')&&main.includes('resolvedIdentity.officialNode'),
  'canonical DAE/DSM/POS lineage and legacy recovery missing');
must(sim.includes('Build.VERSION.SDK_INT >= 24')&&sim.includes(': telephony.getLine1Number()')
  &&sim.includes('catch (Throwable ignored)'), 'Android 6 telephony linkage guard missing');
must(manifest.includes('android:icon="@drawable/ic_launcher_bir"')
  &&read('app/src/main/res/drawable/ic_launcher_bir.xml').includes('android:src="@mipmap/ic_launcher_bir"'),
  'legacy raster launcher identity missing');
must(worker.includes("if (role === 'POS')")&&worker.includes("fullParent.role !== 'DSM'")
  &&worker.includes("requestedIdentity.node_code !== officialExisting.node_code"),
  'Worker must reject ambiguous PoS lineage and recover by SIM only with exact official identity');
must(permanent.includes('BIR-v2.9.4-vc59-Permanent-Baseline.apk')
  &&permanent.includes('adb install -r apk/BIR-Blue-Infinity-Retail-v2.9.6-vc61-Permanent.apk')
  &&permanent.includes('certificate_sha256')&&permanent.includes('api: 23')
  &&permanent.includes('api: 26'),'permanent Android 6/8 in-place upgrade proof missing');

console.log('B.I.R. v2.9.6 field correction contract OK');
