/** @type { import('next').NextConfig } */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // Use 127.0.0.1 to avoid connection issues on some Windows setups
    const backend = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
    return [
      { source: '/api/v1/:path*', destination: `${backend}/api/v1/:path*` },
    ];
  },
};

module.exports = nextConfig;
