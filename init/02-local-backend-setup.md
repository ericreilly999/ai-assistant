# Local Backend Setup

The backend is a Python AWS Lambda application. It runs in **mock provider mode** by default, meaning you do not need live Google, Microsoft, or Plaid credentials to develop and test locally.

## Directory Structure

```
backend/
  src/
    assistant_app/
      handler.py          # Lambda entry point — routes all HTTP requests
      orchestrator.py     # Intent routing, plan/execute flow
      intent.py           # Bedrock-backed intent classification
      consent.py          # Write proposal validation and expiry
      bedrock_client.py   # Amazon Bedrock Converse + Guardrails
      secrets_manager.py  # Loads provider secrets at cold start
      dev_store.py        # Local token file store for dev/test
      config.py           # All environment variable reads
      models.py           # Shared domain types (ActionProposal, etc.)
      http_client.py      # Thin HTTP wrapper for provider API calls
      response.py         # Response shaping and CORS headers
      live_service.py     # Dispatcher for live provider calls
      registry.py         # Tool/action registry
      providers/          # Provider adapters (Google, Microsoft, Plaid)
  tests/
    test_handler.py
    test_orchestrator.py
    test_oauth.py
    test_consent.py
    test_providers.py
    test_dev_store.py
  pyproject.toml
  README.md
```

## Step 1 — Set Up a Virtual Environment

```powershell
cd ai-assistant/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install ruff mypy
```

## Step 2 — Set Environment Variables for Local Mode

Create a file `backend/.local/env.ps1` (this path is gitignored):

```powershell
$env:MOCK_PROVIDER_MODE      = "true"
$env:APP_ENV                 = "dev"
$env:AWS_REGION              = "us-east-1"
$env:CORS_ALLOWED_ORIGINS    = "http://localhost:8081"
$env:LOCAL_SERVER_PORT       = "8787"
# Leave Bedrock vars empty in full mock mode — the mock provider never calls Bedrock
$env:BEDROCK_ROUTER_PROFILE_ARN  = ""
$env:BEDROCK_SUMMARY_PROFILE_ARN = ""
$env:BEDROCK_GUARDRAIL_ID        = ""
$env:BEDROCK_GUARDRAIL_VERSION   = ""
```

Source the file before running scripts:

```powershell
. .\backend\.local\env.ps1
```

## Step 3 — Run Unit Tests

```powershell
cd ai-assistant
.\scripts\run-backend-tests.ps1
```

This discovers all tests under `backend/tests/` and runs them with the standard `unittest` runner. No live credentials are needed.

## Step 4 — Run Lint and Type Check

```powershell
cd ai-assistant/backend
# Activate venv first
ruff check src/ tests/
mypy src/
```

Both tools are configured in `backend/pyproject.toml`.

## Step 5 — Package the Lambda Artifact

```powershell
cd ai-assistant
.\scripts\package-lambda.ps1
```

This compresses `backend/src/` into `dist/orchestrator.zip`, which is the artifact deployed to AWS Lambda.

## Exposed Routes (local reference)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/v1/integrations` | Returns supported providers and connection status |
| POST | `/v1/chat/plan` | Submit a user message, get a read answer or write proposal |
| POST | `/v1/chat/execute` | Approve and execute a previously proposed action |
| GET | `/oauth/google/start` | Start Google OAuth flow (dev only) |
| GET | `/oauth/google/callback` | Google OAuth callback (dev only) |
| GET | `/oauth/microsoft/start` | Start Microsoft OAuth flow (dev only) |
| GET | `/oauth/microsoft/callback` | Microsoft OAuth callback (dev only) |
| GET | `/dev/token-status` | Show locally stored token state (dev only) |
| POST | `/dev/clear-tokens` | Clear locally stored tokens (dev only) |

## Notes

- `MOCK_PROVIDER_MODE=true` makes all provider calls return fixture data.
- The `dev_store.py` module stores OAuth tokens in a local JSON file at `backend/.local/tokens.json` during development. This file is gitignored.
- In Lambda (non-dev), secrets are loaded from AWS Secrets Manager at cold start via `secrets_manager.py`.
