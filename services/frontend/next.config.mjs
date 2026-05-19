/** @type {import('next').NextConfig} */
const nextConfig = {
  // Standalone output → a self-contained server bundle for a small,
  // air-gappable Docker image.
  output: "standalone",
  experimental: {
    // BFF route handlers use `pg`; keep it external so the server build
    // doesn't try to bundle the driver.
    serverComponentsExternalPackages: ["pg"],
  },
};

export default nextConfig;
