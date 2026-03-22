import { useState, useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import { refreshTokens } from "./api/auth";

type LogEntry = {
  time: string;
  text: string;
  type: "info" | "sent" | "recv" | "error";
};


export default function WebSocketDemo() {
    const { ticket_uuid } = useParams<{ ticket_uuid: string }>();
    const [url, setUrl] = useState(`ws://localhost:8000/tickets/${ticket_uuid}/ws`);
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
            socketRef.current.close();
        }
        if (!isRetry) {
            addLog("🔄 Обновляем токен…");
            const ok = await refreshTokens();
            if (!ok) {
                addLog("❌ Не удалось обновить токен, войдите заново", "error");
                return;
            }
        }

        addLog(`Подключаемся к ${url}…`);
        const ws = new WebSocket(url);
        socketRef.current = ws;

        ws.onopen = () => {
            setConnected(true);
            addLog("✅ Соединение установлено", "info");
        };

        ws.onmessage = (event: MessageEvent) => {
            const parsed = JSON.parse(event.data);
            addLog(`← ${parsed.message}`, "recv");
        };

        ws.onerror = () => {
            addLog("❌ Ошибка соединения", "error");
        };

        ws.onclose = async (event: CloseEvent) => {
            setConnected(false);
            addLog(`🔒 Соединение закрыто (code: ${event.code})`, "info");
            socketRef.current = null;

            if (event.code === 1008 && !isRetry) {
                addLog("🔄 Токен истёк, переподключаемся…");
                const ok = await refreshTokens();
                ok ? connect(true) : addLog("❌ Войдите заново", "error");
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

    const logColors: Record<LogEntry["type"], string> = {
        info: "#88aaff",
        sent: "#ffdd88",
        recv: "#88ff88",
        error: "#ff6666",
    };

  return (
    <div style={{ fontFamily: "monospace", padding: "2rem", background: "#111", minHeight: "100vh", color: "#eee" }}>
      <h2>🔌 WebSocket Demo</h2>

      {/* URL + connect */}
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          style={{ padding: "0.5rem", width: 300, background: "#222", color: "#eee", border: "1px solid #444" }}
        />
        <button onClick={connect}>Подключиться</button>
        <button onClick={disconnect} disabled={!connected}>Отключиться</button>
        <span style={{ alignSelf: "center", color: connected ? "#88ff88" : "#888" }}>
          {connected ? "● online" : "○ offline"}
        </span>
      </div>

      {/* Message send */}
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        <input
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Сообщение..."
          style={{ padding: "0.5rem", width: 300, background: "#222", color: "#eee", border: "1px solid #444" }}
        />
        <button onClick={send} disabled={!connected}>Отправить</button>
      </div>

      {/* Log */}
      <div style={{ border: "1px solid #333", padding: "1rem", height: 220, overflowY: "auto", background: "#1a1a1a" }}>
        {log.map((entry, i) => (
          <div key={i} style={{ color: logColors[entry.type] }}>
            [{entry.time}] {entry.text}
          </div>
        ))}
        <div ref={logEndRef} />
      </div>
    </div>
  );
}