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
      
      // Legacy routers are mounted at the backend root (/auth, /agents, /content)
      // rather than under /api/v1, and uploaded files are served from /uploads.
      // Proxy all of them from the same origin too, so the browser never needs a
      // baked NEXT_PUBLIC_API_URL and stays CORS-free.
      return [
        {
          source: '/api/:path*',
          destination: `${apiUrl}/api/:path*`, 
        },
        {
          source: '/auth/:path*',
          destination: `${apiUrl}/auth/:path*`,
        },
        {
          source: '/agents/:path*',
          destination: `${apiUrl}/agents/:path*`,
        },
        {
          source: '/content/:path*',
          destination: `${apiUrl}/content/:path*`,
        },
        {
          source: '/uploads/:path*',
          destination: `${apiUrl}/uploads/:path*`,
        },
      ]
    },
  }
  
  module.exports = nextConfig
