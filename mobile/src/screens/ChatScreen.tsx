import React, { useCallback, useRef, useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { ActionProposalCard } from "../components/ActionProposalCard";
import { AuthError, executeProposal, planMessage } from "../lib/api";
import { AuthTokens, clearTokens } from "../lib/auth";
import { ActionProposal, ChatMessage } from "../types";

type Props = {
  tokens: AuthTokens;
  onSignOut: () => void;
  onAuthError: () => void;
};

let messageCounter = 0;
function nextId() {
  return `msg-${++messageCounter}`;
}

export function ChatScreen({ tokens, onSignOut, onAuthError }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: nextId(),
      role: "assistant",
      text: "Ask about your calendar, groceries, meeting prep, or travel planning.",
      warnings: [
        "Connect your providers via the integrations page after deployment.",
      ],
    },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<ScrollView>(null);

  const appendMessage = useCallback((msg: ChatMessage) => {
    setMessages((prev) => [...prev, msg]);
    // Scroll to bottom after state update
    setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 50);
  }, []);

  const handleAuthError = useCallback(async () => {
    await clearTokens();
    onAuthError();
  }, [onAuthError]);

  const submitPrompt = async () => {
    const text = input.trim();
    if (!text || busy) return;

    setInput("");
    setBusy(true);

    appendMessage({ id: nextId(), role: "user", text });

    try {
      const response = await planMessage(text, tokens.idToken);
      appendMessage({
        id: nextId(),
        role: "assistant",
        text: response.message,
        proposals: response.proposals,
        sources: response.sources,
        warnings: response.warnings,
      });
    } catch (err) {
      if (err instanceof AuthError) {
        await handleAuthError();
        return;
      }
      appendMessage({
        id: nextId(),
        role: "assistant",
        text: err instanceof Error ? err.message : "Something went wrong. Please try again.",
        isError: true,
      });
    } finally {
      setBusy(false);
    }
  };

  const approveProposal = async (proposal: ActionProposal) => {
    setBusy(true);
    try {
      const result = await executeProposal(proposal, tokens.idToken);
      appendMessage({
        id: nextId(),
        role: "assistant",
        text: result.message,
      });
    } catch (err) {
      if (err instanceof AuthError) {
        await handleAuthError();
        return;
      }
      appendMessage({
        id: nextId(),
        role: "assistant",
        text: err instanceof Error ? err.message : "Execution failed. Please try again.",
        isError: true,
      });
    } finally {
      setBusy(false);
    }
  };

  const rejectProposal = (proposal: ActionProposal) => {
    appendMessage({
      id: nextId(),
      role: "assistant",
      text: `Action cancelled: ${proposal.summary}`,
    });
  };

  const handleSignOut = async () => {
    await clearTokens();
    onSignOut();
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={Platform.OS === "ios" ? 0 : 0}
      >
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Assistant</Text>
          <TouchableOpacity testID="sign-out-button" onPress={handleSignOut} style={styles.signOutButton}>
            <Text style={styles.signOutText}>Sign Out</Text>
          </TouchableOpacity>
        </View>

        <ScrollView
          ref={scrollRef}
          style={styles.messageList}
          contentContainerStyle={styles.messageListContent}
          onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
        >
          {messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              message={msg}
              busy={busy}
              onApprove={approveProposal}
              onReject={rejectProposal}
            />
          ))}
          {busy && (
            <View style={styles.typingIndicator}>
              <Text style={styles.typingText}>Thinking…</Text>
            </View>
          )}
        </ScrollView>

        <View style={styles.inputRow}>
          <TextInput
            testID="chat-input"
            editable={!busy}
            placeholder="Ask about tomorrow, groceries, meetings…"
            placeholderTextColor="#a89180"
            value={input}
            onChangeText={setInput}
            style={styles.input}
            multiline
            returnKeyType="send"
            onSubmitEditing={submitPrompt}
          />
          <TouchableOpacity
            testID="send-button"
            style={[styles.sendButton, (!input.trim() || busy) && styles.sendButtonDisabled]}
            disabled={!input.trim() || busy}
            onPress={submitPrompt}
          >
            <Text style={styles.sendButtonText}>↑</Text>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// ---------------------------------------------------------------------------
// MessageBubble — renders a single chat message
// ---------------------------------------------------------------------------
type BubbleProps = {
  message: ChatMessage;
  busy: boolean;
  onApprove: (proposal: ActionProposal) => void | Promise<void>;
  onReject: (proposal: ActionProposal) => void;
};

function MessageBubble({ message, busy, onApprove, onReject }: BubbleProps) {
  const isUser = message.role === "user";
  return (
    <View style={[styles.bubbleWrapper, isUser && styles.bubbleWrapperUser]}>
      <View
        style={[
          styles.bubble,
          isUser ? styles.bubbleUser : styles.bubbleAssistant,
          message.isError && styles.bubbleError,
        ]}
      >
        <Text style={[styles.bubbleText, isUser && styles.bubbleTextUser]}>
          {message.text}
        </Text>
      </View>

      {message.warnings?.map((w) => (
        <Text key={w} style={styles.warningText}>
          ⚠ {w}
        </Text>
      ))}

      {message.proposals?.map((p) => (
        <ActionProposalCard
          key={p.proposal_id}
          proposal={p}
          disabled={busy}
          onApprove={onApprove}
          onReject={onReject}
        />
      ))}
    </View>
  );
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------
const styles = StyleSheet.create({
  flex: { flex: 1 },
  safeArea: {
    flex: 1,
    backgroundColor: "#f4efe6",
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#e8ddd0",
  },
  headerTitle: {
    color: "#1f140c",
    fontSize: 18,
    fontWeight: "700",
  },
  signOutButton: {
    padding: 6,
  },
  signOutText: {
    color: "#8c5e34",
    fontSize: 14,
    fontWeight: "600",
  },
  messageList: {
    flex: 1,
  },
  messageListContent: {
    padding: 16,
    gap: 12,
  },
  bubbleWrapper: {
    gap: 8,
    alignItems: "flex-start",
  },
  bubbleWrapperUser: {
    alignItems: "flex-end",
  },
  bubble: {
    maxWidth: "82%",
    borderRadius: 18,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  bubbleUser: {
    backgroundColor: "#1f6c57",
    borderBottomRightRadius: 4,
  },
  bubbleAssistant: {
    backgroundColor: "#fffaf3",
    borderBottomLeftRadius: 4,
  },
  bubbleError: {
    backgroundColor: "#fef2f2",
  },
  bubbleText: {
    color: "#322418",
    fontSize: 15,
    lineHeight: 22,
  },
  bubbleTextUser: {
    color: "white",
  },
  warningText: {
    color: "#955d11",
    fontSize: 12,
    paddingHorizontal: 4,
  },
  typingIndicator: {
    paddingHorizontal: 4,
  },
  typingText: {
    color: "#8c7b6e",
    fontSize: 14,
    fontStyle: "italic",
  },
  inputRow: {
    flexDirection: "row",
    alignItems: "flex-end",
    padding: 12,
    gap: 10,
    borderTopWidth: 1,
    borderTopColor: "#e8ddd0",
    backgroundColor: "#f4efe6",
  },
  input: {
    flex: 1,
    minHeight: 44,
    maxHeight: 120,
    backgroundColor: "#fffaf3",
    borderRadius: 22,
    paddingHorizontal: 16,
    paddingVertical: 10,
    color: "#1f140c",
    fontSize: 15,
  },
  sendButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: "#1f6c57",
    alignItems: "center",
    justifyContent: "center",
  },
  sendButtonDisabled: {
    opacity: 0.4,
  },
  sendButtonText: {
    color: "white",
    fontSize: 20,
    fontWeight: "700",
  },
});
