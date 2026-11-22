import type { NextConfig } from "next";

// Keep the dev server cache separate so `next build` cannot overwrite its chunks.
const nextConfig: NextConfig = {
  distDir: process.env.NODE_ENV === "development" ? ".next-dev" : ".next",
};

export default nextConfig;
