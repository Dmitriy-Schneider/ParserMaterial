"""
Импорт марок стали из GB/T 1299-1985 (Легированные инструментальные стали)
Данные извлечены из Таблицы 1 стандарта
"""
import sqlite3


def get_gbt_1299_1985_data():
    """
    Возвращает данные о марках стали из GB/T 1299-1985 (Таблица 1)

    Returns:
        List of dict с данными о марках
    """
    steel_grades = []

    # Таблица 1: Химический состав (% от массы)
    # Все марки: P <= 0.030%, S <= 0.030%

    # Группа 1: Низколегированные стали для режущего инструмента
    group1_grades = {
        '9SiCr': {
            'group': 'Low alloy cutting tool steel',
            'c': '0.85-0.95', 'si': '1.20-1.60', 'mn': '0.30-0.60',
            'cr': '0.95-1.25', 's': '0.030', 'p': '0.030'
        },
        '8MnS': {
            'group': 'Low alloy cutting tool steel',
            'c': '0.75-0.85', 'si': '0.30-0.60', 'mn': '0.80-1.10',
            's': '0.030', 'p': '0.030'
        },
        'Cr06': {
            'group': 'Low alloy cutting tool steel',
            'c': '1.30-1.45', 'si': '<=0.40', 'mn': '<=0.40',
            'cr': '0.50-0.70', 's': '0.030', 'p': '0.030'
        },
        'Cr2': {
            'group': 'Low alloy cutting tool steel',
            'c': '0.95-1.10', 'si': '<=0.40', 'mn': '<=0.40',
            'cr': '1.30-1.65', 's': '0.030', 'p': '0.030'
        },
        '9Cr2': {
            'group': 'Low alloy cutting tool steel',
            'c': '0.80-0.95', 'si': '<=0.40', 'mn': '<=0.40',
            'cr': '1.30-1.70', 's': '0.030', 'p': '0.030'
        },
        'W': {
            'group': 'Low alloy cutting tool steel',
            'c': '1.05-1.25', 'si': '<=0.40', 'mn': '<=0.40',
            'cr': '0.10-0.30', 'w': '0.80-1.20', 's': '0.030', 'p': '0.030'
        },
    }

    # Группа 2: Ударопрочные инструментальные стали
    group2_grades = {
        '4CrW2Si': {
            'group': 'Impact resistant tool steel',
            'c': '0.35-0.45', 'si': '0.80-1.10', 'mn': '<=0.40',
            'cr': '1.00-1.30', 'w': '2.00-2.50', 's': '0.030', 'p': '0.030'
        },
        '5CrW2Si': {
            'group': 'Impact resistant tool steel',
            'c': '0.45-0.55', 'si': '0.50-0.80', 'mn': '<=0.40',
            'cr': '1.00-1.30', 'w': '2.00-2.50', 's': '0.030', 'p': '0.030'
        },
        '6CrW2Si': {
            'group': 'Impact resistant tool steel',
            'c': '0.55-0.65', 'si': '0.50-0.80', 'mn': '<=0.40',
            'cr': '1.00-1.30', 'w': '2.20-2.70', 's': '0.030', 'p': '0.030'
        },
    }

    # Группа 3: Стали для холодной штамповки
    group3_grades = {
        'Cr12': {
            'group': 'Cold work die steel',
            'c': '2.00-2.30', 'si': '<=0.40', 'mn': '<=0.40',
            'cr': '11.50-13.00', 's': '0.030', 'p': '0.030',
            'co': '<=1.00'  # Max Co content
        },
        'Cr12Mo1V1': {
            'group': 'Cold work die steel',
            'c': '1.40-1.60', 'si': '<=0.60', 'mn': '<=0.60',
            'cr': '11.00-13.00', 'mo': '0.70-1.20', 'v': '<=1.10',
            's': '0.030', 'p': '0.030', 'co': '<=1.00'
        },
        'Cr12MoV': {
            'group': 'Cold work die steel',
            'c': '1.45-1.70', 'si': '<=0.40', 'mn': '<=0.40',
            'cr': '11.00-12.50', 'mo': '0.40-0.60', 'v': '0.15-0.30',
            's': '0.030', 'p': '0.030'
        },
        'Cr5Mo1V': {
            'group': 'Cold work die steel',
            'c': '0.95-1.05', 'si': '<=0.50', 'mn': '<=1.00',
            'cr': '4.75-5.50', 'mo': '0.90-1.40', 'v': '0.15-0.50',
            's': '0.030', 'p': '0.030'
        },
        '9Mn2V': {
            'group': 'Cold work die steel',
            'c': '0.85-0.95', 'si': '<=0.40', 'mn': '1.70-2.00',
            'v': '0.10-0.25', 's': '0.030', 'p': '0.030'
        },
        'CrWMn': {
            'group': 'Cold work die steel',
            'c': '0.90-1.05', 'si': '<=0.40', 'mn': '0.80-1.10',
            'cr': '0.90-1.20', 'w': '1.20-1.60', 's': '0.030', 'p': '0.030'
        },
        '9CrWMn': {
            'group': 'Cold work die steel',
            'c': '0.85-0.95', 'si': '<=0.40', 'mn': '0.90-1.20',
            'cr': '0.50-0.80', 'w': '0.50-0.80', 's': '0.030', 'p': '0.030'
        },
        'Cr4W2MoV': {
            'group': 'Cold work die steel',
            'c': '1.12-1.25', 'si': '0.40-0.70', 'mn': '<=0.40',
            'cr': '3.50-4.00', 'w': '1.90-2.60', 'mo': '0.80-1.20', 'v': '0.80-1.10',
            's': '0.030', 'p': '0.030', 'nb': '0.20-0.35'
        },
        '6Cr4W3Mo2VNb': {
            'group': 'Cold work die steel',
            'c': '0.60-0.70', 'si': '<=0.40', 'mn': '<=0.40',
            'cr': '3.80-4.40', 'w': '2.50-3.50', 'mo': '1.80-2.50', 'v': '0.80-1.20',
            's': '0.030', 'p': '0.030', 'nb': '0.20-0.35'
        },
        '6W6Mo5Cr4V': {
            'group': 'Cold work die steel',
            'c': '0.55-0.65', 'si': '<=0.40', 'mn': '<=0.60',
            'cr': '3.70-4.30', 'w': '6.00-7.00', 'mo': '4.50-5.50', 'v': '0.70-1.10',
            's': '0.030', 'p': '0.030'
        },
    }

    # Группа 4: Стали для горячей штамповки
    group4_grades = {
        '5CrMnMo': {
            'group': 'Hot work die steel',
            'c': '0.50-0.60', 'si': '0.25-0.60', 'mn': '1.20-1.60',
            'cr': '0.60-0.90', 'mo': '0.15-0.30', 's': '0.030', 'p': '0.030'
        },
        '5CrNiMo': {
            'group': 'Hot work die steel',
            'c': '0.50-0.60', 'si': '<=0.40', 'mn': '0.50-0.80',
            'cr': '0.50-0.80', 'mo': '0.15-0.30', 'ni': '1.40-1.80',
            's': '0.030', 'p': '0.030'
        },
        '3Cr2W8V': {
            'group': 'Hot work die steel',
            'c': '0.30-0.40', 'si': '<=0.40', 'mn': '<=0.40',
            'cr': '2.20-2.70', 'w': '7.50-9.00', 'v': '0.20-0.50',
            's': '0.030', 'p': '0.030'
        },
        '5Cr4Mo3SiMnVAl': {
            'group': 'Hot work die steel',
            'c': '0.47-0.57', 'si': '0.80-1.10', 'mn': '0.80-1.10',
            'cr': '3.80-4.30', 'mo': '2.80-3.40', 'v': '0.80-1.20',
            's': '0.030', 'p': '0.030'
        },
        '3Cr3Mo3W2V': {
            'group': 'Hot work die steel',
            'c': '0.32-0.42', 'si': '0.60-0.90', 'mn': '<=0.65',
            'cr': '2.80-3.30', 'w': '1.20-1.80', 'mo': '2.50-3.00', 'v': '0.80-1.20',
            's': '0.030', 'p': '0.030'
        },
        '5Cr4W5Mo2V': {
            'group': 'Hot work die steel',
            'c': '0.40-0.50', 'si': '<=0.40', 'mn': '<=0.40',
            'cr': '3.40-4.40', 'w': '4.50-5.30', 'mo': '1.50-2.10', 'v': '0.70-1.10',
            's': '0.030', 'p': '0.030'
        },
        '8Cr3': {
            'group': 'Hot work die steel',
            'c': '0.75-0.85', 'si': '<=0.40', 'mn': '<=0.40',
            'cr': '3.20-3.80', 's': '0.030', 'p': '0.030'
        },
        '4CrMnSiMoV': {
            'group': 'Hot work die steel',
            'c': '0.35-0.45', 'si': '0.80-1.10', 'mn': '0.80-1.10',
            'cr': '1.30-1.50', 'mo': '0.40-0.60', 'v': '0.20-0.40',
            's': '0.030', 'p': '0.030'
        },
        '4Cr3Mo3SiV': {
            'group': 'Hot work die steel',
            'c': '0.35-0.45', 'si': '0.80-1.20', 'mn': '0.25-0.70',
            'cr': '3.00-3.75', 'mo': '2.00-3.00', 'v': '0.25-0.75',
            's': '0.030', 'p': '0.030'
        },
        '4Cr5MoSiV': {
            'group': 'Hot work die steel',
            'c': '0.33-0.43', 'si': '0.80-1.20', 'mn': '0.20-0.50',
            'cr': '4.75-5.50', 'mo': '1.10-1.60', 'v': '0.30-0.60',
            's': '0.030', 'p': '0.030'
        },
        '4Cr5MoSiV1': {
            'group': 'Hot work die steel',
            'c': '0.32-0.45', 'si': '0.80-1.20', 'mn': '0.20-0.50',
            'cr': '4.75-5.50', 'mo': '1.10-1.75', 'v': '0.80-1.20',
            's': '0.030', 'p': '0.030'
        },
        '4Cr5W2VSi': {
            'group': 'Hot work die steel',
            'c': '0.32-0.42', 'si': '0.80-1.20', 'mn': '<=0.40',
            'cr': '4.50-5.50', 'w': '1.60-2.40', 'v': '0.60-1.00',
            's': '0.030', 'p': '0.030'
        },
    }

    # Группа 5: Немагнитные инструментальные стали
    group5_grades = {
        '7Mn15Cr2Al3V2WMo': {
            'group': 'Non-magnetic die steel',
            'c': '0.65-0.75', 'si': '<=0.80', 'mn': '14.50-16.50',
            'cr': '2.00-2.50', 'w': '0.50-0.80', 'mo': '0.50-0.80',
            'v': '1.50-2.00', 'al': '2.30-3.30',
            's': '0.030', 'p': None  # Not specified in table
        },
    }

    # Группа 6: Стали для пластмассовых форм
    group6_grades = {
        '3Cr2Mo': {
            'group': 'Plastic mold steel',
            'c': '0.28-0.40', 'si': '0.20-0.80', 'mn': '0.60-1.00',
            'cr': '1.40-2.00', 'mo': '0.30-0.55',
            's': '0.030', 'p': '0.030'
        },
    }

    # Объединяем все группы
    all_groups = {
        **group1_grades,
        **group2_grades,
        **group3_grades,
        **group4_grades,
        **group5_grades,
        **group6_grades
    }

    for grade_name, composition in all_groups.items():
        steel_grade = {
            'grade': grade_name,
            'standard': 'GB/T 1299-1985',
            'tech': composition.get('group'),
            'c': composition.get('c'),
            'si': composition.get('si'),
            'mn': composition.get('mn'),
            'cr': composition.get('cr'),
            'mo': composition.get('mo'),
            'v': composition.get('v'),
            'w': composition.get('w'),
            'ni': composition.get('ni'),
            'co': composition.get('co'),
            's': composition.get('s'),
            'p': composition.get('p'),
            'nb': composition.get('nb'),
            'other_elements': composition.get('al')  # For 7Mn15Cr2Al3V2WMo
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
            print(f"[SKIP] {grade_data['grade']} ({grade_data['standard']}) - already exists")
            skipped_count += 1
            continue

        # Вставка новой марки
        cursor.execute('''
            INSERT INTO steel_grades (
                grade, standard, tech,
                c, si, mn, cr, mo, v, w, ni, co, s, p, nb, other_elements
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            grade_data['grade'],
            grade_data['standard'],
            grade_data.get('tech'),
            grade_data.get('c'),
            grade_data.get('si'),
            grade_data.get('mn'),
            grade_data.get('cr'),
            grade_data.get('mo'),
            grade_data.get('v'),
            grade_data.get('w'),
            grade_data.get('ni'),
            grade_data.get('co'),
            grade_data.get('s'),
            grade_data.get('p'),
            grade_data.get('nb'),
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
    print("Loading GB/T 1299-1985 data...")
    steel_grades = get_gbt_1299_1985_data()
    print(f"Found grades: {len(steel_grades)}")
    print(f"  Group 1 - Low alloy cutting tool steel: 6 grades")
    print(f"  Group 2 - Impact resistant tool steel: 3 grades")
    print(f"  Group 3 - Cold work die steel: 10 grades")
    print(f"  Group 4 - Hot work die steel: 12 grades")
    print(f"  Group 5 - Non-magnetic die steel: 1 grade")
    print(f"  Group 6 - Plastic mold steel: 1 grade")

    print("\nImporting to database...")
    import_to_database(steel_grades)


if __name__ == '__main__':
    main()
