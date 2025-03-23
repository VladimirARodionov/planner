# Этап сборки
FROM node:20-alpine AS build

WORKDIR /app

# Копируем package.json и package-lock.json
COPY package*.json ./

# Устанавливаем зависимости с флагом legacy-peer-deps
RUN npm ci --legacy-peer-deps

# Копируем исходный код
COPY . .

# Копируем .env.docker в .env для использования в сборке
COPY .env.docker .env

# Создаем production сборку
RUN npm run build

# Этап запуска
FROM nginx:alpine

# Установка wget для healthcheck
RUN apk add --no-cache wget

# Копируем собранное приложение
COPY --from=build /app/build /usr/share/nginx/html

# Копируем конфиг nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Открываем порт
EXPOSE 80

# Запускаем nginx
CMD ["nginx", "-g", "daemon off;"] 