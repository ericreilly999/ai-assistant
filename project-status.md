# Project Status — integreat

> Last updated: 2026-04-18

## Summary

Stage 4 (QA Validation on Dev) is in progress. All pending PRs merged: coverage 89% (PR #16), thinking-tag stripping (PR #15), integreat rebrand (PR #14), P1 incident remediation — API URL fix + $default catch-all + plan smoke test (PRs #17/#18). 413 tests passing. Lambda redeploying from latest main push.

## What We Just Completed

- 2026-04-18 — PR #18 merged: multi-block thinking regression test + POST /plan smoke test in CI (non-blocking pending CI Cognito service account)
- 2026-04-18 — PR #17 merged: EXPO_PUBLIC_API_BASE_URL now derived from Terraform outputs in CI; $default catch-all route added to API Gateway
- 2026-04-18 — P1 incident resolved: mobile/.env EXPO_PUBLIC_API_BASE_URL missing /dev suffix since 2026-04-08 — all POST /plan requests were returning API Gateway "Not Found". Fixed locally + CI prevents recurrence.
- 2026-04-18 — PR #16 merged: test coverage raised to 89% (was 67%) — 408 tests, 4 new test modules
- 2026-04-18 — PR #15 merged: `<thinking>` tag stripping — Nova Pro inline XML no longer leaks to mobile UI
- 2026-04-18 — PR #14 merged: integreat display rebrand (app name, screen headers, system prompt, README)
- 2026-04-18 — Zombie infra teardown: 8 ECR repos (us-west-2) + orphaned EIP deleted — ~$20.60/month saved

## What's In Progress

Nothing — all PRs merged, Lambda redeploying from main push.

## What's Coming Next

1. **Eric (human action)** — T-12: Manual smoke test. `mobile/.env` fixed, restart Expo with `--clear`. Sign-in → chat → proposal → approve/reject → sign-out. Verify "integreat" branding and no `<thinking>` leakage.
2. **QA Engineer** — T-16: Provider OAuth flows (Google + Microsoft) — after T-12 passes
3. **QA Engineer** — T-17: Full live end-to-end test + Stage 4 sign-off
4. **DevOps Engineer** — T-18: Staging CI/CD pipeline (after Stage 4 sign-off)

## Blockers

None.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| POST /plan CI smoke test is non-blocking until CI Cognito service account provisioned | M | L | Documented TODO in deploy-dev.yml; T-17 full live test covers this manually |
| Google/Microsoft OAuth app not registered for dev redirect URIs | M | H | Eric to verify redirect URI registration in Google/Microsoft developer consoles during T-16 |
| Staging AWS infrastructure does not yet exist (IAM role, S3 bucket) | L | M | T-18 covers this; not needed until Stage 4 QA sign-off is complete |
| Production go-live blocked if staging reveals systemic issues | L | H | Full live provider test suite in Stage 4 reduces staging risk |
