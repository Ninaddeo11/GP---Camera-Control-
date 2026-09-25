/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // "standalone" is for the Docker self-host path (see Dockerfile, which
  // copies .next/standalone) — Vercel ignores this setting entirely and
  // uses its own build output automatically, so it's safe to deploy the
  // same config to both targets without a branch here.
  output: "standalone",
};

export default nextConfig;
