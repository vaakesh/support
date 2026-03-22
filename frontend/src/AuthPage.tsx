import React, { useMemo, useState } from "react";
import styles from "./AuthPage.module.css";
import { useAuth } from "./auth/AuthContext";
import { Navigate } from "react-router-dom";

export default function AuthPage() {
    const { user, loading: authLoading } = useAuth();
    
    if (authLoading) return <div>Загрузка...</div>;
    if (user) return <Navigate to="/" replace />;

    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const canSubmit = useMemo(() => {
        return username.trim().length > 0 && password.length > 0 && !loading;
    }, [username, password, loading]);

    async function onSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            const body = new URLSearchParams();
            body.set("username", username);
            body.set("password", password);

            const res = await fetch("/api/auth/login", {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                credentials: "include",
                body,
            });

        console.log(res);

        if (!res.ok) {
            const t = await res.text().catch(() => "");
            throw new Error(`login failed (${res.status}) ${t}`);
        }

        window.location.href = "/";
        } catch (err: any) {
            setError(err?.message ?? "login error");
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className={styles.root}>
            <div className={styles.panel}>
                <div className={styles.header}>
                    <div className={styles.logo}>⬡</div>
                    <h1 className={styles.title}>Welcome back</h1>
                    <p className={styles.subtitle}>Sign in to continue</p>
                </div>
 
                <form onSubmit={onSubmit} className={styles.form} noValidate>
                    <div className={styles.field}>
                        <label className={styles.label}>
                            Username
                        </label>
                        <input
                            id="username"
                            className={styles.input}
                            type="text"
                            autoComplete="username"
                            autoFocus
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            placeholder="your_username"
                            disabled={loading}
                        />
                    </div>
 
                    <div className={styles.field}>
                        <label className={styles.label}>
                            Password
                        </label>
                        <input
                            id="password"
                            className={styles.input}
                            type="password"
                            autoComplete="current-password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="••••••••"
                            disabled={loading}
                        />
                    </div>
 
                    {error && (
                        <div className={styles.error} role="alert">
                            <span className={styles.errorIcon}>!</span>
                            {error}
                        </div>
                    )}
 
                    <button
                        type="submit"
                        className={styles.button}
                        disabled={!canSubmit}
                    >
                        {loading ? (
                            <span className={styles.spinner} />
                        ) : (
                            "Sign in"
                        )}
                    </button>
                </form>
            </div>
        </div>
    );
}
