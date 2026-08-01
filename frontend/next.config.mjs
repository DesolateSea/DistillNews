/** @type {import('next').NextConfig} */
const isBuild = process.env.NODE_ENV === 'production' && process.env.BUILD_STANDALONE === 'true';

const nextConfig = {
  ...(isBuild ? { output: "standalone" } : {}),
  devIndicators: false,
  compress: true,
  reactStrictMode: true,
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
}

export default nextConfig
