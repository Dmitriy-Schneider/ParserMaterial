"""
Комплексный импорт марок от всех производителей
Китай, Европа, Нержавейки, Дуплексные стали
"""
import sqlite3
import csv
import re


def get_chinese_manufacturers():
    """
    Марки от китайских производителей TG Group и Heye Special Steel
    """
    steel_grades = []

    # ===== TG Group (Tiangong International) - Китай #1 по HSS =====
    # World's No.1 в высокоскоростных сталях

    tg_grades = {
        # Высокоскоростные стали (HSS)
        'TG-M2': {'c': '0.85', 'cr': '4.00', 'mo': '5.00', 'v': '2.00', 'w': '6.00', 'type': 'High Speed Steel'},
        'TG-M35': {'c': '0.85', 'cr': '4.00', 'mo': '5.00', 'v': '2.00', 'w': '6.00', 'co': '5.00', 'type': 'HSS with Co'},
        'TG-M42': {'c': '1.10', 'cr': '3.75', 'mo': '9.50', 'v': '1.15', 'w': '1.50', 'co': '8.00', 'type': 'HSS with Co'},
        # Горячештамповочные стали
        'TG-H13': {'c': '0.40', 'cr': '5.25', 'mo': '1.30', 'v': '1.00', 'si': '1.00', 'type': 'Hot Work'},
        'TG-H11': {'c': '0.38', 'cr': '5.00', 'mo': '1.50', 'v': '0.40', 'si': '1.00', 'type': 'Hot Work'},
        # Холоднодеформируемые стали
        'TG-D2': {'c': '1.55', 'cr': '12.00', 'mo': '0.80', 'v': '0.90', 'type': 'Cold Work'},
        'TG-D3': {'c': '2.25', 'cr': '12.00', 'v': '0.30', 'type': 'Cold Work'},
    }

    for grade, data in tg_grades.items():
        steel_grades.append({
            'grade': grade,
            'manufacturer': 'TG Group (Tiangong)',
            'standard': 'TG Proprietary',
            'c': data.get('c'),
            'cr': data.get('cr'),
            'mo': data.get('mo'),
            'v': data.get('v'),
            'w': data.get('w'),
            'co': data.get('co'),
            'si': data.get('si'),
            'tech': data.get('type'),
        })

    # ===== Heye Special Steel - Китай, лидер по PM-HSS =====

    heye_grades = {
        # Порошковые быстрорежущие стали (PM-HSS)
        'Heye PM-M4': {'c': '1.30', 'cr': '4.00', 'mo': '5.50', 'v': '4.00', 'w': '5.50', 'type': 'PM High Speed Steel'},
        'Heye PM-T15': {'c': '1.60', 'cr': '4.50', 'mo': '0.70', 'v': '5.00', 'w': '12.00', 'co': '5.00', 'type': 'PM-HSS'},
        'Heye ASP-23': {'c': '1.28', 'cr': '4.20', 'mo': '5.00', 'v': '3.10', 'w': '6.40', 'type': 'PM-HSS'},
        # Традиционные HSS
        'Heye M2': {'c': '0.90', 'cr': '4.00', 'mo': '5.00', 'v': '2.00', 'w': '6.00', 'type': 'Traditional HSS'},
        'Heye M35': {'c': '0.90', 'cr': '4.00', 'mo': '5.00', 'v': '2.00', 'w': '6.00', 'co': '5.00', 'type': 'HSS with Co'},
    }

    for grade, data in heye_grades.items():
        steel_grades.append({
            'grade': grade,
            'manufacturer': 'Heye Special Steel',
            'standard': 'Heye Proprietary',
            'c': data.get('c'),
            'cr': data.get('cr'),
            'mo': data.get('mo'),
            'v': data.get('v'),
            'w': data.get('w'),
            'co': data.get('co'),
            'tech': data.get('type'),
        })

    return steel_grades


def get_european_manufacturers():
    """
    Марки от европейских производителей Ravne, Rovalma, Sandvik
    """
    steel_grades = []

    # ===== SIJ Metal Ravne (Словения) - 5-й в мире по инструментальным сталям =====

    ravne_grades = {
        # SITHERM - Hot Work
        'SITHERM 2343': {'c': '0.38', 'cr': '5.00', 'mo': '1.30', 'v': '0.40', 'si': '1.00', 'type': 'Hot Work (H11)'},
        'SITHERM 2344': {'c': '0.38', 'cr': '5.20', 'mo': '1.30', 'v': '0.90', 'si': '1.00', 'type': 'Hot Work (H13)'},
        'SITHERM 2365': {'c': '0.30', 'cr': '3.00', 'mo': '3.00', 'v': '0.50', 'type': 'Hot Work (H10)'},
        # SIHARD - Cold Work
        'SIHARD 2080': {'c': '2.10', 'cr': '12.50', 'mo': '0.80', 'v': '0.50', 'type': 'Cold Work (D6)'},
        'SIHARD 2436': {'c': '1.00', 'cr': '8.00', 'mo': '1.50', 'v': '0.10', 'type': 'Cold Work (O2)'},
        # SIMOLD - Plastic Mould
        'SIMOLD 2311': {'c': '0.40', 'cr': '2.00', 'ni': '1.00', 'mo': '0.20', 'type': 'Plastic Mould (P20)'},
        'SIMOLD 2738': {'c': '0.38', 'cr': '2.00', 'ni': '1.00', 'mo': '0.20', 'type': 'Plastic Mould'},
    }

    for grade, data in ravne_grades.items():
        steel_grades.append({
            'grade': grade,
            'manufacturer': 'SIJ Metal Ravne',
            'standard': 'DIN/EN',
            'c': data.get('c'),
            'cr': data.get('cr'),
            'mo': data.get('mo'),
            'v': data.get('v'),
            'ni': data.get('ni'),
            'si': data.get('si'),
            'tech': data.get('type'),
        })

    # ===== Rovalma S.A. (Испания) - Термопроводящие стали =====

    rovalma_grades = {
        'FASTCOOL-50': {'c': '0.38', 'cr': '2.80', 'mo': '2.00', 'v': '0.50', 'type': 'High Thermal Conductivity (50-53 HRc)'},
        'FASTCOOL-55': {'c': '0.40', 'cr': '3.00', 'mo': '2.20', 'v': '0.60', 'type': 'High Thermal Conductivity (53-55 HRc)'},
        'HTCS-140': {'c': '0.38', 'cr': '5.00', 'mo': '1.40', 'v': '0.50', 'type': 'High Thermal Conductivity (140 W/m.K)'},
        'GTCS-450': {'c': '0.20', 'cr': '0.50', 'ni': '3.00', 'type': 'Low Thermal Conductivity (ceramic-like)'},
    }

    for grade, data in rovalma_grades.items():
        steel_grades.append({
            'grade': grade,
            'manufacturer': 'Rovalma S.A.',
            'standard': 'Rovalma Proprietary',
            'c': data.get('c'),
            'cr': data.get('cr'),
            'mo': data.get('mo'),
            'v': data.get('v'),
            'ni': data.get('ni'),
            'tech': data.get('type'),
        })

    # ===== Sandvik (Швеция) - Нержавейки и ножевые стали =====

    sandvik_grades = {
        '12C27': {'c': '0.60', 'cr': '13.50', 'mn': '0.40', 'type': 'Knife Steel'},
        '14C28N': {'c': '0.62', 'cr': '14.00', 'mn': '0.60', 'n': '0.11', 'type': 'Knife Steel (improved)'},
        '13C26': {'c': '0.68', 'cr': '13.50', 'mn': '0.70', 'type': 'Knife Steel'},
        '19C27': {'c': '1.00', 'cr': '13.50', 'type': 'Knife Steel (high carbon)'},
        '7C27Mo2': {'c': '0.38', 'cr': '14.00', 'mo': '0.70', 'type': 'Knife Steel (corrosion resistant)'},
    }

    for grade, data in sandvik_grades.items():
        steel_grades.append({
            'grade': grade,
            'manufacturer': 'Sandvik',
            'standard': 'Sandvik Proprietary',
            'c': data.get('c'),
            'cr': data.get('cr'),
            'mn': data.get('mn'),
            'mo': data.get('mo'),
            'n': data.get('n'),
            'tech': data.get('type'),
        })

    return steel_grades


def get_stainless_manufacturers():
    """
    Нержавеющие стали от Outokumpu и других
    """
    steel_grades = []

    # ===== Outokumpu - Лидер по нержавейкам =====

    outokumpu_grades = {
        # Lean Duplex
        'Forta LDX 2101': {'c': '0.03', 'cr': '21.5', 'ni': '1.5', 'mn': '5.0', 'n': '0.22', 'type': 'Lean Duplex'},
        'Forta DX 2304': {'c': '0.03', 'cr': '23.0', 'ni': '4.8', 'mo': '0.3', 'n': '0.10', 'type': 'Lean Duplex'},
        # Standard Duplex
        'SAF 2205': {'c': '0.03', 'cr': '22.0', 'ni': '5.5', 'mo': '3.0', 'n': '0.17', 'type': 'Standard Duplex'},
        # Super Duplex
        'SAF 2507': {'c': '0.03', 'cr': '25.0', 'ni': '7.0', 'mo': '4.0', 'n': '0.27', 'type': 'Super Duplex'},
        # Austenitic
        '304': {'c': '0.07', 'cr': '18.0', 'ni': '8.0', 'mn': '2.0', 'type': 'Austenitic (18-8)'},
        '316L': {'c': '0.03', 'cr': '17.0', 'ni': '10.0', 'mo': '2.0', 'type': 'Austenitic (low carbon)'},
        '317L': {'c': '0.03', 'cr': '18.0', 'ni': '11.0', 'mo': '3.0', 'type': 'Austenitic (high Mo)'},
        # Ferritic
        '409': {'c': '0.08', 'cr': '11.0', 'type': 'Ferritic (low Cr)'},
        '430': {'c': '0.12', 'cr': '17.0', 'type': 'Ferritic (standard)'},
        '444': {'c': '0.025', 'cr': '18.0', 'mo': '2.0', 'type': 'Ferritic (stabilized)'},
    }

    for grade, data in outokumpu_grades.items():
        steel_grades.append({
            'grade': grade,
            'manufacturer': 'Outokumpu',
            'standard': 'ASTM/EN',
            'c': data.get('c'),
            'cr': data.get('cr'),
            'ni': data.get('ni'),
            'mo': data.get('mo'),
            'mn': data.get('mn'),
            'n': data.get('n'),
            'tech': data.get('type'),
        })

    return steel_grades


def import_duplex_csv(csv_path='Дуплексные стали.csv'):
    """
    Импорт дуплексных сталей из CSV
    """
    steel_grades = []

    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                # Пропускаем пустые строки
                if not row.get('EN'):
                    continue

                # Извлекаем марку
                grade = row.get('Марка AISI брендовые', '').strip()
                if '\n' in grade:  # Брендовые названия вроде "SAF 2304"
                    parts = grade.split('\n')
                    grade = parts[-1].strip()  # Берем брендовое название

                if not grade or grade == '—':
                    grade = row.get('EN', '').strip()

                steel_grades.append({
                    'grade': grade,
                    'standard': row.get('EN', '').strip() or None,
                    'analogues': f"UNS {row.get('UNS')}" if row.get('UNS') and row.get('UNS') != '—' else None,
                    'c': row.get('C'),
                    'cr': row.get('Cr'),
                    'ni': row.get('Ni'),
                    'mo': row.get('Mo'),
                    'n': row.get('N'),
                    'mn': row.get('Mn'),
                    'cu': row.get('Cu'),
                    'w': row.get('W'),
                    'tech': 'Duplex Stainless Steel',
                })
    except FileNotFoundError:
        print(f"[WARNING] Файл {csv_path} не найден, пропускаем")
        return []

    return steel_grades


def import_to_database(steel_grades, db_path='database/steel_database.db'):
    """
    Импортирует данные в БД с проверкой на дубликаты
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    imported_count = 0
    skipped_count = 0
    updated_count = 0

    for grade_data in steel_grades:
        # Проверка на существование
        cursor.execute('''
            SELECT id, manufacturer, analogues FROM steel_grades
            WHERE grade = ?
        ''', (grade_data['grade'],))

        existing = cursor.fetchone()

        if existing:
            existing_id, existing_mfg, existing_analogues = existing

            # Если производитель совпадает - пропускаем
            if existing_mfg == grade_data.get('manufacturer'):
                print(f"[SKIP] {grade_data['grade']} ({existing_mfg}) - уже существует")
                skipped_count += 1
                continue

            # Если аналоги совпадают - пропускаем
            new_analogues = grade_data.get('analogues', '')
            if new_analogues and new_analogues in str(existing_analogues):
                print(f"[SKIP] {grade_data['grade']} - аналог уже в БД")
                skipped_count += 1
                continue

            # Если это новый производитель для той же марки - добавляем как аналог
            print(f"[UPDATE] {grade_data['grade']} - добавление как аналог")
            # Для упрощения - создаем новую запись с manufacturer
            updated_count += 1

        # Вставка новой марки
        cursor.execute('''
            INSERT INTO steel_grades (
                grade, manufacturer, standard, analogues, tech,
                c, cr, mo, v, w, co, ni, mn, si, cu, n
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            grade_data['grade'],
            grade_data.get('manufacturer'),
            grade_data.get('standard'),
            grade_data.get('analogues'),
            grade_data.get('tech'),
            grade_data.get('c'),
            grade_data.get('cr'),
            grade_data.get('mo'),
            grade_data.get('v'),
            grade_data.get('w'),
            grade_data.get('co'),
            grade_data.get('ni'),
            grade_data.get('mn'),
            grade_data.get('si'),
            grade_data.get('cu'),
            grade_data.get('n')
        ))

        print(f"[OK] Импортирован: {grade_data['grade']} ({grade_data.get('manufacturer', grade_data.get('standard'))})")
        imported_count += 1

    conn.commit()
    conn.close()

    print(f"\n=== Итоги импорта ===")
    print(f"Импортировано: {imported_count}")
    print(f"Обновлено (аналоги): {updated_count}")
    print(f"Пропущено (дубликаты): {skipped_count}")
    print(f"Всего обработано: {imported_count + updated_count + skipped_count}")


def main():
    """Основная функция"""
    all_grades = []

    print("=== Загрузка данных производителей ===\n")

    print("1. Китайские производители (TG Group, Heye)...")
    chinese = get_chinese_manufacturers()
    all_grades.extend(chinese)
    print(f"   Найдено: {len(chinese)} марок\n")

    print("2. Европейские производители (Ravne, Rovalma, Sandvik)...")
    european = get_european_manufacturers()
    all_grades.extend(european)
    print(f"   Найдено: {len(european)} марок\n")

    print("3. Нержавеющие стали (Outokumpu)...")
    stainless = get_stainless_manufacturers()
    all_grades.extend(stainless)
    print(f"   Найдено: {len(stainless)} марок\n")

    print("4. Дуплексные стали из CSV...")
    duplex = import_duplex_csv()
    all_grades.extend(duplex)
    print(f"   Найдено: {len(duplex)} марок\n")

    print(f"ИТОГО: {len(all_grades)} марок для импорта\n")

    print("=== Импорт в БД ===\n")
    import_to_database(all_grades)


if __name__ == '__main__':
    main()
