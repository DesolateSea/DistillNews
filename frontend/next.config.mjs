/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  devIndicators: false,
  compress: true,
  reactStrictMode: true,
  experimental: {
    // Let the API return its bounded 60-second chat timeout instead of
    // dropping the socket while cold-start indexing/provider calls run.
    proxyTimeout: 75000,
  },
  async rewrites() {
    const backend = (process.env.BACKEND_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
    return [{ source: "/api/:path*", destination: `${backend}/:path*` }];
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  images: {
    unoptimized: true,
  },
}

export default nextConfig
