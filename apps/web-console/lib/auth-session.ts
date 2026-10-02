export const AUTH_SESSION_EXPIRED_EVENT = 'auth-session-expired';

/** Clear only the session that made the failed request, before any navigation. */
export function expireAuthSession(requestToken: string | null) {
    if (typeof window === 'undefined') return;
    const currentToken = localStorage.getItem('token');
    // A late 401 from an old request must not log out a newly signed-in user.
    if (!currentToken || currentToken !== requestToken) return;

    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.dispatchEvent(new Event(AUTH_SESSION_EXPIRED_EVENT));
    if (window.location.pathname !== '/login') {
        window.location.replace('/login');
    }
}
