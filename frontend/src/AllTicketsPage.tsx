import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import styles from "./AllTicketsPage.module.css";
import fetchWithAuth from "./api/auth";

type TicketStatus = "open" | "pending" | "resolved" | "closed";
type TicketPriority = "low" | "medium" | "high" | "critical";
type TicketCategory = string;

interface UserOut {
  uuid: string;
  username: string;
  email: string;
}

interface TicketOut {
  uuid: string;
  subject: string;
  description: string;
  status: TicketStatus;
  priority: TicketPriority;
  category: TicketCategory;
  created_at: string;
  first_response_due_at: string | null;
  resolve_due_at: string | null;
  first_responded_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  customer: UserOut;
  support_agent: UserOut | null;
}

const PRIORITY_LABEL: Record<TicketPriority, string> = {
  low: "Низкий",
  medium: "Средний",
  high: "Высокий",
  critical: "Критический",
};

const STATUS_LABEL: Record<TicketStatus, string> = {
  open: "Открыт",
  pending: "В ожидании",
  resolved: "Решён",
  closed: "Закрыт",
};

export default function AllTickets() {
  const [tickets, setTickets] = useState<TicketOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchWithAuth("/api/tickets/all")
      .then((res) => {
        if (!res.ok) throw new Error("Ошибка загрузки тикетов");
        return res.json();
      })
      .then((data: TicketOut[]) => setTickets(data))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className={styles.center}>
        <div className={styles.spinner} />
        <span className={styles.loadingText}>Загрузка тикетов…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.center}>
        <p className={styles.error}>{error}</p>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Тикеты</h1>
        <span className={styles.count}>{tickets.length}</span>
      </header>

      {tickets.length === 0 ? (
        <p className={styles.empty}>Нет тикетов</p>
      ) : (
        <div className={styles.grid}>
          {tickets.map((t) => (
            <article key={t.uuid} className={styles.card}>
              <div className={styles.cardTop}>
                <span className={`${styles.priority} ${styles[`priority_${t.priority}`]}`}>
                  {PRIORITY_LABEL[t.priority]}
                </span>
                <span className={`${styles.status} ${styles[`status_${t.status}`]}`}>
                  {STATUS_LABEL[t.status]}
                </span>
              </div>

              <h2 className={styles.subject}>{t.subject}</h2>
              <p className={styles.description}>{t.description}</p>

              <div className={styles.meta}>
                <div className={styles.metaRow}>
                  <span className={styles.metaLabel}>Клиент</span>
                  <span className={styles.metaValue}>{t.customer.username}</span>
                </div>
                <div className={styles.metaRow}>
                  <span className={styles.metaLabel}>Агент</span>
                  <span className={styles.metaValue}>
                    {t.support_agent ? t.support_agent.username : "—"}
                  </span>
                </div>
                <div className={styles.metaRow}>
                  <span className={styles.metaLabel}>Категория</span>
                  <span className={styles.metaValue}>{t.category}</span>
                </div>
                <div className={styles.metaRow}>
                  <span className={styles.metaLabel}>Создан</span>
                  <span className={styles.metaValue}>
                    {new Date(t.created_at).toLocaleDateString("ru-RU")}
                  </span>
                </div>
              </div>

              <button
                className={styles.chatBtn}
                onClick={() => navigate(`/ws/${t.uuid}`)}
              >
                Перейти в чат →
              </button>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}