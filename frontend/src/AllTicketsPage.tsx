import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import styles from "./AllTicketsPage.module.css";
import fetchWithAuth from "./api/auth";
import { useAuth } from "./auth/AuthContext";

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

interface Filters {
  search: string;
  status: TicketStatus[];
  priority: TicketPriority[];
  created_from: string;
  created_to: string;
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

const ALL_STATUSES: TicketStatus[] = ["open", "pending", "resolved", "closed"];
const ALL_PRIORITIES: TicketPriority[] = ["low", "medium", "high", "critical"];

const EMPTY_FILTERS: Filters = {
  search: "",
  status: [],
  priority: [],
  created_from: "",
  created_to: "",
};

function buildQuery(filters: Filters): string {
  const params = new URLSearchParams();
  if (filters.search) params.set("search", filters.search);
  filters.status.forEach((s) => params.append("status", s));
  filters.priority.forEach((p) => params.append("priority", p));
  if (filters.created_from)
    params.set("created_from", new Date(filters.created_from).toISOString());
  if (filters.created_to)
    params.set("created_to", new Date(filters.created_to).toISOString());
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

function toggleItem<T>(arr: T[], item: T): T[] {
  return arr.includes(item) ? arr.filter((x) => x !== item) : [...arr, item];
}

export default function AllTickets() {
  const { logout, user } = useAuth();
  const [tickets, setTickets] = useState<TicketOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [applied, setApplied] = useState<Filters>(EMPTY_FILTERS);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const navigate = useNavigate();

  const handleLogout = useCallback(async () => {
    await logout();
    navigate("/login");
  }, [logout, navigate]);

  const fetchTickets = useCallback((f: Filters) => {
    setLoading(true);
    setError(null);
    fetchWithAuth(`/api/tickets${buildQuery(f)}`)
      .then((res) => {
        if (!res.ok) throw new Error("Ошибка загрузки тикетов");
        return res.json();
      })
      .then((data: TicketOut[]) => setTickets(data))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchTickets(EMPTY_FILTERS);
  }, [fetchTickets]);

  function applyFilters() {
    setApplied(filters);
    fetchTickets(filters);
    setFiltersOpen(false);
  }

  function resetFilters() {
    setFilters(EMPTY_FILTERS);
    setApplied(EMPTY_FILTERS);
    fetchTickets(EMPTY_FILTERS);
    setFiltersOpen(false);
  }

  const hasActive =
    applied.search !== "" ||
    applied.status.length > 0 ||
    applied.priority.length > 0 ||
    applied.created_from !== "" ||
    applied.created_to !== "";

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.title}>Тикеты</h1>
          {!loading && <span className={styles.count}>{tickets.length}</span>}
        </div>
        <div className={styles.headerRight}>
          {user && <span className={styles.username}>{user.username}</span>}
          <button
            className={`${styles.filterToggle} ${hasActive ? styles.filterToggleActive : ""}`}
            onClick={() => setFiltersOpen((v) => !v)}
          >
            {filtersOpen ? "✕ Закрыть" : `⚙ Фильтры${hasActive ? " •" : ""}`}
          </button>
          <button className={styles.logoutBtn} onClick={handleLogout}>
            Выйти                                                
          </button>
        </div>
      </header>

      {filtersOpen && (
        <div className={styles.filterPanel}>
          <div className={styles.filterGroup}>
            <label className={styles.filterLabel}>Поиск</label>
            <input
              className={styles.filterInput}
              type="text"
              placeholder="Тема или описание…"
              value={filters.search}
              onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
            />
          </div>

          <div className={styles.filterGroup}>
            <label className={styles.filterLabel}>Статус</label>
            <div className={styles.chips}>
              {ALL_STATUSES.map((s) => (
                <button
                  key={s}
                  className={`${styles.chip} ${filters.status.includes(s) ? styles.chipActive : ""}`}
                  onClick={() =>
                    setFilters((f) => ({ ...f, status: toggleItem(f.status, s) }))
                  }
                >
                  {STATUS_LABEL[s]}
                </button>
              ))}
            </div>
          </div>

          <div className={styles.filterGroup}>
            <label className={styles.filterLabel}>Приоритет</label>
            <div className={styles.chips}>
              {ALL_PRIORITIES.map((p) => (
                <button
                  key={p}
                  className={`${styles.chip} ${styles[`chipPriority_${p}`]} ${
                    filters.priority.includes(p) ? styles.chipActive : ""
                  }`}
                  onClick={() =>
                    setFilters((f) => ({ ...f, priority: toggleItem(f.priority, p) }))
                  }
                >
                  {PRIORITY_LABEL[p]}
                </button>
              ))}
            </div>
          </div>

          <div className={styles.filterRow}>
            <div className={styles.filterGroup}>
              <label className={styles.filterLabel}>Создан с</label>
              <input
                className={styles.filterInput}
                type="date"
                value={filters.created_from}
                onChange={(e) =>
                  setFilters((f) => ({ ...f, created_from: e.target.value }))
                }
              />
            </div>
            <div className={styles.filterGroup}>
              <label className={styles.filterLabel}>Создан по</label>
              <input
                className={styles.filterInput}
                type="date"
                value={filters.created_to}
                onChange={(e) =>
                  setFilters((f) => ({ ...f, created_to: e.target.value }))
                }
              />
            </div>
          </div>

          <div className={styles.filterActions}>
            <button className={styles.btnApply} onClick={applyFilters}>
              Применить
            </button>
            <button className={styles.btnReset} onClick={resetFilters}>
              Сбросить
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className={styles.center}>
          <div className={styles.spinner} />
          <span className={styles.loadingText}>Загрузка тикетов…</span>
        </div>
      ) : error ? (
        <div className={styles.center}>
          <p className={styles.error}>{error}</p>
        </div>
      ) : tickets.length === 0 ? (
        <p className={styles.empty}>Нет тикетов по выбранным фильтрам</p>
      ) : (
        <div className={styles.grid}>
          {tickets.map((t) => (
            <article key={t.uuid} className={styles.card}>
              <div className={styles.cardTop}>
                <span
                  className={`${styles.priority} ${styles[`priority_${t.priority}`]}`}
                >
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