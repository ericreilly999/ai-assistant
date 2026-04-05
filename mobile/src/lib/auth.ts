import * as AuthSession from "expo-auth-session";
import * as SecureStore from "expo-secure-store";

// ---------------------------------------------------------------------------
// Cognito configuration — set these in your .env / app.config.js
// ---------------------------------------------------------------------------
const COGNITO_DOMAIN =
  (globalThis as { process?: { env?: Record<string, string | undefined> } })
    .process?.env?.EXPO_PUBLIC_COGNITO_DOMAIN ?? "";

const CLIENT_ID =
  (globalThis as { process?: { env?: Record<string, string | undefined> } })
    .process?.env?.EXPO_PUBLIC_COGNITO_CLIENT_ID ?? "";

// ---------------------------------------------------------------------------
// Discovery document (Cognito hosted UI endpoints)
// ---------------------------------------------------------------------------
export const cognitoDiscovery: AuthSession.DiscoveryDocument = {
  authorizationEndpoint: `${COGNITO_DOMAIN}/oauth2/authorize`,
  tokenEndpoint: `${COGNITO_DOMAIN}/oauth2/token`,
  revocationEndpoint: `${COGNITO_DOMAIN}/oauth2/revoke`,
};

export const COGNITO_CLIENT_ID = CLIENT_ID;

// ---------------------------------------------------------------------------
// Secure token storage keys
// ---------------------------------------------------------------------------
const KEY_ID_TOKEN = "cognito_id_token";
const KEY_ACCESS_TOKEN = "cognito_access_token";
const KEY_REFRESH_TOKEN = "cognito_refresh_token";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export type AuthTokens = {
  idToken: string;
  accessToken: string;
  refreshToken: string | null;
};

// ---------------------------------------------------------------------------
// SecureStore helpers
// ---------------------------------------------------------------------------
export async function getStoredTokens(): Promise<AuthTokens | null> {
  const [idToken, accessToken, refreshToken] = await Promise.all([
    SecureStore.getItemAsync(KEY_ID_TOKEN),
    SecureStore.getItemAsync(KEY_ACCESS_TOKEN),
    SecureStore.getItemAsync(KEY_REFRESH_TOKEN),
  ]);
  if (!idToken || !accessToken) return null;
  return { idToken, accessToken, refreshToken: refreshToken ?? null };
}

export async function storeTokens(tokens: AuthTokens): Promise<void> {
  await Promise.all([
    SecureStore.setItemAsync(KEY_ID_TOKEN, tokens.idToken),
    SecureStore.setItemAsync(KEY_ACCESS_TOKEN, tokens.accessToken),
    tokens.refreshToken
      ? SecureStore.setItemAsync(KEY_REFRESH_TOKEN, tokens.refreshToken)
      : SecureStore.deleteItemAsync(KEY_REFRESH_TOKEN),
  ]);
}

export async function clearTokens(): Promise<void> {
  await Promise.all([
    SecureStore.deleteItemAsync(KEY_ID_TOKEN),
    SecureStore.deleteItemAsync(KEY_ACCESS_TOKEN),
    SecureStore.deleteItemAsync(KEY_REFRESH_TOKEN),
  ]);
}

// ---------------------------------------------------------------------------
// Token exchange (authorization code → tokens)
// ---------------------------------------------------------------------------
export async function exchangeCodeForTokens(
  code: string,
  codeVerifier: string,
  redirectUri: string,
): Promise<AuthTokens> {
  const result = await AuthSession.exchangeCodeAsync(
    {
      clientId: CLIENT_ID,
      code,
      redirectUri,
      extraParams: { code_verifier: codeVerifier },
    },
    cognitoDiscovery,
  );
  if (!result.idToken) {
    throw new Error("Cognito did not return an id_token. Ensure openid scope is requested.");
  }
  return {
    idToken: result.idToken,
    accessToken: result.accessToken,
    refreshToken: result.refreshToken ?? null,
  };
}

// ---------------------------------------------------------------------------
// Token refresh
// ---------------------------------------------------------------------------
export async function refreshTokens(refreshToken: string): Promise<AuthTokens> {
  const result = await AuthSession.refreshAsync(
    { clientId: CLIENT_ID, refreshToken },
    cognitoDiscovery,
  );
  if (!result.idToken) {
    throw new Error("Token refresh did not return an id_token.");
  }
  return {
    idToken: result.idToken,
    accessToken: result.accessToken,
    refreshToken: result.refreshToken ?? refreshToken,
  };
}
