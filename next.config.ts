import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    const target = process.env.API_PROXY_TARGET ||
      (process.env.NODE_ENV !== "production" ? "http://127.0.0.1:8000" : "");
    return target ? [{ source: "/api/:path*", destination: `${target}/api/:path*` }] : [];
  },
  /* config options here */
  typescript: {
    ignoreBuildErrors: true,
  },
  reactStrictMode: false,
};

export default nextConfig;
