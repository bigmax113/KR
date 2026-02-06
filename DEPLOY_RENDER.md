# Deploy на Render.com (Blueprint)

Этот репозиторий уже содержит `render.yaml`, поэтому деплой можно сделать в 2–3 клика.

## 1) Подготовка репозитория
1. Распакуй архив (или возьми исходники).
2. Создай Git-репозиторий и запушь на GitHub/GitLab.

> Важно: файл `.env` в репозиторий не коммитим. На Render переменные задаются в UI или через `render.yaml`.

## 2) Создание сервиса через Blueprint
1. В Render Dashboard: **New → Blueprint**
2. Выбери репозиторий, где лежит этот код.
3. Render подхватит `render.yaml` и предложит создать Web Service.
4. На шаге env vars Render попросит ввести значение для:
   - `XAI_API_KEY` (секрет, не хранится в репо)

После создания сервиса Render автоматически:
- выполнит `pip install -r requirements.txt`
- запустит команду:
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## 3) Проверка после деплоя
Проверь health endpoint:
- `GET https://<your-service>.onrender.com/v1/health`

Документация FastAPI:
- `GET https://<your-service>.onrender.com/docs`

## 4) Как подключать Android/iOS
В приложениях просто меняешь base URL API на адрес Render-сервиса:
- `https://<your-service>.onrender.com`

Ключевые эндпоинты:
- `GET /v1/recipes?lang=xx`
- `GET /v1/recipes/{id}?lang=xx`
- `POST /v1/recipes/generate`
- `POST /v1/recipes/generate/continue`

## 5) Важные нюансы Render
- **Free/Starter инстанс может “засыпать”** (idle). Тогда первые запросы после паузы будут медленнее (cold start).
- **Сессии resume/continue в MVP в памяти процесса.**
  Если инстанс перезапустится — `session_id` станет невалидным.
  Для production нужно вынести сессии в Redis/Postgres.

## 6) Если нужно больше параллелизма
Uvicorn (1 процесс) подходит для MVP и небольших нагрузок.
Для production обычно ставят Gunicorn + Uvicorn workers (несколько процессов).

Схема:
1) Добавить `gunicorn` в `requirements.txt`
2) Поменять `startCommand` в Render на что-то вроде:
   `gunicorn app.main:app --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --workers 2`

Количество воркеров выбирается по CPU/RAM инстанса.
