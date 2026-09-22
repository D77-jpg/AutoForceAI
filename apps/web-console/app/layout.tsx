import type { Metadata } from 'next'
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
    <html lang="zh" className="dark">
      <body className="bg-black text-[#f5f5f7] antialiased">
        <AuthWrapper>
            {children}
            <Toaster
              position="top-right"
              theme="dark"
              toastOptions={{
                className: '!bg-[#1c1c1e] !text-[#f5f5f7] !border-white/10 !rounded-2xl !shadow-apple',
              }}
            />
        </AuthWrapper>
      </body>
    </html>
  )
}
