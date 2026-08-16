import worker from './index.js';

const OWNER_ADMIN_BOOTSTRAP_SHA256 = '2f15a8ac5465468a991b98cba94e8c126a64b845fe4fcb189f56596afdb42f60';
const MOCK_OWNER_BOOTSTRAP_SHA256 = '207e4a9bca5e4073fa98e767a85bd937a63d9e2f62d2fe5e693360ab2ee3e3cd';

async function sha256(value) {
  const bytes = new TextEncoder().encode(String(value || ''));
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, '0')).join('');
}

function constantTimeEqual(left, right) {
  const a = new TextEncoder().encode(String(left || ''));
  const b = new TextEncoder().encode(String(right || ''));
  let different = a.length ^ b.length;
  const length = Math.max(a.length, b.length, 1);
  for (let index = 0; index < length; index += 1) {
    different |= (a[index % Math.max(a.length, 1)] || 0) ^ (b[index % Math.max(b.length, 1)] || 0);
  }
  return different === 0;
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const action = (url.searchParams.get('action') || 'health').trim();
    if (request.method !== 'POST' || action !== 'owner_enroll') {
      return worker.fetch(request, env, ctx);
    }

    let input = {};
    try {
      input = await request.clone().json();
    } catch (_) {
      return worker.fetch(request, env, ctx);
    }

    const kind = String(input.kind || '').trim().toUpperCase();
    const ownerCode = String(input.owner_code || '');
    const secretName = kind === 'OWNER_ADMIN' ? 'OWNER_ADMIN_SECRET'
      : kind === 'MOCK_OWNER' ? 'MOCK_OWNER_SECRET' : '';
    const configuredSecret = secretName ? String(env[secretName] || '') : '';

    // A Cloudflare secret, when configured later, always takes precedence and disables
    // the bootstrap hash for that entitlement kind. Until then, only the strong private
    // bootstrap code whose SHA-256 is committed here can unlock enrollment.
    if (!secretName || configuredSecret.length >= 32) {
      return worker.fetch(request, env, ctx);
    }

    const expectedHash = kind === 'OWNER_ADMIN'
      ? OWNER_ADMIN_BOOTSTRAP_SHA256 : MOCK_OWNER_BOOTSTRAP_SHA256;
    const providedHash = await sha256(ownerCode);
    if (!constantTimeEqual(expectedHash, providedHash)) {
      return worker.fetch(request, env, ctx);
    }

    const runtimeEnv = {...env, [secretName]: ownerCode};
    return worker.fetch(request, runtimeEnv, ctx);
  }
};
