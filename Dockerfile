# Используем базовый образ Python версии 3.9 на основе slim
FROM python:3.9-slim

# Установка зависимостей
RUN pip install python-dotenv

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копируем приложение в контейнер
COPY parser.py /app/parser.py

# Задаем рабочую директорию
WORKDIR /app

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir requests psycopg2-binary

# Команда по умолчанию для запуска приложения
CMD ["python", "parser.py"]
