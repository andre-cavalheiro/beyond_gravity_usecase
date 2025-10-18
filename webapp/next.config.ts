import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    domains: ["lh3.googleusercontent.com"], // ✅ allow Google avatar URLs
  },
};

export default nextConfig;
