import React, { useState } from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { ActionProposal } from "../types";

type Props = {
  proposal: ActionProposal;
  disabled?: boolean;
  onApprove: (proposal: ActionProposal) => void | Promise<void>;
  onReject: (proposal: ActionProposal) => void;
};

const RISK_COLORS: Record<string, string> = {
  high: "#b91c1c",
  medium: "#c2740a",
  low: "#166534",
};

export function ActionProposalCard({ proposal, disabled, onApprove, onReject }: Props) {
  const [payloadExpanded, setPayloadExpanded] = useState(false);
  const riskColor = RISK_COLORS[proposal.risk_level] ?? "#5f4a38";

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <Text style={styles.provider}>{proposal.provider}</Text>
        <View style={[styles.riskBadge, { backgroundColor: riskColor }]}>
          <Text style={styles.riskText}>{proposal.risk_level.toUpperCase()}</Text>
        </View>
      </View>

      <Text style={styles.summary}>{proposal.summary}</Text>

      <Text style={styles.meta}>
        Action: {proposal.action_type}
        {"  ·  "}
        Resource: {proposal.resource_type}
      </Text>
      <Text style={styles.meta}>Expires: {proposal.expires_at}</Text>

      <TouchableOpacity
        onPress={() => setPayloadExpanded((v) => !v)}
        accessibilityLabel="Toggle payload details"
      >
        <Text style={styles.payloadToggle}>
          {payloadExpanded ? "▾ Hide details" : "▸ Show details"}
        </Text>
      </TouchableOpacity>

      {payloadExpanded && (
        <View style={styles.payloadBox}>
          <Text style={styles.payloadText}>
            {JSON.stringify(proposal.payload, null, 2)}
          </Text>
        </View>
      )}

      <View style={styles.actionRow}>
        <TouchableOpacity
          testID={`reject-${proposal.proposal_id}`}
          style={[styles.rejectButton, disabled && styles.buttonDisabled]}
          disabled={disabled}
          onPress={() => onReject(proposal)}
        >
          <Text style={styles.rejectButtonText}>Reject</Text>
        </TouchableOpacity>

        <TouchableOpacity
          testID={`approve-${proposal.proposal_id}`}
          style={[styles.approveButton, disabled && styles.buttonDisabled]}
          disabled={disabled}
          onPress={() => onApprove(proposal)}
        >
          <Text style={styles.approveButtonText}>Approve</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#f9efe1",
    borderRadius: 16,
    padding: 16,
    gap: 8,
  },
  headerRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  provider: {
    color: "#8c5e34",
    fontSize: 12,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  riskBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 8,
  },
  riskText: {
    color: "white",
    fontSize: 10,
    fontWeight: "700",
    letterSpacing: 0.5,
  },
  summary: {
    color: "#24180f",
    fontSize: 16,
    fontWeight: "600",
  },
  meta: {
    color: "#5f4a38",
    fontSize: 13,
  },
  payloadToggle: {
    color: "#8c5e34",
    fontSize: 13,
    fontWeight: "600",
  },
  payloadBox: {
    backgroundColor: "#f4efe6",
    borderRadius: 8,
    padding: 10,
  },
  payloadText: {
    color: "#322418",
    fontSize: 11,
    fontFamily: "monospace",
  },
  actionRow: {
    flexDirection: "row",
    gap: 10,
    marginTop: 4,
  },
  rejectButton: {
    flex: 1,
    borderWidth: 1,
    borderColor: "#8c5e34",
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: "center",
  },
  rejectButtonText: {
    color: "#8c5e34",
    fontWeight: "700",
  },
  approveButton: {
    flex: 1,
    backgroundColor: "#1f6c57",
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: "center",
  },
  approveButtonText: {
    color: "white",
    fontWeight: "700",
  },
  buttonDisabled: {
    opacity: 0.6,
  },
});
