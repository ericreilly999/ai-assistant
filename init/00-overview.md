# AI Assistant MVP — Init Guide Overview

This `init/` directory contains step-by-step instructions for setting up, running, and deploying the AI Assistant MVP from scratch.

## Always Check Project Status First

> **Before starting any work, read `project-status.md` in the repo root.**
>
> `project-status.md` is the live source of truth for what is deployed, what is blocked, what credentials are loaded, and what the next steps are. It is updated after every significant change. The guides in this `init/` folder describe *how* to do things; `project-status.md` tells you *where things stand right now* so you don't repeat completed work or miss a prerequisite.
>
> Path: `ai-assistant/project-status.md`

## What This Project Is

A mobile-first personal assistant that accepts natural-language chat, reasons across connected productivity and finance systems (Google, Microsoft 365, Plaid), and proposes or executes actions only after explicit user approval. The backend runs on AWS Lambda + Amazon Bedrock. The mobile client is React Native / Expo.

## Guide Index

| File | Purpose |
|------|---------|
| `01-prerequisites.md` | Required tools, accounts, and credentials before anything else |
| `02-local-backend-setup.md` | Set up and run the Python Lambda backend locally |
| `03-local-mobile-setup.md` | Set up and run the React Native / Expo mobile app locally |
| `04-environment-config.md` | All environment variables and where they come from |
| `05-provider-auth.md` | Connecting Google, Microsoft, and Plaid locally |
| `06-running-tests.md` | Running all test suites (unit, integration, lint, type-check) |
| `07-terraform-setup.md` | Initializing and validating Terraform for each environment |
| `08-aws-deployment.md` | Deploying to dev, staging, and prod on AWS |
| `09-ci-cd.md` | CI/CD pipeline structure and how to promote releases |

## Architecture at a Glance

```
Mobile App (React Native / Expo)
  └─> Amazon API Gateway HTTP API
        └─> Lambda Authorizer (Cognito JWT)
        └─> Orchestrator Lambda (Python)
              ├─> Amazon Bedrock Converse + Guardrails
              ├─> Google APIs (Calendar, Tasks, Drive)
              ├─> Microsoft Graph (Calendar, To Do)
              └─> Plaid (read-only finance)
```

## Key Design Rules

- **No writes without explicit user consent.** Every mutating action goes through a `plan` → `approve` → `execute` flow.
- **No application database.** The backend is fully stateless. Mobile stores session artifacts in the device secure store.
- **Mock mode by default.** The backend runs with `MOCK_PROVIDER_MODE=true` so you can develop and test without live credentials.
- **Secrets in AWS Secrets Manager only.** Provider OAuth app credentials and Plaid tokens are never in environment files or source code.

## Quick Start (local mock mode)

```bash
# 1. Backend — run tests
cd ai-assistant
.\scripts\run-backend-tests.ps1

# 2. Mobile — start the dev server
cd mobile
npm install
npx expo start
```

See the individual guides for full setup details.
