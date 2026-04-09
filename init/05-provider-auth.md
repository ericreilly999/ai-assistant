# Provider Authentication — Local Setup

This guide walks through verifying the OAuth flows for Google and Microsoft, and the Plaid sandbox bootstrap, in a local development environment.

## Prerequisites

- Backend is set up (see `02-local-backend-setup.md`).
- Google OAuth client credentials are available.
- Microsoft Azure app registration credentials are available.
- Plaid sandbox credentials are available.
- `LOCAL_SERVER_PORT` is set (default: `8787`).

## Running the Auth Helper Script

The `start-provider-auth.ps1` script opens a local HTTP listener on `LOCAL_SERVER_PORT` to handle OAuth callbacks. Run it before starting any OAuth flow:

```powershell
cd ai-assistant
.\scripts\start-provider-auth.ps1
```

Leave this running in a separate terminal during OAuth verification.

## Google OAuth Flow

### Step 1 — Set credentials in the local environment

In `backend/.local/env.ps1`, add:

```powershell
$env:MOCK_PROVIDER_MODE = "false"
$env:GOOGLE_CLIENT_ID     = "<your-google-client-id>"
$env:GOOGLE_CLIENT_SECRET = "<your-google-client-secret>"
```

Source the file: `. .\backend\.local\env.ps1`

### Step 2 — Start the auth flow

Navigate to:

```
http://localhost:8787/oauth/google/start
```

You will be redirected to Google's consent screen. Grant the following scopes:
- `https://www.googleapis.com/auth/calendar.events`
- `https://www.googleapis.com/auth/tasks`
- `https://www.googleapis.com/auth/drive.readonly`

### Step 3 — Verify token storage

After the callback, check:

```
http://localhost:8787/dev/token-status
```

You should see a `google` entry with a valid `access_token` and `expires_at`.

### Step 4 — Verify live reads

Run the integration test script:

```powershell
.\scripts\test-integrations.ps1
```

Confirm that Google Calendar events, Tasks lists, and Drive files are returned without errors.

---

## Microsoft OAuth Flow

### Step 1 — Set credentials

```powershell
$env:MICROSOFT_CLIENT_ID     = "<your-azure-client-id>"
$env:MICROSOFT_CLIENT_SECRET = "<your-azure-client-secret>"
$env:MICROSOFT_TENANT_ID     = "common"
```

### Step 2 — Start the auth flow

Navigate to:

```
http://localhost:8787/oauth/microsoft/start
```

Grant:
- `Calendars.ReadWrite`
- `Tasks.ReadWrite`
- `offline_access`

### Step 3 — Verify token storage and live reads

```
http://localhost:8787/dev/token-status
```

Confirm the `microsoft` entry is present, then run:

```powershell
.\scripts\test-integrations.ps1
```

---

## Plaid Sandbox Bootstrap

### Step 1 — Set credentials

```powershell
$env:PLAID_CLIENT_ID  = "<your-plaid-client-id>"
$env:PLAID_SECRET     = "<your-plaid-sandbox-secret>"
$env:PLAID_ENV        = "sandbox"
```

### Step 2 — Create a sandbox Item

Plaid's sandbox environment provides test institutions. Use the Plaid sandbox API or dashboard to create a test Item and obtain an `access_token`.

Store the token locally (for dev only) via the dev token endpoint or directly in `backend/.local/tokens.json`:

```json
{
  "plaid": {
    "access_token": "access-sandbox-..."
  }
}
```

### Step 3 — Verify reads

Run `test-integrations.ps1` and confirm Plaid account balances and transactions are returned.

---

## Clearing Local Tokens

To reset all locally stored tokens:

```
POST http://localhost:8787/dev/clear-tokens
```

Or delete `backend/.local/tokens.json` manually.

---

## Token Security Rules

- **Never commit tokens.** The `.local/` directory is gitignored.
- **Never log tokens.** The logging rules in `config.py` and `response.py` explicitly redact token fields.
- In AWS deployments, tokens are never stored server-side. The mobile app holds provider tokens in the device secure store and sends them per-request.
