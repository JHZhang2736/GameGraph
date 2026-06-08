import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emit a self-contained .next/standalone build (+ server.js) so the Docker
  // runtime image needs neither node_modules nor `next start`.
  output: "standalone",
};

export default nextConfig;
