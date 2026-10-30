import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  poweredByHeader: false,
  transpilePackages: ["@complymate/ui", "@complymate/api-types"],
  outputFileTracingRoot: new URL("../..", import.meta.url).pathname,
};

export default nextConfig;
