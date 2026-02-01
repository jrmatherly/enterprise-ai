import { createAuthClient } from "better-auth/react";
import { genericOAuthClient } from "better-auth/client/plugins";

/**
 * Better Auth client for React components
 * 
 * Provides hooks and methods for authentication:
 * - useSession() - Get current session
 * - signIn.social() - Sign in with Microsoft
 * - signOut() - Sign out
 */
export const authClient = createAuthClient({
  // Base URL of the auth server (same origin in our case)
  baseURL: typeof window !== "undefined" ? window.location.origin : "",
  
  plugins: [
    // Support for generic OAuth providers
    genericOAuthClient(),
  ],
});

// Export commonly used methods and hooks
export const {
  signIn,
  signOut,
  signUp,
  useSession,
  getSession,
} = authClient;

/**
 * Sign in with Microsoft EntraID
 */
export async function signInWithMicrosoft(callbackURL: string = "/") {
  return signIn.social({
    provider: "microsoft",
    callbackURL,
  });
}

/**
 * Sign out and redirect to home
 */
export async function signOutAndRedirect(redirectURL: string = "/") {
  return signOut({
    fetchOptions: {
      onSuccess: () => {
        window.location.href = redirectURL;
      },
    },
  });
}
