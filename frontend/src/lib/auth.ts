import { betterAuth } from "better-auth";
import { nextCookies } from "better-auth/next-js";
import { genericOAuth } from "better-auth/plugins";
import { Pool } from "pg";

/**
 * Better Auth configuration for Enterprise AI Platform
 *
 * Uses Microsoft EntraID for enterprise SSO authentication.
 * Database tables are managed by better-auth in the same PostgreSQL instance.
 */
export const auth = betterAuth({
  // Database connection - uses same PostgreSQL as backend
  database: new Pool({
    connectionString: process.env.DATABASE_URL,
  }),

  // Base URL for auth endpoints
  baseURL: process.env.BETTER_AUTH_URL || "http://localhost:3001",

  // Session configuration
  session: {
    expiresIn: 60 * 60 * 24 * 7, // 7 days
    updateAge: 60 * 60 * 24, // Update session every 24 hours
    cookieCache: {
      enabled: true,
      maxAge: 60 * 5, // 5 minutes cache
    },
  },

  // User configuration
  user: {
    additionalFields: {
      tenantId: {
        type: "string",
        required: false,
      },
      department: {
        type: "string",
        required: false,
      },
      jobTitle: {
        type: "string",
        required: false,
      },
    },
  },

  // Microsoft EntraID as primary auth provider
  socialProviders: {
    microsoft: {
      clientId: process.env.AZURE_CLIENT_ID ?? "",
      clientSecret: process.env.AZURE_CLIENT_SECRET ?? "",
      tenantId: process.env.AZURE_TENANT_ID || "common",
      // Request additional scopes for user profile
      scope: ["openid", "profile", "email", "User.Read"],
    },
  },

  // Plugins
  plugins: [
    // Handle cookies in Next.js server actions
    nextCookies(),

    // Generic OAuth for additional enterprise providers if needed
    genericOAuth({
      config: [
        // Microsoft EntraID via generic OAuth (alternative to socialProviders)
        // Uncomment if you need more control over the OIDC flow
        // microsoftEntraId({
        //   clientId: process.env.AZURE_CLIENT_ID!,
        //   clientSecret: process.env.AZURE_CLIENT_SECRET!,
        //   tenantId: process.env.AZURE_TENANT_ID!,
        // }),
      ],
    }),
  ],

  // Advanced configuration
  advanced: {
    // Use cookies for session management
    useSecureCookies: process.env.NODE_ENV === "production",
  },

  // Trust host for production
  trustedOrigins: [
    "http://localhost:3001",
    "http://localhost:8000",
    process.env.BETTER_AUTH_URL || "",
  ].filter(Boolean),
});

// Export auth types for client
export type Session = typeof auth.$Infer.Session;
export type User = typeof auth.$Infer.Session.user;
