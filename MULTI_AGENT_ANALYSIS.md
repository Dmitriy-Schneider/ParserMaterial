# Multi-Agent AI Search - Анализ и Рекомендации

**Статус:** Не реализовано (рекомендация для будущего)
**Сложность:** Очень высокая (100+ часов)
**Приоритет:** Низкий (текущая система работает хорошо после Фаз 1-2)

---

## Суть Multi-Agent подхода

Вместо одного AI запроса → цепочка специализированных агентов:

```
Запрос: "Найти HARDOX 600"
    ↓
[Agent 1: Source Finder] → Находит 5 источников (manufacturer PDF, MatWeb, steelnumber.com)
    ↓
[Agent 2: Data Extractor] → Извлекает данные из каждого источника
    ↓
[Agent 3: Cross-Verifier] → Проверяет совпадение данных между источниками
    ↓
[Agent 4: Analogues Finder] → Ищет аналоги в стандартах
    ↓
[Agent 5: Formatter] → Форматирует итоговый результат
    ↓
Результат с confidence 95% (проверен из 3 источников)
```

---

## Преимущества

✅ **Точность:** Каждый агент специализирован на своей задаче
✅ **Верификация:** Cross-check данных между источниками
✅ **Прозрачность:** Видно откуда каждый элемент данных
✅ **Качество:** Как Web Perplexity (или лучше)

---

## Недостатки

❌ **Сложность:** 5 агентов → сложная архитектура
❌ **Время:** 20-30 сек → 40-60 сек (больше API вызовов)
❌ **Стоимость:** 1 запрос → 5-7 API вызовов (в 5-7 раз дороже)
❌ **Разработка:** 100-150 часов работы

---

## Текущая ситуация после Фаз 1-2

### Что уже работает хорошо:

1. **Кэш 7 дней** → повторные поиски мгновенные
2. **Смягченная валидация** → больше результатов
3. **Улучшенные промпты** → приоритезация источников (tier1-3)
4. **Confidence scoring** → пользователь видит надежность (high/medium/low)
5. **PDF парсинг с таблицами** → больше данных из datasheets

### Проблемы которые остались:

1. **API Perplexity хуже Web** - multi-agent может решить, но дорого
2. **OCR для сканов** - не реализовано (нужен GPT-4 Vision)
3. **100% точность** - недостижимо без ручной проверки

---

## Рекомендация

### ❌ НЕ ДЕЛАТЬ сейчас, потому что:

- Фазы 1-2 дали **2x улучшение** при **6 часах работы**
- Multi-agent даст **1.5x улучшение** при **150 часах работы**
- **ROI слишком низкий** (250 часов / 1.5x = плохо)
- Текущая система достаточно хорошая

### ✅ КОГДА ДЕЛАТЬ:

1. **Если появится бюджет на API** (в 5-7 раз больше расхода)
2. **Если Perplexity API не улучшится** за 3-6 месяцев
3. **Если нужна 95%+ точность** вместо текущих 80-85%

---

## Альтернативы Multi-Agent (проще и дешевле)

### Вариант 1: Retry с разными промптами (10 часов)
```python
# Если первый запрос не нашел composition:
result = search_with_prompt_v1(grade)
if not result.has_composition():
    result = search_with_prompt_v2(grade)  # Другой промпт
```
**Эффект:** +10-15% результатов, удвоение стоимости только для problem cases

### Вариант 2: GPT-4 Vision для PDF (20 часов)
```python
# Если PDF парсер не нашел таблицы:
if not composition_found:
    # Скриншот первой страницы PDF → GPT-4 Vision
    composition = extract_with_vision(pdf_screenshot)
```
**Эффект:** +20% результатов из сканированных PDF, дороже но целенаправленно

### Вариант 3: Perplexity Pro API (0 часов, просто платим больше)
```python
# Использовать sonar-pro-turbo вместо sonar-pro
# Больше токенов → лучшие результаты
```
**Эффект:** +15-20% качества, в 2 раза дороже, но без разработки

---

## Итого

**Multi-Agent = оверкилл для текущей задачи**

Лучше:
1. ✅ Следить за улучшениями Perplexity API
2. ✅ Использовать Фазы 1-2 (уже сделано)
3. ✅ Добавить GPT-4 Vision если будет нужно (20 часов, не 150)
4. ✅ Собирать feedback пользователей → улучшать промпты

---

## Код-пример (если все-таки решите делать)

```python
class MultiAgentSearch:
    def __init__(self):
        self.source_finder = SourceFinderAgent()
        self.extractor = DataExtractorAgent()
        self.verifier = CrossVerifierAgent()
        self.analogues = AnaloguesAgent()
        self.formatter = FormatterAgent()

    def search(self, grade_name):
        # Agent 1: Find sources
        sources = self.source_finder.find(grade_name)  # API call 1

        # Agent 2: Extract data from each source
        data = []
        for source in sources:
            extracted = self.extractor.extract(source)  # API calls 2-4
            data.append(extracted)

        # Agent 3: Cross-verify
        verified = self.verifier.verify(data)  # API call 5

        # Agent 4: Find analogues
        analogues = self.analogues.find(verified)  # API call 6

        # Agent 5: Format result
        result = self.formatter.format(verified, analogues)  # API call 7

        return result
```

**Итого: 7 API вызовов вместо 1 → в 7 раз дороже и медленнее**

---

**Вывод:** Фазы 1-2 достаточно хороши. Multi-Agent - для будущего (когда будет бюджет).
