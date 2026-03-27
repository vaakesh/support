import { useState, useEffect, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { refreshTokens } from "./api/auth";
import styles from "./WebSocket.module.css";
import { useAuth } from "./auth/AuthContext";

type ChatMessage = {
    id: number;
    username: string;
    text: string;
    time: string;
    isSelf: boolean;
};

export default function WebSocketDemo() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const { ticket_uuid } = useParams<{ ticket_uuid: string }>();
    const url = `ws://localhost:8000/tickets/${ticket_uuid}/ws`;

    const [message, setMessage] = useState("");
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [connected, setConnected] = useState(false);
    const [connecting, setConnecting] = useState(false);

    const socketRef = useRef<WebSocket | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const idCounter = useRef(0);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    // Auto-grow textarea
    useEffect(() => {
        const el = textareaRef.current;
        if (!el) return;
        el.style.height = "auto";
        el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
    }, [message]);

    const addMessage = (username: string, text: string, isSelf: boolean) => {
        idCounter.current += 1;
        setMessages((prev) => [
            ...prev,
            {
                id: idCounter.current,
                username,
                text,
                time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                isSelf,
            },
        ]);
    };

    const connect = async (isRetry = false) => {
        if (socketRef.current) {
            socketRef.current.close();
        }
        if (!isRetry) {
            setConnecting(true);
            const ok = await refreshTokens();
            if (!ok) {
                setConnecting(false);
                await logout();
                navigate("/login", { replace: true });
                return;
            }
        }
        const ws = new WebSocket(url);
        socketRef.current = ws;

        ws.onopen = () => {
            setConnected(true);
            setConnecting(false);
        };
        ws.onmessage = (event) => {
            try {
                const parsed = JSON.parse(event.data);
                const text = parsed.message ?? event.data;
                const username = parsed.username ?? "unknown";
                const isSelf = username === user?.username;
                addMessage(username, text, isSelf);
            } catch {
                addMessage("system", event.data, false);
            }
        };
        ws.onerror = () => {
            setConnecting(false);
        };
        ws.onclose = async (event: CloseEvent) => {
            setConnected(false);
            setConnecting(false);
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
        if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return;
        if (!message.trim()) return;

        socketRef.current.send(JSON.stringify({
            type: "message",
            payload: message,
        }));
        addMessage("you", message, true);
        setMessage("");
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            send();
        }
    };

    return (
        <div className={styles.root}>
            <div className={styles.panel}>

                {/* Header */}
                <div className={styles.header}>
                    <div className={styles.headerLeft}>
                        <span className={`${styles.statusDot} ${connected ? styles.connected : ""}`} />
                        <span className={styles.headerLabel}>Тикет #{ticket_uuid}</span>
                    </div>
                    <div className={styles.headerRight}>
                        <span className={`${styles.statusText} ${connected ? styles.connected : ""}`}>
                            {connecting ? "connecting…" : connected ? "online" : "offline"}
                        </span>
                        <button
                            onClick={() => connected ? disconnect() : connect()}
                            disabled={connecting}
                            className={`${styles.connectBtn} ${connected ? styles.connected : ""}`}
                        >
                            {connected ? "disconnect" : connecting ? "…" : "connect"}
                        </button>
                    </div>
                </div>

                {/* Messages */}
                <div className={styles.messages}>
                    {messages.length === 0 && (
                        <div className={styles.messagesEmpty}>
                            {connected ? "Нет сообщений" : "Подключитесь, чтобы начать чат"}
                        </div>
                    )}
                    {messages.map((msg) => (
                        <div
                            key={msg.id}
                            className={`${styles.messageRow} ${msg.isSelf ? styles.self : styles.other}`}
                        >
                            {!msg.isSelf && (
                                <span className={styles.username}>{msg.username}</span>
                            )}
                            <div className={styles.bubble}>
                                <span className={styles.bubbleText}>{msg.text}</span>
                                <span className={styles.bubbleTime}>{msg.time}</span>
                            </div>
                        </div>
                    ))}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input */}
                <div className={styles.sendBar}>
                    <textarea
                        ref={textareaRef}
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={!connected}
                        placeholder={connected ? "Написать сообщение…" : "Сначала подключитесь"}
                        className={styles.messageInput}
                        rows={1}
                    />
                    <button
                        onClick={send}
                        disabled={!connected || !message.trim()}
                        className={`${styles.sendBtn} ${connected ? styles.active : ""}`}
                    >
                        ↵
                    </button>
                </div>

            </div>
        </div>
    );
}