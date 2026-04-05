import * as AuthSession from "expo-auth-session";
import * as WebBrowser from "expo-web-browser";
import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  SafeAreaView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import {
  AuthTokens,
  COGNITO_CLIENT_ID,
  cognitoDiscovery,
  exchangeCodeForTokens,
  storeTokens,
} from "../lib/auth";

// Required for Expo AuthSession to complete the redirect on web/managed workflow
WebBrowser.maybeCompleteAuthSession();

type Props = {
  onSignedIn: (tokens: AuthTokens) => void;
};

export function SignInScreen({ onSignedIn }: Props) {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const redirectUri = AuthSession.makeRedirectUri({ useProxy: false });

  const [request, response, promptAsync] = AuthSession.useAuthRequest(
    {
      clientId: COGNITO_CLIENT_ID,
      redirectUri,
      scopes: ["openid", "email", "profile"],
      usePKCE: true,
    },
    cognitoDiscovery,
  );

  useEffect(() => {
    if (!response) return;

    if (response.type === "success" && request?.codeVerifier) {
      setLoading(true);
      setError(null);
      exchangeCodeForTokens(response.params.code, request.codeVerifier, redirectUri)
        .then((tokens) => storeTokens(tokens).then(() => onSignedIn(tokens)))
        .catch((err: Error) => {
          setError(err.message ?? "Sign-in failed. Please try again.");
          setLoading(false);
        });
    } else if (response.type === "error") {
      setError(response.error?.message ?? "Sign-in failed. Please try again.");
    } else if (response.type === "cancel") {
      setLoading(false);
    }
  }, [response]);

  const handleSignIn = async () => {
    setError(null);
    setLoading(true);
    try {
      await promptAsync();
    } finally {
      // loading stays true until the useEffect above resolves or errors
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        <View style={styles.brandBlock}>
          <Text style={styles.eyebrow}>Personal Operations Assistant</Text>
          <Text style={styles.heading}>Your AI assistant for calendar, tasks, and more</Text>
          <Text style={styles.subtext}>
            Connect your calendar, tasks, and finance accounts. Review and approve every action before it runs.
          </Text>
        </View>

        {error ? <Text style={styles.errorText}>{error}</Text> : null}

        <TouchableOpacity
          testID="sign-in-button"
          style={[styles.button, (!request || loading) && styles.buttonDisabled]}
          disabled={!request || loading}
          onPress={handleSignIn}
        >
          {loading ? (
            <ActivityIndicator color="white" />
          ) : (
            <Text style={styles.buttonText}>Sign In</Text>
          )}
        </TouchableOpacity>

        <Text style={styles.disclaimer}>
          Your provider tokens are stored only on your device. No writes occur without your explicit approval.
        </Text>
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
    padding: 28,
    justifyContent: "center",
    gap: 24,
  },
  brandBlock: {
    gap: 10,
  },
  eyebrow: {
    color: "#8c5e34",
    fontSize: 13,
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 1.2,
  },
  heading: {
    color: "#1f140c",
    fontSize: 30,
    fontWeight: "700",
    lineHeight: 36,
  },
  subtext: {
    color: "#5f4a38",
    fontSize: 15,
    lineHeight: 22,
  },
  errorText: {
    color: "#b91c1c",
    fontSize: 14,
    backgroundColor: "#fef2f2",
    padding: 12,
    borderRadius: 10,
  },
  button: {
    backgroundColor: "#1f6c57",
    borderRadius: 16,
    paddingVertical: 18,
    alignItems: "center",
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: "white",
    fontSize: 17,
    fontWeight: "700",
  },
  disclaimer: {
    color: "#8c7b6e",
    fontSize: 12,
    textAlign: "center",
    lineHeight: 18,
  },
});
