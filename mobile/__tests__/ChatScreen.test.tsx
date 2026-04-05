import React from "react";
import { fireEvent, render, waitFor } from "@testing-library/react-native";

import { ChatScreen } from "../src/screens/ChatScreen";
import { AuthTokens } from "../src/lib/auth";

jest.mock("../src/lib/api", () => ({
  planMessage: jest.fn(),
  executeProposal: jest.fn(),
  AuthError: class AuthError extends Error {
    constructor(message = "Session expired") {
      super(message);
      this.name = "AuthError";
    }
  },
}));
jest.mock("../src/lib/auth", () => ({
  clearTokens: jest.fn().mockResolvedValue(undefined),
}));

const { planMessage, executeProposal, AuthError } = require("../src/lib/api");
const { clearTokens } = require("../src/lib/auth");

const TOKENS: AuthTokens = {
  idToken: "id-token",
  accessToken: "access-token",
  refreshToken: "refresh-token",
};

beforeEach(() => {
  jest.clearAllMocks();
});

describe("ChatScreen", () => {
  it("renders the initial assistant greeting", () => {
    const { getByText } = render(
      <ChatScreen tokens={TOKENS} onSignOut={jest.fn()} onAuthError={jest.fn()} />
    );
    expect(getByText(/Ask about your calendar/)).toBeTruthy();
  });

  it("renders the chat input and send button", () => {
    const { getByTestId } = render(
      <ChatScreen tokens={TOKENS} onSignOut={jest.fn()} onAuthError={jest.fn()} />
    );
    expect(getByTestId("chat-input")).toBeTruthy();
    expect(getByTestId("send-button")).toBeTruthy();
  });

  it("send button is disabled when input is empty", () => {
    const { getByTestId } = render(
      <ChatScreen tokens={TOKENS} onSignOut={jest.fn()} onAuthError={jest.fn()} />
    );
    const button = getByTestId("send-button");
    expect(button.props.accessibilityState?.disabled ?? button.props.disabled).toBeTruthy();
  });

  it("appends user message and assistant response on submit", async () => {
    planMessage.mockResolvedValue({
      message: "You have 2 meetings tomorrow.",
      proposals: [],
      sources: [],
      warnings: [],
    });

    const { getByTestId, getByText } = render(
      <ChatScreen tokens={TOKENS} onSignOut={jest.fn()} onAuthError={jest.fn()} />
    );

    fireEvent.changeText(getByTestId("chat-input"), "What's on my calendar?");
    fireEvent.press(getByTestId("send-button"));

    await waitFor(() => expect(getByText("What's on my calendar?")).toBeTruthy());
    await waitFor(() => expect(getByText("You have 2 meetings tomorrow.")).toBeTruthy());
    expect(planMessage).toHaveBeenCalledWith("What's on my calendar?", TOKENS.idToken);
  });

  it("shows error message on API failure", async () => {
    planMessage.mockRejectedValue(new Error("Network error"));

    const { getByTestId, getByText } = render(
      <ChatScreen tokens={TOKENS} onSignOut={jest.fn()} onAuthError={jest.fn()} />
    );

    fireEvent.changeText(getByTestId("chat-input"), "hello");
    fireEvent.press(getByTestId("send-button"));

    await waitFor(() => expect(getByText("Network error")).toBeTruthy());
  });

  it("calls onAuthError and clearTokens on AuthError", async () => {
    planMessage.mockRejectedValue(new AuthError());
    const onAuthError = jest.fn();

    const { getByTestId } = render(
      <ChatScreen tokens={TOKENS} onSignOut={jest.fn()} onAuthError={onAuthError} />
    );

    fireEvent.changeText(getByTestId("chat-input"), "hello");
    fireEvent.press(getByTestId("send-button"));

    await waitFor(() => expect(onAuthError).toHaveBeenCalled());
    expect(clearTokens).toHaveBeenCalled();
  });

  it("calls clearTokens and onSignOut when sign-out button is pressed", async () => {
    const onSignOut = jest.fn();

    const { getByTestId } = render(
      <ChatScreen tokens={TOKENS} onSignOut={onSignOut} onAuthError={jest.fn()} />
    );

    fireEvent.press(getByTestId("sign-out-button"));
    await waitFor(() => expect(onSignOut).toHaveBeenCalled());
    expect(clearTokens).toHaveBeenCalled();
  });

  it("calls executeProposal when a proposal is approved", async () => {
    const proposal = {
      proposal_id: "prop-1",
      provider: "google_calendar",
      action_type: "create_event",
      resource_type: "event",
      payload: { title: "Standup" },
      payload_hash: "abc",
      summary: "Create standup event",
      risk_level: "low",
      requires_confirmation: true,
      expires_at: "2026-04-06T00:00:00Z",
    };

    planMessage.mockResolvedValue({
      message: "Here is a proposed action.",
      proposals: [proposal],
      sources: [],
      warnings: [],
    });
    executeProposal.mockResolvedValue({ message: "Event created successfully." });

    const { getByTestId, getByText } = render(
      <ChatScreen tokens={TOKENS} onSignOut={jest.fn()} onAuthError={jest.fn()} />
    );

    fireEvent.changeText(getByTestId("chat-input"), "Schedule standup");
    fireEvent.press(getByTestId("send-button"));

    await waitFor(() => expect(getByTestId("approve-prop-1")).toBeTruthy());
    fireEvent.press(getByTestId("approve-prop-1"));

    await waitFor(() => expect(getByText("Event created successfully.")).toBeTruthy());
    expect(executeProposal).toHaveBeenCalledWith(proposal, TOKENS.idToken);
  });
});
