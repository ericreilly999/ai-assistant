# Project Status — integreat

> Last updated: 2026-04-19

## Summary

Stage 4 (QA Validation on Dev) is in progress. Lambda is now fully deployed with all code merged to main — Phase 13 agent loop, thinking-tag stripping, integreat rebrand, hardened regex, and P1 incident remediation are all live. Root cause of the 10-day stale Lambda was identified: `deploy-dev.yml` used `pip install pytest pytest-cov` (no boto3), test job failed, and the `needs:` dependency blocked `terraform apply` on every push since PR #16 merged. Fixed in PR #20. Lambda SHA confirmed updated.

## What We Just Completed

- 2026-04-19 — PR #20 merged: `deploy-dev.yml` pip fix (`backend[test]`) + post-deploy SHA verification step — CI deploy pipeline unblocked
- 2026-04-19 — Lambda redeployed manually by DevOps (`lZH91J…` → `Lv2osQ…`) — Phase 13 + thinking-tag fix + rebrand now live
- 2026-04-18 — PR #19 merged: thinking-tag regex hardened (`\b[^>]*` + `re.IGNORECASE`) — handles `<thinking type="...">` and case variants
- 2026-04-18 — PR #18 merged: multi-block thinking regression test + POST /plan smoke test (non-blocking)
- 2026-04-18 — PR #17 merged: EXPO_PUBLIC_API_BASE_URL derived from Terraform outputs in CI; $default catch-all route added
- 2026-04-18 — P1 resolved: mobile/.env missing /dev suffix — POST /plan was returning API Gateway "Not Found"
- 2026-04-18 — PRs #14/#15/#16 merged: integreat rebrand, thinking-tag stripping, 89% test coverage

## What's In Progress

Nothing — Lambda is live, CI pipeline is unblocked.

## What's Coming Next

1. **Eric (human action)** — T-12: Manual smoke test. Lambda is live with all fixes. Restart Expo with `--clear`, sign in, chat, verify "integreat" branding and no `<thinking>` leakage.
2. **DevOps Engineer** — Checkov cleanup PR: `CKV_AWS_356` (IAM wildcard resource), `CKV_AWS_309` ($default route unauthenticated), + 9 other pre-existing findings. Required before staging promotion.
3. **QA Engineer** — T-16: Provider OAuth flows (Google + Microsoft) — after T-12 passes
4. **QA Engineer** — T-17: Full live end-to-end test + Stage 4 sign-off
5. **DevOps Engineer** — T-18: Staging CI/CD pipeline (after Stage 4 sign-off)

## Blockers

None.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Checkov findings (CKV_AWS_356 IAM wildcard, CKV_AWS_309 unauthenticated $default route) — pre-existing, failing terraform-validate in CI | M | M | DevOps cleanup PR before staging promotion |
| POST /plan CI smoke test non-blocking until CI Cognito service account provisioned | M | L | Documented TODO in deploy-dev.yml; T-17 full live test covers manually |
| Google/Microsoft OAuth app not registered for dev redirect URIs | M | H | Eric to verify redirect URI registration during T-16 |
| Staging AWS infrastructure does not yet exist (IAM role, S3 bucket) | L | M | T-18 covers this; not needed until Stage 4 QA sign-off |
