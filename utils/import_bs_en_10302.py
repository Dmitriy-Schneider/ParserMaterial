"""
Импорт марок стали из BS EN 10302-2008
Creep resisting steels, nickel and cobalt alloys

Этот стандарт охватывает жаропрочные стали для использования при высоких температурах.
"""
import sqlite3
import sys
import os

# Добавляем путь к родительской директории для импорта модулей
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_schema import get_connection


def get_bs_en_10302_data():
    """
    Возвращает данные о марках стали из BS EN 10302-2008

    BS EN 10302-2008 определяет жаропрочные стали, никелевые и кобальтовые сплавы
    для использования при повышенных температурах (креп-стойкие материалы)

    Returns:
        List of dict с данными о марках
    """
    steel_grades = []

    # ===== Ferritic steels (Ферритные жаропрочные стали) =====
    ferritic_grades = {
        'X8CrMoVNb1-1': {
            'steel_number': '1.4903',
            'c': '0.06-0.12', 'si': '0.50', 'mn': '0.30-0.60',
            'cr': '0.90-1.10', 'mo': '0.90-1.10', 'v': '0.25-0.35',
            'nb': '0.06-0.10', 'p': '0.025', 's': '0.015',
            'ni': '0.50', 'n': '0.025',
            'tech': 'Ferritic creep resisting steel. Max service temp ~580°C. Boilers, pressure vessels'
        },
        'X10CrMoVNb9-1': {
            'steel_number': '1.4901',
            'c': '0.08-0.12', 'si': '0.50', 'mn': '0.30-0.60',
            'cr': '8.00-9.50', 'mo': '0.85-1.05', 'v': '0.18-0.25',
            'nb': '0.06-0.10', 'n': '0.030-0.070', 'p': '0.020', 's': '0.010',
            'ni': '0.40',
            'tech': 'Ferritic creep resisting steel. Max service temp ~600°C. Power plant components, headers'
        },
        'X11CrMo9-1': {
            'steel_number': '1.7386',
            'c': '0.08-0.14', 'si': '0.50', 'mn': '0.30-0.60',
            'cr': '8.00-9.50', 'mo': '0.85-1.05', 'p': '0.025', 's': '0.015',
            'ni': '0.50', 'n': '0.012',
            'tech': 'Ferritic creep resisting steel. Max service temp ~580°C. Pressure vessels, boilers'
        },
        'X12CrMo9-1': {
            'steel_number': '1.7335',
            'c': '0.08-0.15', 'si': '0.50', 'mn': '0.40-0.70',
            'cr': '8.00-10.00', 'mo': '0.90-1.10', 'p': '0.025', 's': '0.015',
            'ni': '0.30',
            'tech': 'Ferritic creep resisting steel. Max service temp ~580°C. Boiler tubes, heat exchangers'
        },
    }

    for grade, comp in ferritic_grades.items():
        steel_grades.append({
            'grade': grade,
            'standard': 'BS EN 10302-2008',
            'tech': comp.get('tech', 'Ferritic creep resisting steel'),
            'c': comp.get('c'),
            'si': comp.get('si'),
            'mn': comp.get('mn'),
            'cr': comp.get('cr'),
            'mo': comp.get('mo'),
            'v': comp.get('v'),
            'nb': comp.get('nb'),
            'ni': comp.get('ni'),
            'p': comp.get('p'),
            's': comp.get('s'),
            'n': comp.get('n'),
            'other_elements': f"Steel number: {comp.get('steel_number', 'N/A')}",
            'base': 'Fe'
        })

    # ===== Austenitic steels (Аустенитные жаропрочные стали) =====
    austenitic_grades = {
        'X6CrNi18-10': {
            'steel_number': '1.4948',
            'c': '0.04-0.08', 'si': '1.00', 'mn': '2.00',
            'cr': '17.00-19.00', 'ni': '9.00-11.00', 'p': '0.045', 's': '0.015',
            'n': '0.060',
            'tech': 'Austenitic creep resisting steel. Max service temp ~815°C. Boiler superheaters, steam pipes'
        },
        'X8CrNi25-21': {
            'steel_number': '1.4841',
            'c': '0.05-0.10', 'si': '1.50', 'mn': '2.00',
            'cr': '24.00-26.00', 'ni': '19.00-22.00', 'p': '0.045', 's': '0.015',
            'n': '0.110',
            'tech': 'Austenitic creep resisting steel. Max service temp ~1100°C. Furnace parts, heat treatment equipment'
        },
        'X10CrNiCuNb18-9-3': {
            'steel_number': '1.4961',
            'c': '0.06-0.12', 'si': '1.00', 'mn': '2.00',
            'cr': '17.00-19.00', 'ni': '8.00-10.00', 'cu': '2.50-3.50',
            'nb': '0.15-0.45', 'p': '0.045', 's': '0.015',
            'tech': 'Austenitic creep resisting steel. Max service temp ~700°C. Boiler drums, headers'
        },
        'X10CrNiNb18-9': {
            'steel_number': '1.4550',
            'c': '0.04-0.10', 'si': '1.00', 'mn': '2.00',
            'cr': '17.00-19.00', 'ni': '9.00-12.00',
            'nb': '0.30-0.60', 'p': '0.045', 's': '0.015',
            'tech': 'Austenitic creep resisting steel. Max service temp ~850°C. Furnace parts, heat exchangers'
        },
        'X10CrNiTi18-9': {
            'steel_number': '1.4541',
            'c': '0.04-0.10', 'si': '1.00', 'mn': '2.00',
            'cr': '17.00-19.00', 'ni': '9.00-12.00',
            'p': '0.045', 's': '0.015',
            'tech': 'Austenitic creep resisting steel. Ti stabilized. Max service temp ~850°C'
        },
        'X15CrNiSi25-21': {
            'steel_number': '1.4841',
            'c': '0.12-0.17', 'si': '1.00-2.50', 'mn': '2.00',
            'cr': '24.00-26.00', 'ni': '19.00-22.00', 'p': '0.045', 's': '0.015',
            'n': '0.110',
            'tech': 'Austenitic creep resisting steel. Max service temp ~1100°C. Heat treatment fixtures'
        },
        'X18CrN28': {
            'steel_number': '1.4749',
            'c': '0.15-0.21', 'si': '0.75', 'mn': '2.00',
            'cr': '26.00-28.00', 'ni': '0.60', 'n': '0.15-0.25',
            'p': '0.045', 's': '0.015',
            'tech': 'Austenitic creep resisting steel. Max service temp ~700°C. Valves, pump parts'
        },
    }

    for grade, comp in austenitic_grades.items():
        steel_grades.append({
            'grade': grade,
            'standard': 'BS EN 10302-2008',
            'tech': comp.get('tech', 'Austenitic creep resisting steel'),
            'c': comp.get('c'),
            'si': comp.get('si'),
            'mn': comp.get('mn'),
            'cr': comp.get('cr'),
            'mo': comp.get('mo'),
            'ni': comp.get('ni'),
            'cu': comp.get('cu'),
            'nb': comp.get('nb'),
            'v': comp.get('v'),
            'p': comp.get('p'),
            's': comp.get('s'),
            'n': comp.get('n'),
            'other_elements': f"Steel number: {comp.get('steel_number', 'N/A')}",
            'base': 'Fe'
        })

    # ===== Nickel alloys (Никелевые сплавы) =====
    nickel_alloys = {
        'NiCr15Fe': {
            'steel_number': '2.4816',
            'c': '0.15', 'si': '1.00', 'mn': '1.00',
            'cr': '14.00-17.00', 'ni': 'remainder', 'fe': '6.00-10.00',
            'p': '0.015', 's': '0.015',
            'tech': 'Nickel-chromium-iron alloy. Max service temp ~1150°C. Furnace components, heat treatment'
        },
        'NiCr20TiAl': {
            'steel_number': '2.4952',
            'c': '0.08', 'si': '0.50', 'mn': '1.00',
            'cr': '18.00-21.00', 'ni': 'remainder',
            'p': '0.015', 's': '0.015',
            'tech': 'Nickel-chromium-titanium-aluminum alloy. Max service temp ~1200°C. High-temp applications'
        },
        'NiCr23Fe': {
            'steel_number': '2.4633',
            'c': '0.10', 'si': '1.00', 'mn': '1.50',
            'cr': '20.00-23.00', 'ni': 'remainder', 'fe': '3.00',
            'p': '0.015', 's': '0.015',
            'tech': 'Nickel-chromium-iron alloy. Max service temp ~1200°C. Resistance heating elements'
        },
    }

    for grade, comp in nickel_alloys.items():
        steel_grades.append({
            'grade': grade,
            'standard': 'BS EN 10302-2008',
            'tech': comp.get('tech', 'Nickel-based creep resisting alloy'),
            'c': comp.get('c'),
            'si': comp.get('si'),
            'mn': comp.get('mn'),
            'cr': comp.get('cr'),
            'ni': comp.get('ni'),
            'p': comp.get('p'),
            's': comp.get('s'),
            'other_elements': f"Steel number: {comp.get('steel_number', 'N/A')}. Fe: {comp.get('fe', 'N/A')}",
            'base': 'Ni'
        })

    return steel_grades


def import_to_database():
    """Импортирует марки BS EN 10302-2008 в базу данных"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        grades = get_bs_en_10302_data()
        imported_count = 0
        skipped_count = 0

        for grade_data in grades:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO steel_grades
                    (grade, standard, tech, c, si, mn, cr, mo, v, ni, cu, nb, n, p, s,
                     other_elements, base)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    grade_data.get('grade'),
                    grade_data.get('standard'),
                    grade_data.get('tech'),
                    grade_data.get('c'),
                    grade_data.get('si'),
                    grade_data.get('mn'),
                    grade_data.get('cr'),
                    grade_data.get('mo'),
                    grade_data.get('v'),
                    grade_data.get('ni'),
                    grade_data.get('cu'),
                    grade_data.get('nb'),
                    grade_data.get('n'),
                    grade_data.get('p'),
                    grade_data.get('s'),
                    grade_data.get('other_elements'),
                    grade_data.get('base', 'Fe')
                ))

                if cursor.rowcount > 0:
                    imported_count += 1
                    print(f"[OK] Imported: {grade_data['grade']}")
                else:
                    skipped_count += 1
                    print(f"[SKIP] Skipped (duplicate): {grade_data['grade']}")

            except Exception as e:
                print(f"[ERROR] Error importing {grade_data.get('grade', 'unknown')}: {str(e)}")
                continue

        conn.commit()
        print(f"\n{'='*60}")
        print(f"Import completed!")
        print(f"  Imported: {imported_count} grades")
        print(f"  Skipped:  {skipped_count} duplicates")
        print(f"  Total:    {len(grades)} grades in BS EN 10302-2008")
        print(f"{'='*60}")

    except Exception as e:
        conn.rollback()
        print(f"Database error: {str(e)}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    print("Importing BS EN 10302-2008 steel grades...")
    print("Creep resisting steels, nickel and cobalt alloys")
    print("="*60)
    import_to_database()
