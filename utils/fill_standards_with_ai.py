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
    'TG': 'Китай',
    'Heye': 'Китай',
    'Dorrenberg': 'Германия',
    'Thyssen': 'Германия',
    'Buderus': 'Германия',
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

STANDARD_PREFIX_ALIASES = {
    'GOST-R': 'GOST R',
    'GOSTR': 'GOST R',
    'BSEN': 'BS EN',
    'BS-EN': 'BS EN',
    'GB/T': 'GB/T',
    'GBT': 'GB/T',
}

COUNTRY_ALIASES = {
    'us': 'США',
    'usa': 'США',
    'u.s.': 'США',
    'u.s.a.': 'США',
    'united states': 'США',
    'united states of america': 'США',
    'russia': 'Россия',
    'russian federation': 'Россия',
    'ussr': 'Россия/СССР',
    'soviet union': 'Россия/СССР',
    'germany': 'Германия',
    'deutschland': 'Германия',
    'japan': 'Япония',
    'china': 'Китай',
    'france': 'Франция',
    'austria': 'Австрия',
    'sweden': 'Швеция',
    'slovenia': 'Словения',
    'spain': 'Испания',
    'switzerland': 'Швейцария',
    'italy': 'Италия',
    'poland': 'Польша',
    'czech republic': 'Чехия',
    'czechia': 'Чехия',
    'korea': 'Корея',
    'south korea': 'Корея',
    'uk': 'Великобритания',
    'united kingdom': 'Великобритания',
    'great britain': 'Великобритания',
    'england': 'Великобритания',
    'europe': 'Европа',
    'eu': 'Европа',
    'international': 'Международный',
    'world': 'Международный',
    'south africa': 'ЮАР',
}

KNOWN_COUNTRIES = set(STANDARD_COUNTRIES.values()) | set(MANUFACTURER_COUNTRIES.values()) | {
    'Швейцария',
    'Испания',
    'Словения',
    'Италия',
    'ЮАР',
    'Корея',
    'Польша',
    'Чехия',
    'Великобритания',
    'Международный',
    'Европа',
    'Россия/СССР',
}

STANDARD_NUMBER_PATTERNS = {
    'AISI': re.compile(r'^(?:\d{2,4}[A-Z]?|[A-Z]\d{1,2})$'),
    'SAE': re.compile(r'^\d{4}[A-Z]?$'),
    'ASTM': re.compile(r'^[A-Z]*\d+[A-Z]?(?:-\d+)?$'),
    'UNS': re.compile(r'^[A-Z]\d{5}$'),
    'GOST': re.compile(r'(?=.*\d)[0-9A-ZА-Я-]+$'),
    'GOST R': re.compile(r'(?=.*\d)[0-9A-ZА-Я-]+$'),
    'TU': re.compile(r'(?=.*\d)[0-9A-ZА-Я-]+$'),
    'DIN': re.compile(r'^(?:\d\.\d{4}(?:\.\d+)?|X\d+[A-Z0-9]+)$'),
    'EN': re.compile(r'^[\d-]+$'),
    'ISO': re.compile(r'^(?:[\d-]+|HS\d+[-\d]*)$'),
    'JIS': re.compile(r'^[A-Z]{1,4}\d{1,3}[A-Z]?$'),
    'GB': re.compile(r'^[\d-]+$'),
    'GB/T': re.compile(r'^[\d-]+$'),
    'BS': re.compile(r'^[\d-]+$'),
    'BS EN': re.compile(r'^[\d-]+$'),
    'AFNOR': re.compile(r'^[A-Z0-9-]+$'),
    'NF': re.compile(r'^[A-Z0-9-]+$'),
    'UNI': re.compile(r'^[A-Z0-9-]+$'),
    'SIS': re.compile(r'^[A-Z0-9-]+$'),
    'SS': re.compile(r'^[A-Z0-9-]+$'),
    'PN': re.compile(r'^[A-Z0-9-]+$'),
    'CSN': re.compile(r'^[A-Z0-9-]+$'),
    'KS': re.compile(r'^[A-Z0-9-]+$'),
    'AS': re.compile(r'^[A-Z0-9-]+$'),
    'SABS': re.compile(r'^[A-Z0-9-]+$'),
}

INVALID_MANUFACTURER_NAMES = {
    'steel',
    'standard',
    'alloy',
    'unknown',
    'none',
    'n/a',
    'zknives',
    'z knives',
}


def normalize_country(country):
    if not country:
        return None

    value = str(country).strip()
    if not value:
        return None

    if value in KNOWN_COUNTRIES:
        return value

    value_lower = value.lower().strip()
    if value_lower in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[value_lower]

    return None


def normalize_standard_prefix(prefix):
    if not prefix:
        return None

    value = str(prefix).strip().upper()
    value = value.replace('.', '').replace('_', ' ')
    value = ' '.join(value.split())

    if value in STANDARD_PREFIX_ALIASES:
        return STANDARD_PREFIX_ALIASES[value]

    return value


def normalize_manufacturer(name):
    if not name:
        return None

    value = str(name).strip()
    if not value:
        return None

    for mfr in MANUFACTURER_COUNTRIES:
        if mfr.lower() == value.lower():
            return mfr

    return value


def is_valid_standard_number(prefix, number):
    if not number:
        return False

    pattern = STANDARD_NUMBER_PATTERNS.get(prefix)
    if not pattern:
        return True

    return bool(pattern.match(str(number).strip()))


def is_valid_government_result(prefix, number):
    if not prefix or not number:
        return False

    if prefix not in STANDARD_COUNTRIES:
        return False

    if not is_valid_standard_number(prefix, number):
        return False

    return True


def is_valid_proprietary_result(name, country, grade=None, link=None, manufacturer=None):
    if not name:
        return False, None, None

    normalized_name = normalize_manufacturer(name)
    if not normalized_name:
        return False, None, None

    if normalized_name.lower() in INVALID_MANUFACTURER_NAMES:
        return False, None, None

    if len(normalized_name) < 3:
        return False, None, None

    if normalized_name in MANUFACTURER_COUNTRIES:
        return True, normalized_name, MANUFACTURER_COUNTRIES[normalized_name]

    def contains_name(text):
        return bool(text) and normalized_name.lower() in str(text).lower()

    if contains_name(manufacturer) or contains_name(link) or contains_name(grade):
        normalized_country = normalize_country(country)
        if normalized_country:
            return True, normalized_name, normalized_country

    return False, normalized_name, None

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

    # Специальные паттерны, где нужно сохранить префикс в номере
    match = re.match(r'^M(\d+)$', grade_upper)
    if match:
        return {
            'type': 'government',
            'standard_prefix': 'AISI',
            'standard_number': f"M{match.group(1)}",
            'manufacturer': None,
            'country': STANDARD_COUNTRIES.get('AISI')
        }

    match = re.match(r'^([ADHSWOTL])(\d{1,2})$', grade_upper)
    if match:
        series = match.group(1)
        number = match.group(2)
        return {
            'type': 'government',
            'standard_prefix': 'AISI',
            'standard_number': f"{series}{number}",
            'manufacturer': None,
            'country': STANDARD_COUNTRIES.get('AISI')
        }

    match = re.match(r'^SKH[-\s]?(\d+)$', grade_upper)
    if match:
        return {
            'type': 'government',
            'standard_prefix': 'JIS',
            'standard_number': f"SKH{match.group(1)}",
            'manufacturer': None,
            'country': STANDARD_COUNTRIES.get('JIS')
        }

    match = re.match(r'^HS(\d+[-\d]*)$', grade_upper)
    if match:
        return {
            'type': 'government',
            'standard_prefix': 'ISO',
            'standard_number': f"HS{match.group(1)}",
            'manufacturer': None,
            'country': STANDARD_COUNTRIES.get('ISO')
        }

    match = re.match(r'^K(\d+)$', grade_upper)
    if match:
        return {
            'type': 'proprietary',
            'standard_prefix': None,
            'standard_number': None,
            'manufacturer': 'Bohler',
            'country': 'Австрия'
        }

    match = re.match(r'^NICKEL\s*(\d{3})$', grade_upper)
    if match:
        nickel_number = match.group(1)
        nickel_uns_map = {
            '200': 'N02200',
            '201': 'N02201'
        }
        uns_code = nickel_uns_map.get(nickel_number)
        if uns_code:
            return {
                'type': 'government',
                'standard_prefix': 'UNS',
                'standard_number': uns_code,
                'manufacturer': None,
                'country': STANDARD_COUNTRIES.get('UNS')
            }

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
        (r'^X\d+[A-Za-z]+\d*$', 'DIN'),  # X-series DIN: X100CrMoV5, X210Cr12, etc.
        (r'^[РP]\d+[МMА-ЯA-Z\d]*$', 'GOST'),  # Р-series GOST: Р6М5, Р18, P6M5, etc.
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
                standard_prefix = std_type
                if std_type == 'GB/T':
                    standard_prefix = match.group(1)

                if std_type == 'BS':
                    standard_number = match.group(3)
                elif len(match.groups()) >= 2:
                    standard_number = match.group(2)
                elif len(match.groups()) == 1:
                    standard_number = match.group(1)
                else:
                    standard_number = grade_upper

                return {
                    'type': 'government',
                    'standard_prefix': standard_prefix,
                    'standard_number': standard_number,
                    'manufacturer': None,
                    'country': STANDARD_COUNTRIES.get(standard_prefix)
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
        # Специальная обработка для CPM → Crucible (CPM)
        if detected_manufacturer == 'CPM':
            detected_manufacturer = 'Crucible (CPM)'

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
            # Специальная обработка для CPM → Crucible (CPM)
            final_mfr = 'Crucible (CPM)' if mfr == 'CPM' else mfr

            return {
                'type': 'proprietary',
                'standard_prefix': None,
                'standard_number': None,
                'manufacturer': final_mfr,
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
Link: {link or 'None'}
Manufacturer: {manufacturer or 'None'}

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

IMPORTANT:
- NEVER return "N/A", "unknown", "Н/А", "Неподтверждено", "None", "нет данных", "не указано", "неизвестно", or source-site names like "ZKnives"
- Allowed government standard prefixes: AISI, SAE, ASTM, UNS, GOST, GOST R, TU, DIN, EN, ISO, JIS, GB, GB/T, BS, BS EN, AFNOR, NF, UNI, SIS, SS, PN, CSN, KS, AS, SABS
- Do NOT guess a manufacturer unless it appears in the Manufacturer field, the Link, or the Steel Grade name
- Do NOT return the steel grade itself as the standard unless it is a recognized government format
- If you cannot determine the standard with confidence, return {{"type": "unknown"}}
- Only return specific, verifiable standard names and countries
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


def format_standard_value(detection_result, ai_result=None, grade=None, link=None, manufacturer=None):
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
            ai_standard = normalize_standard_prefix(ai_result.get('standard'))
            result = {
                'type': 'government',
                'standard_prefix': ai_standard,
                'standard_number': ai_result.get('number'),
                'manufacturer': None,
                'country': None
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
    standard_value = None

    if result['type'] == 'government':
        std_name = normalize_standard_prefix(result['standard_prefix'])
        std_number = result['standard_number']

        if std_name and is_valid_government_result(std_name, std_number):
            country = STANDARD_COUNTRIES.get(std_name)
            if std_number:
                standard_value = f"{std_name} {std_number}, {country}"
            else:
                standard_value = f"{std_name}, {country}"

    elif result['type'] == 'proprietary':
        is_valid, mfr, country = is_valid_proprietary_result(
            result['manufacturer'],
            result['country'],
            grade=grade,
            link=link,
            manufacturer=manufacturer
        )

        if is_valid and mfr and country:
            standard_value = f"{mfr}, {country}"

    # Валидация: отклонить значения с N/A
    if standard_value:
        normalized_value = standard_value.lower()
        invalid_patterns = [
            'n/a',
            'unknown',
            'none',
            'null',
            'zknives',
            'z knives',
            'н/а',
            'неподтверждено',
            'нет данных',
            'не указано',
            'неизвестно'
        ]
        for invalid in invalid_patterns:
            if invalid in normalized_value:
                return None

    return standard_value


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
            standard_value = format_standard_value(
                detection,
                ai_result,
                grade=grade,
                link=link,
                manufacturer=manufacturer
            )

            if standard_value:
                # Обновить БД
                cursor.execute(
                    "UPDATE steel_grades SET standard = ? WHERE id = ?",
                    (standard_value, row_id)
                )

                source = "паттерн" if detection['type'] != 'unknown' else "AI"
                # Безопасный вывод Unicode для Windows console
                safe_grade = grade.encode('cp1251', errors='replace').decode('cp1251')
                safe_value = standard_value.encode('cp1251', errors='replace').decode('cp1251')
                print(f"[OK] {safe_grade}: '{safe_value}' ({source})")

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

        # Auto-save if running in non-interactive mode
        import sys
        if sys.stdin.isatty():
            response = input("\n\nСохранить изменения в БД? (yes/no): ")
            if response.lower() == 'yes':
                conn.commit()
                print("[OK] Изменения сохранены")
            else:
                conn.rollback()
                print("[ROLLBACK] Изменения отменены")
        else:
            # Non-interactive mode - auto commit
            conn.commit()
            print("[AUTO-COMMIT] Изменения автоматически сохранены")

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
