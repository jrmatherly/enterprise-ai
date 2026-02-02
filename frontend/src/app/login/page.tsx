"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { signInWithMicrosoft } from "@/lib/auth-client";

function LoginForm() {
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl") || "/";
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSignIn = async () => {
    setIsLoading(true);
    setError(null);

    try {
      await signInWithMicrosoft(callbackUrl);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed");
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-sm">
      {/* Logo/Header */}
      <div className="mb-8 text-center">
        <div className="mx-auto mb-4 flex size-16 items-center justify-center rounded-2xl bg-neutral-800">
          <svg
            className="size-8 text-blue-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"
            />
          </svg>
        </div>
        <h1 className="text-2xl font-semibold text-neutral-100">
          Enterprise AI Platform
        </h1>
        <p className="mt-2 text-sm text-neutral-400">
          Sign in to access your AI assistant
        </p>
      </div>

      {/* Sign In Card */}
      <div className="rounded-xl border border-neutral-800 bg-neutral-900 p-6">
        {error && (
          <div className="mb-4 rounded-lg border border-red-900/50 bg-red-950/30 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        <button
          type="button"
          onClick={handleSignIn}
          disabled={isLoading}
          className="flex w-full items-center justify-center gap-3 rounded-lg bg-neutral-800 px-4 py-3 text-sm font-medium text-neutral-100 transition-colors hover:bg-neutral-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isLoading ? (
            <div className="size-5 animate-spin rounded-full border-2 border-neutral-400 border-t-transparent" />
          ) : (
            <>
              {/* Microsoft Logo */}
              <svg className="size-5" viewBox="0 0 21 21" fill="none">
                <title>Microsoft Logo</title>
                <rect x="1" y="1" width="9" height="9" fill="#F25022" />
                <rect x="11" y="1" width="9" height="9" fill="#7FBA00" />
                <rect x="1" y="11" width="9" height="9" fill="#00A4EF" />
                <rect x="11" y="11" width="9" height="9" fill="#FFB900" />
              </svg>
              Sign in with Microsoft
            </>
          )}
        </button>

        <p className="mt-4 text-center text-xs text-neutral-500">
          Use your organization account to sign in
        </p>
      </div>

      {/* Footer */}
      <p className="mt-6 text-center text-xs text-neutral-600">
        Protected by enterprise-grade security
      </p>
    </div>
  );
}

function LoginFormSkeleton() {
  return (
    <div className="w-full max-w-sm animate-pulse">
      <div className="mb-8 text-center">
        <div className="mx-auto mb-4 flex size-16 items-center justify-center rounded-2xl bg-neutral-800" />
        <div className="mx-auto h-7 w-48 rounded bg-neutral-800" />
        <div className="mx-auto mt-2 h-4 w-56 rounded bg-neutral-800" />
      </div>
      <div className="rounded-xl border border-neutral-800 bg-neutral-900 p-6">
        <div className="h-12 w-full rounded-lg bg-neutral-800" />
        <div className="mx-auto mt-4 h-3 w-48 rounded bg-neutral-800" />
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <div className="flex min-h-dvh items-center justify-center bg-neutral-950 px-4">
      <Suspense fallback={<LoginFormSkeleton />}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
