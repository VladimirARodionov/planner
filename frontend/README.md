# Планировщик задач - Frontend

Фронтенд-часть приложения для планирования задач, написанная на React с использованием TypeScript и Material-UI.

## Требования

- Node.js 16.x или выше
- npm 8.x или выше

## Установка

1. Установите зависимости:
```bash
npm install
```

2. Создайте файл .env в корневой директории проекта и добавьте необходимые переменные окружения:
```bash
REACT_APP_API_URL=http://localhost:5000/api
REACT_APP_TITLE=Планировщик задач
```

## Запуск

Для запуска приложения в режиме разработки:
```bash
npm start
```

Приложение будет доступно по адресу [http://localhost:3000](http://localhost:3000).

## Сборка

Для создания production-сборки:
```bash
npm run build
```

Собранные файлы будут находиться в директории `build`.

## Тестирование

Для запуска тестов:
```bash
npm test
```

## Структура проекта

```
src/
  ├── api/          # API клиенты
  ├── components/   # React компоненты
  ├── types/        # TypeScript типы
  ├── theme.ts      # Настройки темы Material-UI
  ├── App.tsx       # Главный компонент приложения
  └── index.tsx     # Точка входа
```

## Основные технологии

- React 18
- TypeScript 4
- Material-UI 5
- Axios
- React Testing Library
