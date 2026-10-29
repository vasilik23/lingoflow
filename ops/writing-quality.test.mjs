import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {evaluate, fixturePath} from './writing-quality.mjs';

const dataset = JSON.parse(fs.readFileSync(fixturePath, 'utf8'));
const review = errors => ({errors, next_step: 'Review the task requirements.'});
const edit = (quote, correction) => ({quote, correction, explanation: 'Check the construction.'});
const input = runs => ({dataset_version: 1, model: 'synthetic-test', reasoning_effort: 'medium', runs});
const run = (case_id, errors, trial = 0) => ({case_id, language: 'en', trial, review: review(errors)});

test('detects the observed wrong case and does not confuse a correct inflection with its prefix', () => {
  const bad = evaluate(input([run('class-error', [edit('na lekcja', 'na lekcję')])]));
  assert(bad.runs[0].issues.some(issue => issue.kind === 'forbidden_edit'));
  const good = evaluate(input([run('participation-error', [edit('uczestniczyć w zajęcia', 'uczestniczyć w zajęciach')])]));
  assert.equal(good.runs[0].checks_passed, true);
  assert.equal(good.status, 'insufficient_coverage');
  assert.equal(good.quality_accepted, false);
});
test('accepts longer exact quotations and allowed alternative correction', () => {
  const report = evaluate(input([run('request-error', [edit('Bardzo proszę o materiałów z lekcji', 'Bardzo proszę o przesłanie materiałów z lekcji')])]));
  assert.equal(report.runs[0].checks_passed, true);
});
test('detects invented quotations, unchanged edits and false positives on correct controls', () => {
  const report = evaluate(input([run('class-correct', [edit('not in draft', 'different'), edit('Proszę przesłać materiały.', 'Proszę przesłać materiały.')])]));
  const kinds = report.runs[0].issues.map(issue => issue.kind);
  for (const kind of ['quote_not_in_draft', 'unchanged_correction', 'clean_control_flagged_for_review']) assert(kinds.includes(kind));
});
test('repeats never inflate coverage and exact duplicate trials are rejected', () => {
  const runs = [run('class-correct', []), run('class-correct', [], 1)];
  assert.equal(evaluate(input(runs)).coverage.covered, 1);
  assert.throws(() => evaluate(input([runs[0], runs[0]])), /Invalid evaluation input/);
});
test('flags suspect advice for human interpretation instead of treating string matching as linguistic truth', () => {
  const candidate = run('class-correct', []);
  candidate.review.next_step = 'Avoid the phrase być zainteresowanym w.';
  const report = evaluate(input([candidate]));
  assert.equal(report.runs[0].issues[0].kind, 'advice_requires_manual_review');
});
test('full synthetic coverage still does not grant independent quality acceptance', () => {
  const runs = dataset.cases.flatMap(item => dataset.languages.map(language => ({
    case_id: item.id, language,
    review: review(item.expected_edits.map(expected => edit(expected.quote, expected.accepted[0]))),
  })));
  const report = evaluate(input(runs));
  assert.equal(report.status, 'checks_passed');
  assert.equal(report.coverage.covered, 24);
  assert.equal(report.quality_accepted, false);
  assert(!JSON.stringify(report).includes(dataset.cases[0].draft));
});
test('rejects malformed reports rather than assigning a quality score', () => {
  for (const value of [{}, {...input([])}, input([run('unknown', [])]), {...input([run('class-correct', [])]), reasoning_effort: 'unbounded'}])
    assert.throws(() => evaluate(value), /Invalid evaluation input/);
});

test('flags observed incompatible nested corrections without disclosing review text', () => {
  const report = evaluate(input([run('class-error', [
    edit('na lekcja', 'na lekcję'),
    edit('jutro nie mogę być na lekcja', 'jutro nie będę na lekcji'),
  ])]));
  assert(report.runs[0].issues.some(issue => issue.kind === 'overlapping_edits_require_manual_review'));
  assert(!JSON.stringify(report).includes('jutro'));
});
test('equivalent narrow and broad corrections and separate changes do not conflict', () => {
  const report = evaluate(input([run('class-error', [
    edit('na lekcja', 'na lekcji'),
    edit('jutro nie mogę być na lekcja', 'jutro nie mogę być na lekcji'),
    edit('jutro', 'dzisiaj'),
  ])]));
  assert.equal(report.runs[0].checks_passed, true);
});
test('flags competing insertions and skips ambiguous repeated quotations', () => {
  const local = {...dataset, cases: [{id: 'local', draft: 'ab ab cd', expected_edits: [], expect_no_errors: false}]};
  const check = errors => evaluate(input([run('local', errors)]), local).runs[0].issues;
  assert(check([edit('cd', 'cXd'), edit('cd', 'cYd')]).some(issue => issue.kind === 'overlapping_edits_require_manual_review'));
  assert.equal(check([edit('ab', 'ax'), edit('ab', 'ay')]).length, 0);
});

test('inspects criterion feedback for mixed alphabets without flagging separate quoted Polish words', () => {
  const candidate = run('class-correct', []);
  candidate.language = 'ru';
  candidate.review.criteria = Object.fromEntries(['content', 'structure', 'grammar', 'vocabulary'].map(key =>
    [key, {feedback: 'Правильная форма: zajęciach.'}]));
  assert.equal(evaluate(input([candidate])).runs[0].checks_passed, true);
  candidate.review.criteria.grammar.feedback = 'Правильная форма: zajęciaх.';
  assert(evaluate(input([candidate])).runs[0].issues.some(issue => issue.kind === 'mixed_script_token_requires_manual_review'));
});
test('criterion advice participates in language and known advice checks', () => {
  const candidate = run('class-correct', []);
  candidate.review.criteria = Object.fromEntries(['content', 'structure', 'grammar', 'vocabulary'].map(key =>
    [key, {feedback: 'Practice again.'}]));
  candidate.review.criteria.grammar.feedback = 'Совет: być zainteresowanym w.';
  const kinds = evaluate(input([candidate])).runs[0].issues.map(issue => issue.kind);
  assert(kinds.includes('unexpected_cyrillic_in_explanation'));
  assert(kinds.includes('advice_requires_manual_review'));
  candidate.review.criteria = {grammar: {feedback: 'Incomplete'}};
  assert.throws(() => evaluate(input([candidate])), /Invalid evaluation input/);
});

test('replays captured synthetic baseline and reproduces the published findings without network access', () => {
  const baseline = JSON.parse(fs.readFileSync(new URL('./fixtures/writing-quality-medium-baseline-v1.json', import.meta.url), 'utf8'));
  const {evaluated_at, runtime_code, evaluator_revision, ...expected} = JSON.parse(fs.readFileSync(
    new URL('../docs/ai-writing-quality-result-2026-10-29-second.json', import.meta.url), 'utf8'));
  assert.equal(baseline.provenance.synthetic_only, true);
  assert(baseline.runs.every(item => item.review.criteria && item.runtime_commit && item.source_report));
  assert.deepEqual(evaluate(baseline), expected);
});

test('feedback bounds match Django Unicode character counts at 1500 and 600 characters', () => {
  const candidate = run('class-correct', []);
  candidate.review.criteria = Object.fromEntries(['content', 'structure', 'grammar', 'vocabulary'].map(key =>
    [key, {feedback: '🙂'.repeat(1500)}]));
  candidate.review.next_step = '🙂'.repeat(600);
  assert.equal(evaluate(input([candidate])).runs[0].checks_passed, true);
  candidate.review.criteria.grammar.feedback += 'x';
  assert.throws(() => evaluate(input([candidate])), /Invalid evaluation input/);
  candidate.review.criteria.grammar.feedback = 'Valid.';
  candidate.review.next_step += 'x';
  assert.throws(() => evaluate(input([candidate])), /Invalid evaluation input/);
});

test('error fields accept 600 Unicode characters and reject the 601st', () => {
  const candidate = run('class-error', [edit('na lekcja', 'na lekcji')]);
  candidate.review.errors[0].explanation = '🙂'.repeat(600);
  assert.equal(evaluate(input([candidate])).runs[0].checks_passed, true);
  candidate.review.errors[0].explanation += 'x';
  assert.throws(() => evaluate(input([candidate])), /Invalid evaluation input/);
});
