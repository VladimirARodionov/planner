FROM python:3.13-slim-bullseye

# Установка зависимостей для Postgres и сетевых утилит
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    curl \
    dnsutils \
    iputils-ping \
    net-tools


ENV ENVIRONMENT=PRODUCTION

RUN addgroup --system app
RUN adduser --system app --ingroup app

USER app:app
WORKDIR /app

# Copy the rest of the application's source code into the container
COPY --chown=app:app requirements.txt .
COPY --chown=app:app entrypoint.sh .
COPY --chown=app:app alembic.ini .
COPY --chown=app:app .env .
COPY --chown=app:app logs .
COPY --chown=app:app alembic_migrations ./alembic_migrations/
COPY --chown=app:app logging.ini .
COPY --chown=app:app backend ./backend/

RUN chmod +x entrypoint.sh

# Создаем виртуальное окружение в папке app
RUN python -m venv venv
ENV PATH="/app/venv/bin:$PATH"

# Install the dependencies in the virtual environment
RUN . /app/venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt && pip install gunicorn

# Порт для Flask API
#EXPOSE 5000

# Запуск через скрипт-обертку
CMD ["/app/entrypoint.sh"]