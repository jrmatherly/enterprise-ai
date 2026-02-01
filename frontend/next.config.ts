import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'standalone',
  
  // API proxy for development (avoids CORS issues)
  // In Docker: BACKEND_URL=http://backend:8000
  // Local dev: falls back to localhost:8000
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    return [
      {
        source: '/api/v1/:path*',
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
