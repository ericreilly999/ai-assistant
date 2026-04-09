# Prerequisites

Complete everything in this file before moving to any other guide.

## Required Tools

### Python 3.12+

The backend Lambda code targets Python 3.12. The test runner and scripts look for a Python 3.12 or 3.13 installation.

- Download: https://www.python.org/downloads/
- Verify: `python --version` → should print `Python 3.12.x` or higher

### Node.js 20+ and npm

Required for the React Native / Expo mobile app.

- Download: https://nodejs.org/
- Verify: `node --version` and `npm --version`

### Expo CLI

```bash
npm install -g expo-cli
```

### Terraform 1.7+

Required to provision all AWS infrastructure.

- Download: https://developer.hashicorp.com/terraform/downloads
- Verify: `terraform version`

### tflint

Used in CI and local validation.

```bash
# Windows (Chocolatey)
choco install tflint

# Or download the binary from https://github.com/terraform-linters/tflint/releases
```

### tfsec or Checkov

Used for security scanning of Terraform plans.

```bash
# tfsec
choco install tfsec

# OR checkov via pip
pip install checkov
```

### AWS CLI v2

Required for Terraform state backend, Lambda packaging, and Secrets Manager access.

- Download: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
- Verify: `aws --version`

### PowerShell 7+

The helper scripts in `scripts/` are written for PowerShell. Windows ships with PS 5; upgrade to PS 7 for best results.

- Download: https://github.com/PowerShell/PowerShell/releases

---

## Required Accounts and Credentials

You need these before running in live mode. Mock mode works without any of them.

### AWS Account

- An AWS account (or sub-account under an AWS Organization) per environment (`dev`, `staging`, `prod`).
- An IAM user or role with permissions to create: Lambda, API Gateway, Cognito, Bedrock, Secrets Manager, KMS, S3, CloudWatch, IAM, Route 53, ACM.
- Configure the CLI: `aws configure` or set `AWS_PROFILE`.

### Google Cloud Project

1. Create a project at https://console.cloud.google.com/
2. Enable these APIs:
   - Google Calendar API
   - Google Tasks API
   - Google Drive API
3. Create an OAuth 2.0 Client ID (type: Web Application).
4. Add `http://localhost:<LOCAL_SERVER_PORT>/oauth/google/callback` as an authorized redirect URI.
5. Note the **Client ID** and **Client Secret** — these go into Secrets Manager later.

### Microsoft Azure App Registration

1. Register an app at https://portal.azure.com/ → Azure Active Directory → App registrations.
2. Add delegated permissions:
   - `Calendars.ReadWrite`
   - `Tasks.ReadWrite`
   - `offline_access`
   - `openid`, `profile`, `email`
3. Add `http://localhost:<LOCAL_SERVER_PORT>/oauth/microsoft/callback` as a redirect URI.
4. Note the **Application (client) ID**, **Directory (tenant) ID**, and a **Client Secret**.

### Plaid Developer Account

1. Sign up at https://dashboard.plaid.com/
2. Use the **Sandbox** environment for `dev`.
3. Note the **Client ID** and **Secret** for the Sandbox environment.

---

## Python Virtual Environment (recommended)

Set up a virtual environment in the `backend/` directory to isolate dependencies.

```bash
cd ai-assistant/backend
python -m venv .venv
# Windows
.\.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install ruff mypy
```

The backend itself uses only the Python standard library, so no additional pip installs are needed for the application code. `ruff` and `mypy` are needed for lint and type-check.

---

## Checklist

- [ ] Python 3.12+ installed and on PATH
- [ ] Node.js 20+ and npm installed
- [ ] Expo CLI installed globally
- [ ] Terraform 1.7+ installed
- [ ] tflint installed
- [ ] tfsec or Checkov installed
- [ ] AWS CLI v2 configured with appropriate credentials
- [ ] PowerShell 7+ installed
- [ ] Google Cloud project created with OAuth client
- [ ] Microsoft Azure app registration created
- [ ] Plaid sandbox credentials obtained
