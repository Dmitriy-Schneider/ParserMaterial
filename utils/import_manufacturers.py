"""
Импорт марок стали от известных производителей
GMH Gruppe, Böhler-Uddeholm, Hitachi, Buderus, Kind & Co
"""
import sqlite3


def get_manufacturer_grades():
    """
    Возвращает данные о марках от различных производителей

    Returns:
        List of dict с данными о марках
    """
    steel_grades = []

    # ===== GMH Gruppe (Германия) =====
    # Источник: https://www.gmh-gruppe.de/en/products/customized-tool-steel/

    gmh_grades = {
        'TQ1': {
            'description': 'Ideal for high-performance molds and large structural components',
            'application': 'Die casting, large molds',
            'c': '0.38', 'cr': '2.80', 'mo': '2.00', 'v': '0.50'
        },
        'HP1': {
            'description': 'Combines customized properties with cost efficiency',
            'application': 'Die casting, medium-sized molds',
            'c': '0.38', 'cr': '5.00', 'mo': '1.30', 'v': '0.40'
        },
        'CS1': {
            'description': 'Exceptional working hardness for highest requirements',
            'application': 'Die casting',
            'c': '0.38', 'cr': '5.00', 'mo': '1.30', 'v': '0.95', 'w': '1.20'
        },
        'Rm10Co': {
            'description': 'Engineered for casings and screws in Mg thixomolding',
            'application': 'Magnesium die casting',
            'c': '0.34', 'cr': '4.50', 'mo': '2.80', 'v': '1.00', 'co': '10.00'
        },
        'UH1': {
            'description': 'High-performance steel with maximum wear resistance',
            'application': 'Premium tool steel',
            'c': '0.39', 'cr': '5.00', 'mo': '1.30', 'v': '0.50'
        },
        'HMOD': {
            'description': 'Premium steel for extreme heat loads',
            'application': 'Hot work',
            'c': '0.38', 'cr': '5.25', 'mo': '2.50', 'v': '0.50'
        },
        'CR7V-L': {
            'description': 'Exceptional wear resistance for drop forging',
            'application': 'Hot forging, large series',
            'c': '0.50', 'cr': '7.00', 'mo': '1.50', 'v': '0.40'
        },
        'FTCo': {
            'description': 'Superior tempering resistance for forging mandrels',
            'application': 'Hot forging mandrels',
            'c': '0.45', 'cr': '5.00', 'mo': '3.00', 'v': '1.00', 'co': '8.00'
        },
        'GSF': {
            'description': 'High toughness with enhanced tensile strength',
            'application': 'Hot forging',
            'c': '0.55', 'cr': '1.00', 'mo': '0.45', 'v': '0.10'
        },
        'PM823 ESU': {
            'description': 'Highly efficient remelted tool steel for blanking',
            'application': 'Cold stamping, blanking tools',
            'c': '2.30', 'cr': '12.00', 'mo': '0.70', 'v': '4.00'
        },
        'PW812 ESU': {
            'description': 'Superior forming performance for highly stressed tools',
            'application': 'Cold stamping',
            'c': '0.90', 'cr': '8.00', 'mo': '1.50', 'v': '0.50', 'w': '2.00'
        },
    }

    for grade, data in gmh_grades.items():
        steel_grades.append({
            'grade': grade,
            'manufacturer': 'GMH Gruppe',
            'standard': 'GMH Proprietary, Германия',
            'c': data.get('c'),
            'cr': data.get('cr'),
            'mo': data.get('mo'),
            'v': data.get('v'),
            'w': data.get('w'),
            'co': data.get('co'),
            'tech': data.get('description'),
        })

    # ===== Bohler-Uddeholm (Austria/Sweden) =====
    # voestalpine subsidiary

    bohler_grades = {
        'Vanadis 4 Extra': {
            'description': 'P/M tool steel for adhesive wear and chipping resistance',
            'application': 'Stamping ultra high-strength steels',
            'c': '1.40', 'cr': '4.70', 'mo': '3.50', 'v': '3.70'
        },
    }

    for grade, data in bohler_grades.items():
        steel_grades.append({
            'grade': grade,
            'manufacturer': 'Bohler-Uddeholm',
            'standard': 'Bohler-Uddeholm, Австрия',
            'c': data.get('c'),
            'cr': data.get('cr'),
            'mo': data.get('mo'),
            'v': data.get('v'),
            'tech': data.get('description'),
        })

    # ===== Hitachi Metals (Japan) =====
    # Yasugi Specialty Steels

    hitachi_grades = {
        'DAC Magic': {
            'description': 'High conductivity, thermal diffusivity & impact toughness',
            'application': 'Hot work, H13 alternative',
            'c': '0.39', 'cr': '5.00', 'mo': '1.40', 'v': '0.40', 'si': '1.00'
        },
        'SLD-MAGIC': {
            'description': 'Next generation die steel for extended mold life',
            'application': 'Cold work, easy mold fabrication',
            'c': '1.50', 'cr': '11.50', 'mo': '0.60', 'v': '0.25'
        },
        'SLD-i': {
            'description': 'Advanced cold work steel for AHSS parts processing',
            'application': 'Blanking and forming AHSS',
            'c': '1.00', 'cr': '5.50', 'mo': '1.00', 'v': '0.30'
        },
        'YXR3': {
            'description': 'Matrix high-speed steel with superior toughness',
            'application': 'Tool forging',
            'c': '1.30', 'cr': '4.20', 'mo': '5.00', 'v': '3.50', 'w': '6.50', 'co': '8.00'
        },
        'YXR33': {
            'description': 'Matrix high-speed steel with greatest toughness',
            'application': 'Tool forging',
            'c': '1.25', 'cr': '4.20', 'mo': '5.00', 'v': '3.10', 'w': '6.40', 'co': '10.50'
        },
        'YXR7': {
            'description': 'Matrix high-speed steel with superior strength & toughness',
            'application': 'Tool forging',
            'c': '0.85', 'cr': '4.00', 'mo': '2.00', 'v': '1.00', 'w': '6.50'
        },
    }

    for grade, data in hitachi_grades.items():
        steel_grades.append({
            'grade': grade,
            'manufacturer': 'Hitachi Metals',
            'standard': 'Hitachi Metals, Япония',
            'c': data.get('c'),
            'cr': data.get('cr'),
            'mo': data.get('mo'),
            'v': data.get('v'),
            'w': data.get('w'),
            'co': data.get('co'),
            'si': data.get('si'),
            'tech': data.get('description'),
        })

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
            WHERE grade = ? AND (manufacturer = ? OR standard = ?)
        ''', (grade_data['grade'], grade_data.get('manufacturer'), grade_data.get('standard')))

        existing = cursor.fetchone()

        if existing:
            print(f"[SKIP] {grade_data['grade']} ({grade_data.get('manufacturer')}) - уже существует")
            skipped_count += 1
            continue

        # Вставка новой марки
        cursor.execute('''
            INSERT INTO steel_grades (
                grade, manufacturer, standard, tech,
                c, cr, mo, v, w, co, si
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            grade_data['grade'],
            grade_data.get('manufacturer'),
            grade_data.get('standard'),
            grade_data.get('tech'),
            grade_data.get('c'),
            grade_data.get('cr'),
            grade_data.get('mo'),
            grade_data.get('v'),
            grade_data.get('w'),
            grade_data.get('co'),
            grade_data.get('si')
        ))

        print(f"[OK] Импортирован: {grade_data['grade']} ({grade_data.get('manufacturer')})")
        imported_count += 1

    conn.commit()
    conn.close()

    print(f"\n=== Итоги импорта ===")
    print(f"Импортировано: {imported_count}")
    print(f"Пропущено (дубликаты): {skipped_count}")
    print(f"Всего обработано: {imported_count + skipped_count}")


def main():
    """Основная функция"""
    print("Загрузка данных производителей...")
    steel_grades = get_manufacturer_grades()
    print(f"Найдено марок: {len(steel_grades)}")
    print(f"  GMH Gruppe: 11 марок")
    print(f"  Bohler-Uddeholm: 1 марка")
    print(f"  Hitachi Metals: 6 марок")

    print("\nИмпорт в БД...")
    import_to_database(steel_grades)


if __name__ == '__main__':
    main()
