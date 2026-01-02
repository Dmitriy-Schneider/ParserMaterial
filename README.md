# ParserSteel - Профессиональный электронный марочник сталей

Современная система для поиска, сравнения и анализа марок стали со всего мира.

## Возможности

- База данных: **6,448+ марок стали** из различных стандартов
- Поиск по химическому составу (14 элементов)
- Фильтрация по маркам, аналогам, базе
- **AI-powered поиск** неизвестных марок через OpenAI GPT-4
- Автоматический fallback на AI если марка не найдена в БД
- Кэширование AI результатов
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

- `GET /api/steels` - Список марок с фильтрацией (с автоматическим AI fallback)
- `GET /api/steels/ai-search` - Прямой AI поиск
- `GET /api/stats` - Статистика базы данных
- `GET /` - Веб-интерфейс

### Примеры запросов

```bash
# Поиск по марке (автоматически использует AI если не найдена в БД)
curl "http://localhost:5001/api/steels?grade=420"

# Поиск неизвестной марки с AI (например, Bohler K340)
curl "http://localhost:5001/api/steels?grade=Bohler+K340"

# Прямой AI поиск (без проверки БД)
curl "http://localhost:5001/api/steels/ai-search?grade=Uddeholm+Vanadis+4E"

# Поиск по химическому составу
curl "http://localhost:5001/api/steels?c_min=0.9&c_max=1.1&cr_min=1.0"

# Статистика (включает AI статус)
curl "http://localhost:5001/api/stats"

# Отключить AI fallback для конкретного запроса
curl "http://localhost:5001/api/steels?grade=unknownsteel&ai=false"
```

### AI Search Features

ParserSteel использует **каскадный AI поиск** для максимального покрытия:

- **3-уровневый fallback**: Кэш → OpenAI GPT-4 → Perplexity (с доступом к интернету)
- **OpenAI GPT-4**: Для распространённых марок из базы знаний
- **Perplexity Sonar-Pro**: Для редких марок - ищет в интернете в реальном времени
- **Кэширование**: AI результаты сохраняются на 24 часа для быстрого доступа
- **Детальная информация**: Химический состав, аналоги, применение, свойства
- **Умный парсинг**: Извлекает данные из естественного языка в структурированный JSON

**Пример AI ответа:**
```json
{
  "grade": "Bohler K340",
  "found": true,
  "analogues": "AISI D2 1.2379 X155CrVMo12-1",
  "base": "Fe",
  "c": "1.50-1.60",
  "cr": "11.0-12.0",
  "mo": "0.70-0.80",
  "v": "0.90-1.00",
  "standard": "Bohler",
  "application": "Cold work tool steel, punches, dies",
  "ai_source": "openai",
  "cached": false
}
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
- [x] OpenAI fallback для неизвестных марок
- [x] Кэширование AI результатов
- [x] API endpoint для прямого AI поиска
- [ ] Умный поиск по составу с AI
- [ ] Автоматический поиск аналогов через AI
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
