/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    const api = process.env.API_PROXY_TARGET;
    if (!api) return [];
    const base = api.replace(/\/$/, "");
    return [
      { source: "/api/:path*", destination: `${base}/api/:path*` },
      { source: "/health", destination: `${base}/health` },
      { source: "/health/:path*", destination: `${base}/health/:path*` },
    ];
  },
};

export default nextConfig;
