"""
Обновление поля standard с добавлением стран производителей
Для фирменных марок: standard = "Производитель, Страна"
"""
import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from database_schema import get_connection


# Маппинг производителей к странам
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
}


def update_standards():
    """Обновить поле standard с добавлением стран"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1. Обновить записи где есть manufacturer но нет standard
        cursor.execute("""
            SELECT id, grade, manufacturer
            FROM steel_grades
            WHERE manufacturer IS NOT NULL
              AND manufacturer != ''
              AND (standard IS NULL OR standard = '')
        """)

        rows = cursor.fetchall()
        print(f"Записей с manufacturer но без standard: {len(rows)}")

        updated_count = 0
        for row_id, grade, manufacturer in rows:
            # Найти страну производителя
            country = None
            for mfr, cnt in MANUFACTURER_COUNTRIES.items():
                if mfr.lower() in manufacturer.lower():
                    country = cnt
                    break

            if country:
                standard_value = f"{manufacturer}, {country}"
                cursor.execute(
                    "UPDATE steel_grades SET standard = ? WHERE id = ?",
                    (standard_value, row_id)
                )
                updated_count += 1
                print(f"[OK] {grade}: standard = \"{standard_value}\"")

        print(f"\nОбновлено записей: {updated_count}")

        # 2. Обновить записи где standard есть но не содержит страну
        cursor.execute("""
            SELECT id, grade, standard, manufacturer
            FROM steel_grades
            WHERE standard IS NOT NULL
              AND standard != ''
              AND standard NOT LIKE '%,%'
              AND manufacturer IS NOT NULL
        """)

        rows = cursor.fetchall()
        print(f"\nЗаписей со standard без страны: {len(rows)}")

        updated_count2 = 0
        for row_id, grade, standard, manufacturer in rows:
            # Найти страну
            country = None

            # Попробовать из manufacturer
            for mfr, cnt in MANUFACTURER_COUNTRIES.items():
                if mfr.lower() in (manufacturer or '').lower():
                    country = cnt
                    break

            # Попробовать из standard
            if not country:
                for mfr, cnt in MANUFACTURER_COUNTRIES.items():
                    if mfr.lower() in standard.lower():
                        country = cnt
                        break

            if country and ',' not in standard:
                # Проверить, не является ли это государственным стандартом
                if not any(std in standard.upper() for std in ['AISI', 'GOST', 'DIN', 'JIS', 'GB/T', 'BS', 'EN', 'ISO', 'ASTM']):
                    standard_value = f"{standard}, {country}"
                    cursor.execute(
                        "UPDATE steel_grades SET standard = ? WHERE id = ?",
                        (standard_value, row_id)
                    )
                    updated_count2 += 1
                    print(f"[OK] {grade}: standard = \"{standard}\" -> \"{standard_value}\"")

        print(f"\nОбновлено записей (добавлена страна): {updated_count2}")

        # Статистика
        cursor.execute("""
            SELECT COUNT(*) FROM steel_grades
            WHERE standard IS NOT NULL AND standard != ''
        """)
        filled = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM steel_grades")
        total = cursor.fetchone()[0]

        print(f"\n{'='*60}")
        print(f"ИТОГОВАЯ СТАТИСТИКА:")
        print(f"Всего записей: {total}")
        print(f"С заполненным standard: {filled} ({filled*100//total}%)")
        print(f"Обновлено: {updated_count + updated_count2}")
        print(f"{'='*60}")

        response = input("\nСохранить изменения? (yes/no): ")
        if response.lower() == 'yes':
            conn.commit()
            print("[OK] Изменения сохранены")
        else:
            conn.rollback()
            print("[ROLLBACK] Изменения отменены")

    except Exception as e:
        print(f"[ERROR] {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    update_standards()
