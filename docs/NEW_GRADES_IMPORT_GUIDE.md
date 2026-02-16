# 📥 Руководство по добавлению новых марок в базу

## Рекомендуемые способы

### 🥇 Вариант 1: Excel → Python скрипт (рекомендуется)

**Лучший вариант для массового добавления (10+ марок)**

#### Шаг 1: Создать Excel файл

**Формат:** `new_grades_YYYY-MM-DD.xlsx`

**Структура таблицы:**

| grade | standard | manufacturer | c | cr | ni | mo | v | w | co | mn | si | cu | nb | n | s | p | analogues | link | base | tech | other | application | properties |
|-------|----------|--------------|---|----|----|----|----|---|----|----|---|----|----|---|---|---|-----------|------|------|------|-------|-------------|------------|
| K888 | Bohler Edelstahl, Австрия | Bohler | 0.47 | 5.5 | | 2.1 | 0.5 | | | 0.4 | 0.3 | | | | | | Hardox 450 1.2767 | https://... | Fe | ... | ... | Износостойкие детали | Твердость 50-55 HRC |

**Обязательные поля:**
- `grade` - название марки (уникальное!)
- `standard` - стандарт или "Производитель, Страна"
- `base` - базовый элемент (Fe, Ni, Co, Ti)

**Желательные поля:**
- Химический состав (c, cr, ni, mo, v, w, co, mn, si, cu, nb, n, s, p)
- `analogues` - аналоги (через пробел или |)
- `link` - ссылка на источник

**Опциональные поля:**
- `application` - применение (на русском)
- `properties` - свойства (на русском)
- `tech` - технические характеристики
- `other` - дополнительные элементы

#### Шаг 2: Использовать существующий скрипт

У вас уже есть `sync_db_from_excel.py` - он готов к использованию!

```bash
python sync_db_from_excel.py new_grades_2026-01-25.xlsx
```

#### Шаг 3: Проверить добавление

```bash
# Проверить последние добавленные марки
python -c "
import sqlite3
conn = sqlite3.connect('database/steel_database.db')
cursor = conn.cursor()
cursor.execute('SELECT grade, standard FROM steel_grades ORDER BY id DESC LIMIT 10')
for row in cursor.fetchall():
    print(f'{row[0]:30s} {row[1]}')
conn.close()
"
```

---

### 🥈 Вариант 2: Прямой SQL INSERT (для 1-5 марок)

**Лучший вариант для быстрого добавления малого количества марок**

#### Создать скрипт `add_single_grade.py`:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Add single grade to database"""
import sqlite3
from database.backup_manager import backup_before_modification

def add_grade(grade_data):
    """
    Add single grade to database

    Args:
        grade_data: Dictionary with grade information
    """
    # Create backup
    backup_before_modification(reason=f'add_grade_{grade_data["grade"]}')

    conn = sqlite3.connect('database/steel_database.db')
    cursor = conn.cursor()

    # Check if grade already exists
    cursor.execute('SELECT id FROM steel_grades WHERE grade = ?', (grade_data['grade'],))
    if cursor.fetchone():
        print(f'❌ Grade {grade_data["grade"]} already exists!')
        conn.close()
        return False

    # Insert new grade
    cursor.execute('''
        INSERT INTO steel_grades
        (grade, standard, manufacturer, c, cr, ni, mo, v, w, co, mn, si, cu, nb, n, s, p,
         analogues, link, base, tech, other, application, properties)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        grade_data.get('grade'),
        grade_data.get('standard'),
        grade_data.get('manufacturer'),
        grade_data.get('c'),
        grade_data.get('cr'),
        grade_data.get('ni'),
        grade_data.get('mo'),
        grade_data.get('v'),
        grade_data.get('w'),
        grade_data.get('co'),
        grade_data.get('mn'),
        grade_data.get('si'),
        grade_data.get('cu'),
        grade_data.get('nb'),
        grade_data.get('n'),
        grade_data.get('s'),
        grade_data.get('p'),
        grade_data.get('analogues'),
        grade_data.get('link'),
        grade_data.get('base', 'Fe'),
        grade_data.get('tech'),
        grade_data.get('other'),
        grade_data.get('application'),
        grade_data.get('properties')
    ))

    conn.commit()
    conn.close()

    print(f'✅ Grade {grade_data["grade"]} added successfully!')
    return True

# Пример использования
if __name__ == '__main__':
    # Пример: добавление новой марки
    new_grade = {
        'grade': 'K888',
        'standard': 'Bohler Edelstahl, Австрия',
        'manufacturer': 'Bohler',
        'c': '0.47',
        'cr': '5.5',
        'mo': '2.1',
        'v': '0.5',
        'mn': '0.4',
        'si': '0.3',
        's': '0.025',
        'p': '0.025',
        'analogues': 'Hardox 450|1.2767',
        'link': 'https://www.bohler-edelstahl.com/en/products/k888-matrix/',
        'base': 'Fe',
        'application': 'Износостойкие детали для горнодобывающей промышленности',
        'properties': 'Твердость 50-55 HRC, высокая износостойкость'
    }

    add_grade(new_grade)
```

**Использование:**
```bash
python add_single_grade.py
```

---

### 🥉 Вариант 3: Web Admin интерфейс (будущее)

**Создать админ-панель для добавления марок через браузер**

#### Добавить в `app.py`:

```python
@app.route('/admin/add-grade', methods=['GET', 'POST'])
@requires_auth  # Используйте Basic Auth из рекомендаций по безопасности
def admin_add_grade():
    """Admin interface for adding new grades"""
    if request.method == 'POST':
        data = request.form

        # Validate required fields
        if not data.get('grade') or not data.get('standard'):
            return jsonify({'error': 'Grade and standard are required'}), 400

        # Create grade dictionary
        grade_data = {
            'grade': data.get('grade'),
            'standard': data.get('standard'),
            'manufacturer': data.get('manufacturer'),
            'c': data.get('c'),
            'cr': data.get('cr'),
            # ... other fields
        }

        # Insert to database
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''INSERT INTO steel_grades ...''')
            conn.commit()
            return jsonify({'success': True, 'message': f'Grade {grade_data["grade"]} added'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()

    # GET: Show form
    return render_template('admin_add_grade.html')
```

#### HTML форма `templates/admin_add_grade.html`:

```html
<form method="POST">
    <h2>Add New Steel Grade</h2>

    <label>Grade Name*:</label>
    <input type="text" name="grade" required>

    <label>Standard*:</label>
    <input type="text" name="standard" required>

    <h3>Chemical Composition (%)</h3>
    <label>C:</label> <input type="text" name="c">
    <label>Cr:</label> <input type="text" name="cr">
    <!-- ... other elements -->

    <button type="submit">Add Grade</button>
</form>
```

---

## Рекомендации по источникам данных

### 1. Официальные производители

**Bohler, Ovako, SSAB, Carpenter, etc.**

```
✓ Скачать PDF datasheet
✓ Извлечь: grade, composition, application, properties
✓ Link → URL к datasheet
```

### 2. Стандарты (ГОСТ, DIN, AISI, JIS)

```
✓ Официальные сайты стандартов
✓ Базы данных (MatWeb, steelnumber.com)
```

### 3. Excel от клиентов/поставщиков

```
✓ Проверить данные перед импортом
✓ Валидировать химический состав (сумма не >100%)
```

---

## Автоматизация

### Создать шаблон Excel

```python
import pandas as pd

# Создать пустой шаблон
template = pd.DataFrame(columns=[
    'grade', 'standard', 'manufacturer',
    'c', 'cr', 'ni', 'mo', 'v', 'w', 'co', 'mn', 'si', 'cu', 'nb', 'n', 's', 'p',
    'analogues', 'link', 'base', 'tech', 'other', 'application', 'properties'
])

# Добавить примеры
template.loc[0] = {
    'grade': 'K888',
    'standard': 'Bohler Edelstahl, Австрия',
    'c': '0.47',
    'cr': '5.5',
    # ...
}

template.to_excel('template_new_grades.xlsx', index=False)
```

---

## Валидация перед добавлением

### Проверки:

1. **Уникальность марки**
   ```python
   cursor.execute('SELECT grade FROM steel_grades WHERE grade = ?', (new_grade,))
   if cursor.fetchone():
       print('Марка уже существует!')
   ```

2. **Химический состав (сумма не > 100%)**
   ```python
   total = sum([float(v) for v in composition.values() if v])
   if total > 100:
       print('Сумма элементов > 100%!')
   ```

3. **Формат значений (0.01-100.00)**
   ```python
   for element, value in composition.items():
       if value and (float(value) < 0 or float(value) > 100):
           print(f'Некорректное значение {element}: {value}')
   ```

---

## Итоговая рекомендация

**Для 10+ марок:** Excel + `sync_db_from_excel.py`
**Для 1-5 марок:** Прямой SQL через `add_single_grade.py`
**Для частого добавления:** Создать Web Admin интерфейс

**Самый простой путь прямо сейчас:**
1. Создать Excel файл с вашими марками
2. Запустить `python sync_db_from_excel.py your_file.xlsx`
3. Готово!
