# AI Assistant Mobile App MVP Specification

Status: Draft v1.0  
Date: March 16, 2026  
Owner: Product + Platform Engineering

## 1. Executive Summary

Build a mobile-first personal assistant application that accepts natural-language chat requests, reasons across connected personal productivity and finance systems, and returns either:

- a read-only answer
- a proposed action plan that requires explicit user approval before any write

The MVP is deployed fully on AWS, uses Amazon Bedrock for intent routing and response generation, is provisioned with Terraform only, and ships with separate `dev`, `staging`, and `prod` environments.

The system must satisfy the following hard constraints:

- No writes without user consent.
- No sharing of user data between users.
- No application database in MVP.
- No server-side storage of end-user credentials or refresh tokens in app-owned persistence.

Because some requested integrations have platform constraints, this specification makes two explicit implementation assumptions:

1. Reminder support in MVP will be implemented through calendar events for both Google and Microsoft 365. Google does not expose a standalone public consumer Reminders API in the official docs used for this spec, so Google reminders are represented as Google Calendar events with reminder overrides; Microsoft 365 reminders are represented as Outlook calendar events with event reminder settings.
2. Infrastructure-level provider secrets required for OAuth and Plaid are stored only in AWS Secrets Manager with KMS encryption. If "no storing of secrets" must also forbid managed secret storage, Plaid cannot be included in a practical production MVP.

## 2. Product Goals

### 2.1 Primary Goal

Provide a trustworthy personal operations assistant that can:

- read calendars, tasks, reminders, documents, and finance context
- reason across those sources
- propose useful actions
- execute writes only after explicit confirmation

### 2.2 MVP Success Criteria

- A user can connect Google, Microsoft 365, Plaid, and app auth from a mobile client.
- A user can ask questions like "what does my day look like tomorrow?" and get an accurate synthesized answer.
- A user can ask the assistant to add or update tasks, reminders, grocery items, or calendar events and the system produces a reviewable action plan before any mutation.
- A user can fetch and summarize Google Drive documents for meeting preparation.
- All infrastructure is reproducible with Terraform and promoted safely across `dev`, `staging`, and `prod`.

### 2.3 Non-Goals for MVP

- No autonomous background writes.
- No desktop or web client.
- No long-term chat memory stored server-side.
- No internal grocery database.
- No multi-user shared workspaces.
- No generalized browser automation.
- No Bedrock Agents in v1 unless orchestration complexity proves custom orchestration insufficient.

## 3. Core Use Cases

### 3.1 Personal Operations Assistant

User asks: "What does my day look like tomorrow and do I have time to go to the gym?"

System behavior:

- read calendar events from Google Calendar or Microsoft 365
- normalize times to the user timezone
- calculate open windows
- return schedule plus recommendation

### 3.2 Grocery Planning Assistant

User asks: "Plan dinners for the next 3 days and add the ingredients to my grocery list."

System behavior:

- planner creates meal suggestions
- extractor converts ingredients into structured list items
- assistant proposes a write plan
- user approves
- system writes items to the designated grocery list provider

### 3.3 Smart Errand Batching

User asks: "I need groceries, a haircut, and to return an Amazon package this week."

System behavior:

- parse tasks and constraints
- read calendar availability
- optionally use mapped grocery/reminder/task sources
- generate a suggested block and task plan
- do not create holds or tasks without approval

### 3.4 Automated Meeting Preparation

User asks: "Prepare me for my 2pm architecture review."

System behavior:

- locate the matching calendar event
- fetch linked or related Google Drive documents
- summarize context, risks, and likely talking points

### 3.5 Travel Planning Assistant

User asks: "Plan a weekend trip to Miami next month."

System behavior:

- inspect calendar availability
- propose candidate weekends
- generate a draft itinerary
- optionally propose a calendar placeholder write for approval

## 4. Guardrails and Operating Principles

### 4.1 Consent-Only Writes

Every mutating action must use a two-step flow:

1. `plan`
2. `execute`

The `plan` response must include:

- action type
- provider
- target resource
- human-readable summary
- machine-readable payload
- risk classification
- consent requirement

The `execute` request must only be accepted when:

- the user is authenticated
- the action payload matches the previously proposed payload hash
- the action is still valid
- the user explicitly confirms

### 4.2 No Cross-User Data Sharing

- Every request is scoped to the signed-in user.
- No provider tokens are reused across users.
- Logs and traces must never contain raw provider payloads that could expose another user's data.

### 4.3 No Database in MVP

The MVP is intentionally stateless at the application layer.

Allowed persistence:

- Terraform state in S3
- CloudWatch logs and metrics
- Bedrock prompt and guardrail versions
- mobile-device local secure storage
- optional S3 storage for sanitized non-secret operational artifacts if explicitly required

Not allowed:

- DynamoDB
- RDS
- Aurora
- MongoDB
- Redis
- Elasticache
- a custom grocery/task/calendar shadow store

### 4.4 Secrets Handling

Hard rule:

- no end-user provider secrets or refresh tokens stored in any application database or server-side custom persistence

MVP implementation assumption:

- provider application credentials required to operate OAuth and Plaid are kept only in AWS Secrets Manager and decrypted at runtime with IAM + KMS
- mobile clients retain user session artifacts in iOS Keychain / Android Keystore
- backend accepts short-lived delegated access tokens per request where provider behavior allows it

If this assumption is rejected, remove Plaid from MVP and downgrade recurring provider access to session-bound operations only.

## 5. Functional Scope

### 5.1 Supported Integrations

The MVP must include at least these provider integrations:

1. Google Calendar
2. Google Tasks
3. Microsoft 365 Calendar
4. Microsoft To Do
5. Plaid
6. Google Drive

The "grocery list" experience is a first-class product feature, but in MVP it is backed by an existing task provider rather than a new database. The default backing store is:

- Google Tasks list named `Groceries` when Google is the primary task provider
- Microsoft To Do list named `Groceries` when Microsoft is the primary task provider

### 5.2 Integration Matrix

| Capability | Provider/API | Read | Write | MVP Notes |
| --- | --- | --- | --- | --- |
| Calendar events and reminders | Google Calendar API | Yes | Yes | Supports event read, create, update, cancel, and reminder overrides; canonical Google reminder channel in MVP |
| To-do lists and tasks | Google Tasks API | Yes | Yes | Used for task lists, tasks, and grocery items |
| Grocery list | Google Tasks or Microsoft To Do | Yes | Yes | No standalone storage; provider-backed list only |
| Calendar events and reminders | Microsoft Graph Calendar | Yes | Yes | Use `calendarView` for range-based reads; canonical Microsoft reminder channel in MVP |
| Task lists and tasks | Microsoft Graph To Do | Yes | Yes | Used for tasks and grocery items; not the primary reminder channel in MVP |
| Finance context | Plaid | Yes | No | Read-only in MVP; balances/accounts/transactions only |
| Documents | Google Drive API | Yes | No | Read metadata, export Google Workspace docs, summarize content |

### 5.3 Required User Flows

- Sign up / sign in to the mobile app.
- Connect Google account.
- Connect Microsoft account.
- Link Plaid account.
- Ask read-only chat question.
- Receive a structured write proposal.
- Approve or reject the proposal.
- Execute approved action.
- View final execution result.

### 5.4 Out-of-Scope Writes

- Plaid writes or money movement
- email sending
- contact writes
- cross-user sharing actions

## 6. External API Reality Constraints

### 6.1 Google

- Google Calendar supports events and reminder overrides on events.
- Google Tasks supports reading and updating task lists and tasks.
- Google Drive supports file search and export of Google Workspace docs.
- There is no public standalone consumer Google Reminders API documented in the sources used for this spec; therefore reminder support is implemented through Google Calendar events with reminder overrides. This is an inference.

### 6.2 Microsoft 365

- Microsoft Graph `calendarView` should be used for date-range reads because it returns occurrences, exceptions, and single instances.
- Microsoft Graph event resources support calendar-event reminder settings, including `isReminderOn` and `reminderMinutesBeforeStart`.
- Microsoft Graph To Do remains the task and grocery-list integration in MVP, but reminders are modeled as calendar events for consistency with Google.

### 6.3 Plaid

- Plaid expects server-side use of client credentials and secure handling of the Item access token.
- Plaid explicitly recommends storing the access token in a secure datastore and not in client-side code.
- Because this conflicts with the stated "no storing of secrets" constraint, one of the following must be approved:
  - store Plaid access tokens only in AWS Secrets Manager
  - require relinking or session-bound Plaid access for each use
  - remove Plaid from the production MVP

This spec proceeds with the first option because it is the only production-practical path.

## 7. Architecture

### 7.1 High-Level Design

```text
Mobile App
  -> API Gateway HTTP API
    -> Lambda Authorizer
    -> Orchestrator Lambda
      -> Bedrock Converse
      -> Bedrock Guardrails
      -> Provider Adapter Lambdas / in-process adapters
        -> Google APIs
        -> Microsoft Graph
        -> Plaid
      -> CloudWatch Logs / Metrics
```

### 7.2 Architectural Style

- Mobile-first client
- stateless serverless backend
- orchestration owned by application code, not by the model
- deterministic tool execution
- strong separation between planning and execution

### 7.3 Major Components

#### Mobile App

- React Native with Expo or React Native bare workflow
- secure local token storage
- chat UI
- approval sheet for write actions
- connected account management

#### API Layer

- Amazon API Gateway HTTP API
- JWT or Lambda authorizer
- route-level throttling
- request size limits

#### Orchestrator

- AWS Lambda running Python
- owns prompt selection, tool registry, validation, confirmation enforcement, and response shaping
- exposes `plan` and `execute` command paths

#### Model Layer

- Amazon Bedrock Converse API for chat-style interaction
- application inference profiles instead of hard-coded model IDs
- Prompt Management for router, planner, summarizer, and meeting prep templates
- Guardrails applied to both user input and model output

#### Provider Adapters

- Google adapter
- Microsoft adapter
- Plaid adapter
- each adapter validates inputs, normalizes outputs, and strips provider-specific noise before sending data to the model

### 7.4 Why Not Bedrock Agents in MVP

MVP should use custom orchestration plus Bedrock Converse because:

- confirmation enforcement is easier to audit
- deterministic routing is easier to test
- provider-specific failure handling is easier to control
- there is less hidden planning behavior

Bedrock Agents can be evaluated after the tool contract surface stabilizes.

## 8. Interaction Model

### 8.1 Request Types

- `read_only`
- `write_proposal_required`
- `unsupported`
- `clarification_required`

### 8.2 Plan Flow

1. client sends user message plus connected-provider context
2. orchestrator applies input guardrail
3. router determines intent and tool candidates
4. adapters fetch required data
5. planner produces:
   - final read answer, or
   - structured write proposal
6. output guardrail is applied
7. response returned to mobile app

### 8.3 Execute Flow

1. user approves proposed write
2. mobile app sends `execute` with proposal hash and provider token envelope
3. orchestrator validates consent, auth, freshness, and payload
4. orchestrator executes deterministic provider call
5. result is normalized and returned

### 8.4 Consent Expiration

- write proposals expire after 15 minutes
- expired proposals must be replanned

## 9. Domain Model

### 9.1 Core Objects

- `UserIdentity`
- `ConnectedProvider`
- `IntentClassification`
- `ToolInvocation`
- `ActionProposal`
- `ActionExecutionReceipt`
- `DocumentExcerpt`
- `CalendarAvailabilityWindow`
- `TaskItem`
- `FinancialSnapshot`

### 9.2 Action Proposal Schema

Each proposal must contain:

- `proposal_id`
- `user_id`
- `provider`
- `action_type`
- `resource_type`
- `resource_identifier`
- `payload`
- `payload_hash`
- `summary`
- `risk_level`
- `requires_confirmation`
- `expires_at`

## 10. Integration Specifications

### 10.1 Google Calendar

#### Supported Reads

- list events by date range
- get event by id
- calculate availability windows

#### Supported Writes

- create event
- update event title, times, location, notes
- cancel event
- override event reminders

#### Required OAuth Scopes

- `https://www.googleapis.com/auth/calendar.events` for event read/write
- `https://www.googleapis.com/auth/calendar.readonly` for read-only mode where applicable

#### Notes

- All-day and timed events must be treated distinctly.
- Reminder overrides must set `reminders.useDefault = false`.
- Google reminders are represented as calendar events in MVP; do not model them as Google Tasks items.

### 10.2 Google Tasks

#### Supported Reads

- list task lists
- list tasks within a list
- get grocery list items from configured `Groceries` list

#### Supported Writes

- create task
- update task
- complete task
- delete task
- create or update grocery items

#### Required OAuth Scopes

- `https://www.googleapis.com/auth/tasks`
- `https://www.googleapis.com/auth/tasks.readonly` for read-only mode where applicable

#### Notes

- Use Google Tasks for task lists, tasks, and grocery lists only. Google reminder behavior is handled through Google Calendar events in MVP.

### 10.3 Google Drive

#### Supported Reads

- search files by title or keyword
- fetch file metadata
- export Google Workspace docs to text-compatible formats for summarization

#### Supported Writes

- none in MVP

#### Required OAuth Scopes

- `https://www.googleapis.com/auth/drive.readonly`

#### Notes

- Google Workspace document export is limited by Google Drive export constraints.
- Only fetch files explicitly referenced by the user or directly linked from a matched calendar event.

### 10.4 Microsoft 365 Calendar

#### Supported Reads

- list events using `calendarView`
- fetch event details
- calculate availability windows

#### Supported Writes

- create event
- update event
- update event reminder settings
- cancel event

#### Required Graph Permissions

- `Calendars.ReadWrite` delegated

#### Notes

- Use `Prefer: outlook.timezone` to normalize response display behavior.
- Microsoft 365 reminders are represented as calendar events in MVP using event reminder settings such as `isReminderOn` and `reminderMinutesBeforeStart`.

### 10.5 Microsoft To Do

#### Supported Reads

- list task lists
- list tasks
- read grocery list items from configured `Groceries` list

#### Supported Writes

- create task
- update task
- mark complete

#### Required Graph Permissions

- `Tasks.ReadWrite` delegated

#### Notes

- Use Microsoft To Do for task lists, tasks, and grocery lists only. Reminder behavior is handled through Microsoft 365 calendar events in MVP.

### 10.6 Plaid

#### Supported Reads

- link item
- fetch accounts
- fetch balances
- fetch transactions for supported date windows

#### Supported Writes

- none

#### Plaid Products

- `transactions`
- `auth` only if account/routing verification becomes necessary later

#### Notes

- Read-only finance context only.
- No payment initiation or transfer workflows in MVP.

## 11. Security Requirements

### 11.1 Authentication

- App authentication uses Amazon Cognito User Pools.
- Mobile app receives JWTs for API authorization.
- Provider connections use delegated OAuth with PKCE where supported.

### 11.2 Authorization

- API requires authenticated user for all non-health routes.
- Every action is authorized against the requesting user identity.
- No admin route can inspect raw provider content in production.

### 11.3 IAM

- Separate IAM roles per Lambda function where practical.
- Least-privilege policies for Bedrock, Secrets Manager, CloudWatch, and KMS.
- No wildcard IAM permissions except where AWS service APIs require constrained service wildcards.

### 11.4 Encryption

- KMS encryption for Secrets Manager
- server-side encryption for S3 buckets
- TLS 1.2+ for all external calls
- provider tokens redacted from logs

### 11.5 Logging Rules

Never log:

- OAuth access tokens
- refresh tokens
- Plaid access tokens
- raw document content unless explicitly enabled in `dev`
- unredacted PII

Always log:

- request id
- user id hash
- route
- provider
- action type
- latency
- success/failure code

## 12. Observability and Operations

### 12.1 Metrics

- request count
- latency p50/p95/p99
- model latency
- tool latency by provider
- write proposal count
- write approval rate
- write success/failure rate
- guardrail block count

### 12.2 Alarms

- 5xx error rate above threshold
- Lambda duration above threshold
- Lambda throttles
- Bedrock invocation failures
- external provider error surge

### 12.3 Tracing

- correlation id across API Gateway, orchestrator, model call, and provider adapter
- AWS X-Ray optional in `dev` and `staging`, reduced sampling in `prod`

## 13. Environment Strategy

### 13.1 Environments

- `dev`: internal engineering environment
- `staging`: production-like pre-release validation
- `prod`: real user environment

### 13.2 AWS Account Strategy

Preferred:

- one AWS account per environment under AWS Organizations

Fallback:

- one account with strict namespace isolation if budget prevents account separation in early development

### 13.3 Environment Differences

#### dev

- relaxed logging for non-secret debug metadata
- sandbox Plaid
- test provider apps
- fastest Bedrock inference profile allowed

#### staging

- production-like settings
- real OAuth clients against test tenants where possible
- release candidate validation

#### prod

- reduced log verbosity
- strict alarms
- production custom domains
- manual promotion only

### 13.4 Mobile App Distribution

- `dev`: Expo internal builds or device builds
- `staging`: TestFlight + Play internal testing
- `prod`: App Store + Google Play

## 14. Terraform Specification

### 14.1 Terraform Standards

- Terraform version pinned in `required_version`
- provider versions pinned in `required_providers`
- all resources created through modules except tiny root-only glue
- no copy/pasted environment resources
- naming derived from `locals`
- tags standardized across all modules
- remote state stored in S3 with `use_lockfile = true`
- no DynamoDB state locking

### 14.2 Repository Layout

```text
/terraform
  /modules
    /api_gateway
    /lambda_function
    /lambda_authorizer
    /iam_role
    /cognito_user_pool
    /bedrock_guardrail
    /bedrock_prompt
    /bedrock_inference_profile
    /kms_key
    /secrets_manager_secret
    /cloudwatch_alarms
    /cloudwatch_dashboard
    /s3_bucket
    /route53_records
    /acm_certificate
  /environments
    /dev
    /staging
    /prod
```

### 14.3 Root Module Responsibilities

Each environment root module must:

- define backend config
- define environment variables
- instantiate shared modules
- wire outputs between modules
- avoid resource definitions that belong inside reusable modules

### 14.4 Required Terraform Modules

#### `lambda_function`

Creates:

- Lambda function
- execution role attachments
- log group
- environment variables
- optional reserved concurrency

#### `api_gateway`

Creates:

- HTTP API
- routes
- integrations
- stage
- throttling
- custom domain mappings

#### `lambda_authorizer`

Creates:

- Lambda authorizer function
- invoke permissions
- API Gateway authorizer resource

#### `cognito_user_pool`

Creates:

- user pool
- app clients
- custom domain if required
- groups if needed later

#### `bedrock_guardrail`

Creates or manages:

- guardrail base resource
- version references by environment

#### `bedrock_prompt`

Creates or manages:

- router prompt
- planner prompt
- summarizer prompt
- meeting prep prompt

#### `bedrock_inference_profile`

Creates:

- application inference profile for each environment

#### `secrets_manager_secret`

Creates:

- provider credentials secret
- rotation configuration only where supported and approved

### 14.5 Environment Variables

Each environment must define at minimum:

- `APP_ENV`
- `AWS_REGION`
- `BEDROCK_ROUTER_PROFILE_ARN`
- `BEDROCK_SUMMARY_PROFILE_ARN`
- `BEDROCK_GUARDRAIL_ID`
- `BEDROCK_GUARDRAIL_VERSION`
- `GOOGLE_OAUTH_SECRET_ARN`
- `MICROSOFT_OAUTH_SECRET_ARN`
- `PLAID_SECRET_ARN`
- `CORS_ALLOWED_ORIGINS`

### 14.6 Networking

MVP Lambdas should run outside a VPC unless a specific compliance control requires private networking. Rationale:

- no database access
- no NAT gateway cost
- simpler outbound access to Google, Microsoft, Plaid, and Bedrock

### 14.7 State Management

- separate state key per environment
- S3 bucket versioning enabled
- S3 server-side encryption enabled
- `use_lockfile = true`

## 15. CI/CD

### 15.1 Branch Strategy

- `main`: releasable code
- short-lived feature branches
- tagged releases for staging and prod promotion

### 15.2 Pull Request Checks

- mobile lint
- backend lint
- backend unit tests
- mobile unit tests
- Terraform `fmt -check`
- Terraform `validate`
- `tflint`
- `tfsec` or `checkov`
- build/package Lambda artifact

### 15.3 Deployment Flow

1. merge to `main` deploys `dev`
2. release candidate tag deploys `staging`
3. manual approval deploys `prod`

### 15.4 Rollback

- Lambda version rollback via alias shift
- API config rollback via previous Terraform state and artifact version
- mobile rollback through store release reversion strategy

## 16. Testing Strategy

### 16.1 Test Categories

- unit tests
- contract tests
- integration tests
- smoke tests
- prompt regression tests
- infrastructure validation tests

### 16.2 Backend Unit Tests

Target:

- 90%+ coverage for domain, validation, and orchestration code

Mandatory unit coverage:

- intent classification wrappers
- proposal generation
- consent enforcement
- payload hashing and expiry
- provider response normalization
- error mapping
- guardrail decision handling

### 16.3 Mobile Unit Tests

Mandatory coverage:

- chat screen state transitions
- approval modal behavior
- token/session handling
- provider connection state rendering
- optimistic UI disabled for writes until execution success

### 16.4 Contract Tests

Provider adapters must include contract tests for:

- Google Calendar event normalization
- Google Tasks list and task normalization
- Google Drive export parsing
- Microsoft calendar view mapping
- Microsoft 365 calendar reminder mapping
- Plaid account and transaction mapping

### 16.5 Prompt Regression Tests

Maintain golden test cases for:

- schedule question
- grocery plan
- errand batching
- meeting prep
- travel planning
- malicious prompt injection attempt
- write without consent attempt

Each prompt regression suite must verify:

- correct intent
- no unauthorized write execution
- response structure validity
- no leakage of secrets or hidden system instructions

### 16.6 Infrastructure Tests

- `terraform plan` succeeds in each environment root
- module input validation tests
- policy snapshot checks for least privilege
- smoke deploy into `dev`

### 16.7 End-to-End Smoke Tests

For `staging`, run automated smoke tests that:

- sign in
- connect sandbox/test providers
- ask a read-only calendar question
- generate a grocery list proposal
- approve and execute a non-destructive test write
- fetch a Google Drive document summary

## 17. API Contract

### 17.1 `POST /v1/chat/plan`

Request:

- user message
- connected provider context
- provider token envelope references
- locale and timezone

Response:

- assistant message
- optional `action_proposals[]`
- source references
- warnings

### 17.2 `POST /v1/chat/execute`

Request:

- `proposal_id`
- `payload_hash`
- explicit `approved = true`
- provider token envelope references

Response:

- execution result
- updated resource summary
- provider receipt metadata

### 17.3 `GET /v1/integrations`

Returns:

- supported providers
- connection status
- capability flags

## 18. Performance Targets

- p95 read-only request latency under 8 seconds
- p95 write-plan request latency under 10 seconds
- p95 execute request latency under 6 seconds excluding third-party outage conditions
- cold start impact minimized with provisioned concurrency only if justified by usage

## 19. Definition of Done

The MVP is complete when:

1. Mobile apps run in `dev`, `staging`, and `prod`.
2. Terraform can provision all required infrastructure from clean state.
3. All six integrations above are functional within defined MVP scope.
4. No write occurs without explicit approval.
5. No application database is used.
6. Unit, contract, prompt regression, and smoke tests pass in CI.
7. Production alarms and dashboards exist.
8. Secrets and tokens are redacted from logs.

## 20. Delivery Phases

### Phase 1: Foundation

- Terraform foundation
- Cognito
- API Gateway
- orchestrator Lambda
- Bedrock prompt + guardrail setup
- mobile chat shell

### Phase 2: Google Productivity

- Google Calendar
- Google Tasks
- Google Drive
- grocery list backed by Google Tasks

### Phase 3: Microsoft Productivity

- Microsoft 365 Calendar
- Microsoft To Do
- grocery list provider switching

### Phase 4: Finance and Hardening

- Plaid integration
- staging smoke tests
- prod alarms
- release readiness

## 21. Open Decisions Requiring Explicit Sign-Off

1. Confirm whether AWS Secrets Manager is acceptable for provider application secrets and Plaid Item access tokens. If not, Plaid must be removed or sharply reduced.
2. Confirm whether grocery list should default to Google Tasks, Microsoft To Do, or be user-selectable at onboarding.
3. Confirm whether the first release is single-user only or supports multiple independent users from day one.
4. Confirm whether Google Drive fetch should be read-only metadata + export only, or whether file comments and attachments are needed later.

## 22. Source Notes

Key platform facts used in this specification were verified from official vendor documentation on March 16, 2026, including:

- Amazon Bedrock Converse, Guardrails, Prompt Management, and inference profiles
- HashiCorp Terraform S3 backend locking
- Google Calendar, Tasks, and Drive APIs
- Microsoft Graph Calendar and To Do APIs
- Plaid Auth and token handling guidance
