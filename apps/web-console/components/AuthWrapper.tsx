"use client";
import { usePathname } from 'next/navigation';
import { Suspense } from 'react';
import Sidebar from './sidebar';
import { AuthProvider } from '../contexts/AuthContext';
import { GlobalStateProvider } from '../contexts/GlobalStateContext';
import { ToastProvider } from '../contexts/ToastContext';
import OrganizationGate from './OrganizationGate';

export default function AuthWrapper({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLoginPage = pathname === '/login';
  const isLandingPage = pathname === '/landing';
  const isRootPage = pathname === '/';
  const isSolutionPage = pathname === '/solution';
  const isBrainPage = pathname?.startsWith('/knowledge/brain');
  const isGeneratorPage = pathname?.startsWith('/knowledge/solution');
  const isFullScreen = isLoginPage || isLandingPage || isSolutionPage || isRootPage;
  // Pages that keep sidebar but remove padding/scroll for full-height apps
  const isImmersive = isBrainPage || isGeneratorPage;

  return (
    <Suspense fallback={<div className="h-screen w-screen bg-bg" />}>
    <AuthProvider>
        <ToastProvider> 
            <OrganizationGate>
                <div className="flex h-screen overflow-hidden text-text bg-bg">
                    {!isFullScreen && <Sidebar />}

                <main className={`flex-1 min-w-0 relative ${isImmersive ? 'overflow-hidden p-0' : 'overflow-auto p-3'} ${isFullScreen ? 'w-full p-0 flex flex-col' : ''}`}>
                    <GlobalStateProvider>
                        <div className={`h-full ${isImmersive ? 'overflow-hidden p-0' : 'px-1 overflow-y-auto pb-10'} ${isFullScreen ? 'p-0 px-0 pb-0' : ''}`}>
                            {children}
                        </div>
                    </GlobalStateProvider>
                </main>
            </div>
          </OrganizationGate>
        </ToastProvider>
    </AuthProvider>
    </Suspense>
  );
}
