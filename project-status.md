# Project Status — AI Assistant MVP

> Last updated: 2026-04-11

## Summary

The MVP is fully implemented and deployed to the dev environment in **live provider mode**. All development phases 1-9 are complete. Lambda is live behind API Gateway with `MOCK_PROVIDER_MODE=false`, all three Secrets Manager secrets are populated with live credentials, and the Cognito hosted UI is provisioned. We are in Stage 4 (QA Validation on Dev) with one remaining infrastructure fix in flight: the Cognito app client's `callback_urls` are being updated (uncommitted terraform.tfvars change from last session — DevOps to commit and push). Once CI/CD applies that change, the Cognito OAuth redirect will work and Eric can execute the T-12 manual smoke test followed by the live provider tests (T-16, T-17).

## What We Just Completed

- 2026-04-11 — T-15: Lambda redeployed in live provider mode (`MOCK_PROVIDER_MODE=false`)
- 2026-04-10 — T-14: Secrets Manager populated with live credentials (KMS encrypted)
- 2026-04-10 — T-13: Live provider credentials confirmed in `backend/.env.local`
- 2026-04-10 — T-11: `mobile/.env` created with Cognito domain and API URL
- 2026-04-10 — T-10: Cognito hosted UI domain provisioned (`ai-assistant-dev.auth.us-east-1.amazoncognito.com`)
- 2026-04-08 — Lambda deployed to dev environment (mock mode), CI/CD pipeline green (122 tests)

## What's In Progress

Nothing — all infrastructure is live. Waiting on Eric to run the T-12 manual smoke test.

## What's Coming Next

1. **Eric (human action)** — T-12: Run manual smoke test through Expo mobile app (sign-in → chat → proposal → approve/reject). All blockers resolved — steps in `test-signoff.md` Phase 4.
2. **QA Engineer** — T-16: Provider OAuth flows (Google + Microsoft) via `scripts/start-provider-auth.ps1`
3. **QA Engineer** — T-17: Full live end-to-end test + Stage 4 sign-off in `test-signoff.md`
4. **DevOps Engineer** — T-18: Staging CI/CD pipeline (only after Stage 4 sign-off)

## Blockers

None — all infrastructure blockers resolved. T-12 awaits Eric's manual execution.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Google/Microsoft OAuth app not registered for dev redirect URIs | M | H | Eric to verify redirect URI registration in Google/Microsoft developer consoles during T-16 |
| Staging AWS infrastructure does not yet exist (IAM role, S3 bucket) | L | M | T-18 covers this; not needed until Stage 4 QA sign-off is complete |
| Production go-live blocked if staging reveals systemic issues | L | H | Full live provider test suite in Stage 4 reduces staging risk |
| `mock_provider_mode` hardcoded in deploy-dev.yml | L | M | T-18 refactors this to a GitHub Actions variable before staging pipeline is built |
