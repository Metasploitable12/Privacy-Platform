/** @type {import('next').NextConfig} */
const nextConfig = {
  // Rewrites so the SPA can call /api/* in dev without CORS friction;
  // in production this is instead handled by the Nginx reverse proxy
  // (see nginx/nginx.conf), so this rewrite is dev-only convenience.
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};

module.exports = nextConfig;
