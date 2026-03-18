import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactCompiler: true,
  experimental: {
    ppr: true,
    clientSegmentCache: true
  }
};

export default nextConfig;
