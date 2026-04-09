# Environment Configuration

All environment variables are read in `backend/src/assistant_app/config.py`. This file lists every variable, its purpose, and where it comes from in each environment.

## Variable Reference

| Variable | Required | Description | Local dev value | AWS source |
|---|---|---|---|---|
| `APP_ENV` | Yes | `dev`, `staging`, or `prod` | `dev` | Terraform `lambda_function` module |
| `AWS_REGION` | Yes | AWS region for all service calls | `us-east-1` | Lambda execution environment |
| `MOCK_PROVIDER_MODE` | Yes | `true` disables all live provider and Bedrock calls | `true` | Terraform variable |
| `CORS_ALLOWED_ORIGINS` | Yes | Comma-separated allowed origins for CORS | `http://localhost:8081` | Terraform variable |
| `LOCAL_SERVER_PORT` | Dev only | Port used by `start-provider-auth.ps1` for local OAuth redirect | `8787` | Not deployed to Lambda |
| `BEDROCK_ROUTER_PROFILE_ARN` | Live only | ARN of the Bedrock application inference profile used for intent routing | — | Terraform output |
| `BEDROCK_SUMMARY_PROFILE_ARN` | Live only | ARN of the Bedrock inference profile used for summarization | — | Terraform output |
| `BEDROCK_GUARDRAIL_ID` | Live only | ID of the Bedrock Guardrail resource | — | Terraform output |
| `BEDROCK_GUARDRAIL_VERSION` | Live only | Version of the Bedrock Guardrail to apply | — | Terraform output |
| `GOOGLE_OAUTH_SECRET_ARN` | Live only | ARN of the Secrets Manager secret containing Google OAuth credentials | — | Terraform output |
| `MICROSOFT_OAUTH_SECRET_ARN` | Live only | ARN of the Secrets Manager secret containing Microsoft OAuth credentials | — | Terraform output |
| `PLAID_SECRET_ARN` | Live only | ARN of the Secrets Manager secret containing Plaid credentials | — | Terraform output |

## Secrets Manager Secret Shape

Each secret is a JSON object. The Lambda reads and parses it at cold start via `secrets_manager.py`.

### `GOOGLE_OAUTH_SECRET_ARN`

```json
{
  "client_id": "...",
  "client_secret": "...",
  "redirect_uri": "https://api.dev.yourdomain.com/oauth/google/callback"
}
```

### `MICROSOFT_OAUTH_SECRET_ARN`

```json
{
  "client_id": "...",
  "client_secret": "...",
  "tenant_id": "common",
  "redirect_uri": "https://api.dev.yourdomain.com/oauth/microsoft/callback"
}
```

### `PLAID_SECRET_ARN`

```json
{
  "client_id": "...",
  "secret": "...",
  "environment": "sandbox"
}
```

## Environment Differences

### dev

```hcl
mock_provider_mode    = false   # set to true for early development before live credentials
app_env               = "dev"
cors_allowed_origins  = "https://dev.yourdomain.com"
```

- Relaxed CloudWatch log verbosity.
- Plaid sandbox environment.
- Test OAuth apps (not production).
- Fastest available Bedrock inference profile.

### staging

```hcl
mock_provider_mode    = false
app_env               = "staging"
cors_allowed_origins  = "https://staging.yourdomain.com"
```

- Production-like settings.
- Real OAuth clients against test tenants where possible.

### prod

```hcl
mock_provider_mode    = false
app_env               = "prod"
cors_allowed_origins  = "https://yourdomain.com"
```

- Minimum log verbosity (no debug metadata).
- Strict CloudWatch alarms.
- Manual promotion only — never deployed automatically.

## tfvars Files

Each environment has a `terraform.tfvars.example` file under `terraform/environments/<env>/`. Copy it to `terraform.tfvars` (gitignored) and fill in real values:

```bash
cp terraform/environments/dev/terraform.tfvars.example terraform/environments/dev/terraform.tfvars
```

**Never commit `terraform.tfvars` files.** They contain ARN references and may contain sensitive placeholders.
