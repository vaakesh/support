import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import fetchWithAuth, { setUnauthenticatedHandler } from "../api/auth";

interface AuthContextValue {
    user: User | null;
    loading: boolean;
    login: () => Promise<void>;
    logout: () => Promise<void>;
}

export interface User {
    uuid: string;
    username: string;
    email: string;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export async function currentUser(): Promise<User> {
    const res = await fetchWithAuth("/api/users/me");
    if (!res.ok) throw new Error("not authenticated");
    return res.json();
}

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        setUnauthenticatedHandler(() => setUser(null));

        currentUser()
            .then(data => setUser(data))
            .catch(() => setUser(null))
            .finally(() => setLoading(false));
    }, []);

    async function login() {
        const data = await currentUser();
        setUser(data);
    }

    async function logout() {
        await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
        setUser(null);
    }

    return (
        <AuthContext.Provider value={{ user, loading, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error("useAuth must be used within AuthProvider");
    return ctx;
}
