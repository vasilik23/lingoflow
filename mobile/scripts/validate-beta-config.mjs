import { readFileSync } from 'node:fs';
import { EAS_CLI_VERSION } from './build-readiness.mjs';

const eas = JSON.parse(readFileSync(new URL('../eas.json', import.meta.url), 'utf8'));
const app = JSON.parse(readFileSync(new URL('../app.json', import.meta.url), 'utf8')).expo;
const envExample = readFileSync(new URL('../.env.example', import.meta.url), 'utf8');

const fail = (message) => { throw new Error(message); };
if (eas.cli?.version !== EAS_CLI_VERSION) fail('EAS CLI must use the reviewed exact version.');
if (eas.cli?.appVersionSource !== 'remote' || eas.cli?.requireCommit !== true) fail('EAS must use remote versions and committed sources.');
if (eas.build?.preview?.distribution !== 'internal') fail('Preview must remain internal distribution.');
if (eas.build?.production?.distribution !== 'store' || eas.build?.production?.autoIncrement !== true) fail('Production must be store-only with auto-increment.');
if (!app.ios?.bundleIdentifier || !app.android?.package) fail('Stable mobile application identifiers are required.');
for (const name of ['EXPO_PUBLIC_API_BASE_URL', 'EXPO_PUBLIC_SUPABASE_URL', 'EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY']) {
  if (!envExample.includes(`${name}=`)) fail(`Missing ${name} contract.`);
}
if (/SERVICE_ROLE|DATABASE_URL|PASSWORD|SECRET/i.test(envExample)) fail('Public mobile env contract contains a server secret name.');
console.log('Mobile beta build configuration is valid.');
