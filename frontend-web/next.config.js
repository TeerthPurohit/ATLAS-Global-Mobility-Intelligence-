/** @type {import('next').NextConfig} */
const nextConfig = {
  // Disable StrictMode: stops React double-invoking effects/fetches in dev,
  // which was causing every API call to fire twice and the UI to feel sluggish.
  reactStrictMode: false,
  swcMinify: true,
  // Compress responses
  compress: true,
  // Faster image optimization
  images: {
    minimumCacheTTL: 60,
  },
  // Deduplicate fetch requests in the same render
  experimental: {
    optimizePackageImports: ["lucide-react", "@tanstack/react-query"],
  },
  // Reverse-proxies the browser's /api/* calls (incl. the /api/chat/stream
  // WebSocket -- Next's rewrite proxy supports upgrade requests for
  // external destinations) to the FastAPI backend server-side, so the
  // backend's real host/port is never sent to the browser. BACKEND_URL is
  // read here (server-only, no NEXT_PUBLIC_ prefix) -- never inlined into
  // the client bundle.
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.BACKEND_URL ?? "http://localhost:8000"}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
