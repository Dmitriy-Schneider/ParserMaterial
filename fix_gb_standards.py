"""
Fix GB standards for grades starting with # (Chinese GB standards)
Also check for empty grades and rows without chemistry
"""
import sqlite3
from database_schema import get_connection

def fix_gb_standards():
    """Fix Standard for GB grades (starting with #)"""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Check and fix GB grades (starting with #)
    print("=" * 80)
    print("Проверка марок GB (начинающихся с #)")
    print("=" * 80)

    cursor.execute("""
        SELECT grade, standard, link
        FROM steel_grades
        WHERE grade LIKE '#%'
    """)
    gb_grades = cursor.fetchall()

    print(f"\nНайдено марок с #: {len(gb_grades)}")
    print("\nТекущие значения Standard:")
    for grade, standard, link in gb_grades[:5]:
        print(f"  {grade:10} -> {standard:40} | {link}")

    # Update to GB, Китай
    cursor.execute("""
        UPDATE steel_grades
        SET standard = 'GB, Китай'
        WHERE grade LIKE '#%'
    """)
    updated = cursor.rowcount
    conn.commit()
    print(f"\n[OK] Обновлено марок: {updated}")

    # 2. Check for empty grades
    print("\n" + "=" * 80)
    print("Проверка пустых марок")
    print("=" * 80)

    cursor.execute("""
        SELECT COUNT(*) FROM steel_grades
        WHERE grade IS NULL OR grade = ''
    """)
    empty_grades = cursor.fetchone()[0]
    print(f"Пустых марок (grade): {empty_grades}")

    if empty_grades > 0:
        cursor.execute("""
            SELECT id, link FROM steel_grades
            WHERE grade IS NULL OR grade = ''
            LIMIT 5
        """)
        print("Примеры:")
        for row in cursor.fetchall():
            print(f"  ID: {row[0]}, Link: {row[1]}")

    # 3. Check for grades without chemistry
    print("\n" + "=" * 80)
    print("Проверка марок без химического состава")
    print("=" * 80)

    cursor.execute("""
        SELECT COUNT(*) FROM steel_grades
        WHERE (grade IS NOT NULL AND grade != '')
        AND c IS NULL AND si IS NULL AND mn IS NULL
        AND cr IS NULL AND ni IS NULL AND s IS NULL
        AND p IS NULL AND cu IS NULL AND mo IS NULL
        AND v IS NULL AND w IS NULL AND co IS NULL
        AND nb IS NULL AND n IS NULL
    """)
    no_chem = cursor.fetchone()[0]
    print(f"Марок без химсостава: {no_chem}")

    if no_chem > 0:
        cursor.execute("""
            SELECT grade, link FROM steel_grades
            WHERE (grade IS NOT NULL AND grade != '')
            AND c IS NULL AND si IS NULL AND mn IS NULL
            AND cr IS NULL AND ni IS NULL
            LIMIT 10
        """)
        print("\nПримеры марок без химсостава:")
        for grade, link in cursor.fetchall():
            print(f"  {grade:20} | {link}")

    conn.close()

    print("\n" + "=" * 80)
    print("Готово!")
    print("=" * 80)

if __name__ == '__main__':
    fix_gb_standards()
