import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n.ts");

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  poweredByHeader: false,
  transpilePackages: ["@complymate/ui", "@complymate/api-types"],
  outputFileTracingRoot: new URL("../..", import.meta.url).pathname,
};

export default withNextIntl(nextConfig);
