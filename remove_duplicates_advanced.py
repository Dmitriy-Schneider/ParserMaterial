#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Remove duplicates from steel_grades table
Priority: link > element_count > lower_id
Also move 'Бал.' from element columns to Other
"""
import sqlite3
import sys
import io
from database.backup_manager import backup_before_modification

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def count_filled_elements(row):
    """Count how many element columns have numeric values (not None, not empty, not 'Бал.')"""
    elements_indices = range(2, 15)  # c, cr, ni, mo, v, w, co, mn, si, cu, nb, n, s, p (indices 2-15)
    count = 0
    for i in elements_indices:
        val = row[i]
        if val and val not in ['', 'Бал.', 'N/A', 'null', '0', '0.00']:
            count += 1
    return count

def move_bal_to_other(dry_run=True):
    """Move 'Бал.' from element columns to Other column"""

    conn = sqlite3.connect('database/steel_database.db')
    cursor = conn.cursor()

    # Find all records with 'Бал.' in element columns
    elements = ['c', 'cr', 'ni', 'mo', 'v', 'w', 'co', 'mn', 'si', 'cu', 'nb', 'n', 's', 'p']
    conditions = ' OR '.join([f"{elem} LIKE '%Бал.%'" for elem in elements])

    cursor.execute(f"""
        SELECT id, grade, c, cr, ni, mo, v, w, co, mn, si, cu, nb, n, s, p, other
        FROM steel_grades
        WHERE {conditions}
    """)

    records = cursor.fetchall()
    print(f"\n=== Перемещение 'Бал.' в Other ===")
    print(f"Найдено записей с 'Бал.': {len(records)}\n")

    updates = []
    for row in records:
        id_val, grade = row[0], row[1]
        current_other = row[-1] or ''

        # Find which element has 'Бал.'
        bal_elements = []
        new_element_values = {}

        for i, elem in enumerate(elements, start=2):
            if row[i] and 'Бал.' in str(row[i]):
                bal_elements.append(elem.upper())
                new_element_values[elem] = None  # Set to NULL

        if bal_elements:
            # Create Other text
            bal_text = ', '.join([f'{elem} - basis' for elem in bal_elements])

            # Combine with existing Other
            if current_other and current_other not in ['', '-', 'N/A']:
                new_other = f"{current_other}; {bal_text}"
            else:
                new_other = bal_text

            updates.append({
                'id': id_val,
                'grade': grade,
                'elements': bal_elements,
                'new_other': new_other,
                'element_updates': new_element_values
            })

            print(f"ID={id_val:5d} {grade}")
            print(f"  Элементы с 'Бал.': {', '.join(bal_elements)}")
            print(f"  Новый Other: {new_other}")

    if not dry_run and updates:
        print(f"\nПрименение изменений...")
        for update in updates:
            # Update Other column
            cursor.execute(
                "UPDATE steel_grades SET other = ? WHERE id = ?",
                (update['new_other'], update['id'])
            )

            # Set element columns to NULL
            for elem, value in update['element_updates'].items():
                cursor.execute(
                    f"UPDATE steel_grades SET {elem} = ? WHERE id = ?",
                    (value, update['id'])
                )

        conn.commit()
        print(f"[SUCCESS] Обновлено {len(updates)} записей")
    elif dry_run:
        print(f"\n[DRY RUN] Изменения не применены")

    conn.close()
    return len(updates)

def remove_duplicates(dry_run=True):
    """Remove duplicate steel grades, keeping the best one"""

    conn = sqlite3.connect('database/steel_database.db')
    cursor = conn.cursor()

    # Find all grades with duplicates
    cursor.execute("""
        SELECT grade, COUNT(*) as count
        FROM steel_grades
        GROUP BY grade
        HAVING COUNT(*) > 1
        ORDER BY grade
    """)

    duplicate_grades = cursor.fetchall()

    print(f"\n=== Удаление дубликатов ===")
    print(f"Найдено марок с дубликатами: {len(duplicate_grades)}\n")

    ids_to_delete = []

    for grade_name, count in duplicate_grades:
        # Get all records for this grade
        # Columns: id, grade, c, cr, ni, mo, v, w, co, mn, si, cu, nb, n, s, p, link
        cursor.execute("""
            SELECT id, grade, c, cr, ni, mo, v, w, co, mn, si, cu, nb, n, s, p, link
            FROM steel_grades
            WHERE grade = ?
            ORDER BY id
        """, (grade_name,))

        records = cursor.fetchall()

        if len(records) < 2:
            continue

        # Score each record
        scored_records = []
        for record in records:
            id_val = record[0]
            has_link = 1 if (record[-1] and record[-1] != '') else 0
            element_count = count_filled_elements(record)

            # Priority: link (1000 points) > element_count (10 points each) > lower id (1 point)
            score = has_link * 1000 + element_count * 10 + (1 / (id_val + 1))

            scored_records.append((score, record))

        # Sort by score (descending)
        scored_records.sort(key=lambda x: x[0], reverse=True)

        # Keep the best one (highest score)
        best_record = scored_records[0][1]
        best_id = best_record[0]

        # Mark others for deletion
        print(f"Grade: {grade_name} ({count} записей)")
        print(f"  KEEP:   ID={best_id:5d} Elements={count_filled_elements(best_record):2d} Link={'YES' if best_record[-1] else 'NO '}")

        for score, record in scored_records[1:]:
            delete_id = record[0]
            ids_to_delete.append(delete_id)
            print(f"  DELETE: ID={delete_id:5d} Elements={count_filled_elements(record):2d} Link={'YES' if record[-1] else 'NO '}")
        print()

    print(f"Итого записей к удалению: {len(ids_to_delete)}")

    if not dry_run and ids_to_delete:
        print(f"\nУдаление дубликатов...")
        for id_val in ids_to_delete:
            cursor.execute("DELETE FROM steel_grades WHERE id = ?", (id_val,))

        conn.commit()

        # Final stats
        cursor.execute("SELECT COUNT(*) FROM steel_grades")
        final_count = cursor.fetchone()[0]

        print(f"\n[SUCCESS] Удалено {len(ids_to_delete)} дубликатов")
        print(f"Итоговое количество записей: {final_count}")
    elif dry_run:
        print(f"\n[DRY RUN] Изменения не применены")

    conn.close()
    return len(ids_to_delete)

if __name__ == "__main__":
    dry_run = "--execute" not in sys.argv

    if dry_run:
        print("=" * 100)
        print("РЕЖИМ ПРЕДПРОСМОТРА (DRY RUN)")
        print("Добавьте флаг --execute для применения изменений")
        print("=" * 100)
    else:
        print("=" * 100)
        print("РЕЖИМ ВЫПОЛНЕНИЯ")
        print("=" * 100)
        backup_before_modification(reason="remove_duplicates_advanced")

    # Step 1: Move 'Бал.' to Other
    moved_count = move_bal_to_other(dry_run)

    # Step 2: Remove duplicates
    deleted_count = remove_duplicates(dry_run)

    print("\n" + "=" * 100)
    print("ИТОГИ")
    print("=" * 100)
    print(f"Перемещено 'Бал.' в Other: {moved_count}")
    print(f"Удалено дубликатов: {deleted_count}")

    if dry_run:
        print("\n[INFO] Это был предпросмотр. Запустите с --execute для применения изменений.")
