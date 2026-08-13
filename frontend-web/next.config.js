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
};

module.exports = nextConfig;
