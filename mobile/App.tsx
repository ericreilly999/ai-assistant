import React, { useMemo, useState } from "react";
import {
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { ActionProposalCard } from "./src/components/ActionProposalCard";
import { executeProposal, planMessage } from "./src/lib/api";
import { ActionProposal, PlanResponse } from "./src/types";

const initialResponse: PlanResponse = {
  intent: "general",
  message: "Ask about your calendar, groceries, meeting prep, or travel planning.",
  proposals: [],
  sources: [],
  warnings: ["The mobile shell points at the Lambda API once environment variables are configured."],
};

export default function App() {
  const [message, setMessage] = useState("");
  const [response, setResponse] = useState<PlanResponse>(initialResponse);
  const [busy, setBusy] = useState(false);
  const warnings = useMemo(() => response.warnings ?? [], [response.warnings]);

  const submitPrompt = async () => {
    if (!message.trim()) {
      return;
    }

    setBusy(true);
    try {
      const nextResponse = await planMessage(message.trim());
      setResponse(nextResponse);
      setMessage("");
    } finally {
      setBusy(false);
    }
  };

  const approveProposal = async (proposal: ActionProposal) => {
    setBusy(true);
    try {
      const execution = await executeProposal(proposal);
      setResponse({
        intent: response.intent,
        message: execution.message,
        proposals: [],
        sources: response.sources,
        warnings,
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="dark-content" />
      <View style={styles.container}>
        <Text style={styles.eyebrow}>Personal Operations Assistant</Text>
        <Text style={styles.heading}>Chat-first automation with consent-gated writes</Text>
        <ScrollView style={styles.panel} contentContainerStyle={styles.panelContent}>
          <Text style={styles.responseText}>{response.message}</Text>
          {warnings.map((warning) => (
            <Text key={warning} style={styles.warningText}>
              {warning}
            </Text>
          ))}
          {response.proposals.map((proposal) => (
            <ActionProposalCard key={proposal.proposal_id} proposal={proposal} disabled={busy} onApprove={approveProposal} />
          ))}
        </ScrollView>
        <TextInput
          editable={!busy}
          placeholder="Ask about tomorrow, groceries, meetings, or travel..."
          value={message}
          onChangeText={setMessage}
          style={styles.input}
          multiline
        />
        <TouchableOpacity style={[styles.button, busy && styles.buttonDisabled]} disabled={busy} onPress={submitPrompt}>
          <Text style={styles.buttonText}>{busy ? "Working..." : "Send"}</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#f4efe6",
  },
  container: {
    flex: 1,
    padding: 20,
    gap: 12,
  },
  eyebrow: {
    color: "#8c5e34",
    fontSize: 14,
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 1.2,
  },
  heading: {
    color: "#1f140c",
    fontSize: 28,
    fontWeight: "700",
  },
  panel: {
    flex: 1,
    backgroundColor: "#fffaf3",
    borderRadius: 18,
  },
  panelContent: {
    padding: 18,
    gap: 14,
  },
  responseText: {
    color: "#322418",
    fontSize: 16,
    lineHeight: 24,
  },
  warningText: {
    color: "#955d11",
    fontSize: 13,
  },
  input: {
    minHeight: 92,
    backgroundColor: "#fffaf3",
    borderRadius: 16,
    padding: 16,
    textAlignVertical: "top",
    color: "#1f140c",
  },
  button: {
    backgroundColor: "#1f6c57",
    borderRadius: 16,
    paddingVertical: 16,
    alignItems: "center",
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: "white",
    fontSize: 16,
    fontWeight: "700",
  },
});