"""
Импорт марок стали из BS-EN-ISO-4957:2000 (Tool steels)
Данные извлечены из Tables 2, 4, 6 и 8 стандарта
"""
import sqlite3


def get_iso_4957_data():
    """
    Возвращает данные о марках стали из BS-EN-ISO-4957:2000

    Returns:
        List of dict с данными о марках
    """
    steel_grades = []

    # ===== TABLE 2: Non-alloy cold-work tool steels =====
    table2_grades = {
        'C45U': {
            'c': '0.42-0.50', 'si': '0.15-0.40', 'mn': '0.60-0.80',
            'p': '0.030', 's': '0.030',
            'hardness_hb': '207', 'hardening_temp': '810', 'quenching': 'W',
            'tempering_temp': '180', 'hrc_min': '54'
        },
        'C70U': {
            'c': '0.65-0.75', 'si': '0.10-0.30', 'mn': '0.10-0.40',
            'p': '0.030', 's': '0.030',
            'hardness_hb': '183', 'hardening_temp': '800', 'quenching': 'W',
            'tempering_temp': '180', 'hrc_min': '57'
        },
        'C80U': {
            'c': '0.75-0.85', 'si': '0.10-0.30', 'mn': '0.10-0.40',
            'p': '0.030', 's': '0.030',
            'hardness_hb': '192', 'hardening_temp': '790', 'quenching': 'W',
            'tempering_temp': '180', 'hrc_min': '58'
        },
        'C90U': {
            'c': '0.85-0.95', 'si': '0.10-0.30', 'mn': '0.10-0.40',
            'p': '0.030', 's': '0.030',
            'hardness_hb': '207', 'hardening_temp': '780', 'quenching': 'W',
            'tempering_temp': '180', 'hrc_min': '60'
        },
        'C105U': {
            'c': '1.00-1.10', 'si': '0.10-0.30', 'mn': '0.10-0.40',
            'p': '0.030', 's': '0.030',
            'hardness_hb': '212', 'hardening_temp': '780', 'quenching': 'W',
            'tempering_temp': '180', 'hrc_min': '61'
        },
        'C120U': {
            'c': '1.15-1.25', 'si': '0.10-0.30', 'mn': '0.10-0.40',
            'p': '0.030', 's': '0.030',
            'hardness_hb': '217', 'hardening_temp': '770', 'quenching': 'W',
            'tempering_temp': '180', 'hrc_min': '62'
        }
    }

    for grade, comp in table2_grades.items():
        steel_grades.append({
            'grade': grade,
            'standard': 'BS-EN-ISO-4957:2000',
            'tech': f"Non-alloy cold-work tool steel. Hardening: {comp.get('hardening_temp')}°C/{comp.get('quenching')}",
            'c': comp.get('c'),
            'si': comp.get('si'),
            'mn': comp.get('mn'),
            'p': comp.get('p'),
            's': comp.get('s')
        })

    # ===== TABLE 4: Alloy cold-work tool steels =====
    table4_grades = {
        '105V': {
            'c': '1.00-1.10', 'si': '0.10-0.30', 'mn': '0.10-0.40',
            'v': '0.10-0.20', 'hardness_hb': '212', 'hardening_temp': '790',
            'quenching': 'W', 'tempering_temp': '180', 'hrc_min': '61'
        },
        '50WCrV8': {
            'c': '0.45-0.55', 'si': '0.70-1.00', 'mn': '0.15-0.45',
            'cr': '0.90-1.20', 'v': '0.10-0.20', 'w': '1.70-2.20',
            'p': '0.030', 's': '0.030',
            'hardness_hb': '229', 'hardening_temp': '920', 'quenching': 'O',
            'tempering_temp': '180', 'hrc_min': '56'
        },
        '60WCrV8': {
            'c': '0.55-0.65', 'si': '0.70-1.00', 'mn': '0.15-0.45',
            'cr': '0.90-1.20', 'v': '0.10-0.20', 'w': '1.70-2.20',
            'p': '0.030', 's': '0.030',
            'hardness_hb': '229', 'hardening_temp': '910', 'quenching': 'O',
            'tempering_temp': '180', 'hrc_min': '58'
        },
        '102Cr6': {
            'c': '0.95-1.10', 'si': '0.15-0.35', 'mn': '0.25-0.45',
            'cr': '1.35-1.65', 'hardness_hb': '223', 'hardening_temp': '840',
            'quenching': 'O', 'tempering_temp': '180', 'hrc_min': '60'
        },
        '21MnCr5': {
            'c': '0.18-0.24', 'si': '0.15-0.35', 'mn': '1.10-1.40',
            'cr': '1.00-1.30', 'hardness_hb': '217', 'hardening_temp': '820',
            'quenching': 'O'
        },
        '70MnMoCr8': {
            'c': '0.65-0.75', 'si': '0.10-0.50', 'mn': '1.80-2.50',
            'cr': '0.90-1.20', 'mo': '0.90-1.40', 'p': '0.030', 's': '0.030',
            'hardness_hb': '248', 'hardening_temp': '835', 'quenching': 'A',
            'tempering_temp': '180', 'hrc_min': '58'
        },
        '90MnCrV8': {
            'c': '0.85-0.95', 'si': '0.10-0.40', 'mn': '1.80-2.20',
            'cr': '0.20-0.50', 'v': '0.05-0.20', 'hardness_hb': '229',
            'hardening_temp': '790', 'quenching': 'O', 'tempering_temp': '180',
            'hrc_min': '60'
        },
        '95MnWCr5': {
            'c': '0.90-1.00', 'si': '0.10-0.40', 'mn': '1.05-1.35',
            'cr': '0.40-0.60', 'v': '0.05-0.20', 'w': '0.40-0.70',
            'hardness_hb': '229', 'hardening_temp': '800', 'quenching': 'O',
            'tempering_temp': '180', 'hrc_min': '60'
        },
        'X100CrMoV5': {
            'c': '0.95-1.05', 'si': '0.10-0.40', 'mn': '0.40-0.80',
            'cr': '4.80-5.50', 'mo': '0.90-1.20', 'v': '0.15-0.35',
            'p': '0.030', 's': '0.030',
            'hardness_hb': '241', 'hardening_temp': '970', 'quenching': 'A',
            'tempering_temp': '180', 'hrc_min': '60'
        },
        'X153CrMoV12': {
            'c': '1.45-1.60', 'si': '0.10-0.60', 'mn': '0.20-0.60',
            'cr': '11.00-13.00', 'mo': '0.70-1.00', 'v': '0.70-1.00',
            'p': '0.030', 's': '0.030',
            'hardness_hb': '255', 'hardening_temp': '1020', 'quenching': 'A',
            'tempering_temp': '180', 'hrc_min': '61'
        },
        'X210Cr12': {
            'c': '1.90-2.20', 'si': '0.10-0.60', 'mn': '0.20-0.60',
            'cr': '11.00-13.00', 'p': '0.030', 's': '0.030',
            'hardness_hb': '248', 'hardening_temp': '970', 'quenching': 'O',
            'tempering_temp': '180', 'hrc_min': '62'
        },
        'X210CrW12': {
            'c': '2.00-2.30', 'si': '0.10-0.40', 'mn': '0.30-0.60',
            'cr': '11.00-13.00', 'w': '0.60-0.80', 'p': '0.030', 's': '0.030',
            'hardness_hb': '255', 'hardening_temp': '970', 'quenching': 'O',
            'tempering_temp': '180', 'hrc_min': '62'
        },
        '35CrMo7': {
            'c': '0.30-0.40', 'si': '0.30-0.70', 'mn': '0.80-1.00',
            'cr': '1.50-2.00', 'mo': '0.35-0.55', 'p': '0.030', 's': '0.030'
        },
        '40CrMnNiMo8-6-4': {
            'c': '0.35-0.45', 'si': '0.20-0.40', 'mn': '1.30-1.60',
            'cr': '1.80-2.10', 'mo': '0.15-0.25', 'ni': '0.90-1.20',
            'p': '0.030', 's': '0.030'
        },
        '45NiCrMo16': {
            'c': '0.40-0.50', 'si': '0.10-0.40', 'mn': '0.20-0.50',
            'cr': '1.20-1.50', 'mo': '0.15-0.35', 'ni': '3.80-4.30',
            'p': '0.030', 's': '0.030',
            'hardness_hb': '285', 'hardening_temp': '850', 'quenching': 'O',
            'tempering_temp': '180', 'hrc_min': '52'
        },
        'X40Cr14': {
            'c': '0.36-0.42', 'si': '1.00', 'mn': '1.00', 'cr': '12.50-14.50',
            'hardness_hb': '241', 'hardening_temp': '1010', 'quenching': 'O',
            'tempering_temp': '180', 'hrc_min': '52'
        },
        'X38CrMo16': {
            'c': '0.33-0.45', 'si': '1.00', 'mn': '1.50', 'cr': '15.00-17.50',
            'mo': '0.80-1.30', 'ni': '1.00'
        }
    }

    for grade, comp in table4_grades.items():
        steel_grades.append({
            'grade': grade,
            'standard': 'BS-EN-ISO-4957:2000',
            'tech': f"Alloy cold-work tool steel. EN 10027-2",
            'c': comp.get('c'),
            'si': comp.get('si'),
            'mn': comp.get('mn'),
            'cr': comp.get('cr'),
            'mo': comp.get('mo'),
            'v': comp.get('v'),
            'w': comp.get('w'),
            'ni': comp.get('ni'),
            'p': comp.get('p'),
            's': comp.get('s')
        })

    # ===== TABLE 6: Hot-work tool steels =====
    table6_grades = {
        '55NiCrMoV7': {
            'c': '0.50-0.60', 'si': '0.10-0.40', 'mn': '0.60-0.90',
            'cr': '0.80-1.20', 'mo': '0.35-0.55', 'v': '0.05-0.15',
            'w': '', 'ni': '1.50-1.80',
            'hardness_hb': '248', 'hardening_temp': '850', 'quenching': 'O',
            'tempering_temp': '500', 'hrc_min': '42'
        },
        '32CrMoV12-28': {
            'c': '0.28-0.35', 'si': '0.10-0.40', 'mn': '0.15-0.45',
            'cr': '2.70-3.20', 'mo': '2.50-3.00', 'v': '0.40-0.70',
            'hardness_hb': '229', 'hardening_temp': '1040', 'quenching': 'O',
            'tempering_temp': '550', 'hrc_min': '46'
        },
        'X37CrMoV5-1': {
            'c': '0.33-0.41', 'si': '0.80-1.20', 'mn': '0.25-0.50',
            'cr': '4.80-5.50', 'mo': '1.10-1.50', 'v': '0.30-0.50',
            'hardness_hb': '229', 'hardening_temp': '1020', 'quenching': 'O',
            'tempering_temp': '550', 'hrc_min': '48'
        },
        'X38CrMoV5-3': {
            'c': '0.35-0.40', 'si': '0.30-0.50', 'mn': '0.30-0.50',
            'cr': '4.80-5.20', 'mo': '2.70-3.20', 'v': '0.40-0.60',
            'hardness_hb': '229', 'hardening_temp': '1040', 'quenching': 'O',
            'tempering_temp': '550', 'hrc_min': '50'
        },
        'X40CrMoV5-1': {
            'c': '0.35-0.42', 'si': '0.80-1.20', 'mn': '0.25-0.50',
            'cr': '4.80-5.50', 'mo': '1.20-1.50', 'v': '0.85-1.15',
            'hardness_hb': '229', 'hardening_temp': '1020', 'quenching': 'O',
            'tempering_temp': '550', 'hrc_min': '50'
        },
        '50CrMoV13-15': {
            'c': '0.45-0.55', 'si': '0.20-0.80', 'mn': '0.50-0.90',
            'cr': '3.00-3.50', 'mo': '1.30-1.70', 'v': '0.15-0.35',
            'hardness_hb': '248', 'hardening_temp': '1010', 'quenching': 'O',
            'tempering_temp': '510', 'hrc_min': '56'
        },
        'X30WCrV9-3': {
            'c': '0.25-0.35', 'si': '0.10-0.40', 'mn': '0.15-0.45',
            'cr': '2.50-3.20', 'v': '0.30-0.50', 'w': '8.50-9.50',
            'hardness_hb': '241', 'hardening_temp': '1150', 'quenching': 'O',
            'tempering_temp': '600', 'hrc_min': '48'
        },
        'X35CrWMoV5': {
            'c': '0.32-0.40', 'si': '0.80-1.20', 'mn': '0.20-0.50',
            'cr': '4.75-5.50', 'mo': '1.25-1.60', 'v': '0.20-0.50',
            'w': '1.10-1.60', 'hardness_hb': '229', 'hardening_temp': '1020',
            'quenching': 'O', 'tempering_temp': '550', 'hrc_min': '48'
        },
        '38CrCoWV18-17-17': {
            'c': '0.35-0.45', 'si': '0.15-0.50', 'mn': '0.20-0.50',
            'cr': '4.00-4.70', 'v': '1.70-2.10', 'w': '3.80-4.50',
            'co': '4.00-4.50', 'ni': '', 'mo': '0.30-0.50',
            'hardness_hb': '260', 'hardening_temp': '1120', 'quenching': 'O',
            'tempering_temp': '600', 'hrc_min': '48'
        }
    }

    for grade, comp in table6_grades.items():
        steel_grades.append({
            'grade': grade,
            'standard': 'BS-EN-ISO-4957:2000',
            'tech': f"Hot-work tool steel. Hardening: {comp.get('hardening_temp', '')}°C",
            'c': comp.get('c'),
            'si': comp.get('si'),
            'mn': comp.get('mn'),
            'cr': comp.get('cr'),
            'mo': comp.get('mo'),
            'v': comp.get('v'),
            'w': comp.get('w') if comp.get('w') else None,
            'ni': comp.get('ni') if comp.get('ni') else None,
            'co': comp.get('co') if comp.get('co') else None,
            'p': comp.get('p'),
            's': comp.get('s')
        })

    # ===== TABLE 8: High-speed tool steels =====
    table8_grades = {
        'HS0-4-1': {
            'c': '0.77-0.85', 'si': '0.65', 'mn': '', 'cr': '3.90-4.40',
            'mo': '4.00-4.50', 'v': '0.90-1.10', 'w': '', 'co': '',
            'hardness_hb': '262', 'hardening_temp': '1120', 'tempering_temp': '560',
            'hrc_min': '60'
        },
        'HS1-4-2': {
            'c': '0.85-0.95', 'si': '0.65', 'mn': '', 'cr': '3.60-4.30',
            'mo': '4.10-4.80', 'v': '1.70-2.20', 'w': '0.80-1.40',
            'hardness_hb': '262', 'hardening_temp': '1180', 'tempering_temp': '560',
            'hrc_min': '63'
        },
        'HS18-0-1': {
            'c': '0.73-0.83', 'si': '0.45', 'mn': '', 'cr': '3.80-4.50',
            'v': '1.00-1.20', 'w': '17.20-18.70', 'hardness_hb': '269',
            'hardening_temp': '1260', 'tempering_temp': '560', 'hrc_min': '63'
        },
        'HS2-9-2': {
            'c': '0.95-1.05', 'si': '0.70', 'mn': '', 'cr': '3.50-4.50',
            'mo': '8.20-9.20', 'v': '1.75-2.20', 'w': '1.50-2.10',
            'hardness_hb': '269', 'hardening_temp': '1200', 'tempering_temp': '560',
            'hrc_min': '64'
        },
        'HS1-8-1': {
            'c': '0.77-0.87', 'si': '0.70', 'mn': '', 'cr': '3.50-4.50',
            'mo': '8.00-9.00', 'v': '1.00-1.40', 'w': '1.40-2.00',
            'hardness_hb': '262', 'hardening_temp': '1190', 'tempering_temp': '560',
            'hrc_min': '63'
        },
        'HS3-3-2': {
            'c': '0.95-1.03', 'si': '0.45', 'mn': '', 'cr': '3.80-4.50',
            'mo': '2.50-2.90', 'v': '2.20-2.50', 'w': '2.70-3.00',
            'hardness_hb': '255', 'hardening_temp': '1190', 'tempering_temp': '560',
            'hrc_min': '62'
        },
        'HS6-5-2': {
            'c': '0.90-0.98', 'si': '0.45', 'mn': '', 'cr': '3.80-4.50',
            'mo': '4.70-5.20', 'v': '1.70-2.10', 'w': '5.90-6.70',
            'hardness_hb': '262', 'hardening_temp': '1220', 'tempering_temp': '560',
            'hrc_min': '64'
        },
        'HS6-5-2C': {
            'c': '0.86-0.94', 'si': '0.45', 'mn': '', 'cr': '3.80-4.50',
            'mo': '4.70-5.20', 'v': '1.70-2.10', 'w': '5.90-6.70',
            'hardness_hb': '269', 'hardening_temp': '1210', 'tempering_temp': '560',
            'hrc_min': '64'
        },
        'HS6-5-3': {
            'c': '1.15-1.25', 'si': '0.45', 'mn': '', 'cr': '3.80-4.50',
            'mo': '4.70-5.20', 'v': '2.70-3.20', 'w': '5.90-6.70',
            'hardness_hb': '269', 'hardening_temp': '1200', 'tempering_temp': '560',
            'hrc_min': '64'
        },
        'HS6-5-3C': {
            'c': '1.25-1.32', 'si': '0.70', 'mn': '', 'cr': '3.80-4.50',
            'mo': '4.70-5.20', 'v': '2.70-3.20', 'w': '5.90-6.70',
            'hardness_hb': '269', 'hardening_temp': '1180', 'tempering_temp': '560',
            'hrc_min': '64'
        },
        'HS6-6-2': {
            'c': '1.00-1.10', 'si': '0.45', 'mn': '', 'cr': '3.80-4.50',
            'mo': '5.50-6.50', 'v': '2.30-2.60', 'w': '5.90-6.70',
            'hardness_hb': '262', 'hardening_temp': '1200', 'tempering_temp': '560',
            'hrc_min': '64'
        },
        'HS6-5-4': {
            'c': '1.25-1.40', 'si': '0.45', 'mn': '', 'cr': '3.80-4.50',
            'mo': '4.20-5.00', 'v': '3.70-4.20', 'w': '5.20-6.00',
            'hardness_hb': '269', 'hardening_temp': '1210', 'tempering_temp': '560',
            'hrc_min': '64'
        },
        'HS6-5-2-5': {
            'c': '0.87-0.95', 'si': '0.45', 'mn': '', 'cr': '3.80-4.50',
            'mo': '4.70-5.20', 'v': '1.70-2.10', 'w': '5.90-6.70',
            'co': '4.50-5.00', 'hardness_hb': '269', 'hardening_temp': '1210',
            'tempering_temp': '560', 'hrc_min': '64'
        },
        'HS6-5-3-8': {
            'c': '1.23-1.33', 'si': '0.70', 'mn': '', 'cr': '3.80-4.50',
            'mo': '4.70-5.30', 'v': '2.70-3.20', 'w': '5.90-6.70',
            'co': '8.00-8.80', 'hardness_hb': '302', 'hardening_temp': '1180',
            'tempering_temp': '560', 'hrc_min': '65'
        },
        'HS10-4-3-10': {
            'c': '1.20-1.35', 'si': '0.45', 'mn': '', 'cr': '3.80-4.50',
            'mo': '3.20-3.90', 'v': '3.00-3.50', 'w': '9.00-10.00',
            'co': '9.50-10.50', 'hardness_hb': '302', 'hardening_temp': '1230',
            'tempering_temp': '560', 'hrc_min': '66'
        },
        'HS2-9-1-8': {
            'c': '1.05-1.15', 'si': '0.70', 'mn': '', 'cr': '3.50-4.50',
            'mo': '9.00-10.00', 'v': '0.95-1.35', 'w': '1.20-1.90',
            'co': '7.50-8.50', 'hardness_hb': '277', 'hardening_temp': '1190',
            'tempering_temp': '550', 'hrc_min': '66'
        }
    }

    for grade, comp in table8_grades.items():
        steel_grades.append({
            'grade': grade,
            'standard': 'BS-EN-ISO-4957:2000',
            'tech': f"High-speed tool steel. Hardening: {comp.get('hardening_temp', '')}°C",
            'c': comp.get('c'),
            'si': comp.get('si') if comp.get('si') else None,
            'mn': comp.get('mn') if comp.get('mn') else None,
            'cr': comp.get('cr'),
            'mo': comp.get('mo') if comp.get('mo') else None,
            'v': comp.get('v'),
            'w': comp.get('w') if comp.get('w') else None,
            'co': comp.get('co') if comp.get('co') else None,
            'p': comp.get('p') if comp.get('p') else None,
            's': comp.get('s') if comp.get('s') else None
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
                c, mn, si, cr, v, w, mo, co, ni, s, p
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
            grade_data.get('ni'),
            grade_data.get('s'),
            grade_data.get('p')
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
    print("Loading BS-EN-ISO-4957:2000 data...")
    steel_grades = get_iso_4957_data()
    print(f"Found grades: {len(steel_grades)}")
    print(f"  Non-alloy cold-work: 6 grades")
    print(f"  Alloy cold-work: 17 grades")
    print(f"  Hot-work: 9 grades")
    print(f"  High-speed: 16 grades")

    print("\nImporting to database...")
    import_to_database(steel_grades)


if __name__ == '__main__':
    main()
