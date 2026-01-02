# ParserSteel - Профессиональный электронный марочник сталей

Современная система для поиска, сравнения и анализа марок стали со всего мира.

## Возможности

- База данных: **6,448+ марок стали** из различных стандартов
- Поиск по химическому составу (14 элементов)
- Фильтрация по маркам, аналогам, базе
- Веб-интерфейс с интерактивной таблицей
- REST API для интеграций
- Docker контейнеризация

## Быстрый старт

### Docker (рекомендуется)

```bash
# Сборка и запуск
docker-compose up -d --build

# Открыть в браузере
http://localhost:5001
```

### Локальный запуск

```bash
# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt

# Запустить приложение
python app.py
```

## Конфигурация

1. Скопируйте `.env.example` в `.env`:
```bash
cp .env.example .env
```

2. Добавьте ваш OpenAI API ключ в `.env`:
```
OPENAI_API_KEY=sk-your-actual-api-key-here
```

## API Endpoints

- `GET /api/steels` - Список марок с фильтрацией
- `GET /api/stats` - Статистика базы данных
- `GET /` - Веб-интерфейс

### Примеры запросов

```bash
# Поиск по марке
curl "http://localhost:5001/api/steels?grade=420"

# Поиск по химическому составу
curl "http://localhost:5001/api/steels?c_min=0.9&c_max=1.1&cr_min=1.0"

# Статистика
curl "http://localhost:5001/api/stats"
```

## Структура проекта

```
ParserSteel/
├── app.py                 # Flask веб-сервер
├── parser.py              # Парсер zknives.com
├── database_schema.py     # Схема SQLite БД
├── config.py              # Конфигурация
├── requirements.txt       # Python зависимости
├── Dockerfile             # Docker образ
├── docker-compose.yml     # Docker Compose конфигурация
├── templates/
│   └── index.html        # Веб-интерфейс
└── database/
    └── steel_database.db # SQLite база данных
```

## Дорожная карта

### Фаза 1: Очистка и оптимизация (В процессе)
- [x] Docker контейнеризация
- [x] REST API
- [ ] Удаление дубликатов
- [ ] Оптимизация базы данных

### Фаза 2: Расширение базы данных
- [ ] Парсинг GOST (российские стандарты)
- [ ] Парсинг AISI, DIN, JIS
- [ ] Фирменные марки (Uddeholm, Bohler, Erasteel)
- [ ] Цель: 30,000-50,000 марок

### Фаза 3: AI интеграция
- [ ] OpenAI fallback для неизвестных марок
- [ ] Умный поиск по составу
- [ ] Автоматический поиск аналогов
- [ ] OCR для фото спектрометра

### Фаза 4: Визуализация
- [ ] Сравнение марок side-by-side
- [ ] Графики химического состава
- [ ] Экспорт в PDF/Excel

## Технологический стек

- **Backend:** Python 3.11, Flask, SQLite
- **Frontend:** HTML, CSS, JavaScript (Vanilla)
- **Парсинг:** BeautifulSoup, lxml, Selenium
- **AI:** OpenAI GPT-4 API (планируется)
- **DevOps:** Docker, Docker Compose

## Источники данных

- [zknives.com](https://zknives.com/knives/steels/steelchart.php) - основная база ножевых сталей
- Планируется: MatWeb, производители, государственные стандарты

## Разработка

### Запуск парсера

```bash
python parser.py
```

### Создание базы данных

```bash
python database_schema.py
```

### Запуск в режиме разработки

```bash
export FLASK_ENV=development
export FLASK_DEBUG=True
python app.py
```

## Лицензия

MIT License - см. LICENSE файл

## Контакты

Для вопросов и предложений создавайте Issue в репозитории.

---

**ParserSteel** - сделано с ❤️ для инженеров и металлургов
