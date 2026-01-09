# 🚀 Полное руководство по деплою ParserSteel на удаленный сервер

## 📋 Содержание
1. [Требования к серверу](#требования-к-серверу)
2. [Подготовка файлов для переноса](#подготовка-файлов-для-переноса)
3. [Установка на сервер](#установка-на-сервер)
4. [Конфигурация](#конфигурация)
5. [Запуск и проверка](#запуск-и-проверка)
6. [Troubleshooting](#troubleshooting)

---

## 📦 Требования к серверу

### Минимальные требования:
- **OS**: Ubuntu 20.04+ / Debian 10+ / CentOS 8+
- **RAM**: 1 GB (рекомендуется 2 GB)
- **Disk**: 5 GB свободного места
- **CPU**: 1 core (рекомендуется 2 cores)
- **Порты**: 5000 (Flask API), можно изменить

### Необходимое ПО:
```bash
# Docker и Docker Compose
docker --version  # ≥20.10
docker-compose --version  # ≥1.29

# Git (для клонирования репозитория)
git --version  # ≥2.0
```

### Установка Docker (если не установлен):
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

---

## 📂 Подготовка файлов для переноса

### Список КРИТИЧНЫХ файлов (обязательны):

#### 1. Docker конфигурация:
```
docker-compose.yml
Dockerfile
Dockerfile.telegram
```

#### 2. Python приложения:
```
app.py
telegram_bot.py
config.py
ai_search.py
context_analyzer.py
database_schema.py
requirements.txt
```

#### 3. База данных:
```
database/steel_database.db
```

#### 4. Frontend:
```
templates/index.html
static/logo_white.svg
static/logo_colored.svg
```

#### 5. Environment (создать на сервере):
```
.env  # НЕ включать в git! Создать на сервере вручную
```

### Опциональные файлы (рекомендуются):
```
reports/zknives_db_updates.csv
reports/splav_composition_compare.csv
reports/zknives_page_info.csv
reports/zknives_mismatches.csv
reports/splav_ru_grades.csv
.gitignore
```

### ❌ НЕ переносить:
```
archive/              # Архивные файлы
tests/                # Тесты
docs/                 # Документация
reports/archive/      # Старые CSV
```

---

## 🛠️ Установка на сервер

### Вариант 1: Клонирование репозитория (рекомендуется)

```bash
# 1. Подключиться к серверу
ssh user@your-server-ip

# 2. Клонировать репозиторий
git clone <your-repository-url> ParserSteel
cd ParserSteel

# 3. Удалить ненужные файлы (если они есть в репозитории)
rm -rf archive/ tests/ docs/ reports/archive/

# 4. Проверить структуру
ls -lh
```

### Вариант 2: Ручной перенос файлов

```bash
# На локальной машине - создать архив ТОЛЬКО с критичными файлами
cd ParserSteel
tar -czf parsersteel_deploy.tar.gz \
    docker-compose.yml \
    Dockerfile \
    Dockerfile.telegram \
    app.py \
    telegram_bot.py \
    config.py \
    ai_search.py \
    context_analyzer.py \
    database_schema.py \
    requirements.txt \
    database/steel_database.db \
    templates/ \
    static/ \
    reports/*.csv

# Перенести на сервер
scp parsersteel_deploy.tar.gz user@your-server-ip:/home/user/

# На сервере - распаковать
ssh user@your-server-ip
mkdir -p ParserSteel
cd ParserSteel
tar -xzf ../parsersteel_deploy.tar.gz
```

---

## ⚙️ Конфигурация

### 1. Создать .env файл

```bash
cd ParserSteel
nano .env
```

**Содержимое .env:**
```env
# Telegram Bot Token (получить у @BotFather)
TELEGRAM_TOKEN=7821234567:AAHexampleTokenFromBotFather

# Perplexity API Key (основной для AI Search)
PERPLEXITY_API_KEY=pplx-abc123def456

# OpenAI API Key (fallback для AI Search)
OPENAI_API_KEY=sk-proj-abc123def456

# Flask конфигурация (опционально)
FLASK_ENV=production
FLASK_DEBUG=False
```

**Как получить API ключи:**

1. **Telegram Bot Token:**
   - Открыть @BotFather в Telegram
   - Отправить /newbot
   - Следовать инструкциям
   - Скопировать токен

2. **Perplexity API Key:**
   - Зарегистрироваться на perplexity.ai
   - Перейти в API Settings
   - Создать новый API ключ

3. **OpenAI API Key:**
   - Зарегистрироваться на platform.openai.com
   - Перейти в API Keys
   - Создать новый API ключ

### 2. Изменить порт (если нужно)

Отредактировать docker-compose.yml:
```bash
nano docker-compose.yml
```

Изменить порт Flask API:
```yaml
services:
  flask:
    ports:
      - "8080:5000"  # Изменить 5000 на нужный порт
```

### 3. Настроить firewall (если нужен внешний доступ)

```bash
# Ubuntu/Debian с UFW
sudo ufw allow 5000/tcp
sudo ufw reload

# CentOS/RHEL с firewalld
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

---

## 🚀 Запуск и проверка

### 1. Запустить Docker контейнеры

```bash
cd ParserSteel

# Собрать и запустить контейнеры
docker-compose up -d --build

# Процесс займет 3-5 минут при первой сборке
```

### 2. Проверить статус контейнеров

```bash
# Проверить, что контейнеры запущены
docker-compose ps

# Должно быть:
# NAME                STATUS              PORTS
# parsersteel-flask   Up                  0.0.0.0:5000->5000/tcp
# parsersteel-telegram Up
```

### 3. Проверить логи

```bash
# Логи Flask API
docker-compose logs -f flask

# Логи Telegram бота
docker-compose logs -f telegram

# Логи обоих
docker-compose logs -f
```

### 4. Проверить работу API

```bash
# Проверить количество марок в БД
curl http://localhost:5000/api/steels/count

# Должно вернуть: {"count": 10394}

# Поиск марки
curl "http://localhost:5000/api/steels?search=AISI%20304"

# Проверить Web интерфейс
curl -I http://localhost:5000/

# Должно вернуть: HTTP/1.1 200 OK
```

### 5. Открыть Web интерфейс

Открыть в браузере:
```
http://your-server-ip:5000
```

Должен открыться интерфейс с логотипом ВЭМ и формой поиска.

### 6. Проверить Telegram бота

1. Открыть бота в Telegram
2. Отправить /start
3. Попробовать поиск марки: AISI 304
4. Проверить AI Search: K888 (должен найти через Perplexity)

---

## 🔄 Управление контейнерами

```bash
# Остановить контейнеры
docker-compose stop

# Запустить контейнеры
docker-compose start

# Перезапустить контейнеры
docker-compose restart

# Остановить и удалить контейнеры
docker-compose down

# Пересобрать и перезапустить после изменений
docker-compose up -d --build

# Просмотр логов в реальном времени
docker-compose logs -f

# Посмотреть использование ресурсов
docker stats
```

---

## 🔧 Troubleshooting

### Проблема 1: Контейнер Flask не запускается

**Симптомы:**
```
parsersteel-flask exited with code 1
```

**Решение:**
```bash
# Проверить логи
docker-compose logs flask

# Проверить .env файл
cat .env

# Убедиться, что database/steel_database.db существует
ls -lh database/

# Пересобрать контейнер
docker-compose down
docker-compose up -d --build
```

### Проблема 2: Telegram бот не отвечает

**Симптомы:**
- Бот не отвечает на команды
- Логи показывают ошибку авторизации

**Решение:**
```bash
# Проверить логи
docker-compose logs telegram

# Проверить TELEGRAM_TOKEN в .env
cat .env | grep TELEGRAM_TOKEN

# Проверить токен у @BotFather
# Обновить .env и перезапустить
docker-compose restart telegram
```

### Проблема 3: AI Search не работает

**Симптомы:**
- AI Search возвращает ошибку
- Логи показывают "API key invalid"

**Решение:**
```bash
# Проверить API ключи
cat .env | grep API_KEY

# Проверить логи Flask
docker-compose logs flask | grep "AI Search"

# Проверить баланс на Perplexity и OpenAI
# Обновить ключи в .env и перезапустить
docker-compose restart flask
```

### Проблема 4: База данных locked

**Симптомы:**
```
database is locked
```

**Решение:**
```bash
# Проверить WAL файлы
ls -lh database/

# Перезапустить контейнеры
docker-compose restart

# Если не помогло - остановить всё и проверить БД
docker-compose down
sqlite3 database/steel_database.db "PRAGMA integrity_check;"
docker-compose up -d
```

### Проблема 5: Порт 5000 занят

**Симптомы:**
```
Error: port 5000 already in use
```

**Решение:**
```bash
# Найти процесс, использующий порт
sudo lsof -i :5000

# Остановить процесс или изменить порт в docker-compose.yml
nano docker-compose.yml
# Изменить "5000:5000" на "8080:5000"

docker-compose up -d
```

---

## ✅ Финальная проверка

После деплоя проверить:

- [ ] Docker контейнеры запущены: docker-compose ps
- [ ] API возвращает данные: curl http://localhost:5000/api/steels/count
- [ ] Web интерфейс доступен: http://your-server-ip:5000
- [ ] Telegram бот отвечает на команды
- [ ] AI Search работает (протестировать в Telegram)
- [ ] База данных содержит 10,394 марок
- [ ] Логи не содержат критических ошибок

---

## 📝 Обновление проекта

```bash
# Остановить контейнеры
docker-compose down

# Обновить код
git pull origin master

# Пересобрать и запустить
docker-compose up -d --build

# Проверить работу
curl http://localhost:5000/api/steels/count
```

---

**🎉 Проект готов к работе!**

База данных: 10,394 марок стали
Web интерфейс: Работает с логотипом ВЭМ
Telegram бот: Интегрирован с AI Search
Размер для переноса: ~13 MB
