# Project Status — AI Assistant MVP

> Last updated: 2026-04-18

## Summary

Stage 4 (QA Validation on Dev) is actively in progress. During the T-12 manual smoke test, Eric encountered "an error was encountered" on the Cognito hosted UI sign-in page. Root cause identified: `app.json` has `"scheme": "ai-assistant"` set (added during the Expo SDK 54 upgrade), which causes `AuthSession.makeRedirectUri()` to generate `ai-assistant://` as the OAuth redirect URI — but `ai-assistant://` was never registered in Cognito's callback URLs. Only `exp://` URIs are registered. This is a two-part fix: infrastructure (register `ai-assistant://` in Cognito via Terraform) and application code (make the redirect URI scheme explicit in the auth code). Application Engineer and QA Engineer have been invoked to fix the code, cover it with tests, and perform a postmortem on the test gap. DevOps will be invoked to apply the Terraform change once the app fix is on a PR.

## What We Just Completed

- 2026-04-18 — README.md fully rewritten with accurate architecture, CI/CD, branching, and config documentation (PR #6 open)
- 2026-04-11 — T-15: Lambda redeployed in live provider mode (`MOCK_PROVIDER_MODE=false`)
- 2026-04-11 — Cognito callback URLs fixed (Deploy #5) — `exp://` redirect URIs registered
- 2026-04-10 — T-14: Secrets Manager populated with live credentials (KMS encrypted)
- 2026-04-10 — T-13: Live provider credentials confirmed in `backend/.env.local`
- 2026-04-10 — T-11: `mobile/.env` created with Cognito domain and API URL
- 2026-04-10 — T-10: Cognito hosted UI domain provisioned
- 2026-04-08 — Lambda deployed to dev environment, CI/CD pipeline green (122 tests)

## What's In Progress

- **Application Engineer** — fixing `makeRedirectUri()` scheme handling in mobile auth; PR to follow
- **QA Engineer** — postmortem on test gap + writing test coverage for auth redirect URI registration

## What's Coming Next

1. **DevOps Engineer** — register `ai-assistant://` in Cognito callback URLs (Terraform + GitHub Actions variable update), triggered once App Engineer PR is reviewed
2. **Code Reviewer** — review App Engineer PR before merge
3. **Eric (human action)** — T-12: Re-run manual smoke test once fix is deployed
4. **QA Engineer** — T-16 + T-17: Provider OAuth flows and full live end-to-end test

## Blockers

| Blocker | Impact | Owner | Status |
|---------|--------|-------|--------|
| Cognito sign-in fails — `ai-assistant://` not registered as callback URL | High — blocks all of T-12 | Application Engineer + DevOps | Active — fix in progress |

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Mobile auth configuration tests were absent — SDK upgrade changed redirect URI behavior silently | Resolved | High | QA Engineer adding coverage now |
| Google/Microsoft OAuth app not registered for dev redirect URIs | M | H | Eric to verify redirect URI registration in Google/Microsoft developer consoles during T-16 |
| Staging AWS infrastructure does not yet exist (IAM role, S3 bucket) | L | M | T-18 covers this; not needed until Stage 4 QA sign-off is complete |
| Production go-live blocked if staging reveals systemic issues | L | H | Full live provider test suite in Stage 4 reduces staging risk |
