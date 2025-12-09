FROM nginx:alpine

# Копирование файлов фронтенда
COPY src/ /usr/share/nginx/html/

# Копирование конфигурации nginx
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
