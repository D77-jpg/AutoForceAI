/** @type {import('next').NextConfig} */
const nextConfig = {
    output: 'standalone',
    // Clean redirects/rewrites to standard Next.js routing
    // / -> Portal Page (app/page.tsx)
    // /geo -> GEO Dashboard (app/geo/page.tsx)
    async rewrites() {
      // Prefer env var, fallback to default
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8010';
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
