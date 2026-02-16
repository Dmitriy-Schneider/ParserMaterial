# 🤖 Telegram Bot vs Web Interface - Сравнение функций

## Краткое резюме

| Функция | Web Interface | Telegram Bot | Статус |
|---------|---------------|--------------|--------|
| **Поиск марок (Search)** | ✅ | ✅ | **ИДЕНТИЧНО** |
| **Поиск по кириллице** | ✅ | ✅ | **ИДЕНТИЧНО** |
| **AI Search (Perplexity)** | ✅ | ✅ | **ИДЕНТИЧНО** |
| **Similar (Fuzzy Search)** | ✅ | ✅ | **ИДЕНТИЧНО** |
| **Compare с AI марками** | ✅ | ⚠️ | **ЧАСТИЧНО** |
| **Фильтры по элементам** | ✅ | ❌ | **НЕ ПОДДЕРЖИВАЕТСЯ** |

---

## Детальное сравнение

### 1. Поиск марок (Search)

#### Web Interface:
```javascript
// templates/index.html - строка 1105
function searchSteels(exactSearch = false, useAI = false) {
    fetch(`/api/steels?${params}`)
}
```

#### Telegram Bot:
```python
# telegram_bot/handlers/search.py - строка 221
response = requests.get(
    config.SEARCH_ENDPOINT,  # http://localhost:5001/api/steels
    params={
        'grade': grade_name,
        'exact': 'true',
        'ai': 'true' if force_ai else 'false'
    }
)
```

**Вердикт:** ✅ **ИДЕНТИЧНО**
- Оба используют `/api/steels` endpoint
- Оба поддерживают `ai=true` для AI поиска
- Оба поддерживают `exact=true` для точного поиска

---

### 2. Поиск по кириллице

#### Web Interface:
- Вводит "16ХГМФТР" → отправляет в `/api/steels?grade=16ХГМФТР&ai=true`
- Backend (app.py) → вызывает ai_search.py
- ai_search.py определяет кириллицу → добавляет специальные инструкции
- Perplexity ищет в российских источниках

#### Telegram Bot:
- Пользователь отправляет "16ХГМФТР"
- Бот вызывает `perform_ai_search(update, "16ХГМФТР")`
- Отправляет в `/api/steels?grade=16ХГМФТР&ai=true`
- **ТОТ ЖЕ ПУТЬ** → ai_search.py → Perplexity

**Вердикт:** ✅ **ИДЕНТИЧНО**
- Оба используют одинаковый backend (ai_search.py)
- Оба получают специальные инструкции для кириллицы
- Оба ищут в российских источниках (splav.kz, metallicheckiy-portal.ru)

---

### 3. Similar (Fuzzy Search)

#### Web Interface:
```javascript
// templates/index.html - строка 1555
function performFuzzySearch(gradeName) {
    // 1. Найти марку в allSteels (может быть AI марка)
    const steel = allSteels.find(s => s.grade === gradeName);

    // 2. Отправить химсостав в fuzzy-search
    fetch('/api/steels/fuzzy-search', {
        method: 'POST',
        body: JSON.stringify({
            grade_data: steel,  // Полные данные (включая AI марки)
            tolerance_percent: tolerance,
            max_mismatched_elements: maxMismatched
        })
    })
}
```

#### Telegram Bot:
```python
# telegram_bot/handlers/fuzzy_search.py - строка 65-139

# 1. Найти марку в БД
response = requests.get(config.SEARCH_ENDPOINT,
    params={'grade': grade_name, 'exact': 'true'})

# 2. Если не найдена, искать через AI
if not results:
    ai_response = requests.get(config.SEARCH_ENDPOINT,
        params={'grade': grade_name, 'ai': 'true'})

# 3. Отправить химсостав в fuzzy-search
fuzzy_response = requests.post(
    f"{config.SEARCH_ENDPOINT}/fuzzy-search",
    json={
        'grade_data': grade_data,  # Полные данные AI марки
        'tolerance_percent': tolerance,
        'max_mismatched_elements': max_mismatched
    }
)
```

**Вердикт:** ✅ **ИДЕНТИЧНО**
- Оба поддерживают AI марки
- Оба передают полные данные в fuzzy-search endpoint
- Оба используют одинаковый tolerance и max_mismatched

---

### 4. Compare (Сравнение марок)

#### Web Interface (НОВОЕ):
```javascript
// templates/index.html - строка 1821-1864
function performComparison() {
    const requestBody = {
        reference_grade: refGrade,
        compare_grades: compareGrades
    };

    // ИСПРАВЛЕНО: Передаем полные данные AI марок
    if (currentCompareRefSteel.id === 'AI') {
        requestBody.reference_data = currentCompareRefSteel;
    }

    const compareData = [];
    compareGrades.forEach(gradeName => {
        const steel = allSteels.find(s => s.grade === gradeName);
        if (steel && steel.id === 'AI') {
            compareData.push(steel);
        }
    });

    if (compareData.length > 0) {
        requestBody.compare_data = compareData;
    }

    fetch('/api/steels/compare', {
        method: 'POST',
        body: JSON.stringify(requestBody)
    })
}
```

**Backend поддержка:**
```python
# app.py - строка 262-352
@app.route('/api/steels/compare', methods=['POST'])
def compare_grades_endpoint():
    # Принимает reference_data и compare_data для AI марок
    reference_data_provided = data.get('reference_data')
    compare_data_provided = data.get('compare_data', [])

    # Использует AI данные перед поиском в БД
    if reference_data_provided:
        ref_dict = {key: reference_data_provided.get(key) for key in columns}

    # Проверяет AI марки в compare_data
    for grade_name in compare_grades:
        if grade_name in ai_grades_dict:
            results.append(ai_grades_dict[grade_name])
```

#### Telegram Bot (СТАРОЕ):
```python
# telegram_bot/handlers/compare.py - строка 27-161

# 1. Найти reference марку
ref_response = requests.get(config.SEARCH_ENDPOINT,
    params={'grade': reference_grade, 'exact': 'true'})

# 2. Если не найдена, искать через AI ✅
if not ref_found:
    ai_response = requests.get(config.SEARCH_ENDPOINT,
        params={'grade': reference_grade, 'ai': 'true'})

# 3. Найти compare марки - ТОЛЬКО В БД! ❌
for grade in compare_grades:
    response = requests.get(config.SEARCH_ENDPOINT,
        params={'grade': grade, 'exact': 'true'})  # НЕТ ai=true!
```

**Проблемы в телеграм боте:**
1. ❌ НЕ использует `/api/steels/compare` endpoint
2. ❌ Делает отдельные запросы для каждой марки
3. ❌ Compare марки ищутся ТОЛЬКО в БД (нет AI fallback)
4. ❌ НЕ передает полные данные AI марок

**Вердикт:** ⚠️ **ЧАСТИЧНО**
- ✅ Reference марка может быть из AI
- ❌ Compare марки НЕ могут быть из AI
- ❌ НЕ использует улучшенный endpoint

---

### 5. Фильтры по элементам

#### Web Interface:
```html
<!-- templates/index.html - строки 871-942 -->
<div class="element-filter">
    <div class="element-group">
        <label>C</label>
        <input id="c_min" placeholder="мин">
        <input id="c_max" placeholder="макс">
    </div>
    <!-- ... Cr, Ni, Mo, V, W, Co, Mn, Si, Cu, Nb, N, S, P ... -->
</div>
```

```javascript
// Передаются в query параметры
fetch(`/api/steels?c_min=0.4&c_max=0.5&cr_min=12&...`)
```

#### Telegram Bot:
```python
# НЕТ ПОДДЕРЖКИ ФИЛЬТРОВ ПО ЭЛЕМЕНТАМ
# Только поиск по названию марки
```

**Вердикт:** ❌ **НЕ ПОДДЕРЖИВАЕТСЯ**
- Телеграм бот не поддерживает фильтры по химическим элементам
- Можно добавить, но это сложная UI задача для Telegram

---

## Исправление Compare в телеграм боте

### Проблема:
Compare марки (не reference) ищутся ТОЛЬКО в БД. Если марка найдена через AI, её нельзя добавить в сравнение.

### Решение:
Использовать улучшенный `/api/steels/compare` endpoint с поддержкой AI данных.

### Код для исправления:

```python
# telegram_bot/handlers/compare.py

async def perform_compare(update: Update, grades: list):
    """Perform comparison of steel grades"""
    try:
        if len(grades) < 2:
            await update.message.reply_text(
                "❌ Укажите минимум 2 марки для сравнения."
            )
            return

        status_msg = await update.message.reply_text(
            f"⚖️ Сравниваю марки: `{', '.join(grades)}`...\n\n"
            f"▪️ Поиск марок (БД + AI)...",
            parse_mode='Markdown'
        )

        reference_grade = grades[0]
        compare_grades = grades[1:]

        # Step 1: Find ALL grades (reference + compare) in DB or AI
        all_grades_data = {}
        ai_data_to_send = {}

        for grade in grades:
            # Try DB first
            response = requests.get(
                config.SEARCH_ENDPOINT,
                params={'grade': grade, 'exact': 'true'},
                timeout=30
            )

            found = False
            if response.status_code == 200:
                results = response.json()
                if results:
                    found = True
                    all_grades_data[grade] = results[0]

            # If not in DB, try AI
            if not found:
                await status_msg.edit_text(
                    f"⚖️ Сравниваю марки: `{', '.join(grades)}`...\n\n"
                    f"▪️ Марка `{grade}` не в БД, ищу через AI...",
                    parse_mode='Markdown'
                )

                ai_response = requests.get(
                    config.SEARCH_ENDPOINT,
                    params={'grade': grade, 'ai': 'true'},
                    timeout=60
                )

                if ai_response.status_code == 200:
                    ai_results = ai_response.json()
                    if ai_results:
                        found = True
                        all_grades_data[grade] = ai_results[0]
                        ai_data_to_send[grade] = ai_results[0]

            if not found:
                await status_msg.edit_text(
                    f"❌ Марка `{grade}` не найдена ни в БД, ни через AI."
                )
                return

        # Step 2: Use /api/steels/compare endpoint with AI data
        compare_request = {
            'reference_grade': reference_grade,
            'compare_grades': compare_grades
        }

        # Add AI data if reference is from AI
        if reference_grade in ai_data_to_send:
            compare_request['reference_data'] = ai_data_to_send[reference_grade]

        # Add AI data for compare grades
        compare_ai_data = []
        for grade in compare_grades:
            if grade in ai_data_to_send:
                compare_ai_data.append(ai_data_to_send[grade])

        if compare_ai_data:
            compare_request['compare_data'] = compare_ai_data

        # Call compare endpoint
        compare_response = requests.post(
            f"{config.SEARCH_ENDPOINT.replace('/steels', '/steels/compare')}",
            json=compare_request,
            timeout=30
        )

        if compare_response.status_code != 200:
            await status_msg.edit_text(
                f"❌ Ошибка сравнения: {compare_response.status_code}"
            )
            return

        compare_data = compare_response.json()

        # Delete status message
        await status_msg.delete()

        # Format and send comparison
        ref_data = compare_data['reference_data']
        compare_results = compare_data['results']

        message = format_comparison_table(ref_data, compare_results, [])

        # Send (split if too long)
        if len(message) > 4000:
            chunks = message.split('\n\n')
            current_chunk = ""
            for chunk in chunks:
                if len(current_chunk) + len(chunk) + 2 < 4000:
                    current_chunk += chunk + "\n\n"
                else:
                    if current_chunk:
                        await update.message.reply_text(current_chunk, parse_mode='Markdown')
                    current_chunk = chunk + "\n\n"
            if current_chunk:
                await update.message.reply_text(current_chunk, parse_mode='Markdown')
        else:
            await update.message.reply_text(message, parse_mode='Markdown')

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
```

---

## Итоговая таблица после исправления

| Функция | Web Interface | Telegram Bot (До) | Telegram Bot (После) |
|---------|---------------|-------------------|----------------------|
| **Поиск марок** | ✅ | ✅ | ✅ |
| **Поиск по кириллице** | ✅ | ✅ | ✅ |
| **AI Search** | ✅ | ✅ | ✅ |
| **Similar с AI** | ✅ | ✅ | ✅ |
| **Compare: Reference AI** | ✅ | ✅ | ✅ |
| **Compare: Compare AI** | ✅ | ❌ | ✅ |
| **Фильтры элементов** | ✅ | ❌ | ❌ |

---

## Рекомендации

### 1. Исправить Compare в телеграм боте (ПРИОРИТЕТ)
- Использовать `/api/steels/compare` endpoint
- Передавать AI данные как в web интерфейсе
- Поддержать AI марки в compare_grades

### 2. Фильтры по элементам (ОПЦИОНАЛЬНО)
Можно добавить упрощенную версию через команду:
```
/filter C:0.4-0.5 Cr:12-15
```

Но это:
- Сложная UI задача для Telegram
- Не очень востребованная функция в боте
- Лучше использовать web интерфейс для детального фильтра

### 3. Синхронизация функционала
После исправления Compare:
- ✅ Все основные функции идентичны
- ✅ Оба используют одинаковый backend (Flask API)
- ✅ Оба поддерживают AI марки везде
- ❌ Только фильтры остаются эксклюзивными для web

---

## Проверка после исправления

### Тест: Compare с AI маркой в телеграм боте

**Шаг 1:** Найти AI марку
```
/search K888 MATRIX
→ Бот использует AI Search, находит марку
```

**Шаг 2:** Сравнить с другими марками
```
/compare K888 MATRIX D2 440C
→ До исправления: "D2 и 440C не найдены" (если их нет в БД)
→ После исправления: Сравнение работает, AI марка в таблице
```

**Шаг 3:** Сравнить две AI марки
```
/search GRADE_X  (AI марка)
/compare GRADE_X K888 MATRIX
→ После исправления: Обе AI марки сравниваются корректно
```

---

## Заключение

**Текущее состояние:**
- ✅ Поиск (Search): ИДЕНТИЧНО
- ✅ Поиск по кириллице: ИДЕНТИЧНО
- ✅ Similar (Fuzzy): ИДЕНТИЧНО
- ⚠️ Compare: ЧАСТИЧНО (reference работает, compare grades нет)
- ❌ Фильтры: НЕ ПОДДЕРЖИВАЕТСЯ

**После исправления Compare:**
- ✅ ВСЕ основные функции будут ИДЕНТИЧНЫ
- ✅ Телеграм бот = полнофункциональный клиент
- ✅ Только фильтры остаются эксклюзивными для web

**Рекомендация:** Исправить Compare в телеграм боте для полной синхронизации функционала.
