"""
Импорт марок стали из GB/T 9943-2008 (Высокоскоростные инструментальные стали)
Данные извлечены из Таблицы 1 стандарта
"""
import sqlite3


def get_gbt_9943_2008_data():
    """
    Возвращает данные о марках стали из GB/T 9943-2008 (Таблица 1)

    Returns:
        List of dict с данными о марках
    """
    steel_grades = []

    # Таблица 1: Химический состав (% от массы)
    # Все марки: S <= 0.030%, P <= 0.030%
    grades_data = {
        'W3Mo3Cr4V2': {
            'unified_code': 'T63342',
            'c': '0.95-1.03', 'mn': '<=0.40', 'si': '<=0.45',
            'cr': '3.80-4.50', 'v': '2.20-2.50', 'w': '2.70-3.00', 'mo': '2.50-2.90',
            's': '<=0.030', 'p': '<=0.030'
        },
        'W4Mo3Cr4VSi': {
            'unified_code': 'T64340',
            'c': '0.83-0.93', 'mn': '0.20-0.40', 'si': '0.70-1.00',
            'cr': '3.80-4.40', 'v': '1.20-1.80', 'w': '3.50-4.50', 'mo': '2.50-3.50',
            's': '<=0.030', 'p': '<=0.030'
        },
        'W18Cr4V': {
            'unified_code': 'T51841',
            'c': '0.73-0.83', 'mn': '0.10-0.40', 'si': '0.20-0.40',
            'cr': '3.80-4.50', 'v': '1.00-1.20', 'w': '17.20-18.70',
            's': '<=0.030', 'p': '<=0.030'
        },
        'W2Mo8Cr4V': {
            'unified_code': 'T62841',
            'c': '0.77-0.87', 'mn': '<=0.40', 'si': '<=0.70',
            'cr': '3.50-4.50', 'v': '1.00-1.40', 'w': '1.40-2.00', 'mo': '8.00-9.00',
            's': '<=0.030', 'p': '<=0.030'
        },
        'W2Mo9Cr4V2': {
            'unified_code': 'T62942',
            'c': '0.95-1.05', 'mn': '0.15-0.40', 'si': '<=0.70',
            'cr': '3.50-4.50', 'v': '1.75-2.20', 'w': '1.50-2.10', 'mo': '8.20-9.20',
            's': '<=0.030', 'p': '<=0.030'
        },
        'W6Mo5Cr4V2': {
            'unified_code': 'T66541',
            'c': '0.80-0.90', 'mn': '0.15-0.40', 'si': '0.20-0.45',
            'cr': '3.80-4.40', 'v': '1.75-2.20', 'w': '5.50-6.75', 'mo': '4.50-5.50',
            's': '<=0.030', 'p': '<=0.030'
        },
        'CW6Mo5Cr4V2': {
            'unified_code': 'T66542',
            'c': '0.86-0.94', 'mn': '0.15-0.40', 'si': '0.20-0.45',
            'cr': '3.80-4.50', 'v': '1.75-2.10', 'w': '5.90-6.70', 'mo': '4.70-5.20',
            's': '<=0.030', 'p': '<=0.030'
        },
        'W6Mo6Cr4V2': {
            'unified_code': 'T66642',
            'c': '1.00-1.10', 'mn': '<=0.40', 'si': '<=0.45',
            'cr': '3.80-4.50', 'v': '2.30-2.60', 'w': '5.90-6.70', 'mo': '5.50-6.50',
            's': '<=0.030', 'p': '<=0.030'
        },
        'W9Mo3Cr4V': {
            'unified_code': 'T69341',
            'c': '0.77-0.87', 'mn': '0.20-0.40', 'si': '0.20-0.40',
            'cr': '3.80-4.40', 'v': '1.30-1.70', 'w': '8.50-9.50', 'mo': '2.70-3.30',
            's': '<=0.030', 'p': '<=0.030'
        },
        'W6Mo5Cr4V3': {
            'unified_code': 'T66543',
            'c': '1.15-1.25', 'mn': '0.15-0.40', 'si': '0.20-0.45',
            'cr': '3.80-4.50', 'v': '2.70-3.20', 'w': '5.90-6.70', 'mo': '4.70-5.20',
            's': '<=0.030', 'p': '<=0.030'
        },
        'CW6Mo5Cr4V3': {
            'unified_code': 'T66545',
            'c': '1.25-1.32', 'mn': '0.15-0.40', 'si': '<=0.70',
            'cr': '3.75-4.50', 'v': '2.70-3.20', 'w': '5.90-6.70', 'mo': '4.70-5.20',
            's': '<=0.030', 'p': '<=0.030'
        },
        'W6Mo5Cr4V4': {
            'unified_code': 'T66544',
            'c': '1.25-1.40', 'mn': '<=0.40', 'si': '<=0.45',
            'cr': '3.80-4.50', 'v': '3.70-4.20', 'w': '5.20-6.00', 'mo': '4.20-5.00',
            's': '<=0.030', 'p': '<=0.030'
        },
        'W6Mo5Cr4V2Al': {
            'unified_code': 'T66546',
            'c': '1.05-1.15', 'mn': '0.15-0.40', 'si': '0.20-0.60',
            'cr': '3.80-4.40', 'v': '1.75-2.20', 'w': '5.50-6.75', 'mo': '4.50-5.50',
            's': '<=0.030', 'p': '<=0.030',
            'al': '0.80-1.20'  # Aluminum addition
        },
        'W12Cr4V5Co5': {
            'unified_code': 'T71245',
            'c': '1.50-1.60', 'mn': '0.15-0.40', 'si': '0.15-0.40',
            'cr': '3.75-5.00', 'v': '4.50-5.25', 'w': '11.75-13.00', 'co': '4.75-5.25',
            's': '<=0.030', 'p': '<=0.030'
        },
        'W6Mo5Cr4V2Co5': {
            'unified_code': 'T76545',
            'c': '0.87-0.95', 'mn': '0.15-0.40', 'si': '0.20-0.45',
            'cr': '3.80-4.50', 'v': '1.70-2.10', 'w': '5.90-6.70',
            'mo': '4.70-5.20', 'co': '4.50-5.00',
            's': '<=0.030', 'p': '<=0.030'
        },
        'W6Mo5Cr4V3Co8': {
            'unified_code': 'T76438',
            'c': '1.23-1.33', 'mn': '<=0.40', 'si': '<=0.70',
            'cr': '3.80-4.50', 'v': '2.70-3.20', 'w': '5.90-6.70',
            'mo': '4.70-5.30', 'co': '8.00-8.80',
            's': '<=0.030', 'p': '<=0.030'
        },
        'W7Mo4Cr4V2Co5': {
            'unified_code': 'T77445',
            'c': '1.05-1.15', 'mn': '0.20-0.60', 'si': '0.15-0.50',
            'cr': '3.75-4.50', 'v': '1.75-2.25', 'w': '6.25-7.00',
            'mo': '3.25-4.25', 'co': '4.75-5.75',
            's': '<=0.030', 'p': '<=0.030'
        },
        'W2Mo9Cr4VCo8': {
            'unified_code': 'T72948',
            'c': '1.05-1.15', 'mn': '0.15-0.40', 'si': '0.15-0.65',
            'cr': '3.50-4.25', 'v': '0.95-1.35', 'w': '1.15-1.85',
            'mo': '9.00-10.00', 'co': '7.75-8.75',
            's': '<=0.030', 'p': '<=0.030'
        },
        'W10Mo4Cr4V3Co10': {
            'unified_code': 'T71010',
            'c': '1.20-1.35', 'mn': '<=0.40', 'si': '<=0.45',
            'cr': '3.80-4.50', 'v': '3.00-3.50', 'w': '9.00-10.00',
            'mo': '3.20-3.90', 'co': '9.50-10.50',
            's': '<=0.030', 'p': '<=0.030'
        },
    }

    for grade_name, composition in grades_data.items():
        steel_grade = {
            'grade': grade_name,
            'standard': 'GB/T 9943, Китай',
            'tech': f"Unified code: {composition.get('unified_code')}",
            'c': composition.get('c'),
            'mn': composition.get('mn'),
            'si': composition.get('si'),
            'cr': composition.get('cr'),
            'v': composition.get('v'),
            'w': composition.get('w'),
            'mo': composition.get('mo'),
            'co': composition.get('co'),
            's': composition.get('s'),
            'p': composition.get('p'),
            'other_elements': composition.get('al', None)  # For W6Mo5Cr4V2Al
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
    updated_count = 0

    for grade_data in steel_grades:
        # Проверка на существование
        cursor.execute('''
            SELECT id, manufacturer FROM steel_grades
            WHERE grade = ? AND standard = ?
        ''', (grade_data['grade'], grade_data['standard']))

        existing = cursor.fetchone()

        if existing:
            print(f"[SKIP] {grade_data['grade']} ({grade_data['standard']}) - already exists")
            skipped_count += 1
            continue

        # Вставка новой марки
        cursor.execute('''
            INSERT INTO steel_grades (
                grade, standard, tech,
                c, mn, si, cr, v, w, mo, co, s, p, other_elements
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            grade_data['grade'],
            grade_data['standard'],
            grade_data.get('tech'),
            grade_data.get('c'),
            grade_data.get('mn'),
            grade_data.get('si'),
            grade_data.get('cr'),
            grade_data.get('v'),
            grade_data.get('w'),
            grade_data.get('mo'),
            grade_data.get('co'),
            grade_data.get('s'),
            grade_data.get('p'),
            grade_data.get('other_elements')
        ))

        print(f"[OK] Imported: {grade_data['grade']} ({grade_data['standard']})")
        imported_count += 1

    conn.commit()
    conn.close()

    print(f"\n=== Import Summary ===")
    print(f"Imported: {imported_count}")
    print(f"Skipped (duplicates): {skipped_count}")
    print(f"Total processed: {imported_count + skipped_count}")


def main():
    """Основная функция"""
    print("Loading GB/T 9943-2008 data...")
    steel_grades = get_gbt_9943_2008_data()
    print(f"Found grades: {len(steel_grades)}")
    print(f"  High-speed tool steels (HSS): {len(steel_grades)} grades")

    print("\nImporting to database...")
    import_to_database(steel_grades)


if __name__ == '__main__':
    main()
