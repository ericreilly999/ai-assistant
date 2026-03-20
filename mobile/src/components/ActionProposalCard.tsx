import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { ActionProposal } from "../types";

type Props = {
  proposal: ActionProposal;
  disabled?: boolean;
  onApprove: (proposal: ActionProposal) => void | Promise<void>;
};

export function ActionProposalCard({ proposal, disabled, onApprove }: Props) {
  return (
    <View style={styles.card}>
      <Text style={styles.provider}>{proposal.provider}</Text>
      <Text style={styles.summary}>{proposal.summary}</Text>
      <Text style={styles.meta}>Action: {proposal.action_type}</Text>
      <Text style={styles.meta}>Expires: {proposal.expires_at}</Text>
      <TouchableOpacity style={[styles.button, disabled && styles.buttonDisabled]} disabled={disabled} onPress={() => onApprove(proposal)}>
        <Text style={styles.buttonText}>Approve write</Text>
      </TouchableOpacity>
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
  provider: {
    color: "#8c5e34",
    fontSize: 12,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 1,
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
  button: {
    marginTop: 8,
    backgroundColor: "#1f6c57",
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: "center",
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: "white",
    fontWeight: "700",
  },
});