# Workflow State

> Last updated: 2026-04-11 by Project Manager

## Project
**Name**: AI Assistant MVP  
**Route-to-live**: Standard (dev → staging → prod)  
**Started**: 2026-03-16

---

## Current Stage

**Stage**: 4 — QA Validation (Dev Environment)  
**Status**: In Progress — one infrastructure fix in flight, then manual testing by Eric  
**Active agent**: None — awaiting Eric manual action (T-12 smoke test)  
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

**Eric (human action)** — T-12 manual smoke test. Run the Expo app, sign in via Cognito hosted UI, send a chat message, trigger a write proposal, approve it, reject one. Steps are in `test-signoff.md` — Phase 4 section. All infrastructure blockers are resolved.

After T-12 passes: **QA Engineer** runs T-16 (provider OAuth flows via `scripts/start-provider-auth.ps1`) and T-17 (full live end-to-end test + Stage 4 sign-off in `test-signoff.md`).

---

## Active Blockers

None — all infrastructure blockers resolved. Waiting on Eric to execute T-12 manual smoke test.
