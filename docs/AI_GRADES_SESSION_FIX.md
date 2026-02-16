# 🔧 Решение проблемы: AI марки не работают с Similar и Compare

## Проблема

Марки найденные через Perplexity API:
- ❌ Не работают с Similar (химсостав пропадает)
- ❌ Не работают с Compare (марка не найдена)
- ❌ Не сохраняются в БД автоматически

**Причина:** Compare и Similar читают данные ТОЛЬКО из таблицы `steel_grades` (app.py строки 282-287, 303-308).

```python
# Compare endpoint - ищет только в БД
cursor.execute("""
    SELECT grade, c, cr, ni, mo, ...
    FROM steel_grades
    WHERE grade = ?
""", (reference_grade,))

# Если марка из AI → fetchone() возвращает None → ошибка 404
```

---

## Решение 1: Временная сессия (рекомендуется)

### Концепция

1. AI марки сохраняются в **сессию Flask** (in-memory)
2. Compare/Similar проверяют сначала БД, потом сессию
3. Пользователь может добавить марку в БД одной кнопкой

### Код (app.py)

#### Шаг 1: Включить сессии Flask

```python
# В начале app.py
from flask import Flask, jsonify, request, render_template, session
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'change-me-in-production')
app.config['SESSION_TYPE'] = 'filesystem'  # или 'redis' для production
```

#### Шаг 2: Сохранять AI результаты в сессию

```python
@app.route('/api/steels/search', methods=['GET'])
def search_steels():
    # ... существующий код ...

    # Если результат из AI
    if len(results) == 0 and grade_filter and use_ai and ai_search.enabled:
        ai_result = ai_search.search_steel(grade_filter)
        if ai_result:
            # Format AI result
            ai_result['id'] = 'AI'
            ai_result['grade'] = grade_filter

            # НОВОЕ: Сохранить в сессию
            if 'ai_grades' not in session:
                session['ai_grades'] = {}

            session['ai_grades'][grade_filter] = ai_result
            session.modified = True

            print(f'[SESSION] Saved AI grade "{grade_filter}" to session')

            results = [ai_result]

    return jsonify(results)
```

#### Шаг 3: Проверять сессию в Compare

```python
@app.route('/api/steels/compare', methods=['POST'])
def compare_grades_endpoint():
    try:
        data = request.get_json() or {}
        reference_grade = data.get('reference_grade')
        compare_grades = data.get('compare_grades', [])

        if not reference_grade:
            return jsonify({'error': 'reference_grade is required'}), 400

        conn = get_connection()
        cursor = conn.cursor()

        # Reference grade - проверяем БД и сессию
        ref_dict = get_grade_from_db_or_session(cursor, reference_grade)
        if not ref_dict:
            conn.close()
            return jsonify({'error': f'Reference grade "{reference_grade}" not found'}), 404

        # Compare grades
        results = []
        for grade_name in compare_grades:
            grade_dict = get_grade_from_db_or_session(cursor, grade_name)
            if grade_dict:
                results.append(grade_dict)

        conn.close()

        return jsonify({
            'success': True,
            'reference_grade': reference_grade,
            'reference_data': ref_dict,
            'compare_count': len(results),
            'results': results
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def get_grade_from_db_or_session(cursor, grade_name):
    """
    Get grade from database or session (AI results)

    Args:
        cursor: Database cursor
        grade_name: Grade name to search

    Returns:
        Dict with grade data or None
    """
    # Try database first
    cursor.execute("""
        SELECT grade, c, cr, ni, mo, v, w, co, mn, si, cu, nb, n, s, p,
               standard, manufacturer, analogues, link, base, tech, other
        FROM steel_grades
        WHERE grade = ?
    """, (grade_name,))

    row = cursor.fetchone()
    if row:
        columns = ['grade', 'c', 'cr', 'ni', 'mo', 'v', 'w', 'co', 'mn', 'si',
                   'cu', 'nb', 'n', 's', 'p', 'standard', 'manufacturer',
                   'analogues', 'link', 'base', 'tech', 'other']
        return dict(zip(columns, row))

    # Not in DB - check session (AI results)
    ai_grades = session.get('ai_grades', {})
    if grade_name in ai_grades:
        print(f'[SESSION] Found "{grade_name}" in AI session')
        return ai_grades[grade_name]

    return None
```

#### Шаг 4: Обновить fuzzy_search для Similar

```python
# В fuzzy_search.py

def find_similar_steels(...):
    """Find similar steels to the given composition"""

    # Existing code...

    # ДОБАВИТЬ: Проверка сессии для target_grade
    # (передать session через параметр или Flask g)

    # После получения results из БД:
    # Добавить AI марки из сессии для сравнения
    if hasattr(request, 'session'):
        ai_grades = request.session.get('ai_grades', {})
        for ai_grade_name, ai_grade_data in ai_grades.items():
            # Calculate similarity с AI маркой
            # Добавить к results если подходит
            pass

    return results
```

---

## Решение 2: Автоматическое добавление в БД

### Концепция

AI марки автоматически добавляются в БД как "временные" с флагом `ai_source=True`.

### Плюсы:
- ✅ Сразу работает Similar/Compare
- ✅ Марки не теряются после перезапуска

### Минусы:
- ❌ Захламление БД непроверенными данными
- ❌ Нужна очистка старых AI марок

### Код

```python
@app.route('/api/steels/search', methods=['GET'])
def search_steels():
    # ... existing code ...

    if len(results) == 0 and grade_filter and use_ai and ai_search.enabled:
        ai_result = ai_search.search_steel(grade_filter)
        if ai_result:
            # НОВОЕ: Автоматически добавить в БД
            add_ai_grade_to_database(ai_result, temporary=True)

            results = [ai_result]

    return jsonify(results)


def add_ai_grade_to_database(ai_result, temporary=False):
    """
    Add AI search result to database

    Args:
        ai_result: AI search result dictionary
        temporary: Mark as temporary AI result
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Check if exists
        cursor.execute('SELECT id FROM steel_grades WHERE grade = ?', (ai_result['grade'],))
        if cursor.fetchone():
            print(f'[INFO] Grade {ai_result["grade"]} already in DB')
            conn.close()
            return

        # Add tech field to indicate AI source
        tech_info = ai_result.get('tech', '')
        if temporary:
            tech_info = f'[AI-TEMP] {tech_info}' if tech_info else '[AI-TEMP]'

        # Insert
        cursor.execute("""
            INSERT INTO steel_grades
            (grade, standard, manufacturer, c, cr, ni, mo, v, w, co, mn, si, cu, nb, n, s, p,
             analogues, link, base, tech, other)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ai_result.get('grade'),
            ai_result.get('standard'),
            ai_result.get('manufacturer'),
            ai_result.get('c'),
            ai_result.get('cr'),
            ai_result.get('ni'),
            ai_result.get('mo'),
            ai_result.get('v'),
            ai_result.get('w'),
            ai_result.get('co'),
            ai_result.get('mn'),
            ai_result.get('si'),
            ai_result.get('cu'),
            ai_result.get('nb'),
            ai_result.get('n'),
            ai_result.get('s'),
            ai_result.get('p'),
            ai_result.get('analogues'),
            ai_result.get('link'),
            ai_result.get('base', 'Fe'),
            tech_info,
            ai_result.get('other')
        ))

        conn.commit()
        print(f'[AI→DB] Added "{ai_result["grade"]}" to database')

    except Exception as e:
        print(f'[ERROR] Failed to add AI grade to DB: {e}')
    finally:
        conn.close()
```

### Cleanup скрипт для удаления временных AI марок

```python
#!/usr/bin/env python3
"""Remove temporary AI grades from database"""
import sqlite3

conn = sqlite3.connect('database/steel_database.db')
cursor = conn.cursor()

# Find and remove AI-TEMP grades
cursor.execute("""
    DELETE FROM steel_grades
    WHERE tech LIKE '[AI-TEMP]%'
""")

deleted = cursor.rowcount
conn.commit()
conn.close()

print(f'Removed {deleted} temporary AI grades')
```

---

## Решение 3: Кнопка "Добавить в БД"

### Концепция

UI кнопка рядом с AI результатом → клик → добавление в БД → Similar/Compare работают.

### UI (templates/index.html)

```javascript
// Показать кнопку "Добавить в БД" для AI результатов
if (steel.id === 'AI') {
    actionsHtml += `
        <button class="btn-add-to-db"
                onclick="addAIGradeToDatabase('${steel.grade}')">
            💾 Добавить в БД
        </button>
    `;
}

// Функция добавления
async function addAIGradeToDatabase(gradeName) {
    try {
        const response = await fetch('/api/steels/add-ai-grade', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ grade: gradeName })
        });

        if (response.ok) {
            alert(`✅ Марка ${gradeName} добавлена в базу данных`);
            // Обновить результаты
            performSearch();
        } else {
            alert('❌ Ошибка при добавлении');
        }
    } catch (error) {
        console.error('Error:', error);
    }
}
```

### API endpoint

```python
@app.route('/api/steels/add-ai-grade', methods=['POST'])
def add_ai_grade_endpoint():
    """Add AI grade from session to database"""
    data = request.get_json() or {}
    grade_name = data.get('grade')

    if not grade_name:
        return jsonify({'error': 'Grade name required'}), 400

    # Get from session
    ai_grades = session.get('ai_grades', {})
    if grade_name not in ai_grades:
        return jsonify({'error': 'Grade not found in session'}), 404

    # Add to database
    ai_result = ai_grades[grade_name]
    add_ai_grade_to_database(ai_result, temporary=False)

    return jsonify({'success': True, 'message': f'Grade {grade_name} added to database'})
```

---

## Рекомендация

**Комбинация решений 1 и 3:**

1. ✅ **Сессия** - для временного хранения AI марок
2. ✅ **Кнопка "Добавить в БД"** - для постоянного сохранения
3. ✅ **Compare/Similar** - проверяют БД и сессию

**Преимущества:**
- Работает сразу (через сессию)
- Не захламляет БД
- Пользователь контролирует что добавлять
- Similar/Compare работают с AI марками

**Минусы:**
- Требует изменения кода
- ~2-3 часа работы

Хотите, чтобы я реализовал это решение?
