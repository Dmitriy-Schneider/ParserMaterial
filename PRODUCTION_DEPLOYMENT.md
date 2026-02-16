# 📋 Production Deployment Guide - ParserSteel

## ✅ Проверка здоровья проекта

### База данных
- **Размер**: 9.83 MB
- **Всего марок**: 9,614
- **С ссылками**: 9,258 (96.3%)
- **С аналогами**: 6,795 (70.7%)
- **С доп. элементами**: 2,311 (24.0%)
- **Дубликаты**: 0 ✅
- **"Бал." в элементах**: 0 ✅
- **Бэкапы**: 3 последних сохранены

### Статус кода
- ✅ Все функции Similar/Compare работают
- ✅ S и P исключены из расчета, но отображаются
- ✅ Колонка Other показывает полный текст
- ✅ Аналоги парсятся через "|" разделитель
- ✅ Docker контейнеры работают стабильно

---

## 📁 Структура для Production

### Основные файлы (ОБЯЗАТЕЛЬНЫ)

```
ParserSteel/
├── app.py                          # Flask API сервер
├── config.py                       # Конфигурация
├── database_schema.py              # Подключение к БД
├── fuzzy_search.py                 # Алгоритм Similar
├── ai_search.py                    # AI поиск
├── requirements.txt                # Зависимости Flask
├── Dockerfile                      # Docker образ для web
├── docker-compose.yml              # Оркестрация контейнеров
├── .env                            # Переменные окружения (создать!)
│
├── database/
│   ├── steel_database.db           # Основная БД
│   ├── backup_manager.py           # Менеджер бэкапов
│   └── backups/                    # Последние 3 бэкапа
│       └── (MAX 3 backup folders)
│
├── telegram_bot/
│   ├── bot.py                      # Главный файл бота
│   ├── config.py                   # Конфиг бота
│   ├── context_analyzer.py         # Анализ контекста
│   ├── requirements.txt            # Зависимости бота
│   ├── Dockerfile                  # Docker образ для бота
│   └── handlers/
│       ├── search.py
│       ├── compare.py
│       └── fuzzy_search.py
│
├── templates/
│   └── index.html                  # Web интерфейс
│
└── static/
    └── (если есть CSS/JS файлы)
```

---

## 🗑️ Файлы для УДАЛЕНИЯ (не нужны на production)

### Парсеры и синхронизация
```
✗ parser.py
✗ ru_splav_sync.py
✗ ru_metallicheckiy_sync.py
✗ zknives_page_sync.py
✗ zknives_compare.py
✗ sync_db_from_excel.py
✗ add_missing_grades.py
✗ update_extra_grades.py
✗ apply_zknives_mismatches.py
✗ run_full_splav_parser.py
```

### Утилиты проверки
```
✗ check_*.py (все 10 файлов)
✗ verify_*.py
✗ investigate_*.py
✗ analyze_analogues.py
```

### Утилиты очистки (уже выполнены)
```
✗ cleanup_database.py
✗ remove_duplicates*.py (3 файла)
✗ fix_analogues.py
✗ fix_gb_standards.py
✗ find_duplicates.py
✗ find_grade_in_db.py
```

### Служебные файлы
```
✗ ai_batch_processing.py
✗ clear_ai_cache.py
```

### Директории
```
✗ archive/
✗ data/
✗ docs/
✗ importers/
✗ logs/
✗ migrations/
✗ parsers/
✗ reference_docs/
✗ reports/
✗ tests/
✗ utils/
✗ .claude/
```

---

## 🔒 Рекомендации по безопасности

### 1. Защита Web интерфейса

#### Вариант A: Basic Authentication (простой)
```python
# В app.py добавить
from functools import wraps
from flask import request, Response

def check_auth(username, password):
    return username == 'admin' and password == os.getenv('WEB_PASSWORD')

def authenticate():
    return Response(
        'Требуется авторизация', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# Применить ко всем маршрутам
@app.route('/')
@requires_auth
def index():
    ...
```

**.env файл:**
```
WEB_PASSWORD=ваш_сложный_пароль_123
```

#### Вариант B: IP Whitelist (для внутренней сети)
```python
ALLOWED_IPS = ['192.168.1.10', '192.168.1.20']

@app.before_request
def limit_remote_addr():
    if request.remote_addr not in ALLOWED_IPS:
        abort(403)
```

#### Вариант C: Flask-Login (расширенный)
```bash
pip install flask-login
```

---

### 2. Защита Telegram бота

#### Whitelist по Telegram ID

**telegram_bot/config.py:**
```python
# Список владельцев (только эти ID могут использовать бота)
ALLOWED_USER_IDS = [
    123456789,   # Ваш Telegram ID
    987654321,   # ID второго владельца
]

# Проверка доступа
def is_user_allowed(user_id: int) -> bool:
    return user_id in ALLOWED_USER_IDS
```

**telegram_bot/bot.py:**
```python
from telegram import Update
from telegram.ext import ContextTypes
import config

async def check_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Проверка доступа пользователя"""
    user_id = update.effective_user.id

    if not config.is_user_allowed(user_id):
        await update.message.reply_text(
            "⛔ Доступ запрещен. Этот бот доступен только авторизованным пользователям."
        )
        return False
    return True

# Применить ко всем хендлерам
async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update, context):
        return
    # ... остальной код
```

**Как узнать свой Telegram ID:**
1. Напишите боту @userinfobot
2. Скопируйте ID
3. Добавьте в ALLOWED_USER_IDS

---

### 3. Безопасность .env файла

**Создать `.env` файл:**
```bash
# Flask API
FLASK_SECRET_KEY=генерируйте_случайную_строку_64_символа
WEB_PASSWORD=ваш_сложный_пароль

# OpenAI API
OPENAI_API_KEY=sk-your-api-key-here

# Telegram Bot
TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather

# Database
DATABASE_PATH=database/steel_database.db

# Production settings
FLASK_ENV=production
DEBUG=False
```

**ВАЖНО:**
- ✅ `.env` уже в `.gitignore`
- ✅ НЕ коммитить .env в Git
- ✅ На сервере создать отдельный .env

---

## 🚀 Deployment на внешний сервер

### Подготовка к переносу

**1. Создать архив для production:**
```bash
# Удалить лишние файлы (см. список выше)
# Затем создать архив
tar -czf parsersteel-production.tar.gz \
  app.py config.py database_schema.py fuzzy_search.py ai_search.py \
  requirements.txt Dockerfile docker-compose.yml \
  database/ telegram_bot/ templates/ \
  --exclude='database/backups/*' \
  --exclude='database/*.db-wal' \
  --exclude='database/*.db-shm'
```

**2. Размер архива:**
- С БД: ~10-12 MB
- Без бэкапов
- Только production файлы

**3. На сервере:**
```bash
# Распаковать
tar -xzf parsersteel-production.tar.gz

# Создать .env файл
nano .env

# Запустить Docker
docker-compose up -d --build

# Проверить логи
docker-compose logs -f
```

---

## 🛡️ Дополнительные рекомендации

### 1. HTTPS (обязательно для production)
```yaml
# docker-compose.yml с Nginx + Let's Encrypt
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./certs:/etc/nginx/certs
```

### 2. Rate Limiting (ограничение запросов)
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/api/steels/fuzzy-search', methods=['POST'])
@limiter.limit("10 per minute")  # Similar - дорогая операция
def fuzzy_search_endpoint():
    ...
```

### 3. Логирование
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
```

### 4. Monitoring
```bash
# Проверка здоровья сервиса
curl http://localhost:5001/api/stats

# Мониторинг Docker
docker stats parser-steel-app parsersteel-telegram-bot
```

---

## 📊 Финальная структура для GitHub

```
ParserSteel/
├── .gitignore
├── README.md
├── PRODUCTION_DEPLOYMENT.md
├── docker-compose.yml
├── requirements.txt
│
├── app.py
├── config.py
├── database_schema.py
├── fuzzy_search.py
├── ai_search.py
│
├── database/
│   ├── backup_manager.py
│   └── .gitkeep
│
├── telegram_bot/
│   ├── bot.py
│   ├── config.py
│   ├── context_analyzer.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── handlers/
│
└── templates/
    └── index.html
```

**НЕ коммитить:**
- ❌ database/steel_database.db (слишком большой, переносить отдельно)
- ❌ .env (секреты)
- ❌ venv/
- ❌ __pycache__/
- ❌ *.log

---

## ✅ Чеклист перед deployment

- [ ] Удалить все parser/check/fix/remove скрипты
- [ ] Удалить папки: archive, data, docs, parsers, reports, tests, utils
- [ ] Создать .env файл с паролями
- [ ] Настроить ALLOWED_USER_IDS в telegram_bot/config.py
- [ ] Протестировать локально: `docker-compose up`
- [ ] Проверить web: http://localhost:5001
- [ ] Проверить telegram бота
- [ ] Создать финальный бэкап БД
- [ ] Коммит в GitHub (без БД и .env)
- [ ] Перенос на сервер
- [ ] Настроить HTTPS
- [ ] Настроить автозапуск Docker

---

## 🎯 Вердикт

### Проект готов к production ✅

**Что работает отлично:**
1. ✅ База данных чистая (9,614 марок, 0 дубликатов)
2. ✅ Similar/Compare работают корректно
3. ✅ S и P исключены из расчета
4. ✅ Колонка Other показывает полные данные
5. ✅ Docker контейнеры стабильны
6. ✅ Telegram bot функционален
7. ✅ Backup Manager с ротацией

**Что нужно сделать:**
1. 🔧 Удалить 30+ временных скриптов
2. 🔒 Добавить авторизацию для web
3. 🔒 Настроить whitelist для telegram
4. 📦 Подготовить production архив
5. 🌐 Настроить HTTPS на сервере

**Размер финального проекта:**
- Код: ~2-3 MB
- БД: ~10 MB
- Итого: ~13 MB (компактно)
