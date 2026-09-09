# AI Control Tower

Платформа управления и аудита корпоративного использования AI: политики,
реестр использования, согласования, трассировка запрос→ответ, инциденты,
реестр поставщиков.

## Состав репозитория

```
backend/    FastAPI + SQLAlchemy (async) + PostgreSQL + Alembic
frontend/   Next.js (App Router) + TypeScript + axios
docker-compose.yml   Postgres + Redis для локальной разработки
```

## Что реализовано (MVP)

- **Auth** — регистрация организации + email/password логин, JWT.
- **Policy Center** — политики, версии правил (JSON), согласование версии.
- **Usage Registry** — сценарии использования (Use Cases), реестр поставщиков
  (Vendor Risk Desk, базовый CRUD), создание и список запросов к AI.
- **Action Trace** — цепочка запрос → (согласование) → ответ провайдера
  на одной странице.
- **Approval Workflow** — постановка запроса на согласование, решение
  approve/reject с комментарием.
- **Incident Tracker** — регистрация инцидента, статус, первопричина.

## Что НЕ реализовано (осталось от исходной архитектуры)

Эти модули есть в схеме БД или в общем плане, но не реализованы как
работающая логика — оставлены как следующий этап:

- **Prompt Firewall** — сейчас `masked_input_text` не заполняется;
  нет пайплайна маскирования/блокировки чувствительных полей.
- **Shadow AI Monitor** — обнаружение несанкционированного использования AI.
- **Override Console** — ручная остановка/правка/откат запроса.
- **Audit & Reporting** — таблица `ai_audit_logs` есть, но никто её не
  пишет; нет экспорта отчётов/дашбордов комплаенса.
- **Notification Service**, **Event Bus/очередь на Redis**, воркеры
  (`app/workers` — пустой пакет).
- Провайдерский вызов в `RequestService.process_request` — заглушка
  (`Mock response`), реального обращения к OpenAI/Anthropic/др. нет.

## Запуск backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# поднять Postgres/Redis
cd .. && docker compose up -d

cd backend
cp .env.example .env   # при необходимости поправить хосты/пароли
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

API будет доступно на `http://localhost:8000`, документация — на
`http://localhost:8000/docs`.

## Запуск frontend

```bash
cd frontend
npm install
npm run dev
```

Откройте `http://localhost:3000`. По умолчанию фронтенд обращается к API по
адресу `http://localhost:8000/api/v1` — при необходимости переопределите
через переменную окружения `NEXT_PUBLIC_API_URL` (файл `.env.local`).

Первый шаг в интерфейсе — `/register`: создаёт организацию и первого
пользователя с ролью `admin`.

## Типовой сценарий проверки

1. `/register` — создать организацию.
2. `/providers` — добавить поставщика (например, `OpenAI` / `openai`).
3. `/use-cases` — создать сценарий использования.
4. `/policies` — создать политику, добавить версию с
   `{"effect": "require_approval"}` и согласовать её, затем привязать
   `approved_policy_version_id` к сценарию (сейчас — через API/БД напрямую,
   в UI редактирование этой связи из карточки сценария не выведено).
5. `/requests` — создать запрос: если сценарий требует согласования,
   статус станет `pending_approval`.
6. На странице запроса — «Отправить на согласование», затем на
   `/approvals` — одобрить или отклонить.
7. `/incidents` — при необходимости завести инцидент и довести до
   `resolved` с указанием первопричины.
