# planner

# Task Planner Bot

Бот для управления задачами в Telegram с функциями планирования, категоризации задач и установки напоминаний.

## Локализация

Бот поддерживает многоязычность с помощью библиотеки `python-i18n`. Текущие поддерживаемые языки:

- Русский (ru)
- Английский (en)

### Как использовать локализацию в коде

Для получения локализованных строк используется функция `t()`:

```python
from backend.locale_config import t

# Простая строка
message = t("welcome-message")

# Строка с параметрами
message = t("task-created-details", 
           title="Название задачи", 
           description="Описание задачи")
```

### Файлы локализации

Локализованные строки хранятся в JSON-файлах в директории `backend/locale_files/{locale}/main.json`.

### Добавление нового языка

1. Создайте новую директорию с кодом языка в `backend/locale_files/`
2. Добавьте файл `main.json` с переводами
3. Обновите список `AVAILABLE_LANGUAGES` в файле `backend/locale_config.py`

### Переключение языка

Пользователи могут изменить язык с помощью команды `/language`.

## Установка и запуск

```
pip install -r requirements.txt
cd backend 
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

cd frontend
npm install
yarn dev
```