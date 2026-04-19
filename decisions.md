# Decisions Log — AI Assistant MVP

> Maintained by: specialist agents and Project Manager  
> Format: most recent first

---

## D-11 — DynamoDB Accepted for OAuth Token Storage (Revisit Before Multi-Tenant Scale)
**Date**: 2026-04-19
**Decision**: DynamoDB is approved as the OAuth token store for dev, staging, and prod MVP environments. Partition key is composite `{user_id}#{provider}` to enforce per-user token isolation. KMS CMK encryption and TTL are required on the table. This deviates from the original spec §4.3 (no DynamoDB) and §4.4 (no server-side token storage), which were written before the stateless Lambda + multi-provider OAuth persistence requirement was fully understood.
**Rationale**: DynamoDB with per-user partitioning, CMK encryption, and TTL is the standard enterprise pattern for OAuth token storage (used by Zapier, Salesforce, Google Workspace Marketplace apps, etc.). The alternative — Secrets Manager per user per provider — costs $0.40/secret/month and becomes expensive with multiple users and providers. Session-bound tokens degrade UX unacceptably for a personal assistant. The no-database constraint was intended to prevent user *data* persistence, not secure credential management infrastructure.
**Revisit trigger**: When approaching multi-tenant scale or any compliance requirement (SOC2, HIPAA). At that point, evaluate per-user KMS keys and/or migration of Plaid tokens specifically to Secrets Manager (consistent with D-04's spirit).
**Status**: Active — revisit before enterprise/compliance scale

---

## D-10 — Mock Provider Mode for Dev CI/CD
**Date**: ~2026-04-06  
**Decision**: Deploy to dev with `MOCK_PROVIDER_MODE=true` via CI/CD before live provider credentials are available.  
**Rationale**: Allows Lambda packaging, deployment, and pipeline validation to proceed independently of credential provisioning. Live provider testing is a separate sub-phase after the dev environment is confirmed healthy.  
**Status**: Active

---

## D-09 — Python 3.10 Compatibility Requirement
**Date**: ~2026-04-06  
**Decision**: Backend code must be compatible with Python 3.10 (the Lambda runtime version).  
**Rationale**: Lambda runtime constraint. Newer syntax not available in the execution environment.  
**Status**: Active

---

## D-08 — Single AWS Account with Namespace Isolation (Dev Phase)
**Date**: ~2026-03-16  
**Decision**: Use one AWS account with strict resource naming (`ai-assistant-dev-*`, `ai-assistant-staging-*`, etc.) rather than separate accounts per environment during early development.  
**Rationale**: Cost and operational overhead of multi-account AWS Organizations setup is not justified until the project reaches production readiness. Multi-account remains the preferred end-state (see spec §13.2).  
**Status**: Active — revisit before production go-live

---

## D-07 — S3 Native Locking for Terraform State (No DynamoDB)
**Date**: ~2026-03-16  
**Decision**: Use `use_lockfile = true` in Terraform S3 backend for state locking. No DynamoDB table.  
**Rationale**: Terraform 1.10+ supports native S3 locking. DynamoDB adds cost and operational complexity without benefit at this scale.  
**Status**: Active

---

## D-06 — Route-to-Live: Standard (dev → staging → prod)
**Date**: ~2026-03-16  
**Decision**: Use the Standard route-to-live: dev → staging → prod. Staging is a required gate before production.  
**Rationale**: User-facing mobile app with real financial and calendar data. Staging validation is non-negotiable before production exposure.  
**Status**: Active

---

## D-05 — Grocery List Backed by Existing Task Providers (No Standalone Storage)
**Date**: 2026-03-16  
**Decision**: Grocery list functionality is backed by a Google Tasks list named "Groceries" (or Microsoft To Do list named "Groceries"). No custom grocery database.  
**Rationale**: Avoids introducing a new database in MVP. Aligns with the no-application-database constraint (spec §4.3). User's data stays in their own provider account.  
**Status**: Active

---

## D-04 — Plaid Access Tokens Stored in AWS Secrets Manager
**Date**: 2026-03-16  
**Decision**: Plaid Item access tokens are stored in AWS Secrets Manager with KMS encryption, not in a custom application database or client-side code.  
**Rationale**: Plaid explicitly recommends server-side secure storage of access tokens. The only production-practical path without removing Plaid from the MVP. Client-side or session-bound Plaid access was ruled out as impractical.  
**Status**: Active — requires explicit sign-off if constraints change (see spec §21)

---

## D-03 — Custom Orchestration Over Bedrock Agents
**Date**: 2026-03-16  
**Decision**: Use custom orchestration code (Python Lambda + Bedrock Converse API) rather than Bedrock Agents in MVP.  
**Rationale**: Confirmation enforcement is easier to audit, routing is deterministic and testable, provider-specific failure handling is explicit, and there is no hidden planning behavior. Bedrock Agents can be evaluated after the tool contract surface stabilizes.  
**Status**: Active

---

## D-02 — Reminders via Calendar Events (Not Standalone Reminders API)
**Date**: 2026-03-16  
**Decision**: Google reminders are represented as Google Calendar events with reminder overrides. Microsoft 365 reminders are represented as Outlook calendar events with event reminder settings (`isReminderOn`, `reminderMinutesBeforeStart`).  
**Rationale**: No public standalone consumer Google Reminders API exists in the official docs. Using calendar events as the canonical reminder channel keeps the integration consistent across both providers.  
**Status**: Active

---

## D-01 — No Application Database in MVP
**Date**: 2026-03-16  
**Decision**: The MVP backend is intentionally stateless at the application layer. No DynamoDB, RDS, Aurora, Redis, or custom shadow stores.  
**Rationale**: Simplifies architecture, eliminates data retention risk, reduces cost, and satisfies the hard constraint that no user data is stored in an app-owned persistence layer. Allowed persistence: Terraform state (S3), CloudWatch, Bedrock prompt/guardrail versions, mobile device local secure storage.  
**Status**: Active
