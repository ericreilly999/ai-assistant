# Test Sign-Off Log — AI Assistant MVP

> Maintained by: QA Engineer  
> Updated by: Project Manager at stage transitions

---

## Stage 4 — QA Validation (Dev Environment)

**Status**: ⏳ In Progress — automated pre-checks passed; manual device execution pending

### Sign-Off Checklist

- [ ] Mock-mode smoke test: mobile → API Gateway → Lambda → mock responses
- [ ] `/health` endpoint returns 200 from deployed dev URL
- [ ] Cognito sign-in flow completes via hosted UI
- [ ] Chat request round-trip succeeds (mock mode)
- [ ] Write proposal generated and returned to mobile UI
- [ ] Proposal approval and rejection both function correctly
- [ ] Live provider test: Google OAuth flow completes end-to-end
- [ ] Live provider test: Microsoft OAuth flow completes end-to-end
- [ ] Live provider test: Plaid sandbox link and account read
- [ ] Live provider test: Google Calendar read
- [ ] Live provider test: Google Tasks read and write
- [ ] Live provider test: Microsoft Calendar read
- [ ] Live provider test: Microsoft To Do read and write
- [ ] Prompt regression suite passes against live dev endpoint
- [ ] No provider tokens visible in CloudWatch logs

**Sign-off**: ❌ Not yet signed off  
**QA Engineer sign-off date**: —  
**Notes**: Blocked on live provider credentials (Eric: T-13). T-10 Cognito domain is resolved — domain is live. T-12 automated checks complete; manual execution by Eric pending.

**BLOCKER (2026-04-18) — Cognito sign-in flow: redirect URI mismatch after Expo SDK 54 upgrade.** The checklist item "Cognito sign-in flow completes via hosted UI" cannot be checked until the fix below is deployed and T-12 is re-run.
- Root cause: `app.json` has `"scheme": "ai-assistant"` (added during SDK 54 upgrade). Expo SDK 54 changed `AuthSession.makeRedirectUri()` to return `ai-assistant://` in standalone/native builds when a custom scheme is defined. Cognito's `callback_urls` contained only `exp://` URIs so all OAuth redirects were rejected with "an error was encountered".
- Application Engineer fix: `SignInScreen.tsx` updated to call `makeRedirectUri({ native: 'ai-assistant://' })` explicitly. Static analysis confirms this fix is in place (Test A passes).
- DevOps fix required: `terraform/environments/dev/terraform.tfvars` `callback_urls` must include at least one `ai-assistant://` URI, and `terraform apply` must be re-run. Test B in `mobile/__tests__/redirectUri.config.test.ts` will fail until this is done.
- Do not mark "Cognito sign-in flow completes via hosted UI" as passed until: (1) Terraform is updated and applied, (2) full test suite passes (including Test B), (3) Eric re-runs the T-12 manual sign-in step on device.

---

## T-12: Mock-Mode Smoke Test (Mobile → Lambda)

**Date**: 2026-04-10  
**Executed by**: QA Engineer (automated phase) + Eric (manual phase pending)  
**Status**: PARTIAL — automated checks complete, manual execution awaiting Eric

---

### Phase 1 — Automated Setup Validation

#### 1. mobile/.env — PASS
All three required values are present and correct:
- `EXPO_PUBLIC_API_BASE_URL=https://lbg6dypkqi.execute-api.us-east-1.amazonaws.com` ✓
- `EXPO_PUBLIC_COGNITO_CLIENT_ID=4dqle0d1u53tudl6lg7rfmbbgp` ✓
- `EXPO_PUBLIC_COGNITO_DOMAIN=https://ai-assistant-dev.auth.us-east-1.amazoncognito.com` ✓

#### 2. Expo SDK / app.json / package.json — PASS (with one pre-flight note)
- Expo SDK: `~53.0.0` (React 19.0.0 / RN 0.79.0)
- App slug: `ai-assistant` (used by Expo to construct the redirect URI)
- `app.json` does NOT define a custom `scheme`. This means `expo-auth-session` will use the default Expo Go scheme (`exp://`) in Expo Go and a generated scheme in production builds. **For a native standalone build**, a custom scheme must be added to `app.json` (e.g. `"scheme": "ai-assistant"`) and registered as a Cognito callback URL. See blocker note below.
- `node_modules/` is NOT present. Eric must run `npm install` from `mobile/` before starting the dev server.

#### 3. Cognito redirect URI in mobile auth code — PASS (with caveat)
- `mobile/src/screens/SignInScreen.tsx` uses `AuthSession.makeRedirectUri()` — no hard-coded scheme.
- Redirect URI is dynamic: in Expo Go it resolves to `exp://[host]/--/` form; in a native build it uses the app scheme.
- No custom `scheme` is defined in `app.json` — see blocker note below.

#### 4. Cognito App Client callback URLs — BLOCKER
- `terraform/environments/dev/terraform.tfvars` has `callback_urls = []` and `logout_urls = []`.
- The Cognito user pool client (`aws_cognito_user_pool_client.mobile`) is provisioned with **empty callback URL lists**.
- The actual Expo-generated redirect URI (e.g. `exp://127.0.0.1:8081/--/` or a custom scheme URL) is NOT registered. The OAuth redirect will be rejected by Cognito with `redirect_uri_mismatch`.
- **Fix required**: Determine the actual redirect URI (run `npx expo start`, tap Sign In, note the URI in the error), then add it to `callback_urls` in `terraform.tfvars` and re-apply.
- For production/standalone builds: add `"scheme": "ai-assistant"` to `app.json` and register `ai-assistant://` as a callback URL.

#### 5. mobile/.env in .gitignore — PASS
Root `.gitignore` line 15 contains `mobile/.env`. The file will not be committed.

#### 6. Lambda /health endpoint — PASS
```
GET https://lbg6dypkqi.execute-api.us-east-1.amazonaws.com/dev/health
Response: {"service":"ai-assistant","environment":"dev","mock_provider_mode":true,"providers":["google_calendar","google_tasks","google_drive","microsoft_calendar","microsoft_todo","plaid"],"local_env_file":null,"provider_secret_status":{"google":true,"microsoft":true,"plaid":true},"local_store_file":"backend/.local/dev_tokens.json"}
HTTP 200 — mock_provider_mode: true confirmed
```

#### 7. Direct API call to /v1/chat/plan (no auth) — EXPECTED 401, confirmed
```
POST https://lbg6dypkqi.execute-api.us-east-1.amazonaws.com/dev/v1/chat/plan
Response: {"message":"Unauthorized"}
HTTP 401 — auth is enforced as expected
```
Note: `/health` is public (not in `protected_routes`); all `/v1/` routes require a valid Cognito JWT.

---

### Phase 2 — Connectivity Pre-checks

| Check | Result |
|---|---|
| `GET /dev/health` | PASS — HTTP 200, mock mode confirmed |
| `POST /dev/v1/chat/plan` (no token) | PASS — HTTP 401 as expected |
| Cognito hosted UI `https://ai-assistant-dev.auth.us-east-1.amazoncognito.com` | PASS — HTTP 200 (ELB/Cognito responding) |

---

### Phase 3 — Blockers Found

1. **BLOCKER: Cognito callback_urls is empty** — The app client has no registered redirect URIs. OAuth sign-in will fail with `redirect_uri_mismatch` until callback_urls is populated in Terraform and re-applied. Steps to fix:
   a. Run `npx expo start` from `mobile/` in Expo Go mode.
   b. Tap "Sign In" — the OAuth browser session will open and fail with a Cognito error that shows the exact `redirect_uri` being used (e.g. `exp://192.168.x.x:8081/--/`).
   c. Add that URI plus `exp://localhost:8081/--/` to `callback_urls` in `terraform/environments/dev/terraform.tfvars`.
   d. For iOS simulator: add `exp://localhost:8081/--/`.
   e. For Android emulator: add `exp://10.0.2.2:8081/--/`.
   f. Run `terraform apply` from `terraform/environments/dev/`.

2. **Pre-flight: node_modules missing** — Run `npm install` from `mobile/` before starting Expo.

3. **ADVISORY: No custom scheme in app.json** — For standalone/production builds, add `"scheme": "ai-assistant"` to `app.json` and register `ai-assistant://` as a callback URL in Cognito. Not required for Expo Go testing.

---

### Phase 4 — Manual Test Script (Eric to Execute)

**Prerequisites:**
- [ ] `callback_urls` blocker resolved (see Phase 3 above)
- [ ] A device/simulator available: iOS Simulator, Android Emulator, or physical device with Expo Go
- [ ] A Cognito user account exists (create one at `https://ai-assistant-dev.auth.us-east-1.amazoncognito.com/login` or via `aws cognito-idp admin-create-user`)

**Step 1 — Install dependencies and start Expo**
```bash
cd mobile
npm install
npx expo start
```
Expected: QR code displayed in terminal. Expo DevTools at http://localhost:8081.

**Step 2 — Open the app**
- iOS Simulator: press `i` in the Expo terminal
- Android Emulator: press `a`
- Physical device: scan QR code with Expo Go app

Expected: App loads showing "integreat" sign-in screen with a green "Sign In" button.

**Step 3 — Cognito sign-in flow**
1. Tap "Sign In"
2. A browser/web view opens to the Cognito hosted UI at `https://ai-assistant-dev.auth.us-east-1.amazoncognito.com/login`
3. Enter your Cognito user email and password
4. If prompted for MFA or password change, complete it
5. Cognito redirects back to the app via the registered callback URI

Expected on success: Browser closes, app transitions to the Chat screen showing "integreat" in the header and the welcome message: "Ask about your calendar, groceries, meeting prep, or travel planning."

Expected on failure: Error displayed in the sign-in screen. Common causes: callback_url not registered (see blocker above), user does not exist, incorrect password.

**Step 4 — Send a read query (chat round-trip)**
1. Tap the text input at the bottom
2. Type: `what meetings do I have today?`
3. Tap the up-arrow send button (or press Enter)

Expected: "Thinking…" appears briefly, then a mock response appears. In mock mode the response will be a plausible-sounding but synthetic answer, for example:
> "You have 2 meetings today: a standup at 9 AM and a product review at 2 PM. (Mock mode — no real calendar data.)"
The exact text depends on the mock handler implementation.

**Step 5 — Trigger a write proposal**
1. Type: `add a meeting tomorrow at 2pm called Team Sync`
2. Tap send

Expected: Assistant response includes a proposal card with:
- Provider label (e.g. `GOOGLE_CALENDAR`)
- Risk badge (LOW or MEDIUM)
- Summary: e.g. "Create event: Team Sync on [date] at 2:00 PM"
- Action: `create_event`, Resource: `calendar_event`
- "Show details" toggle to expand payload JSON
- "Reject" button (outlined, brown) and "Approve" button (filled, green)

**Step 6 — Approve the proposal**
1. On the proposal card from Step 5, tap "Approve"

Expected: Card buttons disable/grey out momentarily, then a new assistant message appears:
> "Done. Event 'Team Sync' created for [date] at 2:00 PM. (Mock — no real write performed.)"
The mock executor always returns success with a confirmation message.

**Step 7 — Reject a proposal**
1. Send another write intent: `add a reminder to buy groceries`
2. When the proposal card appears, tap "Reject"

Expected: No API call is made. A new assistant message appears immediately:
> "Action cancelled: [proposal summary]"
(This is client-side only — rejection is handled locally in `ChatScreen.tsx`.)

**Step 8 — Sign out**
1. Tap "Sign Out" in the top-right corner

Expected: App returns to the sign-in screen. Stored tokens are cleared from SecureStore.

---

### Pass/Fail Criteria for Manual Execution

| Step | Pass Condition |
|---|---|
| App loads | Sign-in screen renders without crash |
| Cognito sign-in | Chat screen appears after OAuth flow |
| Read query | Mock response returned, no error bubble |
| Write proposal | Proposal card rendered with Approve/Reject buttons |
| Approve | Confirmation message appears |
| Reject | "Action cancelled" message appears, no API call |
| Sign out | Returns to sign-in screen |

---

### T-12 Overall Status: PARTIAL

- Automated checks: 5 PASS, 1 BLOCKER (Cognito callback_urls empty)
- Manual execution: PENDING — Eric to complete once callback_urls blocker is resolved
- Do not mark T-12 complete in TODO.md until all manual steps pass

---

## Stage 6 — QA Validation (Staging Environment)

**Status**: ❌ Not started

**Sign-off**: ❌ Not yet signed off  
**QA Engineer sign-off date**: —  
**Notes**: —

---

## Historical Test Results

### CI Test Suite (main branch — current)
**Date**: 2026-04-08  
**Result**: ✅ Green — 122 tests passing  
**Coverage**: backend unit tests, mobile unit tests, prompt regression suite  
**Notes**: All CI checks green. Lambda artifact validated in pipeline.

---

## Postmortem — Redirect URI Mismatch (Expo SDK 54 Upgrade)

**Date found**: 2026-04-18  
**Found during**: T-12 manual smoke test (Stage 4 QA, dev environment)  
**Severity**: Critical — all Cognito OAuth sign-in attempts blocked in standalone/native builds

### What Was Found

After the Expo SDK 53 → 54 upgrade, attempting to sign in via the Cognito hosted UI resulted in an "an error was encountered" error on the Cognito side. The OAuth flow never completed. The app remained on the sign-in screen with no visible error detail.

### Root Cause

Two separate changes combined to cause the failure:

1. `app.json` had `"scheme": "ai-assistant"` added as part of the Expo SDK 54 upgrade preparation.
2. Expo SDK 54 changed the default behaviour of `AuthSession.makeRedirectUri()`: when a custom `scheme` is defined in `app.json` and the execution environment is `standalone` or `bare`, the function returns `<scheme>://` instead of the previous default `exp://...` form used in Expo Go.

The `makeRedirectUri()` call in `SignInScreen.tsx` was not passing the `native` parameter. Without `native`, SDK 54 resolved the URI using the manifest scheme, producing `ai-assistant://`. Cognito's registered `callback_urls` (in `terraform/environments/dev/terraform.tfvars`) contained only `exp://` URIs. Cognito rejected every redirect because `ai-assistant://` was not a registered callback URL.

### Why Existing Tests Did Not Catch It

The mobile unit tests in `mobile/__tests__/` mock `expo-auth-session` in its entirety. `makeRedirectUri()` was replaced with a jest mock returning a static string (`"myapp://redirect"`). As a result:

- The test suite never called the real `makeRedirectUri()` implementation
- No test validated what URI the function produces given the current `app.json` configuration
- No test cross-referenced the produced URI against the Terraform `callback_urls` list
- The SDK upgrade silently changed the real function's output without any test surface to detect it

### What Was Fixed

**Application code (Application Engineer):** `SignInScreen.tsx` updated to call `makeRedirectUri({ native: 'ai-assistant://' })` explicitly. The `native` parameter makes the return value deterministic in standalone/bare builds regardless of SDK version behaviour: when `native` is provided and the environment is standalone or bare, expo-auth-session returns the `native` value directly without any manifest resolution.

**Infrastructure (DevOps Engineer — action required):** `terraform/environments/dev/terraform.tfvars` must be updated to add `ai-assistant://` to `callback_urls` and `terraform apply` must be re-run.

### Test Coverage Added

New test file: `mobile/__tests__/redirectUri.config.test.ts`

**Test A — `makeRedirectUri` call uses `native` parameter with scheme from `app.json`** (4 tests, static analysis)  
Reads `app.json` and `SignInScreen.tsx` source and asserts:
- `app.json` defines a non-empty, RFC-valid URI scheme
- `SignInScreen.tsx` calls `makeRedirectUri` with a `native` parameter present
- The `native` value in the call matches `<scheme>://` from `app.json`

Static analysis is used rather than calling the real SDK function, because `expo-constants` is a nested transitive dependency not directly mockable from the test environment without additional `moduleNameMapper` configuration. The static check is sufficient: it catches the exact mutation that caused the original bug (omitting `native` or using a wrong scheme string).

**Test B — Terraform `callback_urls` includes the native scheme URI** (4 tests, configuration contract)  
Reads `terraform/environments/dev/terraform.tfvars` and asserts:
- The `callback_urls` list is non-empty
- At least one entry starts with `<scheme>://` (the native URI from `app.json`)
- All entries are valid non-empty strings
- No duplicate entries exist

This test will fail — and should fail — until the DevOps fix is applied.

### Current Test Suite State (2026-04-18)

| File | Tests | Status |
|------|-------|--------|
| `redirectUri.config.test.ts` (Test A) | 4 | PASS — application fix confirmed |
| `redirectUri.config.test.ts` (Test B) | 3 pass, 1 fail | FAIL — Terraform fix pending |
| All pre-existing mobile tests | 37 | PASS — no regressions |

Test B will turn fully green once DevOps adds `ai-assistant://` to `terraform.tfvars` and applies.

### Lessons Learned

SDK upgrades that change the behaviour of authentication-critical functions must be treated as breaking changes. Any function that produces a URI used in an OAuth flow needs a test that:
1. Exercises the real function (not a mock) against the real configuration files
2. Cross-references the output against every registered callback URL list

Mocking at the module boundary (as the existing tests do) is appropriate for testing component behaviour in isolation, but must be complemented by at least one integration-level test that exercises the real implementation path against live configuration.
