/**
 * Configuration contract tests: redirect URI scheme consistency
 *
 * These tests exist to prevent a class of silent breakage discovered during
 * T-12 manual smoke testing (2026-04-18): upgrading Expo SDK 53 → 54 caused
 * AuthSession.makeRedirectUri() to start honouring the `scheme` field in
 * app.json, changing the generated URI from `exp://...` to `ai-assistant://`.
 * The Cognito app client's callback_urls still contained only `exp://` URIs,
 * so every OAuth sign-in attempt was rejected by Cognito with "an error was
 * encountered".
 *
 * Root cause: the `native` parameter was omitted from the makeRedirectUri()
 * call in SignInScreen.tsx. Expo SDK 54 changed the default fallback behaviour
 * and started using the custom scheme from app.json instead of `exp://`.
 *
 * Fix (applied by Application Engineer): pass `{ native: 'ai-assistant://' }`
 * explicitly so that standalone/bare builds always return the registered URI.
 *
 * Why two test approaches are used:
 *
 *   Test A uses static analysis (reading SignInScreen.tsx as text). It does
 *   not call the real makeRedirectUri() because expo-constants is a nested
 *   transitive dependency not resolvable from the test environment, and
 *   existing tests already mock expo-auth-session entirely. Static analysis
 *   directly catches the original bug class (omitting `native` or using the
 *   wrong scheme string) without SDK environment constraints.
 *
 *   Test B reads terraform.tfvars directly. It is a configuration contract
 *   test that catches mismatches between app.json and Terraform configuration
 *   before they reach a deployed environment.
 */

import * as fs from "fs";
import * as path from "path";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Resolve a path relative to the mobile package root (one level above __tests__) */
const fromMobileRoot = (...parts: string[]) =>
  path.resolve(__dirname, "..", ...parts);

/** Resolve a path relative to the repository root (two levels above __tests__) */
const fromRepoRoot = (...parts: string[]) =>
  path.resolve(__dirname, "..", "..", ...parts);

// ---------------------------------------------------------------------------
// Test A — makeRedirectUri call in SignInScreen.tsx uses { native: <scheme>:// }
//
// Validates via static analysis that:
//   1. app.json defines a custom scheme
//   2. SignInScreen.tsx calls makeRedirectUri with a `native` parameter
//   3. The `native` value in that call matches the scheme from app.json
//
// This test will fail if:
//   - The `scheme` field is removed from app.json
//   - The scheme value is changed in app.json without updating SignInScreen.tsx
//   - The `native` parameter is removed from the makeRedirectUri() call
//   - The hardcoded scheme string in SignInScreen.tsx drifts from app.json
//
// Static analysis is used deliberately here rather than calling makeRedirectUri()
// at runtime. expo-constants is a transitive dependency nested inside
// expo-auth-session and expo-linking, and is not resolvable as a jest.mock()
// target from this test file without adding moduleNameMapper configuration.
// The static check is sufficient: it catches the exact change that caused the
// original bug (removing or misspecifying the `native` parameter).
// ---------------------------------------------------------------------------

describe("makeRedirectUri call in SignInScreen.tsx uses native scheme from app.json (Test A)", () => {
  let appScheme: string;
  let signInScreenSource: string;

  beforeAll(() => {
    // Read scheme from app.json
    const appJsonPath = fromMobileRoot("app.json");
    expect(fs.existsSync(appJsonPath)).toBe(true);
    const appJson = JSON.parse(fs.readFileSync(appJsonPath, "utf-8"));
    appScheme = appJson?.expo?.scheme;

    // Read SignInScreen.tsx source
    const screenPath = fromMobileRoot("src", "screens", "SignInScreen.tsx");
    expect(fs.existsSync(screenPath)).toBe(true);
    signInScreenSource = fs.readFileSync(screenPath, "utf-8");
  });

  it("app.json expo.scheme is defined and non-empty", () => {
    expect(typeof appScheme).toBe("string");
    expect(appScheme.length).toBeGreaterThan(0);
  });

  it("SignInScreen.tsx calls makeRedirectUri with a native parameter", () => {
    // The `native` parameter is what guarantees standalone/bare builds return
    // the correct URI. Omitting it was the original bug.
    expect(signInScreenSource).toMatch(/makeRedirectUri\s*\(\s*\{[^}]*native\s*:/);
  });

  it("the native value in makeRedirectUri matches the scheme defined in app.json", () => {
    // The scheme string in the source must match what is in app.json.
    // This catches drift between the two files.
    const expectedNativeUri = `${appScheme}://`;
    // Match: native: 'ai-assistant://' or native: "ai-assistant://"
    const nativeParamPattern = new RegExp(
      `native\\s*:\\s*['"\`]${escapeRegExp(expectedNativeUri)}['"\`]`,
    );
    expect(signInScreenSource).toMatch(nativeParamPattern);
  });

  it("app.json scheme does not contain characters that would be invalid in a URI scheme", () => {
    // URI schemes must match [a-zA-Z][a-zA-Z0-9+\-.]*
    // An invalid scheme would be silently ignored by some OAuth providers.
    expect(appScheme).toMatch(/^[a-zA-Z][a-zA-Z0-9+\-.]*$/);
  });
});

// ---------------------------------------------------------------------------
// Test B — Terraform callback_urls includes the native scheme URI
//
// Reads terraform/environments/dev/terraform.tfvars and asserts that at least
// one entry in callback_urls begins with the native scheme from app.json.
//
// This is a configuration contract test. It will fail if:
//   - The scheme in app.json is changed without updating terraform.tfvars
//   - Someone removes the native scheme entry from terraform.tfvars
//   - A new environment tfvars file is created without the native URI
//
// Note: This test only covers the dev environment. If staging / production
// tfvars files are added they should be tested here too.
// ---------------------------------------------------------------------------

describe("Terraform callback_urls includes native scheme URI (Test B)", () => {
  let appScheme: string;
  let callbackUrls: string[];

  beforeAll(() => {
    // Read scheme from app.json
    const appJsonPath = fromMobileRoot("app.json");
    const appJson = JSON.parse(fs.readFileSync(appJsonPath, "utf-8"));
    appScheme = appJson?.expo?.scheme;
    expect(typeof appScheme).toBe("string");

    // Read and parse terraform.tfvars — extract the callback_urls list.
    // The file uses HCL list syntax:
    //   callback_urls = [
    //     "value1",
    //     "value2",
    //   ]
    const tfvarsPath = fromRepoRoot(
      "terraform",
      "environments",
      "dev",
      "terraform.tfvars",
    );
    expect(fs.existsSync(tfvarsPath)).toBe(true);
    const tfvarsRaw = fs.readFileSync(tfvarsPath, "utf-8");

    // Extract the callback_urls block and pull out all quoted string values
    const blockMatch = tfvarsRaw.match(/callback_urls\s*=\s*\[([^\]]*)\]/s);
    expect(blockMatch).not.toBeNull();
    const blockContent = blockMatch![1];
    const urlMatches = blockContent.matchAll(/"([^"]+)"/g);
    callbackUrls = Array.from(urlMatches, (m) => m[1]);
  });

  it("terraform.tfvars callback_urls list is non-empty", () => {
    expect(callbackUrls.length).toBeGreaterThan(0);
  });

  it("callback_urls contains at least one URI starting with the native scheme from app.json", () => {
    // The Expo SDK 54 fix requires that ai-assistant:// (or whatever the
    // current scheme is) appears as a registered Cognito callback URL.
    // Without this entry Cognito rejects the OAuth redirect with
    // "an error was encountered" on all standalone/native builds.
    const nativePrefix = `${appScheme}://`;
    const hasNativeSchemeUri = callbackUrls.some((url) =>
      url.startsWith(nativePrefix),
    );

    expect(hasNativeSchemeUri).toBe(true);
  });

  it("every callback_url entry is a non-empty string", () => {
    callbackUrls.forEach((url) => {
      expect(typeof url).toBe("string");
      expect(url.length).toBeGreaterThan(0);
    });
  });

  it("callback_urls does not contain duplicate entries", () => {
    const unique = new Set(callbackUrls);
    expect(unique.size).toBe(callbackUrls.length);
  });
});

// ---------------------------------------------------------------------------
// Utility
// ---------------------------------------------------------------------------

function escapeRegExp(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
