import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

export const fixturePath = fileURLToPath(new URL('./fixtures/writing-quality-v1.json', import.meta.url));
const normalize = value => value.normalize('NFC').replace(/\s+/gu, ' ').trim().toLocaleLowerCase('pl');
// Django validates Python string length in Unicode code points, not UTF-16 units.
const characterCount = value => Array.from(value).length;
function contains(text, phrase) {
  const escaped = normalize(phrase).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp(`(?<![\\p{L}\\p{N}_])${escaped}(?![\\p{L}\\p{N}_])`, 'u').test(normalize(text));
}
function requireValue(ok) { if (!ok) throw new Error('Invalid evaluation input'); }

// A review flag, not a grammatical verdict: overlapping rewrites may be valid
// alternatives. Only compare quotes with an unambiguous location in the draft.
function conflictingEdits(draft, errors) {
  const changes = errors.flatMap(error => {
    const offset = draft.indexOf(error.quote);
    if (offset < 0 || draft.indexOf(error.quote, offset + 1) >= 0) return [];
    const {quote, correction} = error;
    let prefix = 0, suffix = 0;
    while (prefix < Math.min(quote.length, correction.length) && quote[prefix] === correction[prefix]) prefix++;
    while (suffix < Math.min(quote.length, correction.length) - prefix &&
      quote[quote.length - 1 - suffix] === correction[correction.length - 1 - suffix]) suffix++;
    if (prefix === quote.length && prefix === correction.length) return [];
    return [{start: offset + prefix, end: offset + quote.length - suffix,
      replacement: correction.slice(prefix, correction.length - suffix)}];
  });
  return changes.some((a, i) => changes.slice(i + 1).some(b => {
    if (a.start === b.start && a.end === b.end && a.replacement === b.replacement) return false;
    if (a.start === a.end || b.start === b.end)
      return a.start === b.start || (a.start < b.end && b.start < a.end);
    return a.start < b.end && b.start < a.end;
  }));
}

export function evaluate(input, dataset = JSON.parse(fs.readFileSync(fixturePath, 'utf8'))) {
  requireValue(input?.dataset_version === dataset.version && typeof input.model === 'string' &&
    input.model.length > 0 && input.model.length <= 100 && ['low', 'medium', 'high'].includes(input.reasoning_effort) &&
    Array.isArray(input.runs) && input.runs.length > 0 && input.runs.length <= 100);
  const cases = new Map(dataset.cases.map(item => [item.id, item]));
  const seen = new Set(), covered = new Set();
  const runs = input.runs.map(run => {
    const item = cases.get(run.case_id), review = run.review;
    const trial = run.trial ?? 0;
    requireValue(item && dataset.languages.includes(run.language) && Number.isSafeInteger(trial) && trial >= 0 && trial < 100 &&
      !seen.has(`${item.id}:${run.language}:${trial}`));
    seen.add(`${item.id}:${run.language}:${trial}`);
    covered.add(`${item.id}:${run.language}`);
    requireValue(review && Array.isArray(review.errors) && review.errors.length <= 6 && typeof review.next_step === 'string' &&
      review.next_step.length > 0 && characterCount(review.next_step) <= 600);
    const issues = [];
    for (const error of review.errors) {
      requireValue(error && ['quote', 'correction', 'explanation'].every(key =>
        typeof error[key] === 'string' && error[key].length > 0 && characterCount(error[key]) <= 600));
      if (!item.draft.includes(error.quote)) issues.push({kind: 'quote_not_in_draft'});
      if (normalize(error.quote) === normalize(error.correction)) issues.push({kind: 'unchanged_correction'});
    }
    if (conflictingEdits(item.draft, review.errors)) issues.push({kind: 'overlapping_edits_require_manual_review'});
    for (const expected of item.expected_edits) {
      const matches = review.errors.filter(error => item.draft.includes(error.quote) && contains(error.quote, expected.quote));
      if (!matches.some(error => expected.accepted.some(value => contains(error.correction, value))))
        issues.push({kind: 'required_edit_not_demonstrated', check: expected.id});
      if (matches.some(error => expected.forbidden.some(value => contains(error.correction, value))))
        issues.push({kind: 'forbidden_edit', check: expected.id});
    }
    if (item.expect_no_errors && review.errors.length) issues.push({kind: 'clean_control_flagged_for_review'});
    const criteriaFeedback = [];
    if (review.criteria !== undefined) {
      requireValue(review.criteria && typeof review.criteria === 'object' && !Array.isArray(review.criteria) &&
        Object.keys(review.criteria).length === 4);
      for (const key of ['content', 'structure', 'grammar', 'vocabulary']) {
        const feedback = review.criteria[key]?.feedback;
        requireValue(typeof feedback === 'string' && feedback.length > 0 && characterCount(feedback) <= 1500);
        criteriaFeedback.push(feedback);
      }
    }
    const advice = [review.next_step, ...review.errors.map(error => error.explanation), ...criteriaFeedback].join('\n');
    if (dataset.manual_advice_flags.some(value => contains(advice, value))) issues.push({kind: 'advice_requires_manual_review'});
    if (run.language !== 'ru' && /[А-Яа-яЁё]/u.test(advice)) issues.push({kind: 'unexpected_cyrillic_in_explanation'});
    if ((advice.match(/[\p{L}\p{M}]+/gu) ?? []).some(word => /\p{Script=Latin}/u.test(word) && /\p{Script=Cyrillic}/u.test(word)))
      issues.push({kind: 'mixed_script_token_requires_manual_review'});
    return {case_id: item.id, language: run.language, trial, checks_passed: issues.length === 0, issues};
  });
  const required = dataset.cases.flatMap(item => dataset.languages.map(language => `${item.id}:${language}`));
  const missing = required.filter(key => !covered.has(key));
  return {
    dataset_version: dataset.version,
    model: input.model,
    reasoning_effort: input.reasoning_effort,
    runs,
    coverage: {covered: covered.size, expected: required.length, missing},
    status: runs.some(run => !run.checks_passed) ? 'findings' : missing.length ? 'insufficient_coverage' : 'checks_passed',
    quality_accepted: false,
  };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    requireValue(process.argv.length === 3);
    requireValue(fs.statSync(process.argv[2]).size <= 1024 * 1024);
    const report = evaluate(JSON.parse(fs.readFileSync(process.argv[2], 'utf8')));
    console.log(JSON.stringify(report, null, 2));
    if (report.status !== 'checks_passed') process.exitCode = 1;
  } catch {
    // Never echo source input: it could contain accidental personal submissions.
    console.error('Invalid evaluation input. Use a bounded synthetic-only report matching writing-quality-v1.');
    process.exitCode = 2;
  }
}
