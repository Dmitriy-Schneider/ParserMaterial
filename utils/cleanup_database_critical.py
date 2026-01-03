"""
Критическая очистка БД от некорректных записей
1. Удаление записей с множественными марками в Grade
2. Удаление дубликатов (приоритет zknives.com)
3. Очистка записей GOST/TU без ссылок
"""
import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from database_schema import get_connection


def cleanup_multigrade_records(cursor):
    """Удалить записи с множественными марками в Grade"""
    print("\n[1/4] Поиск записей с множественными марками в Grade...")

    # Найти записи с разделителями в Grade
    cursor.execute("""
        SELECT id, grade, standard, link
        FROM steel_grades
        WHERE grade LIKE '%*%'
           OR grade LIKE '%
%'
           OR grade LIKE '%|%'
           OR (grade LIKE '% %' AND length(grade) - length(replace(grade, ' ', '')) > 2)
        ORDER BY id
    """)

    multigrade_records = cursor.fetchall()
    print(f"Найдено записей с множественными марками: {len(multigrade_records)}")

    if multigrade_records:
        print("\nПримеры:")
        for rec in multigrade_records[:5]:
            grade_short = rec[1][:60].replace('\n', '\\n')
            print(f"  ID {rec[0]}: {grade_short}... (Std: {rec[2]})")

        response = input(f"\nУдалить {len(multigrade_records)} записей? (yes/no): ")
        if response.lower() == 'yes':
            ids_to_delete = [rec[0] for rec in multigrade_records]
            cursor.execute(f"""
                DELETE FROM steel_grades
                WHERE id IN ({','.join('?' * len(ids_to_delete))})
            """, ids_to_delete)
            print(f"[OK] Удалено {len(multigrade_records)} записей с множественными марками")
            return len(multigrade_records)
        else:
            print("[SKIP] Пропущено")
            return 0
    else:
        print("[OK] Записей с множественными марками не найдено")
        return 0


def cleanup_gost_tu_without_links(cursor):
    """Удалить записи GOST/TU без ссылок (импортированные некорректно)"""
    print("\n[2/4] Поиск записей GOST/TU без ссылок...")

    cursor.execute("""
        SELECT COUNT(*)
        FROM steel_grades
        WHERE standard = 'GOST/TU'
          AND (link IS NULL OR link = '')
    """)

    count = cursor.fetchone()[0]
    print(f"Найдено записей GOST/TU без ссылок: {count}")

    if count > 0:
        # Показать примеры
        cursor.execute("""
            SELECT id, grade, standard
            FROM steel_grades
            WHERE standard = 'GOST/TU'
              AND (link IS NULL OR link = '')
            LIMIT 5
        """)

        print("\nПримеры:")
        for rec in cursor.fetchall():
            grade_short = rec[1][:60] if len(rec[1]) <= 60 else rec[1][:60] + '...'
            print(f"  ID {rec[0]}: {grade_short}")

        response = input(f"\nУдалить {count} записей GOST/TU без ссылок? (yes/no): ")
        if response.lower() == 'yes':
            cursor.execute("""
                DELETE FROM steel_grades
                WHERE standard = 'GOST/TU'
                  AND (link IS NULL OR link = '')
            """)
            print(f"[OK] Удалено {count} записей GOST/TU без ссылок")
            return count
        else:
            print("[SKIP] Пропущено")
            return 0
    else:
        print("[OK] Записей GOST/TU без ссылок не найдено")
        return 0


def cleanup_duplicates(cursor):
    """Удалить дубликаты (приоритет zknives.com)"""
    print("\n[3/4] Поиск дубликатов...")

    # Найти дубликаты по grade (case-insensitive)
    cursor.execute("""
        SELECT LOWER(grade) as grade_lower, COUNT(*) as cnt
        FROM steel_grades
        GROUP BY grade_lower
        HAVING cnt > 1
        ORDER BY cnt DESC
    """)

    duplicates = cursor.fetchall()
    print(f"Найдено марок с дубликатами: {len(duplicates)}")

    if not duplicates:
        print("[OK] Дубликатов не найдено")
        return 0

    print("\nТоп-10 дубликатов:")
    for dup in duplicates[:10]:
        print(f"  {dup[0]}: {dup[1]} записей")

    response = input(f"\nНачать удаление дубликатов? (yes/no): ")
    if response.lower() != 'yes':
        print("[SKIP] Пропущено")
        return 0

    deleted_total = 0

    for grade_lower, count in duplicates:
        # Получить все записи с этой маркой
        cursor.execute("""
            SELECT id, grade, link, standard,
                   c, cr, mo, v, w, co, ni, mn, si, s, p, cu, nb, n
            FROM steel_grades
            WHERE LOWER(grade) = ?
            ORDER BY
                CASE
                    WHEN link LIKE '%zknives.com%' THEN 1
                    WHEN link IS NOT NULL THEN 2
                    ELSE 3
                END,
                id
        """, (grade_lower,))

        records = cursor.fetchall()

        # Оставить первую (с наивысшим приоритетом)
        keep_record = records[0]
        delete_records = records[1:]

        print(f"\n{grade_lower}: оставляем ID {keep_record[0]} (link: {keep_record[2][:40] if keep_record[2] else 'None'})")

        for rec in delete_records:
            print(f"  Удаляем ID {rec[0]} (link: {rec[2][:40] if rec[2] else 'None'})")
            cursor.execute("DELETE FROM steel_grades WHERE id = ?", (rec[0],))
            deleted_total += 1

    print(f"\n[OK] Удалено дубликатов: {deleted_total}")
    return deleted_total


def check_standard_column(cursor):
    """Проверить столбец standard"""
    print("\n[4/4] Проверка столбца standard...")

    # Проверить наличие столбца
    cursor.execute("PRAGMA table_info(steel_grades)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'standard' not in columns:
        print("[ERROR] Столбец 'standard' не найден!")
        return

    print("[OK] Столбец 'standard' существует")

    # Статистика заполненности
    cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE standard IS NOT NULL AND standard != ''")
    filled = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE standard IS NULL OR standard = ''")
    empty = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM steel_grades")
    total = cursor.fetchone()[0]

    print(f"\nСтатистика столбца 'standard':")
    print(f"  Заполнено: {filled} ({filled*100//total if total else 0}%)")
    print(f"  Пусто: {empty} ({empty*100//total if total else 0}%)")
    print(f"  Всего: {total}")

    # Топ стандартов
    cursor.execute("""
        SELECT standard, COUNT(*) as cnt
        FROM steel_grades
        WHERE standard IS NOT NULL AND standard != ''
        GROUP BY standard
        ORDER BY cnt DESC
        LIMIT 10
    """)

    print("\nТоп-10 стандартов:")
    for std, cnt in cursor.fetchall():
        print(f"  {std}: {cnt} марок")


def main():
    """Главная функция очистки БД"""
    print("="*60)
    print("КРИТИЧЕСКАЯ ОЧИСТКА БАЗЫ ДАННЫХ")
    print("="*60)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Статистика ДО
        cursor.execute("SELECT COUNT(*) FROM steel_grades")
        total_before = cursor.fetchone()[0]
        print(f"\nВсего записей ДО очистки: {total_before}")

        # Выполнить очистку
        deleted_multigrade = cleanup_multigrade_records(cursor)
        deleted_gost_tu = cleanup_gost_tu_without_links(cursor)
        deleted_duplicates = cleanup_duplicates(cursor)
        check_standard_column(cursor)

        # Статистика ПОСЛЕ
        cursor.execute("SELECT COUNT(*) FROM steel_grades")
        total_after = cursor.fetchone()[0]

        total_deleted = deleted_multigrade + deleted_gost_tu + deleted_duplicates

        print("\n" + "="*60)
        print("ИТОГИ ОЧИСТКИ:")
        print("="*60)
        print(f"Записей ДО:                    {total_before}")
        print(f"Удалено множественных марок:   {deleted_multigrade}")
        print(f"Удалено GOST/TU без ссылок:    {deleted_gost_tu}")
        print(f"Удалено дубликатов:            {deleted_duplicates}")
        print(f"Всего удалено:                 {total_deleted}")
        print(f"Записей ПОСЛЕ:                 {total_after}")
        print("="*60)

        if total_deleted > 0:
            response = input("\nСохранить изменения в БД? (yes/no): ")
            if response.lower() == 'yes':
                conn.commit()
                print("[OK] Изменения сохранены")
            else:
                conn.rollback()
                print("[ROLLBACK] Изменения отменены")
        else:
            print("\n[OK] Изменений не было")

    except Exception as e:
        print(f"\n[ERROR] Ошибка: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
