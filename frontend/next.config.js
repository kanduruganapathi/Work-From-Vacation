/** @type {import('next').NextConfig} */

// Where the FastAPI backend lives, from the Next.js *server's* perspective.
// In docker-compose this is the service name (http://backend:8000); locally it
// defaults to localhost. This is server-side only — the browser never sees it.
const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN || "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // Proxy all /api/* calls to the backend so the browser talks same-origin.
    // Eliminates CORS and the "localhost:8000 from the browser" problem when
    // the app is opened through a remote preview / tunnel.
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND_ORIGIN}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
