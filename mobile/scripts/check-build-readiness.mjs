import { readFileSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { parseEnv } from 'node:util';
import { fileURLToPath } from 'node:url';
import { assessBuildReadiness, EAS_CLI_VERSION } from './build-readiness.mjs';

const args = process.argv.slice(2);
const platformIndex = args.indexOf('--platform');
const platform = platformIndex >= 0 ? args[platformIndex + 1] : 'android';
if (!['ios', 'android'].includes(platform) || args.some((value, index) => !['--platform', '--check-session', '--json'].includes(value) && !(platformIndex >= 0 && index === platformIndex + 1))) {
  console.error('Usage: npm run build:check -- --platform ios|android [--check-session] [--json]');
  process.exit(2);
}
const cwd = fileURLToPath(new URL('../', import.meta.url));
let report;
try {
  const app = JSON.parse(readFileSync(new URL('../app.json', import.meta.url), 'utf8')).expo;
  const eas = JSON.parse(readFileSync(new URL('../eas.json', import.meta.url), 'utf8'));
  let env = {};
  // This is a local public-env check, not a claim to mirror the remote EAS env.
  for (const name of ['.env', '.env.local']) {
    const path = new URL(`../${name}`, import.meta.url);
    if (existsSync(path)) env = { ...env, ...parseEnv(readFileSync(path, 'utf8')) };
  }
  env = { ...env, ...process.env };
  let clean = false, authenticated = false;
  try { clean = execFileSync('git', ['status', '--porcelain'], { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim() === ''; } catch {}
  if (args.includes('--check-session')) {
    try {
      execFileSync('npm', ['exec', '--yes', `--package=eas-cli@${EAS_CLI_VERSION}`, '--', 'eas', 'whoami'], {
        cwd, env: { ...process.env, EXPO_NO_TELEMETRY: '1' }, timeout: 45000, stdio: ['ignore', 'pipe', 'pipe'],
      });
      authenticated = true;
    } catch { /* Do not print raw tool output or authentication data. */ }
  }
  report = assessBuildReadiness({ app, eas, env, platform, clean, authenticated });
} catch {
  // JSON/.env parse errors can include source contents, so redact them too.
  console.error('Не удалось прочитать конфигурацию сборки. Проверьте app.json, eas.json и локальные env-файлы. Значения не выведены.');
  process.exit(2);
}
if (args.includes('--json')) console.log(JSON.stringify(report, null, 2));
else {
  console.log(report.readyForBuildAttempt ? 'Локальные условия для попытки сборки выполнены.' : 'Сборка пока не готова:');
  for (const check of report.checks) if (!check.ok) console.log(`- ${check.message}`);
  console.log(report.signing);
  console.log(report.scope);
}
process.exitCode = report.readyForBuildAttempt ? 0 : 2;
