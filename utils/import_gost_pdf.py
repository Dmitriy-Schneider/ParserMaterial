"""
Импорт марок стали из GOST 1050-88
Данные взяты из таблицы 1 стандарта
"""
import sqlite3
from pathlib import Path


def get_gost_1050_88_data():
    """
    Возвращает данные о марках стали из GOST 1050-88 (Таблица 1)

    Returns:
        List of dict с данными о марках
    """
    steel_grades = []

    # Таблица 1: Химический состав (% от массы)
    # S max = 0.040%, P max = 0.035%, Ni residual max = 0.30%, Cu residual max = 0.30%
    grades_data = {
        '08': {'c': '0.05-0.12', 'si': '0.17-0.37', 'mn': '0.35-0.65', 'cr': '0.10', 's': '0.040', 'p': '0.035'},
        '10': {'c': '0.07-0.14', 'si': '0.17-0.37', 'mn': '0.35-0.65', 'cr': '0.15', 's': '0.040', 'p': '0.035'},
        '15': {'c': '0.12-0.19', 'si': '0.17-0.37', 'mn': '0.35-0.65', 'cr': '0.25', 's': '0.040', 'p': '0.035'},
        '20': {'c': '0.17-0.24', 'si': '0.17-0.37', 'mn': '0.35-0.65', 'cr': '0.25', 's': '0.040', 'p': '0.035'},
        '25': {'c': '0.22-0.30', 'si': '0.17-0.37', 'mn': '0.50-0.80', 'cr': '0.25', 's': '0.040', 'p': '0.035'},
        '30': {'c': '0.27-0.35', 'si': '0.17-0.37', 'mn': '0.50-0.80', 'cr': '0.25', 's': '0.040', 'p': '0.035'},
        '35': {'c': '0.32-0.40', 'si': '0.17-0.37', 'mn': '0.50-0.80', 'cr': '0.25', 's': '0.040', 'p': '0.035'},
        '40': {'c': '0.37-0.45', 'si': '0.17-0.37', 'mn': '0.50-0.80', 'cr': '0.25', 's': '0.040', 'p': '0.035'},
        '45': {'c': '0.42-0.50', 'si': '0.17-0.37', 'mn': '0.50-0.80', 'cr': '0.25', 's': '0.040', 'p': '0.035'},
        '50': {'c': '0.47-0.55', 'si': '0.17-0.37', 'mn': '0.50-0.80', 'cr': '0.25', 's': '0.040', 'p': '0.035'},
        '55': {'c': '0.52-0.60', 'si': '0.17-0.37', 'mn': '0.50-0.80', 'cr': '0.25', 's': '0.040', 'p': '0.035'},
        '60': {'c': '0.57-0.65', 'si': '0.17-0.37', 'mn': '0.50-0.80', 'cr': '0.25', 's': '0.040', 'p': '0.035'},
    }

    for grade_name, composition in grades_data.items():
        steel_grade = {
            'grade': grade_name,
            'standard': 'GOST 1050-88',
            'c': composition.get('c'),
            'si': composition.get('si'),
            'mn': composition.get('mn'),
            'cr': composition.get('cr'),
            's': composition.get('s'),
            'p': composition.get('p'),
            'ni': '0.30',  # Residual max
            'cu': '0.30',  # Residual max
        }
        steel_grades.append(steel_grade)

    return steel_grades


def import_to_database(steel_grades, db_path='database/steel_database.db'):
    """
    Импортирует данные в БД с проверкой на дубликаты

    Args:
        steel_grades: Список словарей с данными о марках
        db_path: Путь к БД
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    imported_count = 0
    skipped_count = 0

    for grade_data in steel_grades:
        # Проверка на существование
        cursor.execute('''
            SELECT id FROM steel_grades
            WHERE grade = ? AND standard = ?
        ''', (grade_data['grade'], grade_data['standard']))

        existing = cursor.fetchone()

        if existing:
            print(f"[SKIP] {grade_data['grade']} ({grade_data['standard']}) - уже существует")
            skipped_count += 1
            continue

        # Вставка новой марки
        cursor.execute('''
            INSERT INTO steel_grades (
                grade, standard,
                c, si, mn, cr, s, p, ni, cu
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            grade_data['grade'],
            grade_data['standard'],
            grade_data.get('c'),
            grade_data.get('si'),
            grade_data.get('mn'),
            grade_data.get('cr'),
            grade_data.get('s'),
            grade_data.get('p'),
            grade_data.get('ni'),
            grade_data.get('cu')
        ))

        print(f"[OK] Импортирован: {grade_data['grade']} ({grade_data['standard']})")
        imported_count += 1

    conn.commit()
    conn.close()

    print(f"\n=== Итоги импорта ===")
    print(f"Импортировано: {imported_count}")
    print(f"Пропущено (дубликаты): {skipped_count}")
    print(f"Всего обработано: {imported_count + skipped_count}")


def main():
    """Основная функция"""
    print("Загрузка данных GOST 1050-88...")
    steel_grades = get_gost_1050_88_data()
    print(f"Найдено марок: {len(steel_grades)}")

    print("\nИмпорт в БД...")
    import_to_database(steel_grades)


if __name__ == '__main__':
    main()
