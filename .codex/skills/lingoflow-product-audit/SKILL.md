---
name: lingoflow-product-audit
description: Audit LingoFlow as product owner, designer and QA using real learner journeys, reproducible bug evidence and a prioritized improvement backlog. Use for a requested product/UI/quality review, not routine implementation.
---

# LingoFlow product audit

Deliver an evidence-based audit of the Django application in `backend/` and a
small ordered backlog. Read `AGENTS.md`, README future stages and the current
improvements list first; preserve existing exam priorities and distinguish
previously known dependencies from new findings.

## Observe before proposing

Use production for public read-only journeys and a local browser with isolated
fixtures for private journeys when a valid authorized test account is unavailable.
Record commit, date, environment, browser, widths, languages, mocked services
and untested devices. Never classify fixture storage/Auth failures as production
bugs. Do not read secrets, create accounts, send messages, change production data
or enable AI/monitoring just to run an audit. Prior authorization still applies.

Walk through guest discovery/demo/login; Today → recommended lesson → explanation
→ saved result; course/filter/search; reading → dictionary → review; practice/B1
→ answers/timer/review/history; profile/settings/privacy/security. Adapt coverage
to the request and available access; mark every unrun journey explicitly. A page
visit is not a verified end-to-end flow or proof of persistence.

Check compact/mobile (320 or 390 px) and desktop (1440 px), light/dark where
relevant, and RU/PL/EN at representative steps. Use actual keyboard interaction,
refresh/Back, empty/error states and browser console. Exercise save failure,
offline, delayed requests and timer expiration only in isolated local fixtures.
Use synthetic text/audio, never a real learner's submission. Desktop Chromium,
emulated viewport and DOM tests are not physical Safari/microphone/VoiceOver
acceptance. Avoid destructive account operations during a review.

## Three lenses, one finding

- **PO:** Can a learner identify the next useful action, finish it and understand
  the result? Check actual availability of audio/AI, honest progress/score claims,
  goal alignment, continuation and recovery. Prefer improvements with demonstrated
  learning value over another cosmetic or speculative feature.
- **Designer:** Inspect hierarchy, duplicate navigation/settings, visible feedback,
  consistent buttons/filters, small-screen reflow, focus visibility, form labels,
  menu/dialog dismissal and whether sticky controls obscure content. Distinguish
  personal preference from a usability problem observed in a task.
- **QA:** Reproduce faults with exact steps and actual vs expected behavior;
  inspect the relevant code to locate likely causes. Check ownership, stale state,
  duplicate submission, save failure and timeout on authorized/local fixtures.
  Do not infer security, persistence or audio success from a screenshot.

Consult authoritative references when making normative claims. Start with
[WCAG 2.2](https://www.w3.org/TR/WCAG22/) for keyboard, labels, contrast, reflow,
focus and language of content, and
[Nielsen usability heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/)
for status visibility, consistency, error recovery and cognitive load.
Link the relevant criterion; do not claim WCAG certification from a spot audit,
invent an industry standard or treat a heuristic as a conformance requirement.

## Report and roadmap

Write `docs/product-audit-YYYY-MM-DD.md` (append a clearly scoped new run if it
already exists). Include a coverage matrix, passed observations, findings and
manual/external dependencies. Do not copy tokens, personal payloads or browser
state into the report; use relative source links and sanitized screenshots only
when they materially demonstrate the finding.

Each finding needs a stable ID, bug/improvement/verification-gap classification,
PO/Designer/QA lens, priority, affected journey, evidence and environment,
reproduction steps (for bugs), expected/observed behavior, suggested change,
acceptance criterion, effort/dependency and source where useful. Severity and
confidence are separate: an unrun test is a gap, not a confirmed bug.

Prioritize P0 for demonstrated data/security loss or a core-flow outage, P1 for
blocked learning/assessment, P2 for substantial usability/accessibility friction,
P3 for polish. Adjust to real reach/impact and explain uncertain scope. Merge
cross-role duplicates into one item. Reuse existing IDs for known open work;
never reopen fixed items without a reproducible regression. Do not force a quota
of bugs or fill the report with generic recommendations.

Add only actionable future instructions to README's roadmap, with links to
findings. Keep completed work in the ready section and preserve existing human
recording, real-device, legal and production-activation dependencies. Lead the
final answer with the most consequential confirmed findings and the next useful
step, plus coverage limits.

An audit request authorizes inspection, report and roadmap updates; it does not
by itself authorize implementing every suggestion. If the user also requests
fixes, use the project's development/testing/Git skills and existing publication
authorization. Run required release checks before publishing any changes; test
actual affected flows, not just generated wording. For this skill's own changes,
use skill-creator validation and a real audit run; do not add generic helper code
or telemetry unless the task needs it.
