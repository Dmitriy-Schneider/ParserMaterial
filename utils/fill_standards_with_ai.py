"""
Продвинутый парсер для заполнения столбца Standard с использованием AI
Автоматически определяет:
- Государственные стандарты (AISI, GOST, DIN, JIS, etc.) + страна + номер стандарта
- Фирменные марки (Bohler, Carpenter, etc.) + компания + страна головного офиса
"""
import sqlite3
import sys
from pathlib import Path
import re
import json
from openai import OpenAI
import os
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent))
from database_schema import get_connection

# Load environment variables
load_dotenv()

# Mapping стандартов к странам
STANDARD_COUNTRIES = {
    'AISI': 'США',
    'ASTM': 'США',
    'UNS': 'США',
    'SAE': 'США',
    'GOST': 'Россия',
    'GOST R': 'Россия',
    'TU': 'Россия/СССР',
    'DIN': 'Германия',
    'EN': 'Европа',
    'ISO': 'Международный',
    'JIS': 'Япония',
    'GB': 'Китай',
    'GB/T': 'Китай',
    'BS': 'Великобритания',
    'BS EN': 'Великобритания/Европа',
    'AFNOR': 'Франция',
    'NF': 'Франция',
    'UNI': 'Италия',
    'SIS': 'Швеция',
    'SS': 'Швеция',
    'PN': 'Польша',
    'CSN': 'Чехия',
    'KS': 'Корея',
    'AS': 'Австралия',
    'SABS': 'ЮАР',
}

# Маппинг производителей к странам (расширенный)
MANUFACTURER_COUNTRIES = {
    'Bohler': 'Австрия',
    'Bohler-Uddeholm': 'Австрия',
    'Uddeholm': 'Швеция',
    'Sandvik': 'Швеция',
    'Erasteel': 'Франция',
    'Carpenter': 'США',
    'Crucible': 'США',
    'CPM': 'США',
    'Latrobe': 'США',
    'Ravne': 'Словения',
    'Rovalma': 'Испания',
    'Hitachi': 'Япония',
    'Daido': 'Япония',
    'Takefu': 'Япония',
    'Aichi': 'Япония',
    'GMH': 'Германия',
    'TG': 'Германия',
    'Heye': 'Германия',
    'Dorrenberg': 'Германия',
    'Thyssen': 'Германия',
    'Voestalpine': 'Австрия',
    'Assab': 'Швеция',
    'Aubert & Duval': 'Франция',
    'Finkl': 'США',
    'Kind & Co': 'Германия',
    'Grimax': 'Италия',
    'Lucefin': 'Италия',
    'Nachi-Fujikoshi': 'Япония',
    'Sanyo': 'Япония',
    'Nippon Koshuha': 'Япония',
    'Baosteel': 'Китай',
    'Dongbei': 'Китай',
    'Fushun': 'Китай',
    # Nickel alloy manufacturers
    'Special Metals': 'США',
    'Haynes International': 'США',
    'MONEL': 'США',
    'INCONEL': 'США',
    'INCOLOY': 'США',
    'Hastelloy': 'США',
    'Hastalloy': 'США',  # Typo variant
    'Nimonic': 'Великобритания',
}


def detect_standard_pattern(grade_name, link=None, manufacturer=None):
    """
    Определить тип стандарта по паттернам в названии марки

    Returns:
        dict: {
            'type': 'government' | 'proprietary' | 'unknown',
            'standard_prefix': str,
            'standard_number': str or None,
            'manufacturer': str or None,
            'country': str or None
        }
    """
    grade_upper = grade_name.upper()

    # Паттерны государственных стандартов
    gov_patterns = [
        (r'^(AISI)\s*(\d+[A-Z]*)', 'AISI'),
        (r'^(SAE)\s*(\d+)', 'SAE'),
        (r'^(ASTM)\s*([A-Z]*\d+)', 'ASTM'),
        (r'^(UNS)\s*([A-Z]\d+)', 'UNS'),
        (r'^([A-Z]\d{5})$', 'UNS'),  # UNS коды без префикса: N02200, N06625
        (r'^(GOST)\s*(\d+[-\d]*)', 'GOST'),
        (r'^(DIN)\s*([\d.]+)', 'DIN'),
        (r'^(\d\.\d{4})$', 'DIN'),  # Материальные номера DIN: 1.4539, 2.4816
        (r'^(EN)\s*([\d-]+)', 'EN'),
        (r'^(ISO)\s*([\d-]+)', 'ISO'),
        (r'^(JIS)\s*([A-Z]*\d+)', 'JIS'),
        (r'^(GB/?T?)\s*([\d-]+)', 'GB/T'),
        (r'^(BS)\s*(EN\s*)?([\d-]+)', 'BS'),
        (r'^(\d+[A-Z]\d+)$', 'AISI'),  # Например: 420, 304, 440C
        (r'^(Х\d+[А-Я\d]+)$', 'GOST'),  # Русские марки: Х12МФ, 95Х18
        (r'^(\d+Х\d+[А-Я\d]*)$', 'GOST'),  # 12Х18Н10Т
    ]

    # Проверка паттернов государственных стандартов
    for pattern, std_type in gov_patterns:
        match = re.match(pattern, grade_upper)
        if match:
            if std_type == 'BS' and match.group(2):  # BS EN
                return {
                    'type': 'government',
                    'standard_prefix': 'BS EN',
                    'standard_number': match.group(3),
                    'manufacturer': None,
                    'country': STANDARD_COUNTRIES.get('BS EN')
                }
            else:
                return {
                    'type': 'government',
                    'standard_prefix': std_type,
                    'standard_number': match.group(2) if len(match.groups()) > 1 else match.group(1),
                    'manufacturer': None,
                    'country': STANDARD_COUNTRIES.get(std_type)
                }

    # Проверка производителя из поля manufacturer или ссылки
    detected_manufacturer = None
    detected_country = None

    if manufacturer:
        for mfr, country in MANUFACTURER_COUNTRIES.items():
            if mfr.lower() in manufacturer.lower():
                detected_manufacturer = mfr
                detected_country = country
                break

    if not detected_manufacturer and link:
        # Попытка определить производителя из ссылки
        for mfr in MANUFACTURER_COUNTRIES.keys():
            if mfr.lower() in link.lower():
                detected_manufacturer = mfr
                detected_country = MANUFACTURER_COUNTRIES[mfr]
                break

    if detected_manufacturer:
        return {
            'type': 'proprietary',
            'standard_prefix': None,
            'standard_number': None,
            'manufacturer': detected_manufacturer,
            'country': detected_country
        }

    # Проверка по названию марки (может содержать название производителя)
    for mfr, country in MANUFACTURER_COUNTRIES.items():
        if mfr.lower() in grade_name.lower():
            return {
                'type': 'proprietary',
                'standard_prefix': None,
                'standard_number': None,
                'manufacturer': mfr,
                'country': country
            }

    return {
        'type': 'unknown',
        'standard_prefix': None,
        'standard_number': None,
        'manufacturer': None,
        'country': None
    }


def ask_ai_for_standard(grade_name, link=None, manufacturer=None):
    """
    Использовать AI для определения стандарта марки стали

    Returns:
        dict or None
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return None

    try:
        client = OpenAI(api_key=api_key)

        prompt = f"""Analyze this steel grade and determine its standard information:

Steel Grade: {grade_name}
Link: {link or 'N/A'}
Manufacturer: {manufacturer or 'N/A'}

Determine:
1. Is this a government standard (AISI, GOST, DIN, JIS, GB/T, BS, EN, ISO, etc.) or proprietary/manufacturer grade?
2. If government standard:
   - Standard name (e.g., AISI, GOST, DIN)
   - Standard number if applicable (e.g., "304" for AISI 304, "1050-88" for GOST 1050-88)
   - Country of the standard
3. If proprietary:
   - Manufacturer name
   - Country of manufacturer's headquarters

Return ONLY valid JSON in this format:
{{
    "type": "government" or "proprietary",
    "standard": "AISI" or "DIN" or manufacturer name,
    "number": "304" or "1.2379" or null,
    "country": "США" or "Германия" or "Швеция" etc. (in Russian)
}}

If uncertain, return {{"type": "unknown"}}
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a steel standards expert. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=200
        )

        content = response.choices[0].message.content.strip()

        # Извлечь JSON из ответа
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()

        result = json.loads(content)
        return result

    except Exception as e:
        print(f"[AI Error] {grade_name}: {e}")
        return None


def format_standard_value(detection_result, ai_result=None):
    """
    Форматировать значение для столбца Standard

    Format:
    - Государственный: "STANDARD NUMBER, Country" (e.g., "AISI 304, США")
    - Фирменный: "Manufacturer, Country" (e.g., "Bohler-Uddeholm, Австрия")
    """
    # Приоритет: detection_result, затем ai_result
    result = detection_result

    if result['type'] == 'unknown' and ai_result and ai_result.get('type') != 'unknown':
        # Использовать AI результат если паттерн не обнаружен
        if ai_result['type'] == 'government':
            result = {
                'type': 'government',
                'standard_prefix': ai_result.get('standard'),
                'standard_number': ai_result.get('number'),
                'manufacturer': None,
                'country': ai_result.get('country')
            }
        elif ai_result['type'] == 'proprietary':
            result = {
                'type': 'proprietary',
                'standard_prefix': None,
                'standard_number': None,
                'manufacturer': ai_result.get('standard'),
                'country': ai_result.get('country')
            }

    # Форматирование
    if result['type'] == 'government':
        std_name = result['standard_prefix']
        std_number = result['standard_number']
        country = result['country']

        if std_name and country:
            if std_number:
                return f"{std_name} {std_number}, {country}"
            else:
                return f"{std_name}, {country}"
        elif std_name:
            return std_name

    elif result['type'] == 'proprietary':
        mfr = result['manufacturer']
        country = result['country']

        if mfr and country:
            return f"{mfr}, {country}"
        elif mfr:
            return mfr

    return None


def fill_standards_with_ai(use_ai=True, batch_size=100):
    """
    Заполнить столбец standard для всех марок

    Args:
        use_ai: использовать AI для неопределенных марок
        batch_size: размер пакета для обработки (для экономии API запросов)
    """
    conn = get_connection()
    cursor = conn.cursor()

    print("="*70)
    print("ЗАПОЛНЕНИЕ СТОЛБЦА STANDARD С ИСПОЛЬЗОВАНИЕМ AI")
    print("="*70)

    try:
        # Получить все марки
        cursor.execute("""
            SELECT id, grade, link, manufacturer, standard
            FROM steel_grades
            ORDER BY id
        """)

        all_grades = cursor.fetchall()
        total_count = len(all_grades)

        print(f"\nВсего марок в БД: {total_count}")

        # Фильтровать марки без заполненного standard
        grades_to_process = [g for g in all_grades if not g[4] or g[4].strip() == '']
        print(f"Марок без заполненного standard: {len(grades_to_process)}")

        if len(grades_to_process) == 0:
            print("\n[INFO] Все марки уже имеют заполненный standard")
            return

        # Статистика
        updated_by_pattern = 0
        updated_by_ai = 0
        failed = 0

        print(f"\nНачало обработки (AI: {'включен' if use_ai else 'выключен'})...")
        print("-"*70)

        for i, (row_id, grade, link, manufacturer, current_standard) in enumerate(grades_to_process, 1):
            # Прогресс
            if i % 50 == 0:
                print(f"[{i}/{len(grades_to_process)}] Обработано марок...")

            # Определить по паттерну
            detection = detect_standard_pattern(grade, link, manufacturer)

            # Если не определено и AI включен
            ai_result = None
            if detection['type'] == 'unknown' and use_ai:
                ai_result = ask_ai_for_standard(grade, link, manufacturer)

            # Форматировать значение
            standard_value = format_standard_value(detection, ai_result)

            if standard_value:
                # Обновить БД
                cursor.execute(
                    "UPDATE steel_grades SET standard = ? WHERE id = ?",
                    (standard_value, row_id)
                )

                source = "паттерн" if detection['type'] != 'unknown' else "AI"
                print(f"[OK] {grade}: '{standard_value}' ({source})")

                if detection['type'] != 'unknown':
                    updated_by_pattern += 1
                else:
                    updated_by_ai += 1
            else:
                failed += 1
                if i <= 10 or i % 100 == 0:  # Показать только первые 10 и каждую 100-ю
                    print(f"[SKIP] {grade}: не удалось определить стандарт")

        print("\n" + "="*70)
        print("ИТОГИ:")
        print("="*70)
        print(f"Обработано марок:           {len(grades_to_process)}")
        print(f"Обновлено по паттернам:     {updated_by_pattern}")
        print(f"Обновлено через AI:         {updated_by_ai}")
        print(f"Не удалось определить:      {failed}")
        print(f"Всего обновлено:            {updated_by_pattern + updated_by_ai}")
        print("="*70)

        # Проверить общую статистику
        cursor.execute("""
            SELECT COUNT(*) FROM steel_grades
            WHERE standard IS NOT NULL AND standard != ''
        """)
        filled = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM steel_grades")
        total = cursor.fetchone()[0]

        print(f"\nОБЩАЯ СТАТИСТИКА:")
        print(f"Всего марок в БД:           {total}")
        print(f"С заполненным standard:     {filled} ({filled*100//total}%)")
        print(f"Без standard:               {total - filled} ({(total-filled)*100//total}%)")
        print("="*70)

        # Показать примеры обновленных записей
        print("\nПримеры обновленных записей:")
        cursor.execute("""
            SELECT grade, standard
            FROM steel_grades
            WHERE standard IS NOT NULL AND standard != ''
            ORDER BY RANDOM()
            LIMIT 20
        """)

        for grade, standard in cursor.fetchall():
            print(f"  {grade:30s} -> {standard}")

        response = input("\n\nСохранить изменения в БД? (yes/no): ")
        if response.lower() == 'yes':
            conn.commit()
            print("[OK] Изменения сохранены")
        else:
            conn.rollback()
            print("[ROLLBACK] Изменения отменены")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Fill standard column with AI assistance')
    parser.add_argument('--no-ai', action='store_true', help='Disable AI, use only pattern matching')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for processing')

    args = parser.parse_args()

    fill_standards_with_ai(use_ai=not args.no_ai, batch_size=args.batch_size)
