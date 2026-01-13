# Руководство по редактированию поля Standard в базе данных

## Проблема

AI Search (Perplexity) иногда неправильно определяет поле `standard`:

### Примеры ошибок:
- **Bohler-Uddeholm** → пишет "США" или "Швеция" вместо "Австрия"
- **Путает стандарты и производителей** → некоторые марки это США (AISI), а не Bohler-Uddeholm
- **Несогласованность формата** → "GOST", "GOST, Россия", "GOST Russia"

---

## Рекомендуемые способы редактирования

### ⭐ Способ 1: DBeaver (GUI) - **РЕКОМЕНДУЮ ДЛЯ НАЧАЛА**

**Преимущества:**
- ✅ Визуальный интерфейс
- ✅ Встроенный SQL редактор с подсветкой
- ✅ Предпросмотр изменений перед применением
- ✅ Откат транзакций (ROLLBACK)
- ✅ Фильтры, поиск, сортировка
- ✅ Экспорт данных в CSV/Excel

**Установка:**
1. Скачать: https://dbeaver.io/download/
2. Установить и запустить
3. Database → New Database Connection → SQLite
4. Путь к БД: `c:\Users\dmitr\OneDrive\Desktop\AL\ParserSteel\database\steel_grades.db`

**Как исправлять:**
1. Открыть таблицу `steel_grades`
2. Применить фильтр в столбце `standard`: `%Bohler%`
3. Просмотреть все проблемные записи
4. Использовать SQL скриpty (см. ниже) или редактировать вручную
5. Commit изменений

**Примеры SQL в DBeaver:**
```sql
-- 1. Найти все проблемные Bohler-Uddeholm
SELECT id, grade, standard
FROM steel_grades
WHERE standard LIKE '%Bohler%'
ORDER BY standard;

-- 2. Исправить Bohler-Uddeholm на Austria
UPDATE steel_grades
SET standard = 'Bohler-Uddeholm, Austria'
WHERE standard LIKE '%Bohler-Uddeholm%';

-- 3. Проверить результат
SELECT DISTINCT standard
FROM steel_grades
WHERE standard LIKE '%Bohler%';
```

---

### 🚀 Способ 2: SQL скрипты - **САМЫЙ БЫСТРЫЙ ДЛЯ МАССОВЫХ ПРАВОК**

Создайте файл `fix_standards.sql`:

```sql
-- Bohler-Uddeholm - Austria
UPDATE steel_grades
SET standard = 'Bohler-Uddeholm, Austria'
WHERE standard LIKE '%Bohler-Uddeholm%'
  OR standard LIKE '%Böhler-Uddeholm%';

-- AISI - USA
UPDATE steel_grades
SET standard = 'AISI, USA'
WHERE standard = 'AISI'
   OR standard LIKE 'AISI, US%';

-- GOST - Russia
UPDATE steel_grades
SET standard = 'GOST, Russia'
WHERE standard = 'GOST'
   OR standard LIKE 'GOST,%Росс%';

-- DIN - Germany
UPDATE steel_grades
SET standard = 'DIN, Germany'
WHERE standard = 'DIN';

-- JIS - Japan
UPDATE steel_grades
SET standard = 'JIS, Japan'
WHERE standard = 'JIS';

-- BS-EN - UK
UPDATE steel_grades
SET standard = 'BS-EN, UK'
WHERE standard LIKE 'BS-EN%';

-- GB/T - China
UPDATE steel_grades
SET standard = 'GB/T, China'
WHERE standard LIKE 'GB/T%';

-- Carpenter - USA
UPDATE steel_grades
SET standard = 'Carpenter, USA'
WHERE standard LIKE '%Carpenter%';

-- Sandvik - Sweden
UPDATE steel_grades
SET standard = 'Sandvik, Sweden'
WHERE standard LIKE '%Sandvik%';

-- Uddeholm - Sweden
UPDATE steel_grades
SET standard = 'Uddeholm, Sweden'
WHERE standard LIKE '%Uddeholm%'
  AND standard NOT LIKE '%Bohler%';

-- Commit изменений
COMMIT;
```

**Выполнить из командной строки:**
```bash
# Если БД в Docker контейнере
docker exec -it parser-steel-app sqlite3 /app/database/steel_grades.db < fix_standards.sql

# Если БД локально
sqlite3 database/steel_grades.db < fix_standards.sql
```

---

### 🔧 Способ 3: Python скрипт - **ДЛЯ АВТОМАТИЧЕСКОЙ НОРМАЛИЗАЦИИ**

Создайте `normalize_standards.py`:

```python
import sqlite3
import re

# Правила нормализации: стандарт/производитель → страна
NORMALIZATION_RULES = {
    # Стандарты
    'GOST': 'Russia',
    'AISI': 'USA',
    'ASTM': 'USA',
    'SAE': 'USA',
    'DIN': 'Germany',
    'EN': 'Europe',
    'BS-EN': 'UK',
    'JIS': 'Japan',
    'GB/T': 'China',

    # Производители
    'Bohler-Uddeholm': 'Austria',
    'Böhler-Uddeholm': 'Austria',
    'Bohler': 'Austria',
    'Uddeholm': 'Sweden',
    'Carpenter': 'USA',
    'Sandvik': 'Sweden',
    'Thyssen': 'Germany',
    'Hitachi': 'Japan',
    'Daido': 'Japan',
}

def normalize_standard(standard: str) -> str:
    """Нормализует поле standard согласно правилам"""
    if not standard or standard == 'null':
        return standard

    # Проверяем каждое правило
    for key, country in NORMALIZATION_RULES.items():
        if key.lower() in standard.lower():
            # Если уже есть страна, не перезаписываем
            if ',' in standard:
                return standard
            # Добавляем страну
            return f"{key}, {country}"

    return standard

def main():
    conn = sqlite3.connect('database/steel_grades.db')
    cursor = conn.cursor()

    # Получить все записи
    cursor.execute("SELECT id, standard FROM steel_grades")
    records = cursor.fetchall()

    updates = []
    for record_id, standard in records:
        if standard:
            normalized = normalize_standard(standard)
            if normalized != standard:
                updates.append((normalized, record_id))
                print(f"ID {record_id}: '{standard}' → '{normalized}'")

    # Применить изменения
    if updates:
        print(f"\nОбновление {len(updates)} записей...")
        cursor.executemany("UPDATE steel_grades SET standard = ? WHERE id = ?", updates)
        conn.commit()
        print("✅ Готово!")
    else:
        print("Нет записей для обновления")

    conn.close()

if __name__ == '__main__':
    main()
```

**Запустить:**
```bash
python normalize_standards.py
```

---

### ❌ Способ 4: SQLite CLI - **НЕ РЕКОМЕНДУЮ**

Слишком медленно для массовых правок, но подходит для точечных исправлений:

```bash
docker exec -it parser-steel-app sqlite3 /app/database/steel_grades.db
```

```sql
UPDATE steel_grades SET standard = 'Bohler-Uddeholm, Austria' WHERE grade = 'K340';
.quit
```

---

## Рекомендуемая стратегия

### Шаг 1: Анализ проблемы (DBeaver)
```sql
-- Посмотреть все уникальные значения standard
SELECT DISTINCT standard, COUNT(*) as count
FROM steel_grades
GROUP BY standard
ORDER BY count DESC;

-- Найти проблемные записи
SELECT id, grade, standard
FROM steel_grades
WHERE standard LIKE '%Bohler%'
   OR standard LIKE '%США%'
   OR standard LIKE '%Швеция%'
ORDER BY standard;
```

### Шаг 2: Массовое исправление (SQL скрипт)
Используйте готовый `fix_standards.sql` (см. выше)

### Шаг 3: Автоматическая нормализация для будущих AI результатов
Добавьте `normalize_standards.py` в workflow:
- Запускайте после каждого AI Search
- Или добавьте в код `ai_search.py` автоматическую нормализацию

---

## Частые ошибки и их исправления

| Проблема | SQL исправление |
|----------|-----------------|
| Bohler-Uddeholm → США | `UPDATE steel_grades SET standard = 'Bohler-Uddeholm, Austria' WHERE standard LIKE '%Bohler%' AND standard LIKE '%США%';` |
| AISI без страны | `UPDATE steel_grades SET standard = 'AISI, USA' WHERE standard = 'AISI';` |
| GOST без страны | `UPDATE steel_grades SET standard = 'GOST, Russia' WHERE standard = 'GOST';` |
| Разный формат (запятая/пробел) | `UPDATE steel_grades SET standard = REPLACE(standard, ' Russia', ', Russia');` |

---

## Проверка результатов

После исправлений проверьте:

```sql
-- 1. Все уникальные значения
SELECT DISTINCT standard
FROM steel_grades
ORDER BY standard;

-- 2. Статистика по странам
SELECT
    CASE
        WHEN standard LIKE '%Russia%' THEN 'Russia'
        WHEN standard LIKE '%USA%' THEN 'USA'
        WHEN standard LIKE '%Austria%' THEN 'Austria'
        WHEN standard LIKE '%Germany%' THEN 'Germany'
        WHEN standard LIKE '%Japan%' THEN 'Japan'
        ELSE 'Other'
    END as country,
    COUNT(*) as count
FROM steel_grades
GROUP BY country
ORDER BY count DESC;
```

---

## Резервное копирование

**ВАЖНО:** Перед массовыми изменениями сделайте backup:

```bash
# Windows
copy database\steel_grades.db database\steel_grades.db.backup

# Linux/Docker
docker exec parser-steel-app cp /app/database/steel_grades.db /app/database/steel_grades.db.backup
```

**Восстановление:**
```bash
copy database\steel_grades.db.backup database\steel_grades.db
```

---

## Вывод

**Оптимальный подход:**
1. **DBeaver** - для анализа и визуализации проблем
2. **SQL скрипты** - для быстрых массовых UPDATE
3. **Python скрипт** - для автоматической нормализации будущих AI результатов

**Преимущество перед Claude Code:**
- ❌ **Claude Code** = расход токенов на каждую правку
- ✅ **SQL/Python** = одна команда = вся база исправлена
- ✅ **Быстрее:** SQL обновляет 10,000 записей за 1 секунду

**Время на исправление всей базы:**
- DBeaver + SQL: ~10-15 минут
- Python скрипт: ~1-2 минуты автоматически
- Claude Code: несколько часов + токены

Хотите чтобы я подготовил полный `fix_standards.sql` со всеми правилами для вашей базы?
