import type { NextConfig } from "next";

// Proxy dev ke FastAPI: request ke /api/v1/* diteruskan ke backend oleh server Next.js,
// jadi browser tidak butuh CORS. Dipakai bila NEXT_PUBLIC_API_BASE_URL=/api/v1.
// Bila backend sudah memasang CORS, NEXT_PUBLIC_API_BASE_URL boleh langsung ke backend
// (mis. http://localhost:8000/api/v1) dan rewrite ini tidak terpakai.
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${BACKEND_URL}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
