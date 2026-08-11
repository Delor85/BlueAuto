import {readFile, writeFile} from 'node:fs/promises';

const databaseId = String(process.env.CLOUDFLARE_D1_DATABASE_ID || '').trim();
if (!/^[a-f0-9-]{32,64}$/i.test(databaseId)) {
  throw new Error('CLOUDFLARE_D1_DATABASE_ID absent ou invalide.');
}

const source = await readFile(new URL('../wrangler.jsonc', import.meta.url), 'utf8');
if (!source.includes('REPLACE_WITH_D1_DATABASE_ID')) {
  throw new Error('Le marqueur D1 attendu est absent de wrangler.jsonc.');
}

const production = source.replace('REPLACE_WITH_D1_DATABASE_ID', databaseId);
await writeFile(new URL('../wrangler.production.jsonc', import.meta.url), production, {
  encoding: 'utf8',
  mode: 0o600
});
