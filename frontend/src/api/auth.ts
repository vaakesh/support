export async function refreshTokens(): Promise<boolean> {
    const res = await fetch('/api/auth/refresh', {
        method: 'POST',
        credentials: 'include',
    });
    return res.ok;
}
let onUnauthenticated: (() => void) | null = null;
export function setUnauthenticatedHandler(fn: () => void) {
    onUnauthenticated = fn;
}

type FetchOptions = RequestInit & { _retry?: boolean };
let refreshPromise: Promise<Response> | null = null;

async function fetchWithAuth(url: string, options: FetchOptions = {}): Promise<Response> {    
    const { _retry, ...fetchOptions } = options;

    const res = await fetch(url, {
        ...fetchOptions,
        credentials: 'include',
    });

    if (res.status === 401 && !_retry) {
        if (!refreshPromise) {
            refreshPromise = fetch('/api/auth/refresh', {
                method: 'POST',
                credentials: 'include',
            }).finally(() => {
                refreshPromise = null;
            });
        }

        const refreshRes = await refreshPromise;
        
        if (!refreshRes.ok) {
            onUnauthenticated?.();
            return refreshRes;
        }
        return fetchWithAuth(url, { ...fetchOptions, _retry: true });
    }
    return res;
}

export default fetchWithAuth;