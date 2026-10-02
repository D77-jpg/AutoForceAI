"use client";
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import { AUTH_SESSION_EXPIRED_EVENT } from '../lib/auth-session';

interface User {
    id: number;
    username: string;
    role?: string;
    org_id?: number | null;
    org_name?: string; // Add Organization Name
    avatar?: string;
    headimgurl?: string; // Add WeChat headimgurl
    nickname?: string;   // Add WeChat nickname
    invite_code?: string; // Add Enterprise Invite Code
}

interface AuthContextType {
    user: User | null;
    token: string | null;
    login: (token: string, user: User) => void;
    logout: () => void;
    isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const router = useRouter();
    const pathname = usePathname();
    const searchParams = useSearchParams();
    const isPublicPath = ['/login', '/landing', '/solution'].includes(pathname || '');

    // Persist redirect param to handle OAuth callbacks that might strip params
    useEffect(() => {
        const redirect = searchParams?.get('redirect');
        if (redirect) {
            sessionStorage.setItem('login_redirect', redirect);
        }
    }, [searchParams]);

    useEffect(() => {
        // Load from localStorage on mount
        const storedToken = localStorage.getItem('token');
        const storedUser = localStorage.getItem('user');

        try {
            const parsedUser = storedUser ? JSON.parse(storedUser) : null;
            if (storedToken && parsedUser?.id && parsedUser?.username) {
                setToken(storedToken);
                setUser(parsedUser);
            } else {
                localStorage.removeItem('token');
                localStorage.removeItem('user');
            }
        } catch {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
        }
        setIsLoading(false);

        const onSessionExpired = () => {
            setToken(null);
            setUser(null);
        };
        window.addEventListener(AUTH_SESSION_EXPIRED_EVENT, onSessionExpired);
        return () => window.removeEventListener(AUTH_SESSION_EXPIRED_EVENT, onSessionExpired);
    }, []);

    useEffect(() => {
        if (!isLoading) {
            // If not authenticated and not on a public page, redirect
            if (!token && !isPublicPath) {
                router.replace('/login');
            }
            // If authenticated and on login page, redirect to home or requested page
            if (token && pathname === '/login') {
                const redirect = searchParams?.get('redirect');
                const storedRedirect = sessionStorage.getItem('login_redirect');
                const finalRedirect = redirect || storedRedirect || '/';
                
                // Do not remove key immediately to prevent race conditions causing fallthrough to '/'
                // We will let the navigation happen.
                router.push(finalRedirect);
            }
        }
    }, [token, isLoading, pathname, router, searchParams, isPublicPath]);

    const login = (newToken: string, newUser: User) => {
        localStorage.setItem('token', newToken);
        localStorage.setItem('user', JSON.stringify(newUser));
        setToken(newToken);
        setUser(newUser);
        // Clean up any stale redirect param after successful login state set
        // But let useEffect handle the actual routing
    };

    const logout = () => {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        setToken(null);
        setUser(null);
        router.push('/login');
    };

    // Do not mount protected pages (and their API requests) before restoring auth.
    if (isLoading || (!token && !isPublicPath)) return null;

    return (
        <AuthContext.Provider value={{ user, token, login, logout, isAuthenticated: !!token }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
