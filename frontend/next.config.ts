import type { NextConfig } from "next";

// 浏览器只访问前端同源的 /api/*,由 Next 服务端代理到后端。docker-compose 里
// 前后端同处一个网络,目标设为 http://backend:8000(服务名),无需把后端暴露公网,
// 也避免跨域。本地开发默认 http://localhost:8000。目标在构建/启动时由
// API_PROXY_TARGET 环境变量决定。
const API_PROXY_TARGET = process.env.API_PROXY_TARGET ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // Emit a self-contained .next/standalone build (+ server.js) so the Docker
  // runtime image needs neither node_modules nor `next start`.
  output: "standalone",
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${API_PROXY_TARGET}/:path*` },
    ];
  },
};

export default nextConfig;
