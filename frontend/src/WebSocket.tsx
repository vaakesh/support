import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import fetchWithAuth, { refreshTokens } from "./api/auth";
import styles from "./WebSocket.module.css";
import { useAuth, type User } from "./auth/AuthContext";

type ChatMessage = {
    uuid: string;
    username: string;
    text: string;
    time: string;
    isSelf: boolean;
};

type ApiMessage = {
    uuid: string;
    body: string;
    author: User;
    created_at: string;
    updated_at: string;
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
    const [loadingHistory, setLoadingHistory] = useState(false);
    const [hasMore, setHasMore] = useState(true);

    const socketRef = useRef<WebSocket | null>(null);
    const messagesContainerRef = useRef<HTMLDivElement>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const shouldScrollRef = useRef(false);

    const scrollRestoreRef = useRef<{
        awaitingRestore: boolean;
        previousScrollTop: number;
        previousScrollHeight: number;
    }>({
        awaitingRestore: false,
        previousScrollTop: 0,
        previousScrollHeight: 0,
    });

    // Восстановление позиции скролла после prepend истории
    useEffect(() => {
        const container = messagesContainerRef.current;
        if (!container) return;

        if (scrollRestoreRef.current.awaitingRestore) {
            const heightDiff =
                container.scrollHeight - scrollRestoreRef.current.previousScrollHeight;
            container.scrollTop =
                scrollRestoreRef.current.previousScrollTop + heightDiff;
            scrollRestoreRef.current.awaitingRestore = false;
        }
    }, [messages]);

    const oldestUUIDRef = useRef<string | null>(null);
    const isFetchingRef = useRef(false);
    const isInitialLoadRef = useRef(true);

    // ─── Helpers ─────────────────────────────────────────────────────────────

    const toLocalTime = (iso: string) =>
        new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    const toChat = useCallback(
        (msg: ApiMessage): ChatMessage => ({
            uuid: msg.uuid,
            username: msg.author.username,
            text: msg.body,
            time: toLocalTime(msg.created_at),
            isSelf: msg.author.username === user?.username,
        }),
        [user?.username]
    );
    const toChatRef = useRef(toChat);
    useEffect(() => {
        toChatRef.current = toChat;
    }, [toChat]);

    // ─── Авто-рост textarea ──────────────────────────────────────────────────

    useEffect(() => {
        const el = textareaRef.current;
        if (!el) return;
        el.style.height = "auto";
        el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
    }, [message]);

    // ─── Скролл вниз при первой загрузке ────────────────────────────────────

    useEffect(() => {
        if (messages.length === 0 || !isInitialLoadRef.current) return;
        messagesEndRef.current?.scrollIntoView({ behavior: "instant" });
        isInitialLoadRef.current = false;
    }, [messages]);

    useEffect(() => {
        return () => {
            socketRef.current?.close();
        };
    }, []);

    useEffect(() => {
        if (messages.length === 0) return;

        const container = messagesContainerRef.current;
        if (!container) return;

        const isAtBottom =
            container.scrollHeight - container.scrollTop - container.clientHeight < 60;

        if (shouldScrollRef.current || isAtBottom) {
            messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
            shouldScrollRef.current = false;
        }
    }, [messages]);

    // ─── Загрузка страницы истории ───────────────────────────────────────────

    const fetchMessages = useCallback(
        async (before?: string): Promise<boolean> => {
            const params = new URLSearchParams({ limit: "20" });
            if (before) params.set("before", before);

            const res = await fetchWithAuth(
                `/api/tickets/${ticket_uuid}/messages?${params}`
            );
            if (!res.ok) return false;

            const data: { messages: ApiMessage[]; has_more: boolean } =
                await res.json();

            if (data.messages.length > 0) {
                const sorted = data.messages.map(toChat).reverse(); // oldest → newest
                setMessages((prev) => [...sorted, ...prev]);
                oldestUUIDRef.current = sorted[0].uuid;
            }
            setHasMore(data.has_more);
            return true;
        },
        [ticket_uuid, toChat]
    );

    // ─── WebSocket ───────────────────────────────────────────────────────────

    const connect = useCallback(
        async (isRetry = false) => {
            socketRef.current?.close();

            setConnecting(true);

            if (!isRetry) {
                const ok = await refreshTokens();
                if (!ok) {
                    setConnecting(false);
                    await logout();
                    navigate("/login", { replace: true });
                    return;
                }
            }

            setMessages([]);
            oldestUUIDRef.current = null;
            setHasMore(true);
            isInitialLoadRef.current = true;

            setLoadingHistory(true);
            isFetchingRef.current = true;
            const ok = await fetchMessages();
            isFetchingRef.current = false;
            setLoadingHistory(false);

            if (!ok) {
                setConnecting(false);
                await logout();
                navigate("/login", { replace: true });
                return;
            }

            const ws = new WebSocket(url);
            socketRef.current = ws;

            ws.onopen = () => {
                setConnected(true);
                setConnecting(false);
            };

            ws.onmessage = (event) => {
                try {
                    const parsed: ApiMessage = JSON.parse(event.data);
                    setMessages((prev) => [...prev, toChatRef.current(parsed)]);
                } catch {
                    // ignore malformed frames
                }
            };

            ws.onerror = () => {
                setConnecting(false);
            };

            ws.onclose = async (event: CloseEvent) => {
                console.log("WS close:", event.code, event.reason);
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
        },
        [fetchMessages, logout, navigate, toChat, url]
    );

    const disconnect = () => {
        socketRef.current?.close();
    };

    // ─── Отправка ────────────────────────────────────────────────────────────

    const send = () => {
        const ws = socketRef.current;
        if (!ws || ws.readyState !== WebSocket.OPEN) return;
        if (!message.trim()) return;
        ws.send(JSON.stringify({ message }));
        setMessage("");
        shouldScrollRef.current = true;
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            send();
        }
    };

    const handleScroll = useCallback(async () => {
        const container = messagesContainerRef.current;
        if (!container) return;
        
        if (
            container.scrollTop <= 5 &&
            hasMore &&
            !isFetchingRef.current
        ) {
            scrollRestoreRef.current = {
                awaitingRestore: true,
                previousScrollTop: container.scrollTop,
                previousScrollHeight: container.scrollHeight,
            };

            isFetchingRef.current = true;
            setLoadingHistory(true);
            const ok = await fetchMessages(oldestUUIDRef.current ?? undefined);
            setLoadingHistory(false);
            isFetchingRef.current = false;

            if (!ok) {
                scrollRestoreRef.current.awaitingRestore = false;
            }
        }
    }, [hasMore, fetchMessages]);

    // ─── Render ───────────────────────────────────────────────────────────────

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
                            onClick={() => (connected ? disconnect() : connect())}
                            disabled={connecting}
                            className={`${styles.connectBtn} ${connected ? styles.connected : ""}`}
                        >
                            {connected ? "disconnect" : connecting ? "…" : "connect"}
                        </button>
                    </div>
                </div>

                {/* Messages */}
                <div
                    className={styles.messages}
                    ref={messagesContainerRef}
                    onScroll={handleScroll}
                >
                    {loadingHistory && (
                        <div className={styles.loadingHistory}>загрузка…</div>
                    )}

                    {!hasMore && messages.length > 0 && (
                        <div className={styles.noMore}>начало переписки</div>
                    )}

                    {messages.length === 0 && !loadingHistory && (
                        <div className={styles.messagesEmpty}>
                            {connected ? "Нет сообщений" : "Подключитесь, чтобы начать чат"}
                        </div>
                    )}

                    {messages.map((msg) => (
                        <div
                            key={msg.uuid}
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