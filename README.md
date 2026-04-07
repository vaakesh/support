# Support — Система управления тикетами

Полнофункциональная система поддержки клиентов с real-time чатом, построенная на **FastAPI + SQLAlchemy + PostgreSQL + Redis** (backend) и **React + TypeScript** (frontend).

---

## Быстрый старт

```bash
# 1. Скопировать env-файлы
cp .env.example .env
cp backend/.env.example backend/.env

# 2. Запустить
make up

# API:      http://localhost:8000
# Frontend: http://localhost:5173
```

## Тесты

```bash
cp backend/.env.test.example backend/.env.test
make test-up
# дождаться запуска, затем:
docker exec -it support-api-test uv run pytest
```

---

## Архитектура и ключевые решения

### Backend (Python 3.14, FastAPI)

**Слоёная архитектура** — проект разделён на чёткие слои: Router → Service → Repository → Models. Каждый модуль (`users`, `auth`, `tickets`) имеет собственные роутеры, сервисы, репозитории, схемы и кастомные ошибки.

**Unit of Work** — все операции с БД проходят через `UnitOfWork`, который управляет транзакциями, автоматически откатывает при ошибках и предоставляет доступ ко всем репозиториям через единую точку входа.

**Аутентификация и сессии:**
- JWT access-токены (RS256, асимметричные ключи) + refresh-токены
- Refresh token rotation с отслеживанием замены (`replaced_by_session_id`)
- Хеширование refresh-токенов через HMAC-SHA256 с pepper
- Хранение паролей через Argon2
- Поддержка как cookie-based, так и Bearer-авторизации
- Автоматическая генерация RSA-ключей (`ensure-certs.sh`)

**Тикеты и сообщения:**
- Полная модель тикета: статус (NEW → OPEN → PENDING → IN_PROGRESS → RESOLVED → CLOSED), приоритет, категория, SLA-поля (`first_response_due_at`, `resolve_due_at`)
- Контроль допустимых переходов статусов (`ALLOWED_TRANSITIONS`)
- Назначение агента поддержки, фильтрация по множеству параметров (статус, приоритет, категория, даты, текстовый поиск)
- Пагинация сообщений

**Real-time чат (WebSocket + Redis Pub/Sub):**
- `ConnectionManager` подписывается на Redis-каналы `ticket:*` через `psubscribe`
- Сообщения публикуются в Redis и рассылаются всем локальным WebSocket-соединениям — готово к горизонтальному масштабированию на несколько воркеров
- Авторизация WebSocket через cookie

**Кэширование:**
- Redis-кэш для тикетов и пользователей с инвалидацией при изменениях

**Rate Limiting:**
- Реализован через Redis (`INCR` + `EXPIRE`), применяется как FastAPI-зависимость на уровне эндпоинтов (`/auth/login`, `/auth/refresh`, `/users/me`)

**Миграции:**
- Alembic с async-движком (asyncpg), полная история миграций

### Тестирование

- **Unit-тесты** — подмена сервисов через `dependency_overrides`, проверка роутинга и бизнес-логики без БД
- **Интеграционные тесты** — реальная тестовая БД (PostgreSQL), очистка между тестами, фикстуры для аутентифицированных клиентов (cookie и bearer)

### Frontend (React 19, TypeScript, Vite)

- SPA с react-router: авторизация, список тикетов с фильтрами, WebSocket-чат
- Автоматический refresh токенов с retry на 401 (deduplicated refresh promise)
- Infinite scroll для истории сообщений с сохранением позиции скролла

---

## API Endpoints

### Auth (`/auth`)

| Метод | Путь | Описание | Auth |
|---|---|---|---|
| `POST` | `/auth/token` | Получить Bearer access-токен (OAuth2 form) | — |
| `POST` | `/auth/login` | Логин, установка cookie (access + refresh) | — |
| `POST` | `/auth/logout` | Отзыв refresh-токена, очистка cookie | Cookie |
| `POST` | `/auth/refresh` | Ротация токенов (refresh → новая пара) | Cookie |
| `GET` | `/auth/sessions` | Список всех сессий текущего пользователя | ✅ |

### Users (`/users`)

| Метод | Путь | Описание | Auth |
|---|---|---|---|
| `GET` | `/users/me` | Текущий пользователь | ✅ |
| `GET` | `/users/{uuid}` | Публичный профиль пользователя | — |
| `POST` | `/users/` | Регистрация | — |
| `PATCH` | `/users/{uuid}` | Обновление профиля (свой или admin) | ✅ |
| `DELETE` | `/users/{uuid}` | Удаление пользователя (свой или admin) | ✅ |

### Tickets (`/tickets`)

| Метод | Путь | Описание | Auth |
|---|---|---|---|
| `GET` | `/tickets` | Список тикетов с фильтрами (status, priority, category, даты, search) | — |
| `GET` | `/tickets/all` | Все тикеты (без фильтров) | — |
| `GET` | `/tickets/{uuid}` | Детали тикета (с Redis-кэшем) | — |
| `GET` | `/tickets/{uuid}/view` | Просмотр тикета (NEW → OPEN) | — |
| `POST` | `/tickets/` | Создать тикет (с расчётом SLA) | ✅ |
| `PATCH` | `/tickets/{uuid}/status` | Сменить статус (с валидацией переходов) | ✅ |
| `PATCH` | `/tickets/assign/{uuid}` | Назначить агента поддержки | — |

### Messages (`/tickets/{uuid}/messages`)

| Метод | Путь | Описание | Auth |
|---|---|---|---|
| `GET` | `/tickets/{uuid}/messages` | Сообщения тикета (keyset-пагинация, `before` + `limit`) | ✅ |
| `POST` | `/tickets/{uuid}/messages` | Отправить сообщение | ✅ |
| `WS` | `/tickets/{uuid}/ws` | Real-time чат (WebSocket, Redis Pub/Sub) | Cookie |

> **Rate limiting** применяется к `/auth/login` (3 req/min), `/auth/refresh` (10 req/min), `/users/me` (5 req/min).

---

## Стек

| Слой | Технологии |
|---|---|
| API | FastAPI, Uvicorn, Pydantic v2, pydantic-settings |
| ORM / DB | SQLAlchemy 2.0 (async), asyncpg, PostgreSQL 16, Alembic |
| Auth | PyJWT (RS256), Argon2 (pwdlib), HMAC-SHA256 |
| Cache / PubSub | Redis 7, redis-py (async) |
| Frontend | React 19, TypeScript, Vite, react-router-dom |
| Infra | Docker Compose, uv (package manager), Ruff |
| Testing | pytest, pytest-asyncio, httpx (AsyncClient) |

---


## Структура проекта

```
backend/
├── app/
│   ├── auth/          # JWT, сессии, refresh rotation
│   ├── users/         # CRUD пользователей, роли
│   ├── tickets/       # Тикеты, сообщения, WebSocket чат
│   ├── service.py     # Unit of Work
│   ├── repository.py  # Абстрактный репозиторий
│   └── main.py        # Точка входа, middleware, lifespan
├── alembic/           # Миграции
└── tests/             # Unit + интеграционные тесты
```
