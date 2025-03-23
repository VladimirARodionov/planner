# Планировщик задач

Приложение для управления задачами с фронтендом на React и бэкендом на Python (Flask + Aiogram).

## Требования

### Локальная разработка
- Python 3.11+
- Node.js 20+
- PostgreSQL

### Docker
- Docker
- Docker Compose

## Установка и запуск

### Через Docker

1. Скопируйте `.env.example` в `.env` и настройте переменные окружения:

```bash
cp .env.example .env
# Отредактируйте .env, указав необходимые параметры
```

2. Запустите контейнеры:

```bash
docker-compose up -d
```

Приложение будет доступно по адресу: http://localhost

### Локальный запуск

#### Бэкенд

1. Создайте виртуальное окружение Python и активируйте его:

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows
```

2. Установите зависимости:

```bash
pip install -r requirements.txt
```

3. Запустите бэкенд:

```bash
python -m backend.run
```

#### Фронтенд

1. Перейдите в директорию frontend:

```bash
cd frontend
```

2. Установите зависимости:

```bash
npm install
```

3. Запустите фронтенд:

```bash
npm start
```

Приложение будет доступно по адресу: http://localhost:3000