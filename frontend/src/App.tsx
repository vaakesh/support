import type { ReactNode } from "react";
import AuthPage from "./AuthPage";
import WebSocketDemo from "./WebSocket";
import {BrowserRouter, Navigate, Route, Routes, useLocation, } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import AllTicketsPage from "./AllTicketsPage";

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/ws/:ticket_uuid" element={<PrivateRoute> <WebSocketDemo /> </PrivateRoute>} />
                <Route path="/" element={<PrivateRoute><AllTicketsPage /></PrivateRoute>} />
                <Route path="/login" element={<AuthPage />} />
            </Routes>
        </BrowserRouter>
    )
}

export default App

function PrivateRoute({ children }: { children: ReactNode }) {
    const { user, loading } = useAuth();
    const location = useLocation();

    if (loading) return <div>Загрузка...</div>;
    if (!user) return <Navigate to="/login" state={{ from: location }} replace />;

    return <>{children}</>;
}