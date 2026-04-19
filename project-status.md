# Project Status — integreat

> Last updated: 2026-04-19

## Summary

Stage 4 (QA Validation on Dev) is in progress. T-12 signed off. T-16 (provider OAuth flows) was blocked by 4 engineering issues — all fixed and merged. CI/CD deploy is in flight (PRs #21/#22 pushed to main). Once deploy settles, T-16 can complete pending Eric adding redirect URIs in Google Cloud Console and Microsoft Entra.

## What We Just Completed

- 2026-04-19 — T-12 signed off by Eric: sign-in, chat (no thinking tags), proposal card rendered, sign-out ✅
- 2026-04-19 — PR #22 merged: DevTokenStore uses `/tmp` in Lambda (`AWS_LAMBDA_FUNCTION_NAME` detection)
- 2026-04-19 — PR #21 merged: 4 OAuth routes added to API Gateway; `GOOGLE_REDIRECT_URI` + `MICROSOFT_REDIRECT_URI` Lambda env vars set
- 2026-04-19 — PR #20 merged: `deploy-dev.yml` pip fix (`backend[test]`) + post-deploy SHA verification
- 2026-04-19 — PR #19 merged: thinking-tag regex hardened (`\b[^>]*` + `re.IGNORECASE`)
- 2026-04-19 — Lambda redeployed with all Phase 13 + thinking-tag + rebrand code (was stranded since 2026-04-08)

## What's In Progress

- CI/CD deploy triggered by PRs #21/#22 merge — OAuth routes + token store fix landing via `terraform apply`

## What's Coming Next

1. **Eric (human action)** — Add redirect URIs in consoles (if not done yet):
   - Google Cloud Console: `https://lbg6dypkqi.execute-api.us-east-1.amazonaws.com/dev/oauth/google/callback`
   - Microsoft Entra: `https://lbg6dypkqi.execute-api.us-east-1.amazonaws.com/dev/oauth/microsoft/callback`
2. **QA Engineer** — T-16: Re-run provider OAuth flows (Google + Microsoft) once deploy settles
3. **QA Engineer** — T-17: Full live end-to-end test + Stage 4 sign-off
4. **DevOps Engineer** — Checkov cleanup PR (pre-existing findings — required before staging)
5. **DevOps Engineer** — T-18: Staging CI/CD pipeline (after Stage 4 sign-off)

## Blockers

None — engineering fixes merged, waiting on deploy + Eric's console actions.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Eric hasn't yet added redirect URIs in Google/Microsoft consoles | M | H | Surfaced directly — see "What's Coming Next" item 1 |
| Checkov findings (CKV_AWS_356, CKV_AWS_309 + 10 others) — terraform-validate failing in CI | M | M | DevOps cleanup PR before staging promotion |
| `AppConfig` dataclass field default inconsistent with `_default_store_file()` — direct construction bypasses Lambda detection | L | L | Follow-on chore: `field(default_factory=_default_store_file)` |
| Staging AWS infrastructure does not yet exist | L | M | T-18 covers this; not needed until Stage 4 sign-off |
