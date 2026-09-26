/** @type {import('next').NextConfig} */
const nextConfig = {
    output: 'standalone',
    // Clean redirects/rewrites to standard Next.js routing
    // / -> Portal Page (app/page.tsx)
    // /geo -> GEO Dashboard (app/geo/page.tsx)
    async rewrites() {
      // Prefer env var, fallback to default
      // Browser-facing NEXT_PUBLIC_API_URL must not leak an internal Docker hostname.
      // INTERNAL_API_URL is used only by the server-side Next.js rewrite.
      const apiUrl = process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8010';
      console.log(`[Next.js] Proxying API requests to: ${apiUrl}`);
      
      return [
        {
          source: '/api/:path*',
          destination: `${apiUrl}/api/:path*`, 
        },
      ]
    },
  }
  
  module.exports = nextConfig
