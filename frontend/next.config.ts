import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",

  // API proxy is now handled by src/app/api/v1/[...path]/route.ts
  // This ensures cookies are properly forwarded to the backend
};

export default nextConfig;
