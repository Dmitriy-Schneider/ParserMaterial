# 🤖 Рекомендации по улучшению AI Search

## Проблема 1: Perplexity не находит российские марки (например, 16ХГМФТР)

### Причины:
1. **Кириллические символы** - Perplexity работает лучше с латиницей
2. **Редкие российские марки** - мало данных в открытом интернете
3. **Строгий промпт** - требует обязательного химического состава

### Решения:

#### Вариант А: Добавить транслитерацию в промпт (рекомендуется)

Изменить промпт в `ai_search.py` (строка 600):

```python
def _create_prompt(self, grade_name: str) -> str:
    # Добавить транслитерацию для русских марок
    transliterated = self._transliterate_russian(grade_name)

    search_instruction = f"""Find detailed information about steel grade "{grade_name}".

SEARCH STRATEGY FOR RUSSIAN GRADES:
1. If grade contains Cyrillic characters, also search transliterated variant: "{transliterated}"
2. Search both Russian and English sources:
   - Russian: ГОСТ standards, ru.wikipedia.org, splav.ru, metallicheckiy.ru
   - English: International databases (MatWeb, steelnumber.com)
3. For GOST grades, prioritize Russian sources (gost.ru, rusmet.ru)
4. Chemical composition is IMPORTANT but not MANDATORY - return basic info if composition unavailable
```

#### Вариант Б: Смягчить требования к химическому составу

В `ai_search.py` строка 604 изменить:

```python
# БЫЛО:
"2. Chemical composition is MANDATORY - if you cannot find verified chemical composition, set "found": false"

# СТАЛО:
"2. Chemical composition is PREFERRED - if you cannot find verified chemical composition, provide available info (standard, application, properties)"
```

#### Вариант В: Добавить специальную обработку для ГОСТ марок

```python
def _create_prompt_for_gost(self, grade_name: str) -> str:
    """Special prompt for GOST grades"""
    return f"""Find information about Russian steel grade "{grade_name}" (ГОСТ standard).

SEARCH PRIORITY for GOST grades:
1. Russian databases: splav.ru, metallicheckiy.ru, nzizn.ru
2. GOST standards: gost.ru, rusmet.ru, standartgost.ru
3. Russian Wikipedia: ru.wikipedia.org
4. International databases: MatWeb.com, steelnumber.com

IMPORTANT:
- Search in RUSSIAN language first
- Chemical composition from GOST standard if available
- Common Russian grades: 40Х, 65Г, Х12МФ, 9ХС, 16ХГМФТР, etc.
- If composition not found, provide: standard, application, analogues

Example GOST grade names:
- 16ХГМФТР = 16KhGMFTR (transliteration)
- Может быть описана как: "16ХГМФТР по ГОСТ 5950"
```

### Тестирование:

1. Проверить марку **16ХГМФТР**:
   ```bash
   curl "http://localhost:5001/api/steels/ai-search?grade=16ХГМФТР"
   ```

2. Сравнить результаты:
   - Текущий промпт vs улучшенный промпт
   - Perplexity API vs Perplexity web

3. Ожидаемый результат для 16ХГМФТР:
   ```json
   {
     "grade": "16ХГМФТР",
     "standard": "ГОСТ 5950-2000",
     "base": "Fe",
     "c": "0.13-0.19",
     "cr": "1.3-1.7",
     "mn": "1.4-1.8",
     "si": "0.9-1.2",
     "mo": "0.2-0.3",
     "application": "Валки прокатных станов, шестерни",
     "found": true
   }
   ```

### Альтернатива: Прямое добавление ГОСТ марок

Если Perplexity плохо работает с российскими марками, рекомендуется:

1. **Импортировать ГОСТ марки из splav.ru** (парсер уже создан)
2. **Использовать Excel файл** с основными ГОСТ марками
3. **AI search использовать только для западных марок**

---

## Сравнение: Perplexity API vs Web

| Фактор | Perplexity Web | Perplexity API |
|--------|---------------|----------------|
| Источники | Более широкий поиск | Ограниченный поиск |
| Русский язык | Лучше понимает кириллицу | Хуже с кириллицей |
| ГОСТ стандарты | Находит больше | Находит меньше |
| Скорость | Медленнее | Быстрее |
| Стоимость | Бесплатно | Платно (API) |

**Вывод:** Perplexity Web лучше для русских марок, API лучше для автоматизации западных марок.

---

## Практические шаги:

1. **Краткосрочно (1-2 часа)**:
   - Смягчить требование к химическому составу
   - Добавить транслитерацию в промпт
   - Добавить приоритет для русских источников

2. **Среднесрочно (1-2 дня)**:
   - Импортировать ГОСТ марки из splav.ru (парсер готов)
   - Создать Excel файл с 50-100 основными ГОСТ марками
   - Добавить ручную валидацию результатов AI

3. **Долгосрочно (1-2 недели)**:
   - Создать собственную базу ГОСТ марок
   - Использовать AI только для редких западных марок
   - Добавить feedback loop (пользователь может исправить неточные данные)
