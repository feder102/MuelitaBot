import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ['192.168.100.153', '100.124.221.119'],
  async rewrites() {
    return [
      {
        source: '/admin/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/admin/:path*`,
      },
    ];
  },
};

export default nextConfig;
