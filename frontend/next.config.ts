import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Turbopack native bindings unavailable on this machine — use webpack
  bundlePagesRouterDependencies: true,
};

export default nextConfig;
