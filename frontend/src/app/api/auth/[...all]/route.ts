import { auth } from "@/lib/auth";
import { toNextJsHandler } from "better-auth/next-js";

/**
 * Better Auth API route handler
 * 
 * Handles all authentication endpoints:
 * - /api/auth/sign-in/*
 * - /api/auth/sign-out
 * - /api/auth/callback/*
 * - /api/auth/session
 * - etc.
 */
export const { GET, POST } = toNextJsHandler(auth);
