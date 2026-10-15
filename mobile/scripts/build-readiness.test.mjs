import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { assessBuildReadiness, EAS_CLI_VERSION, API_ORIGIN, SUPABASE_ORIGIN } from './build-readiness.mjs';
function fixture(platform = 'ios') {
  return { platform, clean: true, authenticated: true,
    app: { extra: { eas: { projectId: '11111111-1111-4111-8111-111111111111' } }, ios: { bundleIdentifier: 'com.lingoflow.mobile' }, android: { package: 'com.lingoflow.mobile' } },
    eas: { cli: { version: EAS_CLI_VERSION, requireCommit: true }, build: { preview: { distribution: 'internal' } } },
    env: { EXPO_PUBLIC_API_BASE_URL: API_ORIGIN, EXPO_PUBLIC_SUPABASE_URL: SUPABASE_ORIGIN, EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY: 'sb_publishable_testfixture1234' } };
}
test('valid local conditions permit an attempt, without signing approval', () => {
  for (const platform of ['ios', 'android']) {
    const result = assessBuildReadiness(fixture(platform));
    assert.equal(result.readyForBuildAttempt, true);
    assert.match(result.scope, /не подтверждаются/);
  }
});
test('missing project, session, public env and clean source block the attempt', () => {
  const result = assessBuildReadiness({ platform: 'ios' });
  assert.equal(result.readyForBuildAttempt, false);
  for (const id of ['expo-project', 'expo-session', 'committed-source', 'api-origin', 'supabase-origin', 'publishable-key-format']) assert.equal(result.checks.find((c) => c.id === id).ok, false);
});
test('stale CLI, wrong identifier and store distribution fail the beta check', () => {
  const input = fixture(); input.eas.cli.version = '>=16'; input.app.ios.bundleIdentifier = 'com.old.app'; input.eas.build.preview.distribution = 'store';
  const result = assessBuildReadiness(input);
  assert.equal(result.readyForBuildAttempt, false);
  assert.deepEqual(result.checks.filter((c) => !c.ok).map((c) => c.id), ['cli', 'internal-profile', 'application-id']);
});
test('unsafe or alternate URLs are rejected without leaking values', () => {
  for (const url of ['http://lingoflow-learn.vercel.app', API_ORIGIN + '/login/', API_ORIGIN + '?token=private-value', 'https://user:private-value@lingoflow-learn.vercel.app', 'https://example.com']) {
    const input = fixture(); input.env.EXPO_PUBLIC_API_BASE_URL = url;
    const result = assessBuildReadiness(input);
    assert.equal(result.readyForBuildAttempt, false);
    assert.ok(!JSON.stringify(result).includes(url));
    assert.ok(!JSON.stringify(result).includes('private-value'));
  }
});
test('secret keys, JWTs and placeholders cannot pass or leak', () => {
  for (const key of ['sb_secret_private-value', 'eyJhbGciOiJIUzI1NiJ9.private-value', 'YOUR_PUBLIC_PUBLISHABLE_KEY', 'sb_publishable_ci_contract_only']) {
    const input = fixture(); input.env.EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY = key;
    const result = assessBuildReadiness(input);
    assert.equal(result.readyForBuildAttempt, false);
    assert.ok(!JSON.stringify(result).includes(key));
  }
});
test('unknown platform or argument fails before accessing Expo', () => {
  for (const args of [['--platform', 'web'], ['--force'], ['--platform']]) {
    const result = spawnSync(process.execPath, [new URL('./check-build-readiness.mjs', import.meta.url).pathname, ...args], { encoding: 'utf8' });
    assert.equal(result.status, 2);
    assert.match(result.stderr, /Usage:/);
    assert.equal(result.stdout, '');
  }
});
