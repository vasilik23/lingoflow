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
