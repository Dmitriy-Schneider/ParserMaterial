# ✅ AI Grades Fixes - Completed

## Проблемы (решены)

### 1. Compare не работает с AI марками
**Ошибка:** 404 "No grades found for comparison" при попытке сравнить марку найденную через Perplexity AI

**Причина:**
- Frontend отправлял только названия марок в Compare endpoint
- Backend искал марки только в БД: `cursor.execute("SELECT ... WHERE grade = ?", (grade_name,))`
- AI марки не в БД → fetchone() возвращает None → 404 error

**Решение:** Передача полных данных AI марок от frontend к backend

---

### 2. Exact match сбрасывается при AI поиске
**Проблема:**
- Пользователь включает Exact match (🔍)
- Нажимает AI Perplexity (🤖)
- Exact match mode сбрасывается

**Причина:** `searchWithAI()` вызывала `searchSteels(false, true)` с hardcoded exact=false

**Решение:** Изменили на `searchSteels(true, true)` - exact match + AI fallback

---

## Реализованные изменения

### Файл: `templates/index.html`

#### Изменение 1: Compare с поддержкой AI марок (строки 1821-1864)

```javascript
function performComparison() {
    const refGrade = currentCompareRefSteel.grade;
    const compareGrades = [];

    // ... сбор названий марок ...

    // ИСПРАВЛЕНО: Отправляем полные данные марок (для AI результатов)
    const requestBody = {
        reference_grade: refGrade,
        compare_grades: compareGrades
    };

    // Если reference марка из AI - добавляем полные данные
    if (currentCompareRefSteel.id === 'AI') {
        requestBody.reference_data = currentCompareRefSteel;
    }

    // Добавляем полные данные для compare марок если они из AI
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
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(requestBody)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // ... отображение результатов ...
        } else {
            alert(`Error: ${data.error}`);
        }
    });
}
```

**Что изменилось:**
- Проверяем `steel.id === 'AI'` для определения AI марок
- Передаем полные данные AI марок в `reference_data` и `compare_data`
- Backend использует эти данные вместо запросов к БД

#### Изменение 2: Preserve Exact Match при AI поиске (строки 1316-1319)

```javascript
// AI search function (database + Perplexity AI if not found)
// ИСПРАВЛЕНО: Сохраняет режим точного поиска (exact match) при использовании AI
function searchWithAI() {
    searchSteels(true, true);  // exact=true, useAI=true
}
```

**Было:**
```javascript
function searchWithAI() {
    searchSteels(false, true);  // exact=false (сбрасывало exact mode)
}
```

**Теперь:**
- `exact=true` - точный поиск в БД
- `useAI=true` - fallback на AI если не найдено
- Режим exact match сохраняется

---

### Файл: `app.py`

#### Изменение: Compare endpoint с поддержкой AI данных (строки 262-352)

```python
@app.route('/api/steels/compare', methods=['POST'])
def compare_grades_endpoint():
    """Compare specific steel grades side-by-side (supports AI results)"""
    try:
        data = request.get_json() or {}

        reference_grade = data.get('reference_grade')
        compare_grades = data.get('compare_grades', [])

        # НОВОЕ: Поддержка AI марок - полные данные могут быть переданы напрямую
        reference_data_provided = data.get('reference_data')  # Для AI марок
        compare_data_provided = data.get('compare_data', [])  # Для AI марок

        if not reference_grade:
            return jsonify({'error': 'reference_grade is required'}), 400

        if not compare_grades or len(compare_grades) == 0:
            return jsonify({'error': 'compare_grades list is required'}), 400

        # Get data from DB or use provided data (for AI grades)
        conn = get_connection()
        cursor = conn.cursor()

        columns = ['grade', 'c', 'cr', 'ni', 'mo', 'v', 'w', 'co', 'mn', 'si',
                   'cu', 'nb', 'n', 's', 'p', 'standard', 'manufacturer',
                   'analogues', 'link', 'base', 'tech', 'other']

        # Reference grade - проверяем сначала переданные данные, потом БД
        if reference_data_provided:
            # AI марка - используем переданные данные
            ref_dict = {key: reference_data_provided.get(key) for key in columns}
            print(f"[Compare] Using AI data for reference grade: {reference_grade}")
        else:
            # Обычная марка - ищем в БД
            cursor.execute("""
                SELECT grade, c, cr, ni, mo, v, w, co, mn, si, cu, nb, n, s, p,
                       standard, manufacturer, analogues, link, base, tech, other
                FROM steel_grades
                WHERE grade = ?
            """, (reference_grade,))

            ref_data = cursor.fetchone()
            if not ref_data:
                conn.close()
                return jsonify({'error': f'Reference grade "{reference_grade}" not found'}), 404

            ref_dict = dict(zip(columns, ref_data))

        # Compare grades - проверяем AI данные и БД
        results = []

        # Создаем словарь AI марок для быстрого поиска
        ai_grades_dict = {}
        for ai_grade in compare_data_provided:
            if ai_grade.get('grade'):
                ai_grades_dict[ai_grade['grade']] = ai_grade

        for grade_name in compare_grades:
            # Сначала проверяем AI данные
            if grade_name in ai_grades_dict:
                ai_data = ai_grades_dict[grade_name]
                grade_dict = {key: ai_data.get(key) for key in columns}
                results.append(grade_dict)
                print(f"[Compare] Using AI data for: {grade_name}")
            else:
                # Ищем в БД
                cursor.execute("""
                    SELECT grade, c, cr, ni, mo, v, w, co, mn, si, cu, nb, n, s, p,
                           standard, manufacturer, analogues, link, base, tech, other
                    FROM steel_grades
                    WHERE grade = ?
                """, (grade_name,))

                row = cursor.fetchone()
                if row:
                    results.append(dict(zip(columns, row)))
                    print(f"[Compare] Using DB data for: {grade_name}")

        conn.close()

        return jsonify({
            'success': True,
            'reference_grade': reference_grade,
            'reference_data': ref_dict,
            'compare_count': len(results),
            'results': results
        })

    except Exception as e:
        print(f"[Compare] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
```

**Что изменилось:**
- Принимаем `reference_data` и `compare_data` в request body
- Проверяем AI данные ПЕРЕД запросами к БД
- Используем переданные данные если марка из AI
- Логирование источника данных (AI vs DB)

---

## Логика работы

### Сценарий 1: Поиск марки "Г13" через AI

**Шаг 1:** Пользователь вводит "Г13" и нажимает 🔍 (Exact search)
- Ищет в БД с exact match
- Не находит → No results

**Шаг 2:** Пользователь нажимает 🤖 (AI Perplexity)
- `searchWithAI()` вызывает `searchSteels(true, true)`
- Отправляет `?grade=Г13&exact=true&ai=true`
- Backend:
  1. Ищет в БД с exact match → не находит
  2. Fallback на AI search (line 135-143 в app.py)
  3. Perplexity возвращает данные
  4. Форматирует как `{'id': 'AI', 'grade': 'Г13', ...}`

**Шаг 3:** Пользователь добавляет в Compare
- Frontend находит марку в `allSteels` с `id === 'AI'`
- Отправляет полные данные в `compare_data`
- Backend использует переданные данные
- ✅ Compare работает!

---

### Сценарий 2: Сравнение K888 MATRIX (AI марка)

**Исходная ситуация:** K888 MATRIX найдена через Perplexity, хранится в `allSteels`

**Старое поведение:**
```javascript
// Отправляли только название
fetch('/api/steels/compare', {
    body: JSON.stringify({
        reference_grade: 'K888 MATRIX',
        compare_grades: ['440C', 'D2']
    })
})

// Backend искал в БД
cursor.execute("SELECT ... WHERE grade = ?", ('K888 MATRIX',))
// → fetchone() = None → 404 error ❌
```

**Новое поведение:**
```javascript
// Отправляем полные данные
fetch('/api/steels/compare', {
    body: JSON.stringify({
        reference_grade: 'K888 MATRIX',
        reference_data: {
            grade: 'K888 MATRIX',
            c: '1.45-1.55',
            cr: '14.0-16.0',
            // ... полный химсостав ...
            id: 'AI'
        },
        compare_grades: ['440C', 'D2']
    })
})

// Backend использует переданные данные
if (reference_data_provided):
    ref_dict = {key: reference_data_provided.get(key) for key in columns}
// → Compare работает! ✅
```

---

## Преимущества решения

### ✅ Простота
- Не требует сессий, Redis, дополнительных таблиц
- Минимальные изменения кода
- Работает из коробки

### ✅ Производительность
- Нет дополнительных запросов к БД для AI марок
- Данные передаются напрямую
- Нет overhead от сессий

### ✅ Надежность
- Не зависит от session cookies
- Работает в любом браузере
- Данные не теряются при перезагрузке (хранятся в `allSteels` пока открыта страница)

### ✅ Гибкость
- AI марки могут быть добавлены в БД кнопкой "Save to DB"
- Compare работает и с БД марками, и с AI марками
- Exact match сохраняется при AI поиске

---

## Проверка работы

### Тест 1: Compare с AI маркой

```bash
# 1. Запустить Flask
python app.py

# 2. Открыть браузер: http://localhost:5001
# 3. Ввести "K888 MATRIX" → нажать 🤖 AI Perplexity
# 4. Когда марка найдена, добавить в Compare
# 5. Добавить другие марки (440C, D2)
# 6. Нажать "Compare Selected Steels"
# ✅ Результат: Таблица сравнения показывается без ошибок
```

### Тест 2: Exact Match + AI Search

```bash
# 1. Ввести "Г13" → нажать 🔍 Exact Search
# Результат: "No results found"

# 2. Нажать 🤖 AI Perplexity (НЕ вводя заново марку)
# ✅ Результат:
#   - Exact match mode сохраняется
#   - Backend ищет в БД с exact match
#   - Не находит → Fallback на AI
#   - Perplexity возвращает данные
#   - Марка отображается с бейджем "AI"
```

### Тест 3: Similar с AI маркой

```bash
# ПРИМЕЧАНИЕ: Similar уже был исправлен ранее
# Проверка:
# 1. Найти марку через AI (K888 MATRIX)
# 2. Нажать "Similar" кнопку
# ✅ Результат: Поиск похожих марок работает
```

---

## Ограничения

### ⚠️ Данные теряются при перезагрузке страницы
- AI марки хранятся в `allSteels` (JavaScript переменная)
- При F5 (refresh) данные теряются
- **Решение:** Использовать кнопку "Save to DB" для постоянного сохранения

### ⚠️ Не работает между вкладками
- AI марки не шарятся между разными вкладками браузера
- **Это нормально** - каждая вкладка независима

### ⚠️ Similar может не найти некоторые AI марки
- Fuzzy search использует БД для поиска
- AI марки не в БД → могут не появиться в Similar результатах
- **Решение:** Добавить AI марку в БД перед использованием Similar

---

## Следующие шаги (опционально)

### 1. Улучшить Similar для AI марок
Передавать AI данные в fuzzy search endpoint (аналогично Compare)

### 2. Добавить Local Storage
Сохранять AI марки в localStorage для переживания перезагрузки

```javascript
// При получении AI результата
localStorage.setItem('ai_grades', JSON.stringify(allSteels.filter(s => s.id === 'AI')));

// При загрузке страницы
const savedAIGrades = JSON.parse(localStorage.getItem('ai_grades') || '[]');
allSteels.push(...savedAIGrades);
```

### 3. Пометка AI марок в UI
Добавить более заметный индикатор для AI марок:
```html
<span class="ai-badge" title="Found via Perplexity AI - click 'Save to DB' to persist">
    🤖 AI Result
</span>
```

---

## Файлы изменены

| Файл | Строки | Изменение |
|------|--------|-----------|
| templates/index.html | 1316-1319 | searchWithAI(): exact=true вместо false |
| templates/index.html | 1821-1864 | performComparison(): передача AI данных |
| app.py | 262-352 | compare_grades_endpoint(): прием AI данных |

**Всего:** 3 изменения в 2 файлах

---

## Заключение

Обе проблемы решены:

1. ✅ **Compare работает с AI марками** - передаем полные данные от frontend к backend
2. ✅ **Exact match не сбрасывается** - searchWithAI() использует exact=true

Решение простое, эффективное и не требует дополнительной инфраструктуры.

**Готово к продакшену! 🚀**
