// Operator-initiated GET diagnostics. No background collector or learner telemetry.
import {performance} from 'node:perf_hooks';
import {open, realpath, stat} from 'node:fs/promises';
import {constants} from 'node:fs';
import {dirname, resolve, relative} from 'node:path';
import {fileURLToPath} from 'node:url';

export const ORIGIN = 'https://lingoflow-learn.vercel.app';
const ROUTES = Object.freeze({intro: '/start/', login: '/login/', sources: '/sources/',
  today: '/', course: '/course/', reading: '/reading/'});
const PUBLIC = ['intro', 'login', 'sources'];
const AUTHENTICATED = ['today', 'course', 'reading'];
const fail = () => { throw new Error('Invalid performance evidence'); };
const exact = (value, keys) => {
  if (!value || typeof value !== 'object' || Array.isArray(value)
      || Object.keys(value).sort().join(',') !== [...keys].sort().join(',')) fail();
};
const milliseconds = value => Number.isFinite(value) && value >= 0 && value <= 120000;
export function percentile(values, fraction) {
  if (!Array.isArray(values) || !values.length || values.some(v => !milliseconds(v))
      || !Number.isFinite(fraction) || fraction <= 0 || fraction > 1) fail();
  return Math.ceil([...values].sort((a,b) => a-b)[Math.ceil(values.length * fraction)-1]);
}

export function appDuration(header) {
  if (typeof header !== 'string') return null;
  const matches = [...header.matchAll(/(?:^|,)\s*app\s*;\s*dur=(\d+(?:\.\d+)?)\s*(?=,|$)/g)];
  if (matches.length !== 1) return null;
  const value = Number(matches[0][1]);
  return milliseconds(value) ? value : null;
}

export function summarize(evidence) {
  exact(evidence, ['version', 'commit', 'context', 'samples']);
  if (evidence.version !== 1 || typeof evidence.commit !== 'string' || !/^[a-f0-9]{40}$/.test(evidence.commit)
      || !['public', 'authenticated'].includes(evidence.context)
      || !Array.isArray(evidence.samples) || !evidence.samples.length || evidence.samples.length > 60) fail();
  const allowed = evidence.context === 'public' ? PUBLIC : AUTHENTICATED;
  const groups = new Map();
  for (const s of evidence.samples) {
    exact(s, ['route', 'run', 'status', 'headers_ms', 'total_ms', 'app_ms', 'error']);
    if (!allowed.includes(s.route) || !Number.isInteger(s.run) || s.run < 1 || s.run > 10) fail();
    const samples = groups.get(s.route) || [];
    if (samples.some(x => x.run === s.run)) fail();
    if (s.error === 'transport') {
      if ([s.status, s.headers_ms, s.total_ms, s.app_ms].some(x => x !== null)) fail();
    } else if (s.error !== null || !Number.isInteger(s.status) || s.status < 200 || s.status > 599
        || !milliseconds(s.headers_ms) || !milliseconds(s.total_ms) || s.total_ms < s.headers_ms
        || (s.app_ms !== null && !milliseconds(s.app_ms))) fail();
    samples.push(s); groups.set(s.route, samples);
  }
  const metric = values => values.length ? {count: values.length, p50_ms: percentile(values, .5), p95_ms: percentile(values, .95)} : null;
  const stats = samples => ({
    attempts: samples.length,
    http_responses: samples.filter(x => x.status !== null).length,
    successful: samples.filter(x => x.status === 200).length,
    redirects: samples.filter(x => x.status >= 300 && x.status < 400).length,
    client_errors: samples.filter(x => x.status >= 400 && x.status < 500).length,
    server_errors: samples.filter(x => x.status >= 500).length,
    transport_errors: samples.filter(x => x.error === 'transport').length,
    // Successful-page latency only; failures remain in explicit counters.
    headers: metric(samples.filter(x => x.status === 200).map(x => x.headers_ms)),
    total: metric(samples.filter(x => x.status === 200).map(x => x.total_ms)),
    app: metric(samples.filter(x => x.status === 200 && x.app_ms !== null).map(x => x.app_ms)),
  });
  return {version: 1, commit: evidence.commit, commit_source: 'operator_supplied', context: evidence.context,
    kind: 'operator_get_sample', field_metrics: false, beta_readiness_evidence: false,
    routes: [...groups].map(([route, samples]) => {
      samples.sort((a,b) => a.run-b.run);
      if (samples.some((x,i) => x.run !== i+1)) fail();
      return {route, first: stats(samples.slice(0,1)), subsequent: stats(samples.slice(1)), all: stats(samples)};
    }), limits: ['First request is not proof of a cold start; subsequent requests are not proof of a warm instance.',
      'Operator GET sample, not participant telemetry, rendering time, LCP or INP.',
      'Success latency excludes failed requests; redirects and failures are counted separately.',
      'Commit must be checked against the actual deployment before and after capture. No release approval.']};
}

export async function probe({commit, context = 'public', runs = 3, fetcher = fetch}) {
  if (typeof commit !== 'string' || !/^[a-f0-9]{40}$/.test(commit) || !['public','authenticated'].includes(context)
      || !Number.isInteger(runs) || runs < 2 || runs > 10) fail();
  const started_at = new Date().toISOString();
  const samples = [];
  for (const route of context === 'public' ? PUBLIC : AUTHENTICATED) {
    for (let run = 1; run <= runs; run++) {
      const start = performance.now();
      try {
        const response = await fetcher(ORIGIN + ROUTES[route], {
          method: 'GET', redirect: 'manual', signal: AbortSignal.timeout(15000),
          headers: {'Accept-Language': 'ru', 'User-Agent': 'LingoFlow-Operator-Performance/1'},
        });
        const headers_ms = performance.now() - start;
        const app_ms = appDuration(response.headers.get('server-timing'));
        // Consume bounded bytes, never decode or persist page content or private headers.
        let size = 0;
        try {
          for await (const chunk of response.body || []) {
            size += chunk.length; if (size > 5 * 1024 * 1024) throw new Error('Response too large');
          }
        } catch { throw new Error('Transport failed'); }
        samples.push({route, run, status: response.status, headers_ms,
          total_ms: performance.now() - start, app_ms, error: null});
      } catch {
        samples.push({route, run, status: null, headers_ms: null, total_ms: null, app_ms: null, error: 'transport'});
      }
    }
  }
  return {evidence: {version: 1, commit, context, samples}, report: {
    ...summarize({version:1, commit, context, samples}), started_at, finished_at: new Date().toISOString(),
  }};
}

export async function writeReport(path, report) {
  const dir = await realpath(dirname(resolve(path)));
  const repo = await realpath(fileURLToPath(new URL('..', import.meta.url)));
  const rel = relative(repo, dir);
  if ((rel === '' || (!rel.startsWith('..' + '/') && rel !== '..'))
      || (await stat(dir)).mode & 0o077) fail();
  const file = await open(resolve(path), constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL, 0o600);
  try { await file.writeFile(JSON.stringify(report, null, 2) + '\n'); } finally { await file.close(); }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const [commit, output, ...extra] = process.argv.slice(2);
    if (!output || extra.length) fail();
    const {report} = await probe({commit});
    await writeReport(output, report);
    console.log(JSON.stringify({output_written: true, context: report.context,
      attempts: report.routes.reduce((n,r) => n+r.all.attempts, 0)}));
    if (report.routes.some(r => r.all.successful !== r.all.attempts)) process.exitCode = 2;
  } catch { console.error('Performance probe failed; no request details printed'); process.exitCode = 1; }
}
