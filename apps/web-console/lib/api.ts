import axios from 'axios';
import { expireAuthSession } from './auth-session';

const api = axios.create({
    // Use env var or default to relative root
    baseURL: process.env.NEXT_PUBLIC_API_URL || '', 
    timeout: 60000, 
});

// Debug log to help identify connection issues
if (typeof window !== 'undefined') {
    console.log("[API] Base URL:", api.defaults.baseURL);
}

api.interceptors.request.use(
    (config) => {
        if (typeof window !== 'undefined') {
            const token = localStorage.getItem('token');
            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            }
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

api.interceptors.response.use(
    (response) => response,
    (error) => {
        // Log detailed error for debugging
        console.error("API Error:", error.config?.url, error.message);
        
        if (error.response) {
            // Server responded with error status
            const status = error.response.status;
            if (status === 401) {
                if (typeof window !== 'undefined') {
                    const authorization = error.config?.headers?.Authorization;
                    const requestToken = typeof authorization === 'string' && authorization.startsWith('Bearer ')
                        ? authorization.slice(7)
                        : null;
                    expireAuthSession(requestToken);
                }
            }
        } else if (error.request) {
            // Request made but no response
            console.error("No response received from server");
        }
        
        return Promise.reject(error);
    }
);

export default api;
