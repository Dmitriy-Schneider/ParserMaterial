# Используем официальный образ Python 3.11
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл requirements.txt
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы проекта
COPY . .

# Создаем папку для базы данных
RUN mkdir -p database

# Устанавливаем переменные окружения
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Открываем порт 5000
EXPOSE 5000

# Команда для запуска приложения
CMD ["python", "app.py"]






