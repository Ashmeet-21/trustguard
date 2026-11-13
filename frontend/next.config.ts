import type { NextConfig } from "next";

const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
      // Used by ServerWakeNotice to wake the free-tier backend
      { source: "/health", destination: `${backendUrl}/health` },
    ];
  },
};

export default nextConfig;
