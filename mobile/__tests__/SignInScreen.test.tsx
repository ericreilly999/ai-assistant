import React from "react";
import { fireEvent, render, waitFor } from "@testing-library/react-native";
import * as AuthSession from "expo-auth-session";
import * as WebBrowser from "expo-web-browser";

import { SignInScreen } from "../src/screens/SignInScreen";

jest.mock("expo-auth-session");
jest.mock("expo-web-browser");
jest.mock("../src/lib/auth", () => ({
  COGNITO_CLIENT_ID: "test-client-id",
  cognitoDiscovery: {
    authorizationEndpoint: "https://example.com/oauth2/authorize",
    tokenEndpoint: "https://example.com/oauth2/token",
  },
  exchangeCodeForTokens: jest.fn(),
  storeTokens: jest.fn(),
}));

const mockUseAuthRequest = AuthSession.useAuthRequest as jest.Mock;

beforeEach(() => {
  jest.clearAllMocks();
  (WebBrowser.maybeCompleteAuthSession as jest.Mock).mockReturnValue(undefined);
  (AuthSession.makeRedirectUri as jest.Mock).mockReturnValue("myapp://redirect");
});

describe("SignInScreen", () => {
  it("renders the sign-in button", () => {
    mockUseAuthRequest.mockReturnValue([{ codeVerifier: "verifier" }, null, jest.fn()]);

    const { getByTestId } = render(<SignInScreen onSignedIn={jest.fn()} />);
    expect(getByTestId("sign-in-button")).toBeTruthy();
  });

  it("disables the button when request is null", () => {
    mockUseAuthRequest.mockReturnValue([null, null, jest.fn()]);

    const { getByTestId } = render(<SignInScreen onSignedIn={jest.fn()} />);
    const button = getByTestId("sign-in-button");
    expect(button.props.accessibilityState?.disabled ?? button.props.disabled).toBeTruthy();
  });

  it("calls promptAsync when sign-in button is pressed", () => {
    const mockPromptAsync = jest.fn().mockResolvedValue(undefined);
    mockUseAuthRequest.mockReturnValue([{ codeVerifier: "verifier" }, null, mockPromptAsync]);

    const { getByTestId } = render(<SignInScreen onSignedIn={jest.fn()} />);
    fireEvent.press(getByTestId("sign-in-button"));
    expect(mockPromptAsync).toHaveBeenCalled();
  });

  it("shows error text on error response", () => {
    mockUseAuthRequest.mockReturnValue([
      { codeVerifier: "verifier" },
      { type: "error", error: { message: "access_denied" } },
      jest.fn(),
    ]);

    const { getByText } = render(<SignInScreen onSignedIn={jest.fn()} />);
    expect(getByText("access_denied")).toBeTruthy();
  });

  it("calls onSignedIn after successful token exchange", async () => {
    const { exchangeCodeForTokens, storeTokens } = require("../src/lib/auth");
    const mockTokens = { idToken: "id", accessToken: "access", refreshToken: "refresh" };
    exchangeCodeForTokens.mockResolvedValue(mockTokens);
    storeTokens.mockResolvedValue(undefined);

    const onSignedIn = jest.fn();
    mockUseAuthRequest.mockReturnValue([
      { codeVerifier: "verifier" },
      { type: "success", params: { code: "auth-code" } },
      jest.fn(),
    ]);

    render(<SignInScreen onSignedIn={onSignedIn} />);

    await waitFor(() => expect(onSignedIn).toHaveBeenCalledWith(mockTokens));
  });
});
