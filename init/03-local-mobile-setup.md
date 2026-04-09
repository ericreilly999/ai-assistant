# Local Mobile Setup

The mobile app is a React Native / Expo application. It connects to the backend via the API URL configured in `mobile/src/api.ts`.

## Directory Structure

```
mobile/
  src/
    api.ts              # Base URL and fetch helpers
    auth.ts             # Cognito sign-in flow and token storage
  __tests__/            # Jest unit tests
  App.tsx               # Root component — chat screen, approval modal
  app.json              # Expo configuration
  package.json
  tsconfig.json
```

## Step 1 — Install Dependencies

```bash
cd ai-assistant/mobile
npm install
```

## Step 2 — Configure the API URL

The default API base URL in `mobile/src/api.ts` points to `http://localhost:8787`. For local development against the backend mock this does not need changing.

To point at a deployed AWS environment, set the `EXPO_PUBLIC_API_BASE_URL` environment variable before starting:

```bash
export EXPO_PUBLIC_API_BASE_URL=https://api.dev.yourdomain.com
npx expo start
```

## Step 3 — Start the Expo Dev Server

```bash
cd ai-assistant/mobile
npx expo start
```

This opens the Expo developer tools. From there you can:
- Press `i` to open the iOS simulator (macOS only, requires Xcode)
- Press `a` to open the Android emulator (requires Android Studio)
- Scan the QR code with the Expo Go app on a physical device

## Step 4 — Authentication (local mock)

In local development against the mock backend, Cognito authentication is not enforced. The sign-in screen can be bypassed or pointed at a Cognito User Pool you create in the `dev` AWS environment.

To connect to a real Cognito User Pool:

1. Deploy the Terraform `dev` environment (see `07-terraform-setup.md`).
2. Copy the Cognito `user_pool_id` and `client_id` outputs.
3. Set them in `mobile/app.json` or as Expo environment variables:

```json
{
  "extra": {
    "cognitoUserPoolId": "us-east-1_XXXXXXXXX",
    "cognitoClientId": "XXXXXXXXXXXXXXXXXXXXXXXXXX",
    "cognitoRegion": "us-east-1"
  }
}
```

## Step 5 — Run Mobile Unit Tests

```bash
cd ai-assistant/mobile
npm test
```

Tests live in `mobile/__tests__/` and use Jest with React Native Testing Library.

## Key UI Flows

| Screen / Component | Description |
|---|---|
| Sign-in screen | Cognito hosted UI or in-app form |
| Chat screen | Multi-turn conversation with scroll-to-bottom |
| `ActionProposalCard` | Shows `resource_type`, `risk_level`, and payload details for proposed writes |
| Approval modal | Approve or reject button — rejection short-circuits the execute call |
| Error surface | API errors surfaced inline in the chat thread |
| Provider connection | Shows which of Google / Microsoft / Plaid are connected |

## Distribution

| Environment | Distribution method |
|---|---|
| `dev` | Expo internal build or direct device build |
| `staging` | TestFlight (iOS) + Play internal testing (Android) |
| `prod` | App Store + Google Play |
