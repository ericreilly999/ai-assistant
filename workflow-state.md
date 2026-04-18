# Workflow State

> Last updated: 2026-04-18 by Project Manager

## Project
**Name**: AI Assistant MVP  
**Route-to-live**: Standard (dev → staging → prod)  
**Started**: 2026-03-16

---

## Current Stage

**Stage**: 4 — QA Validation (Dev Environment)  
**Status**: In Progress — Cognito auth fix deployed, T-12 unblocked  
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

**Eric (human action)** — T-12 manual smoke test. All blockers resolved.

Steps:
1. `cd mobile && npx expo start`
2. Press `i` (iOS Simulator), `a` (Android Emulator), or scan QR with Expo Go
3. Tap Sign In → complete Cognito hosted UI sign-in
4. Send a read query → confirm mock response
5. Send a write intent → confirm proposal card renders → Approve
6. Send another write intent → Reject → confirm "Action cancelled"
7. Sign Out

Full pass/fail criteria in `test-signoff.md` Phase 4.

After T-12 passes: **QA Engineer** runs T-16 (provider OAuth flows) and T-17 (full live end-to-end test + Stage 4 sign-off).

---

## Active Blockers

None — all blockers resolved. `ai-assistant://` registered in Cognito (Deploy #6, 2026-04-18). T-12 awaits Eric's execution.
