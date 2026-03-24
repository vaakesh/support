import { useState, useEffect, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { refreshTokens } from "./api/auth";
import styles from "./WebSocket.module.css";
import { useAuth } from "./auth/AuthContext";

type LogEntry = {
    time: string;
    text: string;
    type: "info" | "sent" | "recv" | "error";
};

export default function WebSocketDemo() {
    const { logout } = useAuth();
    const navigate = useNavigate();
    const { ticket_uuid } = useParams<{ ticket_uuid: string }>();
    const url = `ws://localhost:8000/tickets/${ticket_uuid}/ws`;
    const [message, setMessage] = useState("");
    const [log, setLog] = useState<LogEntry[]>([]);
    const [connected, setConnected] = useState(false);
    const socketRef = useRef<WebSocket | null>(null);
    const logEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        logEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [log]);

    const addLog = (text: string, type: LogEntry["type"] = "info") => {
        setLog((prev) => [
            ...prev,
            { time: new Date().toLocaleTimeString(), text, type },
        ]);
    };

    const connect = async (isRetry = false) => {
        if (socketRef.current) {
            console.log("found active connection, closing it...");
            socketRef.current.close();
        }
        if (!isRetry) {
            console.log("refreshing tokens...");
            const ok = await refreshTokens();
            if (!ok) {
                console.log("error when refreshing token");
                await logout();
                navigate("/login", { replace: true });
                return;
            }
        }
        console.log("connecting to websocket...");
        addLog(`Подключаемся к ${url}…`);
        const ws = new WebSocket(url);
        socketRef.current = ws;

        ws.onopen = () => {
            setConnected(true);
            addLog("✅ Соединение установлено", "info");
        };
        ws.onmessage = (event) => {
            try {
                const parsed = JSON.parse(event.data);
                addLog(`← ${parsed.message ?? event.data}`, "recv");
            } catch {
                addLog(`← [raw] ${event.data}`, "recv");
            }
        };
        ws.onerror = () => {
            addLog("❌ Ошибка соединения", "error");
        };
        ws.onclose = async (event: CloseEvent) => {
            setConnected(false);
            addLog(`🔒 Соединение закрыто (code: ${event.code})`, "info");
            socketRef.current = null;
            if (event.code === 1008 && !isRetry) {
                const ok = await refreshTokens();
                if (!ok) {
                    await logout();
                    navigate("/login", { replace: true });
                } else {
                    connect(true);
                }
            }
        };
    };

    const disconnect = () => {
        socketRef.current?.close();
    };

    const send = () => {
        if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
            addLog("Нет активного соединения", "error");
            return;
        }
        if (!message.trim()) return;
        socketRef.current.send(message);
        addLog(`→ ${message}`, "sent");
        setMessage("");
    };

    return (
        <div className={styles.root}>
            <div className={styles.panel}>

                {/* Header */}
                <div className={styles.header}>
                    <div className={styles.headerLeft}>
                        <span className={`${styles.statusDot} ${connected ? styles.connected : ""}`} />
                        <span className={styles.headerLabel}>websocket</span>
                    </div>
                    <div className={styles.headerRight}>
                        <span className={`${styles.statusText} ${connected ? styles.connected : ""}`}>
                            {connected ? "connected" : "disconnected"}
                        </span>
                        <button
                            onClick={() => setLog([])}
                            className={styles.clearBtn}
                        >
                            clear
                        </button>
                    </div>
                </div>

                {/* URL Bar */}
                <div className={styles.urlBar}>
                    <input
                        value={url}
                        readOnly
                        className={styles.urlInput}
                        placeholder="ws://…"
                    />
                    <button
                        onClick={() => connected ? disconnect() : connect()}
                        className={`${styles.connectBtn} ${connected ? styles.connected : ""}`}
                    >
                        {connected ? "disconnect" : "connect"}
                    </button>
                </div>

                {/* Log */}
                <div className={styles.log}>
                    {log.length === 0 && (
                        <div className={styles.logEmpty}>— no events —</div>
                    )}
                    {log.map((entry, i) => (
                        <div key={i} className={styles.logRow}>
                            <span className={styles.logTime}>{entry.time}</span>
                            <span className={`${styles.logText} ${styles[entry.type]}`}>
                                {entry.text}
                            </span>
                        </div>
                    ))}
                    <div ref={logEndRef} />
                </div>

                {/* Send Bar */}
                <div className={styles.sendBar}>
                    <input
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && send()}
                        disabled={!connected}
                        placeholder={connected ? "type a message…" : "connect first"}
                        className={styles.messageInput}
                    />
                    <button
                        onClick={send}
                        disabled={!connected}
                        className={`${styles.sendBtn} ${connected ? styles.active : ""}`}
                    >
                        send ↵
                    </button>
                </div>

            </div>
        </div>
    );
}