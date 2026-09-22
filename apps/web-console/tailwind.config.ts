import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './contexts/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        apple: {
          bg: '#000000',
          surface: '#1c1c1e',
          raised: '#2c2c2e',
          overlay: '#3a3a3c',
          blue: '#0a84ff',
          blueStrong: '#0071e3',
          label: '#f5f5f7',
          secondary: '#86868b',
          tertiary: '#6e6e73',
          green: '#30d158',
          orange: '#ff9f0a',
          red: '#ff453a',
          yellow: '#ffd60a',
        },
      },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          '"SF Pro Text"',
          '"SF Pro Display"',
          '"Helvetica Neue"',
          'Inter',
          'system-ui',
          'sans-serif',
        ],
      },
      borderRadius: {
        apple: '14px',
        'apple-lg': '20px',
        'apple-xl': '28px',
      },
      boxShadow: {
        apple: '0 8px 30px rgba(0,0,0,0.32)',
        'apple-lg': '0 18px 50px rgba(0,0,0,0.4)',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic':
          'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
      },
      animation: {
        shine: 'shine 3s linear infinite',
      },
      keyframes: {
        shine: {
          '0%': { backgroundPosition: '200% center' },
          '100%': { backgroundPosition: '-200% center' },
        },
      },
    },
  },
  plugins: [],
}
export default config
