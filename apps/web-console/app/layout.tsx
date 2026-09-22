import type { Metadata } from 'next'
import '@autoforce/ui-tokens/tokens.css'
import './globals.css'
import AuthWrapper from '../components/AuthWrapper'
import { Toaster } from 'sonner'

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
    <html lang="zh" data-theme="dark">
      <body className="bg-bg text-text antialiased">
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
