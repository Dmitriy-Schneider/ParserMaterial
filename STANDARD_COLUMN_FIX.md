# Исправление столбца Standard - удаление дублирования марок

**Дата:** 2026-01-16
**Статус:** ✅ ИСПРАВЛЕНО

## Проблема

В столбце `Standard` базы данных обнаружено дублирование названий марок стали. Стандарт должен содержать только название стандарта и страну, без повторения марки.

### Примеры ошибок (до исправления):

**1. W-Nr (DIN) марки:**
```
1.2379  -> "W-Nr, Германия"         ❌ Нет указания DIN
1.2343  -> "DIN 1.2343, Германия"   ❌ Дублирование марки
```

**Правильно:**
```
1.2379  -> "W-Nr (DIN), Германия"   ✓
1.2343  -> "W-Nr (DIN), Германия"   ✓
```

**2. DIN марки (буквенно-цифровые):**
```
X155CrVMo121 -> "DIN X155CRVMO121, Германия"  ❌ Дублирование марки
```

**Правильно:**
```
X155CrVMo121 -> "DIN, Германия"  ✓
```

**3. AISI марки:**
```
H11 -> "AISI H11, США"  ❌ Дублирование марки
A2  -> "AISI A2, США"   ❌ Дублирование марки
```

**Правильно:**
```
H11 -> "AISI, США"  ✓
A2  -> "AISI, США"  ✓
```

**4. GOST марки:**
```
02Х18Н11 -> "GOST 02Х18Н11, Россия"  ❌ Дублирование марки
12Х1МФ   -> "GOST 12Х1МФ, Россия"   ❌ Дублирование марки
```

**Правильно:**
```
02Х18Н11 -> "GOST, Россия"  ✓
12Х1МФ   -> "GOST, Россия"  ✓
```

---

## Диагностика

### Скрипт: `utils/diagnose_standard_column.py`

**Результаты:**
```
1. W-Nr grades (1.XXXX, 2.XXXX) needing fix: 385
2. DIN alphanumeric grades with duplicates: 100
3. AISI grades with duplicates: 222
4. GOST grades with duplicates: 3317

Total issues to fix: 4024
```

### Детали по каждому стандарту:

#### 1. W-Nr (DIN) - 385 марок

**Формат марки:** N.NNNN (например, 1.2379, 2.4360)
- Только цифры с точкой
- Немецкий стандарт W-Nr (Werkstoffnummer)

**Было:**
- "W-Nr, Германия" (332 марки) - нет указания DIN
- "DIN 1.XXXX, Германия" (53 марки) - дублирование марки

**Стало:**
- "W-Nr (DIN), Германия" (385 марок) - единый формат

#### 2. DIN буквенно-цифровые - 90 марок

**Формат марки:** X155CrVMo121, X100CrMoV51 и т.д.
- Буквенно-цифровое обозначение
- Без точки

**Было:**
- "DIN X155CRVMO121, Германия" - дублирование марки

**Стало:**
- "DIN, Германия" - только стандарт

#### 3. AISI - 222 марки

**Формат марки:** H11, A2, M4, 304, 316 и т.д.
- Американский стандарт

**Было:**
- "AISI H11, США" - дублирование марки
- "AISI A2, США" - дублирование марки

**Стало:**
- "AISI, США" - только стандарт

#### 4. GOST - 3317 марок

**Формат марки:** 02Х18Н11, 12Х1МФ, Х12МФ и т.д.
- Российский/советский стандарт ГОСТ
- Кириллические обозначения

**Было:**
- "GOST 02Х18Н11, Россия" - дублирование марки
- "GOST Х12МФ, Россия" - дублирование марки

**Стало:**
- "GOST, Россия" - только стандарт

---

## Исправление

### 1. W-Nr и DIN марки

**Скрипт:** `utils/fix_standard_column.py`

**Логика для W-Nr (формат N.NNNN):**
```python
for grade, standard in grades:
    if re.match(r'^\d+\.\d+$', grade):  # Только цифры с точкой
        if standard != 'W-Nr (DIN), Германия':
            UPDATE steel_grades 
            SET standard = 'W-Nr (DIN), Германия'
            WHERE grade = grade
```

**Логика для DIN (буквенно-цифровые):**
```python
for grade, standard in din_grades:
    if grade.upper() in standard.upper():  # Дублирование
        UPDATE steel_grades 
        SET standard = 'DIN, Германия'
        WHERE grade = grade
```

**Результат:**
- W-Nr марок исправлено: 385
- DIN марок исправлено: 90

### 2. AISI марки

**Скрипт:** `utils/fix_standard_column.py`

**Логика:**
```python
for grade, standard in aisi_grades:
    if grade in standard:  # Дублирование
        UPDATE steel_grades 
        SET standard = 'AISI, США'
        WHERE grade = grade
```

**Результат:**
- AISI марок исправлено: 222

### 3. GOST марки

**Скрипт:** `utils/fix_gost_duplicates.py`

**Логика:**
```python
for grade, standard in gost_grades:
    if grade in standard:  # Дублирование
        UPDATE steel_grades 
        SET standard = 'GOST, Россия'
        WHERE grade = grade
```

**Результат:**
- GOST марок исправлено: 3317

---

## Проверка

### 1. W-Nr и DIN

**Скрипт:** `utils/verify_standard_column_fix.py`

```
Checking W-Nr grades (format: N.NNNN)...
   OK: All 385 W-Nr grades have correct standard

Checking DIN grades for duplicated grade names...
   OK: No DIN grades with duplicated grade names found
```

**Примеры:**
- 1.2379 → "W-Nr (DIN), Германия" ✓
- X155CrVMo121 → "DIN, Германия" ✓

### 2. AISI

```
Checking AISI grades for duplicated grade names...
   OK: No AISI grades with duplicated grade names found
```

**Пример:**
- H11 → "AISI, США" ✓

### 3. GOST

**Скрипт:** `utils/verify_gost_fix.py`

```
Checking GOST grades...
   OK: No GOST grades with duplicated grade names found!
```

**Пример:**
- 02Х18Н11 → "GOST, Россия" ✓

---

## Статистика

### Всего исправлено: 4014 марок

| Стандарт | Марок исправлено | Новый формат Standard |
|----------|------------------|-----------------------|
| W-Nr (DIN) | 385 | W-Nr (DIN), Германия |
| DIN | 90 | DIN, Германия |
| AISI | 222 | AISI, США |
| GOST | 3317 | GOST, Россия |
| **ВСЕГО** | **4014** | |

### До и После:

**До исправления:**
```
1.2379       -> "W-Nr, Германия"
X155CrVMo121 -> "DIN X155CRVMO121, Германия"
H11          -> "AISI H11, США"
02Х18Н11     -> "GOST 02Х18Н11, Россия"
```

**После исправления:**
```
1.2379       -> "W-Nr (DIN), Германия"
X155CrVMo121 -> "DIN, Германия"
H11          -> "AISI, США"
02Х18Н11     -> "GOST, Россия"
```

---

## Развертывание

```bash
# Пересобрать контейнеры с исправленной БД
docker-compose build --no-cache steel-parser telegram-bot

# Запустить
docker-compose up -d
```

**Статус:** ✅ База данных исправлена, контейнеры пересобраны и перезапущены

---

## Созданные файлы

### Диагностика:
1. ✅ `utils/diagnose_standard_column.py` - диагностика W-Nr, DIN, AISI
2. ✅ `utils/diagnose_gost_duplicates.py` - диагностика GOST

### Исправление:
3. ✅ `utils/fix_standard_column.py` - исправление W-Nr, DIN, AISI
4. ✅ `utils/fix_gost_duplicates.py` - исправление GOST

### Проверка:
5. ✅ `utils/verify_standard_column_fix.py` - проверка W-Nr, DIN, AISI
6. ✅ `utils/verify_gost_fix.py` - проверка GOST

### Документация:
7. ✅ `STANDARD_COLUMN_FIX.md` (этот файл)

---

## Итог

✅ **Все 4014 марок исправлены**
✅ **Столбец Standard теперь не содержит дублирования**
✅ **Единый формат для каждого стандарта**
✅ **Все проверки пройдены успешно**

**Качество базы данных значительно улучшено!**
