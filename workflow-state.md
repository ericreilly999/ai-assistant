# Workflow State

> Last updated: 2026-04-18 by Project Manager

## Project
**Name**: AI Assistant MVP  
**Route-to-live**: Standard (dev → staging → prod)  
**Started**: 2026-03-16

---

## Current Stage

**Stage**: 4 — QA Validation (Dev Environment)  
**Status**: Blocked — Cognito auth failure discovered during T-12 manual smoke test  
**Active agent**: Application Engineer (code fix) + QA Engineer (test coverage + postmortem)  
**Started**: 2026-04-08

---

## Gate Status

| Gate | Required | Status |
|------|----------|--------|
| Spec complete + TODO.md written | Stage 0 → 1 | ✅ |
| All QA test-writing tasks complete | Stage 1 → 2 | ✅ |
| All DEV tasks complete, code on main | Stage 2 → 3 | ✅ |
| Dev environment live + smoke tests pass | Stage 3 → 4 | ✅ |
| QA sign-off on dev (test-signoff.md) | Stage 4 → 5 | ⏳ |
| Staging live + smoke tests pass | Stage 5 → 6 | ❌ |
| QA sign-off on staging (test-signoff.md) | Stage 6 → 7 | ❌ |
| **Human approval for production** | Stage 7 | ❌ |

---

## Next Action

1. **Application Engineer** — fix `makeRedirectUri()` scheme handling in `mobile/src/lib/auth.ts` and `mobile/src/screens/SignInScreen.tsx`; open PR
2. **QA Engineer** — write tests covering auth redirect URI configuration; postmortem on test gap
3. **Code Reviewer** — review App Engineer PR
4. **DevOps Engineer** — register `ai-assistant://` in Cognito callback URLs via Terraform + GitHub Actions variable update; re-deploy
5. **Eric (human)** — re-run T-12 manual smoke test once fix is deployed

---

## Active Blockers

**Blocker**: Cognito sign-in fails — `ai-assistant://` redirect URI not registered in Cognito app client callback URLs.  
**Root cause**: `"scheme": "ai-assistant"` added to `app.json` during Expo SDK 54 upgrade silently changed `makeRedirectUri()` output from `exp://...` to `ai-assistant://`. Cognito only has `exp://` URIs registered.  
**Resolution owner**: Application Engineer (code) + DevOps Engineer (Terraform)  
**Status**: Application Engineer and QA Engineer invoked — fix in progress.
