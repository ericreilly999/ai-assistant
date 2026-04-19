# Test Sign-Off Log — AI Assistant MVP

> Maintained by: QA Engineer  
> Updated by: Project Manager at stage transitions

---

## T-16: OAuth Token Persistence — DynamoDB Live Validation

**Date**: 2026-04-18
**Environment**: dev — `https://lbg6dypkqi.execute-api.us-east-1.amazonaws.com/dev`
**Executed by**: QA Engineer
**Context**: Eric completed OAuth consent flows for Google and Microsoft via the deployed Lambda OAuth endpoints. DynamoDB table `ai-assistant-dev-tokens` (PAY_PER_REQUEST, partition key `provider`) stores tokens durably across Lambda invocations. `DevTokenStore` routes to DynamoDB when `OAUTH_TOKEN_TABLE` env var is set.

---

### Check 1 — Google token stored (connections endpoint, call 1)

**Request**: `GET /dev/v1/dev/connections`
**Response**:
```json
{"google": {"connected": true, "expires_at": null}, "microsoft": {"connected": true, "expires_at": null}, "plaid": {"has_access_token": false, "institution_id": null}}
```
**HTTP status**: 200
**Result**: PASS — `google.connected: true` confirmed. DynamoDB read path returned a live access token for the google provider.

---

### Check 2 — Microsoft token stored (connections endpoint, call 1)

**Request**: Same response as Check 1 (single call covers both).
**Result**: PASS — `microsoft.connected: true` confirmed. DynamoDB read path returned a live access token for the microsoft provider.

---

### Check 3 — Token persistence (sequential call 2)

**Request**: `GET /dev/v1/dev/connections` (second independent call)
**Response**:
```json
{"google": {"connected": true, "expires_at": null}, "microsoft": {"connected": true, "expires_at": null}, "plaid": {"has_access_token": false, "institution_id": null}}
```
**HTTP status**: 200
**Result**: PASS — Both calls returned identical provider state. DynamoDB read path is consistent across potentially different Lambda containers. Token persistence is confirmed.

---

### Check 4 — Google OAuth flow completeness (refresh_token probe via calendar read)

**Request**: `GET /dev/v1/dev/google/calendar/events`
**HTTP status**: 200
**Result**: PASS — Endpoint returned 48 real Google Calendar events spanning 2022–2024 (personal events visible: flights, restaurant reservations, interviews, hotel stays). The access token stored in DynamoDB is valid and accepted by the Google Calendar API. The OAuth flow used `access_type=offline&prompt=consent` — a `refresh_token` must have been issued and stored alongside the `access_token` in the DynamoDB item (the `DevTokenStore.set_tokens` call stores the entire token response from Google's token endpoint, which includes `refresh_token` when `access_type=offline` is used).

**Note on refresh_token verification**: The `/v1/dev/connections` endpoint exposes only `connected` and `expires_at`, not the raw token fields. There is no read endpoint that surfaces the stored token payload directly. The presence of `refresh_token` in DynamoDB cannot be confirmed by calling a live endpoint — it can only be confirmed by direct DynamoDB inspection (`aws dynamodb get-item`). The calendar read succeeding on a live token does not prove a refresh_token was stored; it proves the access_token is valid and unexpired. **Recommend Eric runs `aws dynamodb get-item --table-name ai-assistant-dev-tokens --key '{"provider":{"S":"google"}}'` to confirm `refresh_token` is present in the stored JSON.**

---

### Check 5 — Microsoft OAuth flow completeness (token probe via provider read endpoints)

**Request 1**: `GET /dev/v1/dev/microsoft/calendar/events` (no query params)
**HTTP status**: 400
**Root cause**: The Microsoft Graph `/me/calendarView` endpoint **requires** `startDateTime` and `endDateTime` query parameters — they are mandatory per the Graph API contract. The Lambda handler passes `query.get("start")` and `query.get("end")` to `list_microsoft_calendar_events()`, which only conditionally sets these params. When omitted, Graph returns 400. This is a pre-existing API usage issue — it is not a token problem.

**Recovery**: This failure does not indicate a missing or invalid token. The Microsoft token in DynamoDB is valid, as confirmed by Check 2 (`connected: true`) and the following fallback probe.

**Request 2 (fallback probe)**: `GET /dev/v1/dev/microsoft/todo/lists`
**HTTP status**: 200
**Response**:
```json
{"task_lists": [{"id": "AQMkADAwATMwMAExLThjZWQtOTgxZC0wMAItMDAKAC4AAAOcn1U2QheuQLX2kKD8JvMGAQC_vNuyzVXkR4IKY10poJ1eAAACARIAAAA=", "displayName": "Tasks"}], "provider": "microsoft_todo"}
```
**Result**: PASS — Microsoft Graph authenticated successfully. Real account data returned (one task list: "Tasks"). The Microsoft access token in DynamoDB is live and valid.

**Note on refresh_token verification**: Same caveat as Google. The MS OAuth flow requested `offline_access` scope, which causes Microsoft's token endpoint to issue a `refresh_token`. Stored value cannot be confirmed from the read API surface — recommend direct DynamoDB inspection.

---

### Failure Analysis

| Failure | Endpoint | Root Cause | Token issue? | Recoverable without re-consent? |
|---------|----------|------------|-------------|----------------------------------|
| HTTP 400 | `GET /v1/dev/microsoft/calendar/events` | `calendarView` requires mandatory `startDateTime`/`endDateTime` params; none provided | No — token is valid | Yes — pass date params or switch to `/me/events`. No re-consent needed. |

**Classification**: Code/API usage bug (pre-existing). The Lambda handler at line 107 of `handler.py` maps `GET /v1/dev/microsoft/calendar/events` to `dev_service.list_microsoft_calendar_events(query.get("start"), query.get("end"))`. When called without `?start=...&end=...`, `calendarView` rejects the request. Fix: use `/me/events` (which does not require a date range) or enforce that start/end params are required at the handler level with a clear 400 message.

---

### Pass Criteria Assessment

| Criterion | Result |
|-----------|--------|
| `GET /v1/dev/connections` returns `google: true` | PASS |
| `GET /v1/dev/connections` returns `microsoft: true` | PASS |
| Token reads consistent on 2 sequential calls (persistence) | PASS |
| No 500 errors on provider read endpoints | PASS — no 500s observed |
| Google provider read endpoint succeeds | PASS — 48 calendar events returned |
| Microsoft provider read endpoint succeeds | PARTIAL — calendar 400 (API usage, not token); Todo read PASS |

---

### Sign-off Decision

**CONDITIONAL PASS** — Core objectives are met.

The DynamoDB token persistence layer is functioning correctly for both Google and Microsoft. Both tokens were written during consent and are being read successfully across Lambda invocations. Real provider data was returned from Google Calendar and Microsoft To Do, confirming live token validity in both cases.

The single failure (`GET /v1/dev/microsoft/calendar/events` returning 400) is an API usage issue that predates this work: `calendarView` is not callable without date range parameters and this was never guarded at the handler level. It is not a token, DynamoDB, or OAuth flow failure. It is recoverable without re-consent.

Two items require follow-up but do not block T-16 sign-off:

1. **Microsoft calendar endpoint bug** — Report to Application Engineer: `GET /v1/dev/microsoft/calendar/events` must either require `start`/`end` params and return a structured 400, or switch to `/me/events` which does not mandate a date range. No re-consent needed.
2. **Refresh token confirmation** — Recommend direct DynamoDB verification for both providers to confirm `refresh_token` is present in stored payloads: `aws dynamodb get-item --table-name ai-assistant-dev-tokens --key '{"provider":{"S":"google"}}'` and same for `microsoft`.

**QA Engineer sign-off date**: 2026-04-18

---

## Stage 4 — QA Validation (Dev Environment)

**Status**: ✅ SIGNED OFF — 2026-04-19

### Sign-Off Checklist

- [x] Mock-mode smoke test: mobile → API Gateway → Lambda → mock responses
- [x] `/health` endpoint returns 200 from deployed dev URL
- [x] Cognito sign-in flow completes via hosted UI (ai-assistant:// scheme registered in Deploy #6)
- [x] Chat request round-trip succeeds (mock mode)
- [x] Write proposal generated and returned to mobile UI
- [x] Proposal approval and rejection both function correctly
- [x] Live provider test: Google OAuth flow completes end-to-end (T-16)
- [x] Live provider test: Microsoft OAuth flow completes end-to-end (T-16)
- [x] Live provider test: Plaid sandbox link and account read (T-17)
- [x] Live provider test: Google Calendar read (T-17)
- [x] Live provider test: Google Tasks read and write (T-17)
- [x] Live provider test: Microsoft Calendar read (T-17)
- [x] Live provider test: Microsoft To Do read and write (T-17)
- [x] Prompt regression suite passes against live dev endpoint (T-17)
- [x] No provider tokens visible in CloudWatch logs (T-17)

**Sign-off**: ✅ Signed off  
**QA Engineer sign-off date**: 2026-04-19  
**Notes**: T-16 (OAuth/DynamoDB persistence) and T-17 (full live E2E) both signed off. Cognito redirect URI mismatch (Expo SDK 54) was resolved via Deploy #6 (ai-assistant:// registered) and the SignInScreen.tsx fix. Stage 4 → Stage 5 gate cleared. See T-16 sign-off and T-17 project-status.md entry for details.

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
