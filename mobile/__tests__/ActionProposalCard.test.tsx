import React from "react";
import { StyleSheet } from "react-native";
import { fireEvent, render } from "@testing-library/react-native";

import { ActionProposalCard } from "../src/components/ActionProposalCard";
import { ActionProposal } from "../src/types";

const makeProposal = (overrides: Partial<ActionProposal> = {}): ActionProposal => ({
  proposal_id: "prop-test",
  provider: "google_calendar",
  action_type: "create_event",
  resource_type: "event",
  payload: { title: "Team lunch", date: "2026-04-06" },
  payload_hash: "hash123",
  summary: "Create team lunch event",
  risk_level: "low",
  requires_confirmation: true,
  expires_at: "2026-04-06T00:00:00Z",
  ...overrides,
});

describe("ActionProposalCard", () => {
  it("renders summary and provider", () => {
    const proposal = makeProposal();
    const { getByText } = render(
      <ActionProposalCard proposal={proposal} onApprove={jest.fn()} onReject={jest.fn()} />
    );
    expect(getByText("Create team lunch event")).toBeTruthy();
    expect(getByText("google_calendar".toUpperCase())).toBeTruthy();
  });

  it("renders risk level badge text", () => {
    const proposal = makeProposal({ risk_level: "high" });
    const { getByText } = render(
      <ActionProposalCard proposal={proposal} onApprove={jest.fn()} onReject={jest.fn()} />
    );
    expect(getByText("HIGH")).toBeTruthy();
  });

  it("renders resource_type in meta", () => {
    const proposal = makeProposal({ resource_type: "calendar_event" });
    const { getByText } = render(
      <ActionProposalCard proposal={proposal} onApprove={jest.fn()} onReject={jest.fn()} />
    );
    expect(getByText(/calendar_event/)).toBeTruthy();
  });

  it("calls onApprove with proposal when approve button is pressed", () => {
    const proposal = makeProposal();
    const onApprove = jest.fn();
    const { getByTestId } = render(
      <ActionProposalCard proposal={proposal} onApprove={onApprove} onReject={jest.fn()} />
    );
    fireEvent.press(getByTestId("approve-prop-test"));
    expect(onApprove).toHaveBeenCalledWith(proposal);
  });

  it("calls onReject with proposal when reject button is pressed", () => {
    const proposal = makeProposal();
    const onReject = jest.fn();
    const { getByTestId } = render(
      <ActionProposalCard proposal={proposal} onApprove={jest.fn()} onReject={onReject} />
    );
    fireEvent.press(getByTestId("reject-prop-test"));
    expect(onReject).toHaveBeenCalledWith(proposal);
  });

  it("approve and reject buttons are disabled when disabled prop is true", () => {
    const proposal = makeProposal();
    const { getByTestId } = render(
      <ActionProposalCard proposal={proposal} disabled onApprove={jest.fn()} onReject={jest.fn()} />
    );
    const approveBtn = getByTestId("approve-prop-test");
    const rejectBtn = getByTestId("reject-prop-test");
    expect(approveBtn.props.accessibilityState?.disabled ?? approveBtn.props.disabled).toBeTruthy();
    expect(rejectBtn.props.accessibilityState?.disabled ?? rejectBtn.props.disabled).toBeTruthy();
  });

  it("toggles payload details when show/hide details is pressed", () => {
    const proposal = makeProposal();
    const { getByText, queryByText } = render(
      <ActionProposalCard proposal={proposal} onApprove={jest.fn()} onReject={jest.fn()} />
    );
    expect(queryByText(/Team lunch/)).toBeNull();
    fireEvent.press(getByText(/Show details/));
    expect(getByText(/Team lunch/)).toBeTruthy();
    fireEvent.press(getByText(/Hide details/));
    expect(queryByText(/Team lunch/)).toBeNull();
  });

  it("high risk badge uses red color", () => {
    const proposal = makeProposal({ risk_level: "high" });
    const { getByTestId } = render(
      <ActionProposalCard proposal={proposal} onApprove={jest.fn()} onReject={jest.fn()} />
    );
    const flat = StyleSheet.flatten(getByTestId("risk-badge").props.style);
    expect(flat.backgroundColor).toBe("#b91c1c");
  });

  it("medium risk badge uses orange color", () => {
    const proposal = makeProposal({ risk_level: "medium" });
    const { getByTestId } = render(
      <ActionProposalCard proposal={proposal} onApprove={jest.fn()} onReject={jest.fn()} />
    );
    const flat = StyleSheet.flatten(getByTestId("risk-badge").props.style);
    expect(flat.backgroundColor).toBe("#c2740a");
  });

  it("low risk badge uses green color", () => {
    const proposal = makeProposal({ risk_level: "low" });
    const { getByTestId } = render(
      <ActionProposalCard proposal={proposal} onApprove={jest.fn()} onReject={jest.fn()} />
    );
    const flat = StyleSheet.flatten(getByTestId("risk-badge").props.style);
    expect(flat.backgroundColor).toBe("#166534");
  });
});
