import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import '@autoforce/ui-tokens/tokens.css'
import './globals.css'
import AuthWrapper from '../components/AuthWrapper'
import { Toaster } from 'sonner'

// Inter：Windows 上英文与数字的观感（macOS 仍优先使用系统字体）
const inter = Inter({ subsets: ['latin'], variable: '--font-inter', display: 'swap' })

export const metadata: Metadata = {
  title: 'GlobalPilot AI | 全球 B2B 智能增长操作系统',
  description: 'AI Operating System for Global B2B Growth',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh" suppressHydrationWarning className={inter.variable}>
      <body className="bg-bg text-text antialiased">
        {/* 首屏渲染前确定主题：localStorage 优先，否则跟随系统偏好 */}
        <script
          dangerouslySetInnerHTML={{
            __html:
              "(function(){try{var t=window.localStorage.getItem('theme');if(t!=='light'&&t!=='dark'){t=window.matchMedia('(prefers-color-scheme: light)').matches?'light':'dark';}document.documentElement.setAttribute('data-theme',t);}catch(e){document.documentElement.setAttribute('data-theme','dark');}})();",
          }}
        />
        <AuthWrapper>
            {children}
            <Toaster
              position="top-right"
              theme="dark"
              toastOptions={{
                className: '!bg-surface !text-text !border !border-separator !rounded-xl !shadow-popover',
              }}
            />
        </AuthWrapper>
      </body>
    </html>
  )
}
