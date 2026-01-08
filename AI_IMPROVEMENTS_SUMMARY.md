# Улучшения Perplexity API интеграции

## Дата: 2026-01-08

## Краткое описание
Улучшена интеграция с Perplexity API для поиска марок стали, которых нет в базе данных. Добавлены обязательная проверка химического состава, извлечение ссылок на источники, и улучшенная работа с производителями.

## Реализованные изменения

### 1. ✅ Обязательный химический состав (MANDATORY)
**Файл:** `ai_search.py`

#### Изменения в промпте (_create_prompt)
- Добавлено требование: "Chemical composition is MANDATORY - if you cannot find verified chemical composition, set 'found': false"
- AI теперь явно инструктируется отклонять марки без химического состава

#### Изменения в валидации (_validate_composition)
- Добавлен счетчик `valid_elements_found`
- Требуется минимум 1 валидный химический элемент
- Если ни один элемент не найден, валидация провалена
- Вывод: `[OK] Found N valid chemical elements` или `VALIDATION FAILED: No valid chemical composition found`

#### Изменения в search_steel
- Результаты без валидного химического состава полностью отклоняются (return None)
- Вывод: `[REJECTED] AI result for 'grade' - химический состав не найден или некорректен`
- Такие марки НЕ добавляются в базу данных

### 2. ✅ Извлечение ссылок на источники (Source URL)
**Файл:** `ai_search.py`

#### Изменения в промпте (_create_prompt)
Добавлен новый параметр `source_url` с приоритетами:
```
8. MANDATORY: Provide source URL with the following priority:
   a) If found on official manufacturer website -> provide manufacturer product page URL
   b) If found in standard document -> provide standard document URL
   c) If found in PDF datasheet -> provide PDF URL
   d) Otherwise -> provide the most reliable source URL you found
```

Пример для K888:
- manufacturer: "Bohler Edelstahl"
- manufacturer_country: "Австрия"
- source_url: "https://www.bohler-edelstahl.com/en/products/k888-matrix/" или PDF

#### Изменения в парсинге (_parse_ai_response)
- Извлечение `source_url` или `pdf_url` из результата AI
- Маппинг в поле `link` для совместимости с базой данных
- Вывод: `[SOURCE] Extracted link: {url}` или `[WARNING] No source URL found`

### 3. ✅ Производитель и страна
**Файл:** `ai_search.py`

#### Новый параметр в промпте
- Добавлен `manufacturer_country`: страна производителя (Австрия, США, Германия, Франция, Швеция, Япония, Россия)

#### Логика в парсинге
Если есть производитель и страна:
- Формат: `"Manufacturer, Country"` (например, "Bohler Edelstahl, Австрия")
- Если нет стандарта, информация о производителе записывается в поле `standard`
- Вывод: `[INFO] Set standard to manufacturer info: {info}`

### 4. ✅ Исправления в API (app.py)

#### Исправление в /api/steels (строка 124)
**До:**
```python
ai_result['link'] = None  # Перезаписывало извлеченную ссылку!
```

**После:**
```python
# Keep the link field from AI result (don't override)
if 'link' not in ai_result:
    ai_result['link'] = None
```

#### Исправление в /api/steels/add (строка 223)
**До:**
```python
data.get('source') or data.get('pdf_url')  # Не учитывало новое поле link
```

**После:**
```python
data.get('link') or data.get('source_url') or data.get('pdf_url')
```

## Структура базы данных

Таблица `steel_grades` содержит поле `link TEXT` для хранения URL источников:
- Ссылки на официальные сайты производителей (приоритет 1)
- Ссылки на стандарты (приоритет 2)
- Ссылки на PDF спецификации (приоритет 3)
- Другие надежные источники (приоритет 4)

## Как это работает

### Процесс поиска через Telegram Bot

1. **Пользователь ищет марку** (например, "K888")
2. **Поиск в БД** - сначала проверяется локальная база данных
3. **AI Fallback** - если не найдено, запускается Perplexity API:
   - Приоритет: Perplexity (доступ к интернету)
   - Fallback: OpenAI GPT-4 (если Perplexity недоступен)
4. **Валидация**:
   - ✅ Проверка химического состава (минимум 1 элемент)
   - ✅ Извлечение source_url
   - ✅ Проверка manufacturer/country
   - ❌ Отклонение, если нет состава
5. **Кеширование** - только валидные результаты сохраняются в кеш
6. **Отображение** - результат показывается пользователю с кнопкой "Добавить в БД"
7. **Добавление** - при нажатии кнопки марка добавляется со всеми полями, включая link

## Примеры ожидаемых результатов

### K888 (Bohler Edelstahl)
```json
{
  "grade": "K888",
  "manufacturer": "Bohler Edelstahl",
  "manufacturer_country": "Австрия",
  "standard": "Bohler Edelstahl, Австрия",
  "link": "https://www.bohler-edelstahl.com/en/products/k888-matrix/",
  "c": "0.90",
  "cr": "8.0",
  "mo": "2.0",
  "v": "0.5",
  "w": "1.2",
  "validated": true,
  "ai_source": "perplexity"
}
```

### Марка без химического состава (будет отклонена)
```json
{
  "grade": "UnknownSteel",
  "found": true,
  "manufacturer": "Some Company",
  "link": "https://example.com",
  // НЕТ химического состава!
}
```
**Результат:** `None` (марка не будет добавлена)

## Тестирование

### Ручное тестирование через Telegram Bot
1. Запустить Flask API: `python app.py`
2. Запустить Telegram Bot
3. Найти марку, которой нет в БД: `/search K888`
4. Проверить результат:
   - ✅ Химический состав присутствует
   - ✅ Производитель и страна указаны
   - ✅ Ссылка на источник присутствует
5. Нажать "Добавить в БД"
6. Проверить в БД:
   ```sql
   SELECT grade, link, standard, manufacturer FROM steel_grades WHERE grade='K888';
   ```

### Автоматическое тестирование
Создан скрипт `test_ai_k888.py` для проверки:
- Наличие химического состава
- Извлечение manufacturer и country
- Извлечение source URL
- Валидация всех полей

## Файлы изменены

1. **ai_search.py** - основные изменения в AI логике
   - `_create_prompt()` - обновлен промпт
   - `_parse_ai_response()` - извлечение source_url и link
   - `_validate_composition()` - обязательная валидация
   - `search_steel()` - отклонение невалидных результатов

2. **app.py** - исправления в API эндпоинтах
   - `/api/steels` (GET) - не перезаписывать link
   - `/api/steels/add` (POST) - правильное извлечение link

3. **test_ai_k888.py** - тестовый скрипт (новый файл)

## Совместимость

- ✅ Обратная совместимость с существующими марками в БД
- ✅ Кеш AI запросов работает корректно
- ✅ Старые результаты AI без link будут иметь link=None
- ✅ Telegram Bot корректно отображает новые поля

## Важные примечания

1. **API предназначен только для марок, которых НЕТ в базе данных**
   - Включается только при поиске через Telegram Bot
   - Не используется для пакетной обработки существующих марок

2. **Perplexity имеет приоритет над OpenAI**
   - Perplexity имеет доступ к интернету → более точные результаты
   - OpenAI используется как fallback

3. **Валидация строгая**
   - Без химического состава → марка не добавляется
   - Это предотвращает добавление неполных/неточных данных

4. **Кеширование**
   - Только валидные результаты сохраняются в `ai_searches` таблице
   - TTL: 24 часа (по умолчанию)

## Логи и отладка

### Полезные сообщения в логах

**Успешный поиск:**
```
[Perplexity] Searching for 'K888' with internet access...
[SOURCE] Extracted link: https://www.bohler-edelstahl.com/en/products/k888-matrix/
[INFO] Set standard to manufacturer info: Bohler Edelstahl, Австрия
[OK] Found 5 valid chemical elements
[OK] Результат проверен и сохранен в кеш для 'K888'
```

**Отклонение марки:**
```
[Perplexity] Searching for 'BadSteel' with internet access...
[WARNING] No source URL found for 'BadSteel'
VALIDATION FAILED: No valid chemical composition found
[REJECTED] AI result for 'BadSteel' - химический состав не найден или некорректен
[INFO] Марка НЕ будет добавлена в базу данных (требуется химический состав)
```

## Конфигурация

В `.env` файле:
```env
# Perplexity API (приоритет)
PERPLEXITY_API_KEY=your_key_here
PERPLEXITY_MODEL=sonar-pro

# OpenAI API (fallback)
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4

# AI Search Settings
ENABLE_AI_FALLBACK=True
AI_CACHE_TTL=86400  # 24 hours
```

## Следующие шаги (опционально)

1. Добавить более детальную статистику по источникам ссылок
2. Добавить возможность ручной проверки AI результатов перед добавлением
3. Расширить список стран в промпте
4. Добавить автоматическую проверку доступности ссылок
5. Интеграция с другими источниками данных (MatWeb API, и т.д.)
