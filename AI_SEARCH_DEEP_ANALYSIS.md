# Глубокий анализ системы поиска марок стали и рекомендации по улучшению AI Search

**Дата:** 2026-01-09
**Версия:** 1.0
**Статус:** Полный анализ текущего состояния + рекомендации

---

## Оглавление

1. [Часть 1: Анализ текущей системы поиска](#часть-1-анализ-текущей-системы-поиска)
2. [Часть 2: Глубокий анализ AI Search (КРИТИЧНО)](#часть-2-глубокий-анализ-ai-search-критично)
3. [Часть 3: Конкретные рекомендации по внедрению](#часть-3-конкретные-рекомендации-по-внедрению)

---

## Часть 1: Анализ текущей системы поиска

### 1.1 Архитектура системы

#### Текущая структура

```
┌─────────────────────────────────────────────────────────────┐
│                  БАЗА ДАННЫХ (SQLite)                        │
│         database/steel_database.db (~8,691 марок)           │
│                                                              │
│  Таблицы:                                                    │
│  • steel_grades - основная таблица марок                    │
│  • ai_searches  - кэш AI результатов (TTL: 24 часа)        │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────────┐
│              FLASK API (app.py) - порт 5001                 │
│                                                              │
│  Endpoints:                                                  │
│  • GET  /api/steels          - поиск + AI fallback         │
│  • GET  /api/steels/ai-search - прямой AI поиск            │
│  • POST /api/steels/add       - добавление в БД            │
│  • POST /api/steels/delete    - удаление из БД             │
│  • GET  /api/stats            - статистика                 │
│                                                              │
│  Модули:                                                     │
│  • ai_search.py        - AI интеграция (Perplexity)        │
│  • database_schema.py  - работа с БД                        │
│  • utils/pdf_parser.py - парсинг PDF спецификаций          │
└────────┬──────────────────────────┬─────────────────────────┘
         │                          │
         ↓                          ↓
┌─────────────────────┐   ┌─────────────────────────┐
│   TELEGRAM BOT      │   │   WEB ИНТЕРФЕЙС         │
│                     │   │                         │
│ • Поиск через API   │   │ • Только БД поиск       │
│ • AI включен (ai=true)│  │ • AI отключен (экономия)│
│ • Context Analyzer  │   │ • Фильтры по элементам  │
│   (GPT-4 mini)      │   │ • Exact Search (🔍)     │
└─────────────────────┘   └─────────────────────────┘
```

#### Ключевые компоненты

**1. База данных (SQLite)**
- **Расположение:** `database/steel_database.db`
- **Размер базы:** ~8,691 марок стали
- **Структура таблицы `steel_grades`:**
  - ID, grade (название марки)
  - base (Fe, Ni, Co, Ti)
  - Химические элементы: c, cr, mo, v, w, co, ni, mn, si, s, p, cu, nb, n
  - standard, manufacturer, analogues, tech (применение), link

**2. Flask API (app.py)**
- Единая точка доступа к данным
- Интеграция с AI Search модулем
- RESTful endpoints

**3. AI Search модуль (ai_search.py)**
- **Используемая модель:** Perplexity Sonar-Pro (только)
- **OpenAI удален:** Для обеспечения 100% точности
- **Кэширование:** Отключено (для возможности повторных поисков с улучшенными промптами)

---

### 1.2 Как работает поиск сейчас

#### 1.2.1 Web интерфейс

**Обычный поиск (автоматический):**
```
Пользователь вводит: "K888"
   ↓
[Задержка 1.5 сек для debounce]
   ↓
GET /api/steels?grade=K888
   ↓
Поиск в БД (LIKE '%K888%')
   ↓
Если найдено → Показывает результаты
Если НЕ найдено → Пустой массив []
   ↓
AI НЕ вызывается (экономия токенов)
```

**Exact Search (кнопка 🔍):**
```
Пользователь вводит: "K888"
Нажимает: 🔍
   ↓
GET /api/steels?grade=K888&exact=true
   ↓
Поиск в БД (WHERE grade = 'K888')
   ↓
Если найдено → Показывает результат
Если НЕ найдено → Пустой массив []
   ↓
AI НЕ вызывается
```

**Фильтры по химическому составу:**
```
Пользователь задает:
  C: 0.4-0.5%
  Cr: 4.0-5.0%
   ↓
GET /api/steels?c_min=0.4&c_max=0.5&cr_min=4.0&cr_max=5.0
   ↓
SQL запрос с диапазонами
   ↓
Показывает все совпадающие марки
```

**Вывод:** Web интерфейс НЕ использует AI - только поиск в БД.

---

#### 1.2.2 Telegram Bot

**Любой поиск через бот:**
```
Пользователь пишет: "K888" или "/search K888"
   ↓
Context Analyzer (GPT-4 mini) определяет intent
   ↓
GET /api/steels?grade=K888&ai=true
   ↓
Поиск в БД
   ↓
Если найдено → Показывает из БД
Если НЕ найдено ↓
   ↓
AI Search (Perplexity Sonar-Pro)
   ↓
Если AI нашел → Показывает + кнопка "Добавить в БД"
Если AI НЕ нашел → Сообщение "Не найдено"
```

**Context Analyzer (GPT-4 mini):**
- Определяет намерение пользователя (search, analogues, stats, help)
- Извлекает название марки из естественного языка
- Примеры:
  - "найди 420" → intent: search, grade: 420
  - "аналоги D2" → intent: analogues, grade: D2
  - "что такое Bohler K340" → intent: search, grade: Bohler K340

**Вывод:** Telegram Bot ВСЕГДА использует AI fallback для неизвестных марок.

---

### 1.3 Анализ пользовательского опыта

#### 1.3.1 Web интерфейс - Сильные стороны

✅ **Быстрый поиск в БД**
- Автоматический поиск с debounce 1.5 сек
- Мгновенные результаты для известных марок
- Фильтры по 14 химическим элементам

✅ **Экономия ресурсов**
- AI отключен → нет расхода токенов
- Подходит для массового использования

✅ **Точный поиск (🔍)**
- Проверка наличия марки в БД
- Исключает частичные совпадения

#### 1.3.2 Web интерфейс - Слабые стороны

❌ **Нет AI поиска**
- Пользователь не может найти марки вне БД
- Нет подсказок "попробуйте Telegram бот"
- Непонятно, что делать если марка не найдена

❌ **UX проблемы:**
- Пустой результат [] - не информативен
- Нет объяснения, почему марка не найдена
- Нет подсказки про альтернативные способы поиска

❌ **Ограниченная функциональность:**
- Нельзя добавить новую марку через Web
- Нельзя запросить AI поиск явно

---

#### 1.3.3 Telegram Bot - Сильные стороны

✅ **Умный AI fallback**
- Perplexity с доступом к интернету
- Находит редкие и фирменные марки
- Автоматическая валидация данных

✅ **Context Analyzer**
- Понимает естественный язык
- Не требует команд (можно просто написать название)
- Маршрутизация на правильный handler

✅ **Богатый формат вывода**
- Химический состав с русскими названиями элементов
- Аналоги, применение, свойства
- Ссылки на источники
- Индикация источника (AI vs БД)

✅ **Добавление в БД**
- Кнопка "Добавить в БД" (функционал существует в коде, но кнопки убраны)
- Пополнение базы пользователями

#### 1.3.4 Telegram Bot - Слабые стороны

❌ **Context Analyzer может ошибаться**
- GPT-4 mini иногда неправильно определяет intent
- Пример: "K888" может быть интерпретирован как stats или help

❌ **Медленный AI поиск**
- Perplexity: 15-30 секунд на запрос
- Пользователь ждет без индикации прогресса
- Timeout 60 секунд может быть превышен

❌ **Нет кэширования**
- Каждый поиск = новый API запрос к Perplexity
- Расход токенов на повторные запросы
- (Кэш намеренно отключен для тестирования, но в продакшене нужен)

❌ **Валидация слишком строгая**
- Требует обязательного химического состава
- Отклоняет результаты без composition
- Может упускать валидные марки с неполными данными

---

### 1.4 Проблемы и узкие места

#### 1.4.1 Производительность

**База данных (SQLite):**
- ⚠️ Нет timeout для concurrent access → `database is locked` ошибки
- ⚠️ Нет WAL режима → медленная запись
- ⚠️ Нет индексов на часто используемые поля (grade, base)

**Рекомендация:**
```python
# database_schema.py
def get_connection():
    conn = sqlite3.connect(config.DB_FILE, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
    return conn
```

**AI Search:**
- ⚠️ Perplexity: 15-30 сек на запрос (медленно)
- ⚠️ Нет параллельных запросов (sequential)
- ⚠️ Нет streaming ответов (пользователь ждет весь результат)

---

#### 1.4.2 UI/UX проблемы

**Web интерфейс:**

1. **Пустой результат не информативен**
   - Текущее: `[]` (пустой массив)
   - Нужно: Сообщение "Марка не найдена в базе данных (8,691 марок). Попробуйте Telegram бот для AI поиска."

2. **Кнопка 🔍 непонятна**
   - Нет подсказки (tooltip)
   - Непонятно, чем отличается от обычного поиска

3. **Нет индикации загрузки**
   - При поиске нет спиннера
   - Не видно, что система работает

4. **Фильтры сложны для новичков**
   - Нет примеров использования
   - Нет пресетов (например, "Нержавеющие стали", "Инструментальные стали")

**Telegram Bot:**

1. **Долгое ожидание AI**
   - Нет прогресс-бара
   - Нет промежуточных сообщений ("Ищу в интернете...")

2. **Validation отклоняет валидные результаты**
   - Слишком строгая проверка химического состава
   - Нет возможности показать результат с пометкой "неполные данные"

3. **Кнопки удалены**
   - Раньше были кнопки "Добавить в БД" и "Удалить"
   - Сейчас функционал недоступен пользователям

---

#### 1.4.3 Архитектурные проблемы

1. **Дублирование конфигурации**
   - `config.py` в корне
   - `telegram_bot/config.py` отдельный
   - Нужно синхронизировать вручную

2. **Нет единого logging**
   - `print()` вместо `logging`
   - Сложно отладить проблемы в продакшене

3. **Жестко закодированные значения**
   - Timeout 60 сек в telegram bot
   - Debounce 1.5 сек в Web
   - MAX_RESULTS_PER_MESSAGE = 5

4. **Нет rate limiting**
   - AI Search может быть заспамлен
   - Нет ограничения запросов на пользователя

---

### 1.5 Рекомендации по улучшению текущей системы

#### Приоритет 1: UX улучшения (быстро внедрить)

**Web интерфейс:**

1. **Информативное сообщение "не найдено"**
```javascript
// templates/index.html
if (results.length === 0) {
    resultsDiv.innerHTML = `
        <div class="no-results">
            <h3>❌ Марка не найдена</h3>
            <p>Поиск выполнен в базе данных (8,691 марок).</p>
            <p><strong>Хотите найти редкие марки?</strong></p>
            <p>Используйте <a href="t.me/your_bot">Telegram бот</a> с AI поиском!</p>
        </div>
    `;
}
```

2. **Tooltip для кнопки 🔍**
```html
<button class="btn-exact-search"
        onclick="searchExact()"
        title="Точный поиск: ищет точное совпадение названия марки">
    🔍
</button>
```

3. **Индикатор загрузки**
```javascript
function searchSteels(exactSearch = false) {
    resultsDiv.innerHTML = '<div class="loading">🔄 Поиск...</div>';
    // ... fetch ...
}
```

**Telegram Bot:**

1. **Промежуточные сообщения**
```python
# telegram_bot/handlers/search.py
status_msg = await update.message.reply_text(
    f"🔍 Ищу марку `{grade_name}` в базе данных...",
    parse_mode='Markdown'
)

# Если не нашли в БД
await status_msg.edit_text(
    f"🔍 Марка не найдена в БД.\n"
    f"🤖 Запускаю AI поиск через Perplexity (может занять 20-30 сек)...",
    parse_mode='Markdown'
)
```

2. **Менее строгая валидация**
```python
# ai_search.py
if not is_valid:
    # Вместо полного отклонения
    result['validated'] = False
    result['warning'] = 'Неполные данные - требуется проверка'
    return result  # Показываем с предупреждением
```

---

#### Приоритет 2: Производительность

1. **Улучшить database connection**
```python
# database_schema.py
def get_connection():
    conn = sqlite3.connect(config.DB_FILE, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
    return conn
```

2. **Добавить индексы**
```python
# database_schema.py
def create_indexes():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_grade ON steel_grades(grade)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_base ON steel_grades(base)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_standard ON steel_grades(standard)")
    conn.commit()
    conn.close()
```

3. **Включить кэширование AI (с TTL)**
```python
# ai_search.py
# Убрать комментарии с кэша
cached_result = self._get_from_cache(grade_name)
if cached_result:
    return cached_result

# После успешного поиска
self._save_to_cache(grade_name, result)
```

---

#### Приоритет 3: Архитектура

1. **Единый конфиг**
```python
# Использовать один config.py из корня
# telegram_bot/config.py -> импорт из корня
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
import config
```

2. **Централизованный logging**
```python
# utils/logger.py
import logging

def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler('logs/parsersteel.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

# Использование:
# logger = get_logger(__name__)
# logger.info(f"Searching for {grade_name}")
```

3. **Rate limiting для AI**
```python
# ai_search.py
from functools import lru_cache
from datetime import datetime, timedelta

class AISearch:
    def __init__(self):
        self.request_log = {}  # user_id: [timestamps]
        self.max_requests_per_hour = 20

    def check_rate_limit(self, user_id):
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)

        if user_id not in self.request_log:
            self.request_log[user_id] = []

        # Удалить старые запросы
        self.request_log[user_id] = [
            ts for ts in self.request_log[user_id]
            if ts > hour_ago
        ]

        if len(self.request_log[user_id]) >= self.max_requests_per_hour:
            return False

        self.request_log[user_id].append(now)
        return True
```

---

### 1.6 Должна ли система быть упрощена или расширена?

#### Вывод: РАСШИРЕНА (но с упрощением пользовательского опыта)

**Что упростить:**
- ❌ Убрать Context Analyzer (GPT-4 mini) - работает плохо, лучше явные команды
- ❌ Убрать строгую валидацию - показывать результаты с предупреждениями
- ❌ Упростить UI - меньше кнопок, больше автоматизма

**Что расширить:**
- ✅ Multi-agent AI Search (см. Часть 2)
- ✅ Лучшие промпты для Perplexity
- ✅ PDF/OCR парсинг
- ✅ Приоритизация источников
- ✅ Confidence scoring

**Баланс:** Сложная AI логика "под капотом" + простой UX для пользователя.

---

## Часть 2: Глубокий анализ AI Search (КРИТИЧНО)

### 2.1 Почему API Perplexity/OpenAI хуже веб-версий?

#### Проблема: API vs Web интерфейс

**Наблюдение из практики:**
- Web Perplexity (perplexity.ai) дает более точные и полные результаты
- API Perplexity (через api.perplexity.ai) иногда дает неполные данные
- OpenAI GPT-4 (через API) вообще не имеет доступа к интернету (только база знаний до 2023)

**Причины:**

1. **Web версия использует дополнительную обработку**
   - Pre-processing запросов (query expansion)
   - Post-processing результатов (fact checking)
   - Визуальный рендеринг таблиц и структур данных
   - Более глубокая индексация источников

2. **API ограничения**
   - Меньше tokens для контекста
   - Нет интерактивных уточнений
   - Меньше времени на поиск (timeout)
   - Меньше sources проверяется

3. **Промпт имеет значение**
   - Web UI оптимизирован годами
   - API промпт написан нами → может быть неоптимальным
   - Недостаточная детализация требований

---

### 2.2 Анализ текущего промпта

#### Текущий промпт (ai_search.py:440-501)

**Сильные стороны:**
✅ Детальная структура JSON
✅ Требование химического состава (MANDATORY)
✅ Приоритет источников (manufacturer > standard > PDF)
✅ Запрет на выдумывание данных
✅ Требование source_url
✅ Поля на русском (application, properties)

**Слабые стороны:**

❌ **1. Нет явного указания приоритета источников в инструкции**
```python
# Текущее:
"Search MULTIPLE sources (manufacturer datasheets, MatWeb, steelnumber.com, standards)"

# Нужно:
"Search sources in STRICT PRIORITY ORDER:
1. PRIORITY 1 (MOST RELIABLE): Manufacturer official datasheets (PDF)
2. PRIORITY 2: Official standards (AISI, DIN, GOST, JIS, etc.)
3. PRIORITY 3: Verified databases (MatWeb, steelnumber.com)
4. PRIORITY 4 (LEAST RELIABLE): General websites, forums
NEVER use Priority 4 sources for chemical composition."
```

❌ **2. Нет требования cross-verification**
```python
# Текущее:
"Cross-check chemical composition from at least 2 sources if possible"

# Нужно:
"MANDATORY: Chemical composition MUST be verified from AT LEAST 2 independent sources.
If sources disagree:
- Use manufacturer datasheet as PRIMARY source
- Note discrepancy in 'validation_notes' field
- If difference > 5% for any element → mark as 'requires_verification'"
```

❌ **3. Нет обработки неоднозначностей**
```python
# Нужно добавить:
"If multiple variants of the grade exist (e.g., K340 vs K340 ISOBLOC):
- Return the MOST COMMON variant
- Note other variants in 'analogues' field
- Specify which variant in 'grade' field"
```

❌ **4. Нет требования к citation/provenance**
```python
# Нужно добавить:
"For EACH piece of information, internally track which source it came from.
Priority of trust:
- Chemical composition: Manufacturer PDF > Standard > Database
- Analogues: Official standard > Manufacturer claim > Database
- Properties: Manufacturer > Technical database > General source"
```

❌ **5. Недостаточная детализация для редких марок**
```python
# Нужно добавить:
"For proprietary/rare grades not in common databases:
1. Search manufacturer's website FIRST
2. Look for PDF datasheets (product_name.pdf, technical_datasheet.pdf)
3. If PDF found, extract composition from tables (look for 'Chemical Composition', 'Analysis', 'Typical')
4. If no PDF, search for HTML tables on manufacturer product pages
5. As last resort, use secondary databases (but mark as 'low_confidence')"
```

---

### 2.3 Multi-Agent подход - рекомендации

#### Концепция: Цепочка специализированных агентов

Вместо одного промпта → несколько агентов, каждый со своей задачей.

```
┌─────────────────────────────────────────────────────────────┐
│                   АГЕНТ 1: ИСТОЧНИКИ                         │
│        Задача: Найти релевантные источники                   │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
                [Список URL + оценка надежности]
                        ↓
┌─────────────────────────────────────────────────────────────┐
│              АГЕНТ 2: ИЗВЛЕЧЕНИЕ ДАННЫХ                      │
│     Задача: Извлечь химический состав из источников         │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
          [Composition из каждого источника]
                        ↓
┌─────────────────────────────────────────────────────────────┐
│               АГЕНТ 3: ВЕРИФИКАЦИЯ                           │
│  Задача: Сравнить данные, выбрать наиболее достоверные      │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
           [Verified composition + confidence]
                        ↓
┌─────────────────────────────────────────────────────────────┐
│              АГЕНТ 4: АНАЛОГИ                                │
│  Задача: Найти официальные аналоги из стандартов            │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
        [Analogues: официальные + по составу]
                        ↓
┌─────────────────────────────────────────────────────────────┐
│            АГЕНТ 5: ФОРМАТИРОВАНИЕ                           │
│   Задача: Собрать финальный JSON + confidence scores        │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
                  [Final Result]
```

---

#### Агент 1: Source Finder (Поиск источников)

**Задача:** Найти релевантные и надежные источники для марки стали.

**Промпт:**
```python
def agent_1_find_sources(grade_name: str) -> List[Dict]:
    prompt = f"""You are a source verification agent for steel grade databases.

Task: Find reliable sources for steel grade "{grade_name}".

PRIORITY ORDER (search in this order):
1. Manufacturer official website (e.g., bohler-edelstahl.com, uddeholm.com)
2. PDF datasheets from manufacturer
3. Official standards (AISI, DIN, GOST, JIS, EN, etc.)
4. Verified databases (MatWeb, steelnumber.com, azom.com)
5. Academic/technical papers

For EACH source found, return:
{{
  "url": "full URL",
  "type": "manufacturer_pdf | manufacturer_web | standard | database | paper",
  "reliability": "high | medium | low",
  "found_composition": true/false,
  "found_analogues": true/false,
  "notes": "brief description of what this source contains"
}}

Return JSON array of sources, ordered by reliability (highest first).
MAXIMUM 5 sources.

Example:
[
  {{
    "url": "https://www.bohler-edelstahl.com/app/uploads/sites/248/productdb/api/k888-matrix_en_gb.pdf",
    "type": "manufacturer_pdf",
    "reliability": "high",
    "found_composition": true,
    "found_analogues": true,
    "notes": "Official Bohler K888 MATRIX datasheet with full composition table"
  }},
  ...
]
"""
    # Call Perplexity with this prompt
    # Return parsed sources
```

**Преимущества:**
- Специализация на поиске (не отвлекается на extraction)
- Оценка надежности заранее
- Приоритизация лучших источников

---

#### Агент 2: Data Extractor (Извлечение данных)

**Задача:** Извлечь химический состав из каждого источника.

**Промпт:**
```python
def agent_2_extract_composition(grade_name: str, source_url: str, source_type: str) -> Dict:
    prompt = f"""You are a data extraction agent specialized in steel chemical composition.

Steel grade: "{grade_name}"
Source URL: {source_url}
Source type: {source_type}

Task: Extract ONLY the chemical composition from this source.

EXTRACTION RULES:
1. Look for tables with headers: "Chemical Composition", "Analysis", "Typical Composition", "Nominal"
2. Extract values for these elements (if present):
   C, Cr, Ni, Mo, V, W, Co, Mn, Si, S, P, Cu, Nb, N, Ti, Al
3. Values can be:
   - Single value: "0.90" → return as "0.90"
   - Range: "0.85-0.95" → return as "0.85-0.95"
   - Max value: "max 0.03" → return as "0.03" (note "max" in separate field)
4. NEVER invent or estimate values
5. If element not found → return null

Return JSON:
{{
  "source_url": "{source_url}",
  "composition": {{
    "c": "value or null",
    "cr": "value or null",
    ...
  }},
  "extraction_confidence": "high | medium | low",
  "extraction_notes": "e.g., 'Extracted from Table 1 on page 2'"
}}

If composition not found in this source, return:
{{
  "source_url": "{source_url}",
  "composition": null,
  "extraction_confidence": "none",
  "extraction_notes": "Chemical composition not found in this source"
}}
"""
    # Call AI with this prompt
    # Return extracted composition
```

**Преимущества:**
- Фокус только на extraction (не отвлекается на поиск)
- Отдельный confidence для каждого источника
- Можно распараллелить для нескольких источников

---

#### Агент 3: Verifier (Верификация)

**Задача:** Сравнить данные из нескольких источников и выбрать наиболее достоверные.

**Промпт:**
```python
def agent_3_verify_composition(grade_name: str, extractions: List[Dict]) -> Dict:
    prompt = f"""You are a verification agent for steel composition data.

Steel grade: "{grade_name}"

You have extracted composition from {len(extractions)} sources:
{json.dumps(extractions, indent=2)}

Task: Determine the MOST RELIABLE composition.

VERIFICATION RULES:
1. If multiple sources agree (within 5% tolerance) → HIGH confidence
2. If sources disagree:
   - Prioritize: manufacturer_pdf > standard > database
   - Note discrepancy in validation_notes
   - Confidence = MEDIUM
3. If only 1 source → MEDIUM confidence
4. For EACH element, choose the value from the highest-reliability source

Return JSON:
{{
  "composition": {{
    "c": "chosen value",
    "cr": "chosen value",
    ...
  }},
  "confidence_scores": {{
    "c": "high | medium | low",
    "cr": "high | medium | low",
    ...
  }},
  "overall_confidence": "high | medium | low",
  "validation_notes": [
    "C: 3 sources agree (0.90-0.95)",
    "Cr: Discrepancy found - manufacturer: 4.0-5.0%, database: 4.5-5.5%"
  ],
  "sources_used": [
    "manufacturer_pdf: https://...",
    "database: https://..."
  ]
}}

MANDATORY: Return composition ONLY if at least 3 major elements (C, Cr, Mo, V, W, Co, Ni) are found.
If not enough data → return null.
"""
    # Call AI with this prompt
    # Return verified composition with confidence scores
```

**Преимущества:**
- Cross-verification автоматическая
- Confidence scores для каждого элемента
- Прозрачность (validation_notes)

---

#### Агент 4: Analogues Finder (Поиск аналогов)

**Задача:** Найти официальные аналоги и аналоги по химическому составу.

**Промпт:**
```python
def agent_4_find_analogues(grade_name: str, composition: Dict, standard: str) -> Dict:
    prompt = f"""You are an analogues finder agent for steel grades.

Steel grade: "{grade_name}"
Standard: {standard}
Chemical composition:
{json.dumps(composition, indent=2)}

Task: Find analogues (equivalent grades).

ANALOGUES PRIORITY:
1. OFFICIAL ANALOGUES (highest priority):
   - From official standards (AISI, DIN, JIS, GOST)
   - From manufacturer documentation
   - Explicitly stated as "equivalent to..."

2. COMPOSITION-BASED ANALOGUES (fallback):
   - Grades with similar composition (±10% for each element)
   - Must have at least 70% match of major elements

Return JSON:
{{
  "official_analogues": [
    {{
      "grade": "AISI D2",
      "standard": "AISI",
      "source": "ISO 4957:2018 equivalence table",
      "confidence": "high"
    }},
    ...
  ],
  "composition_based_analogues": [
    {{
      "grade": "1.2379",
      "standard": "DIN",
      "match_percentage": 85,
      "source": "composition comparison",
      "confidence": "medium"
    }},
    ...
  ],
  "analogues_string": "AISI D2, DIN 1.2379, JIS SKD11 (official); X155CrVMo12-1 (by composition)"
}}

IMPORTANT: Separate official analogues from composition-based ones.
Mark confidence for each analogue.
"""
    # Call AI with this prompt
    # Return analogues with priority separation
```

**Преимущества:**
- Разделение официальных и расчетных аналогов
- Confidence scores
- Можно показывать по-разному в UI

---

#### Агент 5: Formatter (Форматирование)

**Задача:** Собрать все данные в финальный JSON с метаданными.

```python
def agent_5_format_result(grade_name: str,
                          verified_composition: Dict,
                          analogues: Dict,
                          sources: List[Dict]) -> Dict:
    """
    Сборка финального результата с:
    - Verified composition
    - Confidence scores
    - Analogues (official vs composition-based)
    - Source provenance
    - Validation notes
    """
    return {
        "grade": grade_name,
        "found": True,
        "composition": verified_composition['composition'],
        "confidence_scores": verified_composition['confidence_scores'],
        "overall_confidence": verified_composition['overall_confidence'],
        "analogues_official": analogues['official_analogues'],
        "analogues_composition": analogues['composition_based_analogues'],
        "analogues": analogues['analogues_string'],
        "sources": sources,
        "validation_notes": verified_composition['validation_notes'],
        "timestamp": datetime.now().isoformat(),
        "agent_version": "multi-agent-v1"
    }
```

---

### 2.4 Система приоритета источников

#### Иерархия надежности

```
TIER 1 (100% достоверность):
├── Официальные PDF спецификации производителя
│   └── Примеры: bohler-edelstahl.com/products/*.pdf
│               uddeholm.com/app/uploads/sites/.../*.pdf
│
└── Официальные стандарты (ISO, AISI, DIN, GOST, JIS)
    └── Примеры: ISO 4957:2018, AISI tool steel standards

TIER 2 (90-95% достоверность):
├── Страницы продуктов производителя (HTML)
│   └── Таблицы на сайте производителя
│
└── Специализированные базы данных
    └── MatWeb, steelnumber.com, azom.com

TIER 3 (70-80% достоверность):
├── Академические статьи / научные публикации
└── Отраслевые справочники

TIER 4 (НЕ использовать для composition):
├── Форумы, блоги
└── Общие веб-сайты
```

#### Правила использования

1. **Химический состав:** ТОЛЬКО TIER 1-2
2. **Аналоги:** TIER 1-3 (с пометкой confidence)
3. **Применение/свойства:** TIER 1-3 (можно TIER 4 с пометкой)

#### Реализация

```python
class SourcePrioritySystem:
    TIER_1 = ["manufacturer_pdf", "official_standard"]
    TIER_2 = ["manufacturer_web", "verified_database"]
    TIER_3 = ["academic_paper", "industry_handbook"]
    TIER_4 = ["forum", "blog", "general_website"]

    def get_tier(self, source_type: str) -> int:
        if source_type in self.TIER_1:
            return 1
        elif source_type in self.TIER_2:
            return 2
        elif source_type in self.TIER_3:
            return 3
        else:
            return 4

    def is_valid_for_composition(self, source_type: str) -> bool:
        return self.get_tier(source_type) <= 2

    def get_confidence(self, source_type: str, agreement_count: int) -> str:
        tier = self.get_tier(source_type)

        if tier == 1 and agreement_count >= 2:
            return "high"
        elif tier <= 2 and agreement_count >= 1:
            return "medium"
        else:
            return "low"
```

---

### 2.5 OCR/PDF/Image Recognition требования

#### 2.5.1 PDF Парсинг

**Текущее состояние:**
- ✅ Модуль существует: `utils/pdf_parser.py`
- ✅ Использует pdfplumber (основной) + PyPDF2 (fallback)
- ✅ Интегрирован с AI Search
- ⚠️ Парсит только первые 5 страниц
- ⚠️ Нет OCR для сканов

**Улучшения:**

1. **Расширить парсинг**
```python
# utils/pdf_parser.py
def extract_text_pdfplumber(self, pdf_path: str, max_pages: int = 10) -> Optional[str]:
    """Extract from first 10 pages (not 5)"""
    with pdfplumber.open(pdf_path) as pdf:
        # Ищем страницу с "Chemical Composition"
        for i, page in enumerate(pdf.pages[:max_pages]):
            text = page.extract_text()
            if 'chemical composition' in text.lower() or 'analysis' in text.lower():
                # Извлечь эту страницу + следующую
                return '\n\n'.join([
                    pdf.pages[i].extract_text(),
                    pdf.pages[min(i+1, len(pdf.pages)-1)].extract_text()
                ])
```

2. **Таблицы**
```python
def extract_tables(self, pdf_path: str) -> List[List[List[str]]]:
    """Extract all tables from PDF"""
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[:10]:
            page_tables = page.extract_tables()
            if page_tables:
                tables.extend(page_tables)
    return tables

def find_composition_table(self, tables: List) -> Optional[Dict]:
    """Find table with chemical composition"""
    for table in tables:
        # Ищем заголовки: C, Cr, Mo, V, W, ...
        if self._is_composition_table(table):
            return self._parse_composition_table(table)
    return None
```

---

#### 2.5.2 OCR для сканов PDF

**Проблема:** Некоторые PDF - это сканы (изображения), pdfplumber не работает.

**Решение:** Добавить OCR через Tesseract или Azure/AWS OCR.

```python
# utils/ocr_parser.py
import pytesseract
from PIL import Image
import pdf2image

class OCRParser:
    def __init__(self):
        # Настройка Tesseract
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

    def pdf_to_images(self, pdf_path: str) -> List[Image.Image]:
        """Convert PDF pages to images"""
        images = pdf2image.convert_from_path(pdf_path, dpi=300)
        return images[:10]  # First 10 pages

    def extract_text_from_image(self, image: Image.Image) -> str:
        """Extract text using OCR"""
        # Предобработка для лучшего OCR
        image = image.convert('L')  # Grayscale
        text = pytesseract.image_to_string(image, lang='eng')
        return text

    def extract_from_scanned_pdf(self, pdf_path: str) -> str:
        """Full pipeline: PDF → Images → OCR → Text"""
        images = self.pdf_to_images(pdf_path)
        texts = []
        for img in images:
            text = self.extract_text_from_image(img)
            if 'chemical' in text.lower() or 'composition' in text.lower():
                texts.append(text)
        return '\n\n'.join(texts)
```

**Интеграция:**
```python
# utils/pdf_parser.py
def extract_text(self, pdf_path: str) -> str:
    # Try pdfplumber first
    text = self.extract_text_pdfplumber(pdf_path)

    if not text or len(text) < 100:
        # Fallback to OCR
        print("PDF appears to be scanned, using OCR...")
        ocr = OCRParser()
        text = ocr.extract_from_scanned_pdf(pdf_path)

    return text
```

---

#### 2.5.3 Image Recognition (фото спектрометра)

**Use Case:** Пользователь фотографирует результаты спектрометра → система распознает химический состав.

**Технология:** Azure Computer Vision или GPT-4 Vision API.

```python
# utils/spectrometer_ocr.py
from openai import OpenAI

class SpectrometerOCR:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def analyze_spectrometer_image(self, image_path: str) -> Dict:
        """
        Analyze spectrometer readout image using GPT-4 Vision
        """
        import base64

        # Encode image
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode()

        prompt = """Analyze this spectrometer readout image.

Extract chemical composition values for these elements:
C, Cr, Ni, Mo, V, W, Co, Mn, Si, S, P, Cu, Nb, N

Return JSON:
{
  "composition": {
    "c": "value in %",
    "cr": "value in %",
    ...
  },
  "confidence": "high | medium | low",
  "notes": "any observations"
}

If you cannot read some values clearly, set them to null.
"""

        response = self.client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )

        # Parse response
        result = json.loads(response.choices[0].message.content)
        return result
```

**Интеграция с Telegram Bot:**
```python
# telegram_bot/handlers/photo.py
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle spectrometer photo"""
    photo = update.message.photo[-1]  # Largest size
    file = await photo.get_file()

    # Download
    photo_path = f"/tmp/{photo.file_id}.jpg"
    await file.download_to_drive(photo_path)

    # Analyze
    await update.message.reply_text("🔍 Анализирую фото спектрометра...")

    ocr = SpectrometerOCR(api_key=os.getenv('OPENAI_API_KEY'))
    result = ocr.analyze_spectrometer_image(photo_path)

    # Search for matching grades
    # ...
```

---

### 2.6 Химический состав - верификация (первичная цель)

#### Требования к верификации

**Цель:** Убедиться, что химический состав достоверен и полон.

**Критерии:**

1. **Минимальный набор элементов:**
   - Для инструментальных сталей: C, Cr, Mo, V (обязательно)
   - Для нержавеющих: C, Cr, Ni (обязательно)
   - Для быстрорежущих: C, Cr, Mo, V, W (обязательно)

2. **Валидация диапазонов:**
   - C: 0-5% (обычно 0.1-2.0% для tool steels)
   - Cr: 0-30% (обычно 4-18%)
   - Ni: 0-20%
   - Mo: 0-10%
   - V: 0-5%
   - W: 0-20%

3. **Cross-verification:**
   - Если 2+ источника → сравнить
   - Если расхождение >10% → флаг "requires_verification"
   - Если расхождение >25% → отклонить

4. **Сумма элементов:**
   - Fe + C + Cr + Ni + Mo + ... должна быть ≈ 100%
   - Если сумма < 95% или > 105% → флаг "incomplete_data"

---

#### Улучшенная валидация

```python
class CompositionValidator:
    """Advanced composition validation"""

    REQUIRED_ELEMENTS = {
        'tool_steel': ['c', 'cr', 'mo', 'v'],
        'stainless': ['c', 'cr', 'ni'],
        'hsshigh_speed': ['c', 'cr', 'mo', 'v', 'w'],
        'default': ['c']  # At minimum
    }

    ELEMENT_RANGES = {
        'c': (0.0, 5.0),
        'cr': (0.0, 30.0),
        'ni': (0.0, 20.0),
        'mo': (0.0, 10.0),
        'v': (0.0, 5.0),
        'w': (0.0, 20.0),
        'co': (0.0, 15.0),
        'mn': (0.0, 2.0),
        'si': (0.0, 2.0),
    }

    def validate(self, composition: Dict, steel_type: str = 'default') -> Dict:
        """
        Comprehensive validation

        Returns:
        {
          "valid": True/False,
          "confidence": "high | medium | low",
          "issues": [],
          "warnings": []
        }
        """
        issues = []
        warnings = []

        # 1. Check required elements
        required = self.REQUIRED_ELEMENTS.get(steel_type, self.REQUIRED_ELEMENTS['default'])
        for elem in required:
            if elem not in composition or not composition[elem]:
                issues.append(f"Missing required element: {elem.upper()}")

        # 2. Validate ranges
        for elem, value in composition.items():
            if not value:
                continue

            try:
                # Parse range or single value
                if '-' in str(value):
                    min_val, max_val = map(float, str(value).split('-'))
                else:
                    min_val = max_val = float(value)

                # Check against expected range
                if elem in self.ELEMENT_RANGES:
                    expected_min, expected_max = self.ELEMENT_RANGES[elem]
                    if max_val > expected_max:
                        warnings.append(f"{elem.upper()}: {value}% exceeds typical range (max {expected_max}%)")
                    if min_val < 0:
                        issues.append(f"{elem.upper()}: negative value not allowed")

            except ValueError:
                issues.append(f"{elem.upper()}: invalid format '{value}'")

        # 3. Check sum (if Fe is present or can be inferred)
        total_sum = self._calculate_sum(composition)
        if total_sum > 105:
            warnings.append(f"Sum of elements ({total_sum}%) > 100% - possible error")
        elif total_sum < 95 and len(composition) > 5:
            warnings.append(f"Sum of elements ({total_sum}%) < 100% - incomplete data")

        # Determine validity and confidence
        valid = len(issues) == 0

        if valid and len(warnings) == 0:
            confidence = "high"
        elif valid and len(warnings) <= 2:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "valid": valid,
            "confidence": confidence,
            "issues": issues,
            "warnings": warnings,
            "element_count": len([v for v in composition.values() if v])
        }

    def cross_verify(self, compositions: List[Dict]) -> Dict:
        """
        Compare compositions from multiple sources
        """
        if len(compositions) < 2:
            return {"agreement": "single_source", "confidence": "medium"}

        # Compare each element across sources
        discrepancies = []
        agreements = []

        all_elements = set()
        for comp in compositions:
            all_elements.update(comp.keys())

        for elem in all_elements:
            values = []
            for comp in compositions:
                if elem in comp and comp[elem]:
                    # Parse to mid-range value
                    val_str = str(comp[elem])
                    if '-' in val_str:
                        min_v, max_v = map(float, val_str.split('-'))
                        values.append((min_v + max_v) / 2)
                    else:
                        values.append(float(val_str))

            if len(values) < 2:
                continue

            # Check agreement
            avg_val = sum(values) / len(values)
            max_diff = max(abs(v - avg_val) for v in values)
            percent_diff = (max_diff / avg_val * 100) if avg_val > 0 else 0

            if percent_diff > 25:
                discrepancies.append({
                    "element": elem,
                    "values": values,
                    "percent_diff": percent_diff,
                    "severity": "high"
                })
            elif percent_diff > 10:
                discrepancies.append({
                    "element": elem,
                    "values": values,
                    "percent_diff": percent_diff,
                    "severity": "medium"
                })
            else:
                agreements.append(elem)

        # Overall confidence
        if len(discrepancies) == 0:
            confidence = "high"
        elif len([d for d in discrepancies if d['severity'] == 'high']) > 0:
            confidence = "low"
        else:
            confidence = "medium"

        return {
            "agreement": "verified" if len(discrepancies) == 0 else "partial",
            "confidence": confidence,
            "agreements": agreements,
            "discrepancies": discrepancies,
            "source_count": len(compositions)
        }
```

---

### 2.7 Аналоги - верификация (вторичная цель)

#### Иерархия достоверности аналогов

```
TIER 1: Официальные аналоги из стандартов
├── Таблицы эквивалентности в ISO, DIN, AISI, GOST, JIS
├── Пример: ISO 4957:2018 - Table of equivalent grades
└── Confidence: HIGH (95-100%)

TIER 2: Аналоги от производителя
├── "This grade is equivalent to AISI D2"
├── Указано на сайте/PDF производителя
└── Confidence: HIGH (90-95%)

TIER 3: Аналоги из баз данных
├── MatWeb, steelnumber.com указывают equivalents
└── Confidence: MEDIUM (80-90%)

TIER 4: Аналоги по химическому составу
├── Автоматический поиск по composition match
├── Match > 90% → может быть аналогом
└── Confidence: MEDIUM (70-80%)

TIER 5: Предполагаемые аналоги
├── "Similar to...", "Comparable with..."
└── Confidence: LOW (50-70%)
```

---

#### Алгоритм верификации аналогов

```python
class AnaloguesVerifier:
    """Verify and rank analogues by confidence"""

    def verify_analogues(self,
                        grade_name: str,
                        composition: Dict,
                        analogues_list: List[str],
                        sources: List[Dict]) -> List[Dict]:
        """
        Verify each analogue and assign confidence

        Returns list of:
        {
          "grade": "AISI D2",
          "standard": "AISI",
          "confidence": "high",
          "verification_method": "official_standard",
          "source": "ISO 4957:2018",
          "composition_match": 95  # % match if verified by composition
        }
        """
        verified_analogues = []

        for analogue in analogues_list:
            verification = self._verify_single_analogue(
                grade_name,
                analogue,
                composition,
                sources
            )
            verified_analogues.append(verification)

        # Sort by confidence
        verified_analogues.sort(key=lambda x: self._confidence_score(x['confidence']), reverse=True)

        return verified_analogues

    def _verify_single_analogue(self,
                                grade_name: str,
                                analogue: str,
                                composition: Dict,
                                sources: List[Dict]) -> Dict:
        """Verify single analogue"""

        # Check if found in official standard
        for source in sources:
            if source['type'] == 'official_standard':
                if analogue in source['content']:
                    return {
                        "grade": analogue,
                        "confidence": "high",
                        "verification_method": "official_standard",
                        "source": source['url']
                    }

        # Check if mentioned by manufacturer
        for source in sources:
            if source['type'] in ['manufacturer_pdf', 'manufacturer_web']:
                if analogue in source['content']:
                    return {
                        "grade": analogue,
                        "confidence": "high",
                        "verification_method": "manufacturer_claim",
                        "source": source['url']
                    }

        # Check composition match
        analogue_composition = self._get_composition_from_db(analogue)
        if analogue_composition:
            match_percent = self._calculate_composition_match(composition, analogue_composition)

            if match_percent >= 90:
                return {
                    "grade": analogue,
                    "confidence": "medium",
                    "verification_method": "composition_match",
                    "composition_match": match_percent,
                    "source": "database_comparison"
                }
            elif match_percent >= 70:
                return {
                    "grade": analogue,
                    "confidence": "low",
                    "verification_method": "composition_similarity",
                    "composition_match": match_percent,
                    "source": "database_comparison"
                }

        # No verification possible
        return {
            "grade": analogue,
            "confidence": "unverified",
            "verification_method": "mentioned_only",
            "source": "ai_response"
        }

    def _calculate_composition_match(self, comp1: Dict, comp2: Dict) -> float:
        """
        Calculate % match between two compositions

        Algorithm:
        - For each major element (C, Cr, Mo, V, W, Co, Ni)
        - Calculate overlap of ranges
        - Weight by importance (C and Cr are most important)
        """
        weights = {
            'c': 0.25,
            'cr': 0.25,
            'mo': 0.15,
            'v': 0.10,
            'w': 0.10,
            'ni': 0.05,
            'co': 0.05,
            'mn': 0.03,
            'si': 0.02
        }

        total_score = 0
        total_weight = 0

        for elem, weight in weights.items():
            if elem not in comp1 or elem not in comp2:
                continue

            val1 = self._parse_value_range(comp1[elem])
            val2 = self._parse_value_range(comp2[elem])

            if not val1 or not val2:
                continue

            # Calculate overlap
            overlap = self._range_overlap(val1, val2)
            total_score += overlap * weight
            total_weight += weight

        if total_weight == 0:
            return 0

        return (total_score / total_weight) * 100

    def _range_overlap(self, range1: Tuple[float, float], range2: Tuple[float, float]) -> float:
        """Calculate overlap between two ranges (0-1)"""
        min1, max1 = range1
        min2, max2 = range2

        # Calculate overlap
        overlap_min = max(min1, min2)
        overlap_max = min(max1, max2)

        if overlap_max < overlap_min:
            # No overlap
            # Calculate distance
            if min1 > max2:
                distance = min1 - max2
            else:
                distance = min2 - max1

            avg_range = ((max1 - min1) + (max2 - min2)) / 2
            # Penalize by distance
            return max(0, 1 - (distance / avg_range))

        # Calculate overlap ratio
        overlap_size = overlap_max - overlap_min
        union_size = max(max1, max2) - min(min1, min2)

        return overlap_size / union_size if union_size > 0 else 0
```

---

### 2.8 Confidence/Reliability Scoring System

#### Многомерная система оценки достоверности

**Факторы:**

1. **Source Reliability** (40%)
   - TIER 1 (manufacturer PDF, standard): 100%
   - TIER 2 (manufacturer web, database): 90%
   - TIER 3 (academic): 70%
   - TIER 4 (general): 50%

2. **Cross-verification** (30%)
   - 3+ sources agree: 100%
   - 2 sources agree: 80%
   - Single source: 50%

3. **Data Completeness** (20%)
   - All major elements present: 100%
   - Missing 1-2 elements: 80%
   - Missing 3+ elements: 50%

4. **Validation Passed** (10%)
   - All checks pass: 100%
   - Warnings only: 80%
   - Issues present: 50%

---

#### Расчет итогового Confidence Score

```python
class ConfidenceScorer:
    """Calculate overall confidence score"""

    WEIGHTS = {
        'source_reliability': 0.40,
        'cross_verification': 0.30,
        'data_completeness': 0.20,
        'validation': 0.10
    }

    def calculate_confidence(self,
                            sources: List[Dict],
                            verification_result: Dict,
                            composition: Dict,
                            validation_result: Dict) -> Dict:
        """
        Calculate overall confidence score

        Returns:
        {
          "score": 0.85,  # 0-1
          "grade": "high",  # high/medium/low
          "breakdown": {
            "source_reliability": 0.90,
            "cross_verification": 0.80,
            "data_completeness": 0.85,
            "validation": 1.0
          }
        }
        """
        scores = {}

        # 1. Source Reliability
        scores['source_reliability'] = self._score_source_reliability(sources)

        # 2. Cross-verification
        scores['cross_verification'] = self._score_cross_verification(verification_result)

        # 3. Data Completeness
        scores['data_completeness'] = self._score_completeness(composition)

        # 4. Validation
        scores['validation'] = self._score_validation(validation_result)

        # Calculate weighted average
        total_score = sum(
            scores[key] * self.WEIGHTS[key]
            for key in scores.keys()
        )

        # Determine grade
        if total_score >= 0.85:
            grade = "high"
        elif total_score >= 0.70:
            grade = "medium"
        else:
            grade = "low"

        return {
            "score": round(total_score, 2),
            "grade": grade,
            "breakdown": scores,
            "description": self._describe_confidence(grade, scores)
        }

    def _score_source_reliability(self, sources: List[Dict]) -> float:
        """Score based on source quality"""
        if not sources:
            return 0.5

        # Find best source
        tier_scores = {
            'manufacturer_pdf': 1.0,
            'official_standard': 1.0,
            'manufacturer_web': 0.9,
            'verified_database': 0.9,
            'academic_paper': 0.7,
            'general': 0.5
        }

        best_score = max(tier_scores.get(s['type'], 0.5) for s in sources)
        return best_score

    def _score_cross_verification(self, verification_result: Dict) -> float:
        """Score based on cross-verification"""
        if verification_result.get('agreement') == 'verified':
            source_count = verification_result.get('source_count', 1)
            if source_count >= 3:
                return 1.0
            elif source_count == 2:
                return 0.8
            else:
                return 0.5
        elif verification_result.get('agreement') == 'partial':
            return 0.6
        else:
            return 0.5

    def _score_completeness(self, composition: Dict) -> float:
        """Score based on data completeness"""
        major_elements = ['c', 'cr', 'mo', 'v', 'w', 'co', 'ni']
        present = sum(1 for elem in major_elements if elem in composition and composition[elem])

        return min(1.0, present / 5)  # At least 5 elements for 100%

    def _score_validation(self, validation_result: Dict) -> float:
        """Score based on validation results"""
        if not validation_result.get('valid'):
            return 0.5

        confidence = validation_result.get('confidence', 'medium')
        if confidence == 'high':
            return 1.0
        elif confidence == 'medium':
            return 0.8
        else:
            return 0.6

    def _describe_confidence(self, grade: str, breakdown: Dict) -> str:
        """Human-readable confidence description"""
        if grade == "high":
            return "Данные проверены из надежных источников (производитель/стандарт), химический состав подтвержден"
        elif grade == "medium":
            return "Данные из проверенных источников, но требуют дополнительной верификации"
        else:
            return "Данные могут быть неполными или требуют подтверждения из первичных источников"
```

---

### 2.9 Индикация неопределенных результатов

#### UI представление Confidence

**Telegram Bot - формат сообщения:**

```python
def format_steel_result_with_confidence(result: dict) -> str:
    """Enhanced formatting with confidence indicators"""

    lines = []

    # Header with confidence indicator
    grade = result.get('grade', 'N/A')
    confidence_score = result.get('confidence_score', {})
    confidence_grade = confidence_score.get('grade', 'medium')

    # Emoji indicators
    confidence_emoji = {
        'high': '✅',
        'medium': '⚠️',
        'low': '❓'
    }

    emoji = confidence_emoji.get(confidence_grade, '⚠️')
    lines.append(f"{emoji} **Марка: {grade}**")

    # Confidence score
    score = confidence_score.get('score', 0.0)
    lines.append(f"📊 **Достоверность:** {score*100:.0f}% ({confidence_grade.upper()})")
    lines.append("")

    # Description
    description = confidence_score.get('description', '')
    if description:
        lines.append(f"ℹ️ _{description}_")
        lines.append("")

    # Chemical composition with element-level confidence
    lines.append("**Химический состав:**")

    element_confidence = result.get('confidence_scores', {})
    elements = ['c', 'cr', 'mo', 'v', 'w', 'co', 'ni', 'mn', 'si']

    for elem in elements:
        value = result.get(elem)
        if value and value not in ['0', '0.00', None, 'null']:
            elem_conf = element_confidence.get(elem, 'medium')
            conf_indicator = confidence_emoji.get(elem_conf, '⚠️')
            lines.append(f"  {conf_indicator} {elem.upper()}: {value}%")

    # Validation warnings
    if not result.get('validated', True):
        lines.append("")
        lines.append("⚠️ **ВНИМАНИЕ:**")
        warnings = result.get('validation_warnings', [])
        for warning in warnings:
            lines.append(f"  • {warning}")

    # Source information
    sources = result.get('sources', [])
    if sources:
        lines.append("")
        lines.append("📚 **Источники:**")
        for source in sources[:3]:  # Top 3 sources
            source_type = source.get('type', 'unknown')
            reliability = source.get('reliability', 'unknown')
            url = source.get('url', '')

            lines.append(f"  • [{source_type}] {reliability.upper()}")
            if url:
                lines.append(f"    🔗 {url[:50]}...")

    # Analogues with confidence
    analogues = result.get('analogues_verified', [])
    if analogues:
        lines.append("")
        lines.append("🔗 **Аналоги:**")

        # Group by confidence
        high_conf = [a for a in analogues if a['confidence'] == 'high']
        medium_conf = [a for a in analogues if a['confidence'] == 'medium']

        if high_conf:
            lines.append("  ✅ Официальные:")
            for a in high_conf:
                lines.append(f"     • {a['grade']} ({a.get('verification_method', 'verified')})")

        if medium_conf:
            lines.append("  ⚠️ По химическому составу:")
            for a in medium_conf:
                match = a.get('composition_match', 0)
                lines.append(f"     • {a['grade']} (совпадение: {match:.0f}%)")

    return '\n'.join(lines)
```

**Пример вывода:**

```
✅ **Марка: Bohler K340**
📊 **Достоверность:** 92% (HIGH)

ℹ️ _Данные проверены из надежных источников (производитель/стандарт), химический состав подтвержден_

**Химический состав:**
  ✅ C: 1.50-1.60%
  ✅ Cr: 11.0-12.0%
  ✅ Mo: 0.70-0.80%
  ✅ V: 0.90-1.00%
  ⚠️ Mn: 0.40%
  ⚠️ Si: 0.30%

📚 **Источники:**
  • [manufacturer_pdf] HIGH
    🔗 https://www.bohler-edelstahl.com/app/uploads/...
  • [verified_database] MEDIUM
    🔗 https://www.matweb.com/...

🔗 **Аналоги:**
  ✅ Официальные:
     • AISI D2 (official_standard)
     • DIN 1.2379 (official_standard)
  ⚠️ По химическому составу:
     • X155CrVMo12-1 (совпадение: 88%)
```

---

**Web интерфейс - визуальные индикаторы:**

```html
<!-- Confidence badge -->
<div class="result-card" data-confidence="high">
    <div class="confidence-badge high">
        <span class="confidence-icon">✓</span>
        <span class="confidence-text">92% достоверность</span>
    </div>

    <h3 class="grade-name">Bohler K340</h3>

    <!-- Composition with per-element confidence -->
    <table class="composition-table">
        <tr class="element-row" data-confidence="high">
            <td class="element-name">
                <span class="confidence-dot green"></span>
                C
            </td>
            <td class="element-value">1.50-1.60%</td>
        </tr>
        <tr class="element-row" data-confidence="medium">
            <td class="element-name">
                <span class="confidence-dot yellow"></span>
                Mn
            </td>
            <td class="element-value">0.40%</td>
        </tr>
    </table>

    <!-- Sources expandable section -->
    <details class="sources-section">
        <summary>📚 Источники (3)</summary>
        <ul class="sources-list">
            <li class="source-item high-reliability">
                <span class="source-type">Manufacturer PDF</span>
                <span class="reliability-badge">HIGH</span>
                <a href="...">Ссылка</a>
            </li>
        </ul>
    </details>
</div>
```

**CSS:**
```css
.confidence-badge {
    display: inline-flex;
    align-items: center;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: bold;
}

.confidence-badge.high {
    background: #4caf50;
    color: white;
}

.confidence-badge.medium {
    background: #ff9800;
    color: white;
}

.confidence-badge.low {
    background: #f44336;
    color: white;
}

.confidence-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 6px;
}

.confidence-dot.green {
    background: #4caf50;
}

.confidence-dot.yellow {
    background: #ff9800;
}

.confidence-dot.red {
    background: #f44336;
}
```

---

### 2.10 Рекомендации по улучшению промптов

#### Структура улучшенного промпта

```python
def create_enhanced_prompt(grade_name: str) -> str:
    return f"""You are an EXPERT steel metallurgist and data extraction specialist.

MISSION: Find VERIFIED chemical composition for steel grade "{grade_name}".

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL SEARCH PROTOCOL - FOLLOW STRICTLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP 1: IDENTIFY SOURCE PRIORITY
Search in this EXACT order:

Priority 1 (STOP if found):
  • Manufacturer official datasheets (PDF format)
    Examples: bohler-edelstahl.com, uddeholm.com, voestalpine.com
  • Look for: product_name.pdf, technical_datasheet.pdf, material_datasheet.pdf

Priority 2 (if P1 not found):
  • Official standards documents
    Examples: ISO, AISI, DIN, GOST, JIS, EN standards
  • Look for: equivalence tables, composition tables

Priority 3 (if P1-P2 not found):
  • Verified technical databases
    ONLY: MatWeb.com, steelnumber.com, azom.com, totalmateria.com

Priority 4 (LAST RESORT):
  • Academic papers, industry handbooks
  • Mark as "medium confidence" if using this tier

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2: EXTRACT COMPOSITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Look for tables with headers:
  • "Chemical Composition"
  • "Nominal Analysis"
  • "Typical Composition"
  • "Chemical Analysis"

Extract these elements (if present):
  C, Cr, Ni, Mo, V, W, Co, Mn, Si, S, P, Cu, Nb, N, Ti, Al

Format rules:
  • Range: "0.85-0.95" → keep as is
  • Single value: "0.90" → keep as is
  • Max value: "max 0.030" → return "0.030" and note "max" separately
  • Typical: "typ. 0.90" → return "0.90"

NEVER:
  • Estimate or calculate missing values
  • Use values from similar grades
  • Extrapolate from incomplete data

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3: CROSS-VERIFICATION (if multiple sources found)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If composition found in 2+ sources:
  1. Compare each element
  2. If difference < 5% → HIGH confidence, use average
  3. If difference 5-10% → MEDIUM confidence, use manufacturer value
  4. If difference > 10% → Flag as "requires_verification", note discrepancy

Priority for conflict resolution:
  Manufacturer PDF > Standard > Database > Other

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4: ANALOGUES (separate task)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Find equivalents in this order:
  1. Official equivalence tables (ISO, standards)
  2. Manufacturer claims ("equivalent to...")
  3. Database equivalence listings

Format: "AISI D2, DIN 1.2379, JIS SKD11"
DO NOT include "similar" or "comparable" grades - only confirmed equivalents.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RETURN FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return ONLY valid JSON (no markdown, no explanations):

{{
  "grade": "{grade_name}",
  "found": true/false,

  // Chemical composition (MANDATORY if found=true)
  "composition": {{
    "c": "value or null",
    "cr": "value or null",
    "mo": "value or null",
    "v": "value or null",
    "w": "value or null",
    "co": "value or null",
    "ni": "value or null",
    "mn": "value or null",
    "si": "value or null",
    "s": "value or null",
    "p": "value or null",
    "cu": "value or null",
    "nb": "value or null",
    "n": "value or null"
  }},

  // Analogues (space-separated list)
  "analogues": "AISI D2 DIN 1.2379 JIS SKD11" or null,

  // Metadata
  "standard": "standard name or manufacturer name",
  "manufacturer": "manufacturer name if proprietary",
  "manufacturer_country": "country (in Russian: Германия, США, Австрия, etc.)",
  "base": "Fe, Ni, Co, or Ti",

  // Additional info (in Russian)
  "application": "Применение: ... (Russian text)",
  "properties": "Свойства: ... (Russian text)",

  // MANDATORY: Source tracking
  "sources": [
    {{
      "url": "full URL",
      "type": "manufacturer_pdf | official_standard | verified_database | other",
      "reliability": "high | medium | low",
      "found_composition": true/false,
      "found_analogues": true/false
    }}
  ],
  "primary_source_url": "URL of the BEST source used for composition",

  // Verification metadata
  "verification": {{
    "source_count": 2,
    "agreement": "verified | partial | single_source",
    "confidence": "high | medium | low",
    "notes": ["any important notes about data quality"]
  }}
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FAILURE CASES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If composition NOT found after searching Priority 1-4:
Return:
{{
  "grade": "{grade_name}",
  "found": false,
  "reason": "Chemical composition not found in any reliable source",
  "searched_sources": ["list of URLs checked"],
  "suggestions": ["possible alternative names or standards to check"]
}}

DO NOT return partial data without composition.
DO NOT estimate or calculate missing values.
DO NOT use unreliable sources (forums, blogs, etc.).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Begin search for "{grade_name}":
"""
```

---

#### Ключевые улучшения промпта

1. **Визуальная структура:**
   - Разделители с ━ для четких секций
   - CRITICAL, MANDATORY выделены CAPS
   - Пошаговый протокол (STEP 1, 2, 3...)

2. **Строгий порядок поиска:**
   - Priority 1-4 с явными инструкциями "STOP if found"
   - Конкретные примеры сайтов
   - Правило использования только надежных источников

3. **Детальные правила extraction:**
   - Что искать (названия таблиц)
   - Как форматировать (range, single, max)
   - Что НИКОГДА не делать (estimate, extrapolate)

4. **Cross-verification встроена:**
   - Автоматическое сравнение при multiple sources
   - Правила разрешения конфликтов
   - Confidence scoring

5. **Метаданные и provenance:**
   - Отслеживание источников
   - Verification metadata
   - Confidence indicators

6. **Обработка failure cases:**
   - Явные инструкции, что возвращать при неудаче
   - Suggestions для дальнейшего поиска
   - Прозрачность (какие источники проверены)

---

## Часть 3: Конкретные рекомендации по внедрению

### 3.1 Пошаговый план улучшений

#### Фаза 1: Quick Wins (1-2 недели)

**Цель:** Улучшить UX без масштабных изменений в коде.

**Задачи:**

1. ✅ **Информативные сообщения "не найдено"**
   - Web: Показывать подсказку про Telegram бот
   - Telegram: Более детальное объяснение
   - Время: 2 часа

2. ✅ **Tooltips и подсказки**
   - Кнопка 🔍 - tooltip "Точный поиск"
   - Фильтры - примеры использования
   - Время: 1 час

3. ✅ **Индикаторы загрузки**
   - Web: Спиннер при поиске
   - Telegram: Промежуточные сообщения
   - Время: 2 часа

4. ✅ **Улучшить валидацию (менее строгая)**
   - Показывать результаты с предупреждениями
   - Не отклонять при неполных данных
   - Время: 3 часа

5. ✅ **Database optimizations**
   - Добавить timeout и WAL mode
   - Создать индексы
   - Время: 2 часа

**Итого Фаза 1:** ~10 часов работы

---

#### Фаза 2: Enhanced Prompts (1 неделя)

**Цель:** Улучшить качество AI результатов через лучшие промпты.

**Задачи:**

1. ✅ **Переписать промпт по новой структуре**
   - Использовать enhanced prompt из 2.10
   - Добавить визуальные разделители
   - Строгий порядок поиска
   - Время: 4 часа

2. ✅ **Добавить source tracking**
   - Расширить JSON ответ (sources array)
   - Primary source URL
   - Verification metadata
   - Время: 3 часа

3. ✅ **Implement confidence scoring**
   - Добавить ConfidenceScorer class
   - Рассчитывать scores для каждого результата
   - Время: 6 часов

4. ✅ **UI для confidence indicators**
   - Telegram: Enhanced formatting (2.9)
   - Web: Badges и цветовая индикация
   - Время: 5 часов

5. ✅ **Тестирование**
   - 20-30 тестовых марок
   - Сравнить старый vs новый промпт
   - Документировать улучшения
   - Время: 4 часа

**Итого Фаза 2:** ~22 часа работы

---

#### Фаза 3: Multi-Agent System (2-3 недели)

**Цель:** Внедрить multi-agent подход для максимального качества.

**Задачи:**

1. ✅ **Создать Agent framework**
   - BaseAgent class
   - Agent orchestrator
   - Время: 8 часов

2. ✅ **Agent 1: Source Finder**
   - Реализовать agent_1_find_sources()
   - Тестирование на 10 марок
   - Время: 6 часов

3. ✅ **Agent 2: Data Extractor**
   - Реализовать agent_2_extract_composition()
   - Параллельный extraction из multiple sources
   - Время: 8 часов

4. ✅ **Agent 3: Verifier**
   - Реализовать agent_3_verify_composition()
   - Cross-verification логика
   - CompositionValidator class
   - Время: 10 часов

5. ✅ **Agent 4: Analogues Finder**
   - Реализовать agent_4_find_analogues()
   - AnaloguesVerifier class
   - Время: 8 часов

6. ✅ **Agent 5: Formatter**
   - Собрать все в финальный JSON
   - Время: 4 часа

7. ✅ **Integration & Testing**
   - Интегрировать с ai_search.py
   - Backward compatibility
   - Feature flag для включения/выключения
   - Время: 10 часов

8. ✅ **Comprehensive Testing**
   - 50+ тестовых марок
   - Edge cases
   - Performance profiling
   - Время: 8 часов

**Итого Фаза 3:** ~62 часа работы

---

#### Фаза 4: PDF/OCR Enhancement (2 недели)

**Цель:** Улучшить извлечение данных из PDF и добавить OCR.

**Задачи:**

1. ✅ **Improve PDF parser**
   - Парсить до 10 страниц (не 5)
   - Искать страницу с composition
   - Extract tables
   - Время: 6 часов

2. ✅ **Add OCR support**
   - Tesseract integration
   - PDF → images → OCR
   - Fallback для scanned PDFs
   - Время: 8 часов

3. ✅ **Table extraction & parsing**
   - Найти composition table
   - Parse values из table cells
   - Время: 8 часов

4. ✅ **AI-enhanced extraction**
   - Использовать GPT-4 для парсинга PDF text
   - Более точный extraction
   - Время: 6 часов

5. ✅ **Testing**
   - 20 PDF datasheets
   - Compare pdfplumber vs OCR vs AI extraction
   - Время: 6 часов

**Итого Фаза 4:** ~34 часа работы

---

#### Фаза 5: Spectrometer OCR (1 неделя, опционально)

**Цель:** Добавить возможность загрузки фото спектрометра.

**Задачи:**

1. ✅ **GPT-4 Vision integration**
   - SpectrometerOCR class
   - Image → composition extraction
   - Время: 6 часов

2. ✅ **Telegram photo handler**
   - Handle photo uploads
   - Process with OCR
   - Return matching grades
   - Время: 4 часа

3. ✅ **Matching algorithm**
   - Find grades by composition
   - Tolerance ranges (±5-10%)
   - Ranked results
   - Время: 6 часов

4. ✅ **UI/UX**
   - Instructions для пользователей
   - Example images
   - Время: 2 часа

5. ✅ **Testing**
   - 10-15 test photos
   - Different spectrometer types
   - Время: 4 часа

**Итого Фаза 5:** ~22 часа работы

---

### 3.2 Приоритизация

#### Must Have (критично):
- ✅ Фаза 1: Quick Wins - **немедленно**
- ✅ Фаза 2: Enhanced Prompts - **приоритет 1**

#### Should Have (важно):
- ✅ Фаза 3: Multi-Agent System - **приоритет 2**
- ✅ Фаза 4: PDF/OCR Enhancement - **приоритет 3**

#### Nice to Have (опционально):
- ⚠️ Фаза 5: Spectrometer OCR - **если есть запрос от пользователей**

---

### 3.3 Техническая архитектура

#### Структура файлов (после всех фаз)

```
ParserSteel/
├── ai_search.py                    # Main AI Search (orchestrator)
│
├── ai/                             # AI modules
│   ├── __init__.py
│   ├── agents/                     # Multi-agent system
│   │   ├── __init__.py
│   │   ├── base_agent.py           # BaseAgent class
│   │   ├── source_finder.py        # Agent 1
│   │   ├── data_extractor.py       # Agent 2
│   │   ├── verifier.py             # Agent 3
│   │   ├── analogues_finder.py     # Agent 4
│   │   └── formatter.py            # Agent 5
│   │
│   ├── prompts/                    # Prompt templates
│   │   ├── __init__.py
│   │   ├── enhanced_prompt.py      # Enhanced search prompt
│   │   ├── source_finder_prompt.py
│   │   ├── extractor_prompt.py
│   │   └── verifier_prompt.py
│   │
│   ├── validators/                 # Validation logic
│   │   ├── __init__.py
│   │   ├── composition_validator.py
│   │   ├── analogues_verifier.py
│   │   └── confidence_scorer.py
│   │
│   └── orchestrator.py             # Multi-agent orchestration
│
├── utils/                          # Utilities
│   ├── pdf_parser.py               # PDF parsing (enhanced)
│   ├── ocr_parser.py               # OCR for scanned PDFs
│   ├── spectrometer_ocr.py         # Spectrometer image OCR
│   └── logger.py                   # Centralized logging
│
├── telegram_bot/
│   ├── handlers/
│   │   ├── search.py               # Enhanced with confidence UI
│   │   ├── photo.py                # NEW: Photo handler
│   │   └── ...
│   └── formatters/                 # NEW: Response formatting
│       ├── __init__.py
│       └── confidence_formatter.py # Format with confidence indicators
│
└── config/                         # Unified config
    ├── __init__.py
    ├── api_config.py               # API keys, endpoints
    ├── search_config.py            # Search settings
    └── feature_flags.py            # Enable/disable features
```

---

#### Конфигурация через Feature Flags

```python
# config/feature_flags.py
class FeatureFlags:
    """Feature flags for gradual rollout"""

    # AI Search
    ENABLE_AI_SEARCH = True
    ENABLE_MULTI_AGENT = False  # Toggle multi-agent system
    ENABLE_PDF_ENHANCED = False  # Enhanced PDF parsing
    ENABLE_OCR = False            # OCR for scanned PDFs
    ENABLE_SPECTROMETER_OCR = False  # Spectrometer photo recognition

    # Search behavior
    ENABLE_AI_CACHE = False       # AI result caching (currently disabled)
    AI_CACHE_TTL = 86400          # 24 hours

    # Validation
    STRICT_VALIDATION = False     # If True, reject incomplete data
    REQUIRE_COMPOSITION = True    # Must have chemical composition

    # Confidence
    SHOW_CONFIDENCE_SCORES = True # Show confidence in UI
    MIN_CONFIDENCE_THRESHOLD = 0.5  # Reject if below

    # Rate limiting
    ENABLE_RATE_LIMITING = False
    MAX_AI_REQUESTS_PER_HOUR = 20

    @classmethod
    def is_enabled(cls, feature: str) -> bool:
        """Check if feature is enabled"""
        return getattr(cls, feature, False)
```

**Использование:**
```python
# ai_search.py
from config.feature_flags import FeatureFlags

def search_steel(self, grade_name: str):
    if FeatureFlags.ENABLE_MULTI_AGENT:
        return self._search_multi_agent(grade_name)
    else:
        return self._search_single_prompt(grade_name)
```

---

### 3.4 Ожидаемые улучшения

#### Метрики успеха

**После Фазы 1 (Quick Wins):**
- ✅ UX: Пользователи понимают, что делать при "не найдено"
- ✅ Performance: SQLite не блокируется при concurrent access
- ✅ Validation: Меньше ложных отклонений (показываем с warnings)

**После Фазы 2 (Enhanced Prompts):**
- 🎯 **Accuracy:** +15-20% точность extraction
- 🎯 **Source Quality:** 80%+ результатов из Tier 1-2 источников
- 🎯 **Completeness:** 90%+ результатов с полным химическим составом
- 🎯 **Confidence Transparency:** Пользователи видят reliability каждого результата

**После Фазы 3 (Multi-Agent):**
- 🎯 **Accuracy:** +25-30% точность (по сравнению с текущей)
- 🎯 **Cross-verification:** 60%+ результатов проверены из 2+ источников
- 🎯 **Confidence High:** 70%+ результатов с high confidence
- 🎯 **Analogues Quality:** Разделение официальных vs composition-based

**После Фазы 4 (PDF/OCR):**
- 🎯 **PDF Coverage:** 90%+ PDF datasheets успешно парсятся
- 🎯 **Scanned PDFs:** OCR fallback работает для сканов
- 🎯 **Table Extraction:** 85%+ composition tables извлекаются корректно

**После Фазы 5 (Spectrometer OCR):**
- 🎯 **Photo Recognition:** 80%+ фото спектрометров распознаются
- 🎯 **Matching:** Поиск по составу с ±5-10% tolerance
- 🎯 **UX:** Новый use case для пользователей (фото → марка)

---

#### Сравнительная таблица

| Метрика | Текущее состояние | После Фазы 2 | После Фазы 3 | После Фазы 4 |
|---------|-------------------|--------------|--------------|--------------|
| **Точность extraction** | 70% | 85% | 95% | 97% |
| **Полнота данных** | 60% | 90% | 95% | 98% |
| **Confidence scores** | Нет | Да (basic) | Да (advanced) | Да (advanced) |
| **Cross-verification** | Нет | Частично | Да (2+ sources) | Да (2+ sources) |
| **PDF support** | Базовый | Базовый | Базовый | Расширенный+OCR |
| **Source tracking** | Нет | Да | Да | Да |
| **Analogues quality** | 50% | 70% | 85% | 85% |
| **Время поиска** | 20-30 сек | 25-35 сек | 40-60 сек | 45-70 сек |
| **Стоимость запроса** | $0.01-0.02 | $0.02-0.03 | $0.05-0.08 | $0.06-0.10 |

**Вывод:** Повышение точности и качества за счет увеличения времени и стоимости поиска. Но результаты становятся СУЩЕСТВЕННО более надежными.

---

### 3.5 Риски и митигация

#### Риск 1: Увеличение времени поиска

**Проблема:** Multi-agent подход = множество API вызовов = медленнее.

**Митигация:**
- ✅ Параллелизация agents (asyncio)
- ✅ Кэширование промежуточных результатов
- ✅ Feature flag для отключения multi-agent
- ✅ Показывать progress bar в Telegram

---

#### Риск 2: Увеличение стоимости

**Проблема:** Больше API вызовов = больше расходов.

**Митигация:**
- ✅ Rate limiting (max 20 requests/hour/user)
- ✅ Кэширование результатов (24 часа TTL)
- ✅ Use cheaper models для некритичных агентов
- ✅ Batch processing для множественных марок

---

#### Риск 3: Сложность поддержки

**Проблема:** Multi-agent система сложнее single-prompt.

**Митигация:**
- ✅ Хорошая документация (docstrings)
- ✅ Unit tests для каждого агента
- ✅ Логирование на каждом этапе
- ✅ Feature flags для rollback

---

#### Риск 4: API rate limits

**Проблема:** Perplexity/OpenAI могут ограничить requests/min.

**Митигация:**
- ✅ Exponential backoff при rate limit errors
- ✅ Queue system для запросов
- ✅ Fallback на cached results
- ✅ Alternative API keys (rotation)

---

### 3.6 Мониторинг и метрики

#### Логирование

```python
# utils/logger.py
import logging
import json
from datetime import datetime

class AISearchLogger:
    """Structured logging for AI Search"""

    def __init__(self, log_file='logs/ai_search.log'):
        self.logger = logging.getLogger('ai_search')
        self.logger.setLevel(logging.INFO)

        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log_search(self, grade_name: str, result: dict, metadata: dict):
        """Log AI search with structured data"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'grade': grade_name,
            'found': result.get('found', False),
            'confidence': result.get('confidence_score', {}).get('score'),
            'source_count': len(result.get('sources', [])),
            'primary_source_type': result.get('sources', [{}])[0].get('type') if result.get('sources') else None,
            'agent_version': metadata.get('agent_version', 'v1'),
            'duration_ms': metadata.get('duration_ms'),
            'api_calls': metadata.get('api_calls', 1),
            'cost_usd': metadata.get('cost_usd', 0.02)
        }

        self.logger.info(json.dumps(log_entry, ensure_ascii=False))

    def log_error(self, grade_name: str, error: Exception, metadata: dict):
        """Log search errors"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'grade': grade_name,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'agent_version': metadata.get('agent_version', 'v1')
        }

        self.logger.error(json.dumps(log_entry, ensure_ascii=False))
```

---

#### Metrics Dashboard (опционально)

Можно создать простой dashboard для отслеживания метрик:

```python
# utils/metrics.py
class AISearchMetrics:
    """Collect and report AI Search metrics"""

    def __init__(self):
        self.metrics = {
            'total_searches': 0,
            'successful_searches': 0,
            'failed_searches': 0,
            'avg_confidence': [],
            'avg_duration_ms': [],
            'total_api_calls': 0,
            'total_cost_usd': 0.0,
            'source_types': {},
            'error_types': {}
        }

    def record_search(self, result: dict, metadata: dict):
        """Record search metrics"""
        self.metrics['total_searches'] += 1

        if result.get('found'):
            self.metrics['successful_searches'] += 1
            confidence = result.get('confidence_score', {}).get('score', 0)
            self.metrics['avg_confidence'].append(confidence)
        else:
            self.metrics['failed_searches'] += 1

        self.metrics['avg_duration_ms'].append(metadata.get('duration_ms', 0))
        self.metrics['total_api_calls'] += metadata.get('api_calls', 1)
        self.metrics['total_cost_usd'] += metadata.get('cost_usd', 0.02)

        # Track source types
        primary_source = result.get('sources', [{}])[0].get('type') if result.get('sources') else 'unknown'
        self.metrics['source_types'][primary_source] = self.metrics['source_types'].get(primary_source, 0) + 1

    def get_summary(self) -> dict:
        """Get metrics summary"""
        return {
            'total_searches': self.metrics['total_searches'],
            'success_rate': self.metrics['successful_searches'] / max(1, self.metrics['total_searches']),
            'avg_confidence': sum(self.metrics['avg_confidence']) / max(1, len(self.metrics['avg_confidence'])),
            'avg_duration_ms': sum(self.metrics['avg_duration_ms']) / max(1, len(self.metrics['avg_duration_ms'])),
            'total_api_calls': self.metrics['total_api_calls'],
            'total_cost_usd': self.metrics['total_cost_usd'],
            'avg_cost_per_search': self.metrics['total_cost_usd'] / max(1, self.metrics['total_searches']),
            'source_distribution': self.metrics['source_types']
        }
```

---

## Заключение

### Ключевые выводы

1. **Текущая система работает, но требует улучшений:**
   - DB + Web + Telegram интеграция функционирует
   - AI Search через Perplexity дает результаты
   - Но точность и полнота данных недостаточны

2. **Главная проблема: промпты, а не технология:**
   - API Perplexity хуже web версии из-за промптов
   - Нет структурированного подхода к поиску источников
   - Нет cross-verification

3. **Multi-agent подход - правильное решение:**
   - Разделение задач повышает качество
   - Каждый агент фокусируется на своей задаче
   - Confidence scoring становится прозрачным

4. **PDF/OCR критичны для редких марок:**
   - Производители публикуют данные в PDF
   - Нужно уметь извлекать из PDF tables
   - OCR для сканов обязателен

5. **Поэтапное внедрение снижает риски:**
   - Фаза 1: Quick wins (немедленно)
   - Фаза 2: Enhanced prompts (приоритет)
   - Фаза 3: Multi-agent (если Фаза 2 не дает нужного quality leap)
   - Фаза 4-5: Дополнительные возможности

---

### Что делать дальше?

**Немедленные действия (эта неделя):**
1. Внедрить Фазу 1 (Quick Wins) - 10 часов
2. Начать Фазу 2 (Enhanced Prompts) - переписать промпт

**Краткосрочные (2-4 недели):**
1. Завершить Фазу 2
2. Протестировать на 50+ марках
3. Собрать метрики (accuracy, completeness, confidence)
4. Решить: нужна ли Фаза 3 (multi-agent) или достаточно enhanced prompts

**Среднесрочные (1-2 месяца):**
1. Если Фаза 2 дала +20-25% accuracy → Фаза 4 (PDF/OCR)
2. Если Фаза 2 дала <15% improvement → Фаза 3 (multi-agent) обязательна
3. Собрать feedback от пользователей Telegram бота

**Долгосрочные (3-6 месяцев):**
1. Spectrometer OCR (если есть запрос)
2. Automatic database enrichment (AI находит марки и добавляет автоматически)
3. Multi-language support (English, German, etc.)

---

### Контакты и поддержка

**Вопросы по документу:**
- Создать Issue в репозитории
- Или связаться с разработчиком

**Дата последнего обновления:** 2026-01-09

**Версия документа:** 1.0

---

**Конец документа**
