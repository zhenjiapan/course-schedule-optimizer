import type {NextConfig} from "next";
const configuredLimit = Number(process.env.V4_MAX_TIMEOUT_SECONDS ?? 180);
const solverLimitSeconds = Number.isSafeInteger(configuredLimit) ? Math.max(30, configuredLimit) : 180;
const config: NextConfig = {
  experimental: {
    // Keep the rewrite open through the solver deadline and response overhead.
    proxyTimeout: (solverLimitSeconds + 15) * 1000,
  },
  async rewrites() {
    const origin = process.env.PLANNER_API_URL ?? "http://127.0.0.1:8000";
    return [{source:"/api/:path*", destination:`${origin}/api/:path*`}];
  },
};
export default config;
