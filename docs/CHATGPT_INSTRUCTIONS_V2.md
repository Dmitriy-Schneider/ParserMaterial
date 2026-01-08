# Инструкции для ChatGPT (версия 2 - улучшенная)

## 🎯 Что случилось:

Первый запуск обработал **~790 марок**, но:
- AI вернул **392 записи с "N/A"** вместо реальных стандартов
- Заполненность: **33.4%** (вместо целевых >90%)
- **Паттерны не сработали** для очевидных марок:
  - M4 → должно быть "AISI M4, США"
  - SKH54 → должно быть "JIS SKH54, Япония"
  - X100CrMoV5 → должно быть "DIN X100CrMoV5, Германия"

## ✅ Что сделано:

1. ✅ **Очищено 392 записи с N/A** (вернуты к пустому состоянию)
2. ✅ Создан файл `improved_patterns.txt` с новыми паттернами

**Текущая статистика:**
- С заполненным standard: 2,017 (27.9%)
- Без standard: **5,201** (нужно обработать)

---

## 🛠️ ЗАДАЧА ДЛЯ CHATGPT:

### Шаг 1: Улучшить паттерны в `utils/fill_standards_with_ai.py`

Открой файл `utils/fill_standards_with_ai.py` и найди функцию `detect_standard_pattern()` (примерно строка 98).

**В массив `gov_patterns` (строка 114-131) ДОБАВЬ эти паттерны:**

```python
# ДОБАВИТЬ ПЕРЕД ПОСЛЕДНЕЙ СТРОКОЙ массива gov_patterns:

# M-серия (AISI высокоскоростные)
(r'^M(\d+)$', 'AISI-M'),  # M1, M2, M4, M35, M42
(r'^M(\d+)\s*(?:Eur|HC)?$', 'AISI-M'),  # M2 Eur, M4 HC

# SKH-серия (JIS японские)
(r'^SKH[-]?(\d+)$', 'JIS-SKH'),  # SKH50, SKH51, SKH54

# X-серия (DIN европейские)
(r'^X\d+[A-Z]', 'DIN-X'),  # X100CrMoV5, X130WMoCrV

# HS-серия (высокоскоростные)
(r'^HS(\d+[-\d]*)$', 'ISO-HS'),  # HS6-5-2, HS2-9-1-8

# K-серия (Bohler)
(r'^K(\d+)$', 'BOHLER-K'),  # K294, K980, K990

# Nickel-серия (UNS)
(r'^Nickel\s*(\d{3})$', 'UNS-NICKEL'),  # Nickel 200, Nickel 205

# Р-серия (GOST русские быстрорежущие)
(r'^[РP]\d+[МMА-Я]', 'GOST-R'),  # Р6М5, Р0М2СФ10
```

### Шаг 2: Добавить обработку новых паттернов

**ПОСЛЕ строки 152 (в конце цикла for pattern, std_type...) ДОБАВЬ:**

```python
# Обработка новых паттернов
if std_type == 'AISI-M':
    return {
        'type': 'government',
        'standard_prefix': 'AISI',
        'standard_number': 'M' + match.group(1),
        'manufacturer': None,
        'country': 'США'
    }
elif std_type == 'JIS-SKH':
    return {
        'type': 'government',
        'standard_prefix': 'JIS',
        'standard_number': 'SKH' + match.group(1),
        'manufacturer': None,
        'country': 'Япония'
    }
elif std_type == 'DIN-X':
    return {
        'type': 'government',
        'standard_prefix': 'DIN',
        'standard_number': grade_name,
        'manufacturer': None,
        'country': 'Германия'
    }
elif std_type == 'ISO-HS':
    return {
        'type': 'government',
        'standard_prefix': 'ISO',
        'standard_number': 'HS' + match.group(1),
        'manufacturer': None,
        'country': 'Международный'
    }
elif std_type == 'BOHLER-K':
    return {
        'type': 'proprietary',
        'standard_prefix': None,
        'standard_number': None,
        'manufacturer': 'Bohler',
        'country': 'Австрия'
    }
elif std_type == 'UNS-NICKEL':
    nickel_num = match.group(1)
    uns_code = f"N0{nickel_num}00"
    return {
        'type': 'government',
        'standard_prefix': 'UNS',
        'standard_number': uns_code,
        'manufacturer': None,
        'country': 'США'
    }
elif std_type == 'GOST-R':
    return {
        'type': 'government',
        'standard_prefix': 'GOST',
        'standard_number': grade_name,
        'manufacturer': None,
        'country': 'Россия'
    }
```

### Шаг 3: Добавить валидацию N/A

Найди функцию `format_standard_value()` (примерно строка 276).

**ПЕРЕД последним return добавь валидацию:**

```python
# В конце функции format_standard_value, ПЕРЕД return standard_value:

# Валидация: не сохранять N/A и пустые значения
if standard_value:
    invalid_patterns = ['N/A', 'unknown', 'Н/A', 'Неподтверждено', 'не найден']
    for invalid in invalid_patterns:
        if invalid in standard_value:
            return None
    if len(standard_value.strip()) < 3:
        return None
    return standard_value

return None
```

### Шаг 4: Обновить промпт AI

Найди функцию `ask_ai_for_standard()` (строка 209) и **ЗАМЕНИ промпт** (строка 223-248):

```python
prompt = f"""Analyze this steel grade and determine its standard:

Steel Grade: {grade_name}
Link: {link or 'N/A'}
Manufacturer: {manufacturer or 'N/A'}

IMPORTANT RULES:
1. If you cannot determine the standard with confidence, return {{"type": "unknown"}}
2. NEVER return "N/A" as a value
3. Only return valid standards (AISI, GOST, DIN, JIS, etc.) or manufacturer names
4. Format examples:
   - Government: {{"type": "government", "standard": "AISI", "number": "M4", "country": "США"}}
   - Proprietary: {{"type": "proprietary", "standard": "Bohler", "number": null, "country": "Австрия"}}
   - Unknown: {{"type": "unknown"}}

Return ONLY valid JSON in this format:
{{
    "type": "government" or "proprietary" or "unknown",
    "standard": "AISI" or "DIN" or manufacturer name,
    "number": "304" or "1.2379" or null,
    "country": "США" or "Германия" etc. (in Russian)
}}
"""
```

### Шаг 5: Запустить обработку

```bash
python ai_batch_processing.py
```

**Ожидаемый результат:**
- Паттерны распознают: M-серию, SKH-серию, X-серию, HS-серию, K-серию, Nickel, Р-серию
- AI не вернет N/A (благодаря валидации)
- Заполненность: **>80-90%**

---

## 📊 Ожидаемые результаты:

### Примеры что должно обработаться ПАТТЕРНАМИ (без AI):

```
M4                -> AISI M4, США ✅
M2                -> AISI M2, США ✅
M35               -> AISI M35, США ✅
SKH54             -> JIS SKH54, Япония ✅
SKH51             -> JIS SKH51, Япония ✅
X100CrMoV5        -> DIN X100CrMoV5, Германия ✅
X130WMoCrV        -> DIN X130WMoCrV, Германия ✅
HS6-5-2           -> ISO HS6-5-2, Международный ✅
K294              -> Bohler, Австрия ✅
K980              -> Bohler, Австрия ✅
Nickel 205        -> UNS N02050, США ✅
Nickel 212        -> UNS N02120, США ✅
Р6М5              -> GOST Р6М5, Россия ✅
Р0М2СФ10          -> GOST Р0М2СФ10, Россия ✅
```

### После обработки ожидаем:

- **Обработано**: 5,201 марок
- **Заполненность**: >80-90% (5,800-6,500 из 7,218)
- **N/A записей**: 0 (благодаря валидации)
- **Паттерны**: ~60-70% марок
- **AI**: ~20-30% марок

---

## 🔄 Что делать после:

1. Скопируй финальную статистику из вывода
2. Проверь что нет записей с N/A:
   ```python
   cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE standard LIKE '%N/A%'")
   ```
   Должно быть **0**

3. Вернись в Claude Code для проверки

---

## ⚠️ ВАЖНО:

- **НЕ пропускай шаги 1-4** - они критически важны!
- Убедись что все паттерны добавлены в **ПРАВИЛЬНОЕ место**
- Валидация должна **отфильтровывать N/A**
- Если AI вернул unknown - это OK, просто не сохраняем

---

**Удачи! После завершения возвращайся в Claude Code.** 🚀
