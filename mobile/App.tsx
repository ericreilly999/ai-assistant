import React, { useEffect, useState } from "react";
import { ActivityIndicator, StyleSheet, View } from "react-native";

import { ChatScreen } from "./src/screens/ChatScreen";
import { SignInScreen } from "./src/screens/SignInScreen";
import { AuthTokens, getStoredTokens } from "./src/lib/auth";

type AppState = "loading" | "unauthenticated" | "authenticated";

export default function App() {
  const [appState, setAppState] = useState<AppState>("loading");
  const [tokens, setTokens] = useState<AuthTokens | null>(null);

  useEffect(() => {
    getStoredTokens()
      .then((stored) => {
        if (stored) {
          setTokens(stored);
          setAppState("authenticated");
        } else {
          setAppState("unauthenticated");
        }
      })
      .catch(() => setAppState("unauthenticated"));
  }, []);

  const handleSignedIn = (newTokens: AuthTokens) => {
    setTokens(newTokens);
    setAppState("authenticated");
  };

  const handleSignOut = () => {
    setTokens(null);
    setAppState("unauthenticated");
  };

  if (appState === "loading") {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#1f6c57" />
      </View>
    );
  }

  if (appState === "unauthenticated" || !tokens) {
    return <SignInScreen onSignedIn={handleSignedIn} />;
  }

  return (
    <ChatScreen
      tokens={tokens}
      onSignOut={handleSignOut}
      onAuthError={handleSignOut}
    />
  );
}

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    backgroundColor: "#f4efe6",
    alignItems: "center",
    justifyContent: "center",
  },
});
