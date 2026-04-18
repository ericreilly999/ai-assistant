# integreat

A mobile-first personal assistant that accepts natural-language requests, reasons across Google (Calendar, Tasks, Drive), Microsoft 365 (Calendar, To Do), and Plaid (banking), and returns either a direct answer or a reviewable action proposal that requires explicit user approval before any write is performed. The backend runs on AWS Lambda with Amazon Bedrock for intent routing and guardrails. All infrastructure is managed with Terraform.

---

## How it works

```
Mobile (Expo)
    │  Cognito JWT on every request
    ▼
API Gateway (HTTP API, JWT authorizer)
    │  Proxy integration
    ▼
Lambda  ──► Bedrock Guardrails (input check)
    │
    ├─► POST /v1/chat/plan
    │       │  Bedrock Nova Pro classifies intent
    │       │  Read intents  → call provider APIs → return answer
    │       └  Write intents → return ActionProposal (no write yet)
    │
    └─► POST /v1/chat/execute   (user approved a proposal)
            └  Call provider API → return confirmation
```

**Consent rule**: no provider write is ever performed without an approved `ActionProposal` round-trip through the mobile client.

**Provider credentials** are stored only in AWS Secrets Manager (KMS-encrypted). The Lambda loads them at cold start and never logs or re-serialises them.

---

## Repository structure

```
ai-assistant/
├── backend/
│   ├── src/assistant_app/        # Lambda application package
│   │   ├── handler.py            # Lambda entrypoint — HTTP routing
│   │   ├── orchestrator.py       # Chat orchestration (plan + execute)
│   │   ├── bedrock_client.py     # Bedrock Converse router + Guardrails
│   │   ├── intent.py             # Intent classification helpers
│   │   ├── consent.py            # ActionProposal building + validation
│   │   ├── config.py             # AppConfig (env vars + Secrets Manager)
│   │   ├── secrets_manager.py    # AWS Secrets Manager cold-start loader
│   │   ├── live_service.py       # Local dev integration service (OAuth + dev routes)
│   │   ├── registry.py           # Provider registry (mock vs live)
│   │   ├── models.py             # PlanResult, ExecuteResult, CalendarEvent
│   │   ├── response.py           # HTTP response helpers
│   │   ├── dev_store.py          # Local token file store (dev only)
│   │   ├── http_client.py        # Shared HTTP client + error types
│   │   └── providers/            # Provider adapters (mock + live)
│   │       ├── google_calendar.py
│   │       ├── google_tasks.py
│   │       ├── google_drive.py
│   │       ├── microsoft_calendar.py
│   │       ├── microsoft_todo.py
│   │       └── plaid.py
│   ├── tests/                    # pytest suite — 122 tests
│   ├── local_server.py           # Local HTTP server (port 8787, API GW v2 format)
│   ├── pyproject.toml            # pytest / ruff / mypy config
│   └── .env.local                # Local credentials — gitignored, see .env.local.example
├── mobile/
│   ├── src/
│   │   ├── screens/              # SignInScreen.tsx, ChatScreen.tsx
│   │   ├── components/           # ActionProposalCard.tsx
│   │   ├── lib/                  # api.ts (API calls), auth.ts (Cognito token management)
│   │   └── types.ts
│   └── .env                      # Expo public vars — gitignored, see below
├── terraform/
│   ├── bootstrap/                # One-time: S3 state bucket, OIDC provider, IAM deploy role
│   ├── environments/
│   │   ├── dev/                  # Dev environment (deployed)
│   │   ├── staging/              # Staging (not yet deployed)
│   │   └── prod/                 # Production (not yet deployed)
│   └── modules/
│       ├── kms_key/              # CMK for Secrets Manager encryption
│       ├── cognito_user_pool/    # User pool + hosted UI + app client
│       ├── secrets_bundle/       # Secrets Manager bundle (google-oauth, microsoft-oauth, plaid)
│       ├── bedrock_ai_config/    # Bedrock guardrail + prompt config
│       ├── lambda_service/       # Lambda function + alias + IAM role
│       ├── http_api/             # API Gateway HTTP API + JWT authorizer + routes
│       ├── service_observability/ # CloudWatch alarms + dashboard
│       ├── acm_certificate/      # ACM cert (staging/prod custom domains)
│       └── route53_records/      # DNS records (staging/prod)
├── scripts/                      # PowerShell helper scripts (see Scripts reference)
├── .github/
│   └── workflows/
│       ├── ci.yml                # PR gate: tests, lint, typecheck, terraform validate
│       ├── deploy-dev.yml        # Deploy to dev on push to main
│       └── auto-fmt.yml          # Manual: terraform fmt + commit
├── .claude/
│   ├── settings.json             # Claude Code permissions + branch policy hook config
│   └── hooks/branch-policy.sh   # Blocks direct push or merge to main
├── docs/
│   └── assistant-mvp-spec.md     # Full product specification
└── init/                         # Step-by-step first-time setup guides (00–09)
```

---

## First-time setup

### Prerequisites

- Python 3.12+
- Node.js 24+
- Terraform 1.9.8+
- AWS CLI configured with credentials for the target account
- Expo Go app installed on a physical device, or iOS/Android simulator

### 1. Clone and install backend dependencies

```bash
cd backend
pip install pytest pytest-cov ruff mypy
```

### 2. Create `backend/.env.local`

Copy from the example (not committed) and fill in credentials:

```bash
cp backend/.env.local.example backend/.env.local
# Edit backend/.env.local — see Configuration reference below
```

### 3. Install mobile dependencies

```bash
cd mobile
npm install
```

### 4. Create `mobile/.env`

```
EXPO_PUBLIC_API_BASE_URL=https://lbg6dypkqi.execute-api.us-east-1.amazonaws.com
EXPO_PUBLIC_COGNITO_CLIENT_ID=4dqle0d1u53tudl6lg7rfmbbgp
EXPO_PUBLIC_COGNITO_DOMAIN=https://ai-assistant-dev.auth.us-east-1.amazoncognito.com
```

### 5. Bootstrap AWS infrastructure (first time only)

One-time setup: creates the S3 Terraform state bucket, GitHub OIDC provider, and IAM deploy role. Follow `init/07-terraform-setup.md` and `init/08-aws-deployment.md`.

```bash
cd terraform/bootstrap
terraform init
terraform apply
```

### 6. Deploy dev environment

Push to `main` — the `deploy-dev.yml` workflow handles everything. Or apply manually:

```bash
cd terraform/environments/dev
terraform init -backend-config=backend.hcl
terraform apply -var-file=terraform.tfvars
```

---

## Day-to-day workflow

### Run the local backend

```bash
python backend/local_server.py
# Listening on http://localhost:8787
```

The local server translates real HTTP into the API Gateway v2 event format and calls the same `lambda_handler` that runs in AWS. Set `MOCK_PROVIDER_MODE=false` in `backend/.env.local` to use live provider credentials.

### Run the mobile app

```bash
cd mobile
npx expo start
# i = iOS simulator, a = Android emulator, scan QR for Expo Go on device
```

### Run backend tests

```bash
cd backend
PYTHONPATH=src python -m pytest tests -v
# or
./scripts/run-backend-tests.ps1
```

### Run provider OAuth flows (local dev)

```bash
./scripts/start-provider-auth.ps1
# Opens browser to /oauth/google/start or /oauth/microsoft/start
# Completes OAuth and writes tokens to backend/.local/dev_tokens.json
```

### Validate Terraform before a PR

```bash
./scripts/validate-terraform.ps1
```

---

## API reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | None | Service health, provider secret status, mock mode flag |
| `GET` | `/v1/integrations` | Cognito JWT | Integration connection status |
| `POST` | `/v1/chat/plan` | Cognito JWT | Submit a user message — returns `PlanResult` (answer or `ActionProposal`) |
| `POST` | `/v1/chat/execute` | Cognito JWT | Execute an approved `ActionProposal` — returns `ExecuteResult` |
| `GET` | `/oauth/google/start` | None | Initiate Google OAuth (local dev) |
| `GET` | `/oauth/google/callback` | None | Complete Google OAuth (local dev) |
| `GET` | `/oauth/microsoft/start` | None | Initiate Microsoft OAuth (local dev) |
| `GET` | `/oauth/microsoft/callback` | None | Complete Microsoft OAuth (local dev) |
| `GET` | `/v1/dev/connections` | None | Provider connection status (local dev) |
| `GET/POST` | `/v1/dev/google/*` | None | Direct Google provider calls (local dev) |
| `GET/POST` | `/v1/dev/microsoft/*` | None | Direct Microsoft provider calls (local dev) |
| `GET/POST` | `/v1/dev/plaid/*` | None | Plaid sandbox bootstrap + reads (local dev) |

`/v1/dev/*` and OAuth routes are only reachable via the local server — they are not exposed through API Gateway in deployed environments.

---

## CI/CD

### Workflows

| Workflow | Triggers | Jobs |
|----------|----------|------|
| `ci.yml` | Every PR, every push to `main` | `backend-tests` · `backend-lint` (ruff) · `backend-typecheck` (mypy) · `mobile-typecheck` · `terraform-validate` (dev/staging/prod) · `lambda-package-build` |
| `deploy-dev.yml` | Push to `main` | CI gate (tests, typecheck, terraform-validate) → build Lambda zip → write `terraform.tfvars` from GitHub vars/secrets → `terraform apply` → smoke test `/health` and `/v1/integrations` |
| `auto-fmt.yml` | Manual (`workflow_dispatch`) | `terraform fmt -recursive terraform` → commit if changed |

### Deploy pipeline detail

1. CI gate jobs run in parallel — deploy is blocked if any fail.
2. AWS credentials are obtained via OIDC (no long-lived keys). The IAM role is `ai-assistant-github-actions-deploy`, trusted only for the `dev` GitHub environment.
3. `terraform.tfvars` is written from GitHub Actions environment variables (not committed to the repo). Required variables are listed in the Configuration reference below.
4. Terraform plan + apply runs against the `dev` environment using the S3 remote state backend.
5. Post-deploy smoke tests hit `/health` (retries × 5, 30 s apart) and `/v1/integrations`.

### Concurrency

The `deploy-dev` workflow uses `concurrency: group: deploy-dev` with `cancel-in-progress: false`. Concurrent deploys to the same environment are queued, not cancelled.

---

## Branching policy

- `main` is the only long-lived branch. All commits land via pull request.
- A Claude Code branch policy hook (`hooks/branch-policy.sh`) blocks direct `git push` or `git merge` to `main` at the tool level.
- Feature branches use prefixes: `feature/`, `fix/`, `claude/`.
- CI runs on every PR. The deploy workflow runs on merge to `main`.
- Force-push to `main` and `master` is blocked in `.claude/settings.json`.

---

## Environments

| Environment | Status | API endpoint | Cognito domain | Mock mode |
|-------------|--------|--------------|----------------|-----------|
| dev | Deployed | `https://lbg6dypkqi.execute-api.us-east-1.amazonaws.com` | `https://ai-assistant-dev.auth.us-east-1.amazoncognito.com` | false (live providers) |
| staging | Not deployed | — | — | false |
| prod | Not deployed | — | — | false |

All environments are in `us-east-1`. Bedrock model: `us.amazon.nova-pro-v1:0` (Amazon Nova Pro).

---

## Configuration reference

### `backend/.env.local` (local dev — gitignored)

| Variable | Description |
|----------|-------------|
| `APP_ENV` | Runtime environment label (`dev`) |
| `LOG_LEVEL` | Log verbosity (`INFO`, `DEBUG`) |
| `LOCAL_SERVER_PORT` | Local server port (default `8787`) |
| `CORS_ALLOWED_ORIGINS` | Allowed CORS origins for local server |
| `MOCK_PROVIDER_MODE` | `true` = use mock providers, `false` = call real APIs |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth app credentials |
| `MICROSOFT_CLIENT_ID` / `MICROSOFT_CLIENT_SECRET` | Azure app registration credentials |
| `PLAID_CLIENT_ID` / `PLAID_SECRET` | Plaid API credentials |
| `PLAID_ENV` | Plaid environment (`sandbox`) |
| `BEDROCK_ROUTER_MODEL_ID` | Bedrock model ID for intent routing |
| `BEDROCK_GUARDRAIL_ID` / `BEDROCK_GUARDRAIL_VERSION` | Bedrock guardrail for content safety |
| `LOCAL_STORE_FILE` | Path to local OAuth token store (default `backend/.local/dev_tokens.json`) |

### `mobile/.env` (gitignored)

| Variable | Description |
|----------|-------------|
| `EXPO_PUBLIC_API_BASE_URL` | Base URL of the deployed API Gateway |
| `EXPO_PUBLIC_COGNITO_CLIENT_ID` | Cognito app client ID |
| `EXPO_PUBLIC_COGNITO_DOMAIN` | Cognito hosted UI base URL |

### GitHub Actions environment: `dev`

| Name | Type | Description |
|------|------|-------------|
| `AWS_DEPLOY_ROLE_ARN` | Secret | IAM role ARN assumed via OIDC for deploy |
| `TF_BACKEND_BUCKET` | Secret | S3 bucket name for Terraform remote state |
| `AWS_REGION` | Variable | AWS region (default `us-east-1`) |
| `MOCK_PROVIDER_MODE` | Variable | `false` for live providers |
| `TF_CORS_ORIGINS` | Variable | Allowed CORS origins (quoted, comma-separated) |
| `TF_CALLBACK_URLS` | Variable | Cognito OAuth callback URLs (quoted, comma-separated) |
| `TF_LOGOUT_URLS` | Variable | Cognito logout URLs (quoted, comma-separated) |
| `TF_BEDROCK_MODEL_ID` | Variable | Bedrock model ID |
| `TF_COGNITO_DOMAIN` | Variable | Cognito hosted UI prefix (e.g. `ai-assistant-dev`) |

### AWS Secrets Manager (dev)

| Secret path | Keys | KMS key |
|-------------|------|---------|
| `ai-assistant-dev/google-oauth` | `google-client-id`, `google-client-secret` | `alias/ai-assistant-dev` |
| `ai-assistant-dev/microsoft-oauth` | `microsoft-client-id`, `microsoft-client-secret` | `alias/ai-assistant-dev` |
| `ai-assistant-dev/plaid` | `plaid-client-id`, `plaid-secret` | `alias/ai-assistant-dev` |

---

## Scripts reference

| Script | Description |
|--------|-------------|
| `scripts/run-backend-tests.ps1` | Run the full pytest suite |
| `scripts/test-integrations.ps1` | Run integration smoke tests against the local server |
| `scripts/package-lambda.ps1` | Build `dist/orchestrator.zip` for manual Lambda upload |
| `scripts/validate-terraform.ps1` | Run `terraform fmt -check` + `terraform validate` locally |
| `scripts/start-provider-auth.ps1` | Open browser to initiate Google or Microsoft OAuth against the local server |

---

## Known limitations

- **No custom app scheme in `app.json`**: Expo Go testing uses `exp://` scheme URIs. Standalone / production builds require `"scheme": "ai-assistant"` added to `app.json` and the corresponding `ai-assistant://` callback URL registered in Cognito.
- **Staging and production not yet deployed**: Infrastructure config exists but no apply has run. Staging pipeline CI/CD does not exist yet (T-18).
- **Stateless backend**: No server-side conversation history. Each `/v1/chat/plan` call is independent.
- **Plaid in sandbox mode**: Local dev and dev environment use Plaid sandbox credentials. Production requires real Plaid credentials and Plaid's production access approval.
- **Reminders via calendar events**: Google and Microsoft native reminder/alert APIs are not used. Reminders are created as calendar events with reminder overrides.
- **No desktop or web client**: Mobile (Expo) only.

---

## External links

- GitHub repo: `https://github.com/ericreilly999/ai-assistant`
- Dev API: `https://lbg6dypkqi.execute-api.us-east-1.amazonaws.com`
- Dev Cognito hosted UI: `https://ai-assistant-dev.auth.us-east-1.amazoncognito.com`
- Google Cloud Console (OAuth credentials): `https://console.cloud.google.com/apis/credentials`
- Azure App Registrations (Microsoft OAuth): `https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps`
- Plaid Dashboard: `https://dashboard.plaid.com/developers/keys`
