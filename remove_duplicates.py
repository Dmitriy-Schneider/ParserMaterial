#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Remove duplicate steel grades from database"""
import sqlite3
import sys
import io
from database.backup_manager import backup_before_modification

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def remove_duplicates(dry_run=True):
    """Remove duplicates keeping only the best entry for each grade"""

    print("Creating backup before removing duplicates...")
    backup_before_modification(reason="remove_duplicates")

    conn = sqlite3.connect('database/steel_database.db')
    cursor = conn.cursor()

    # Find grades with duplicates
    cursor.execute("""
        SELECT grade, COUNT(*) as count
        FROM steel_grades
        GROUP BY grade
        HAVING COUNT(*) > 1
        ORDER BY grade
    """)

    duplicates = cursor.fetchall()
    print(f"\nFound {len(duplicates)} grades with duplicates")
    print("=" * 100)

    ids_to_delete = []

    for grade_name, count in duplicates:
        # Get all instances of this grade, ordered by priority:
        # 1. Has link (link IS NOT NULL AND link != '')
        # 2. Does NOT have "zknives.com" in Other
        # 3. Lowest ID (first created)
        cursor.execute("""
            SELECT id, grade, link, other
            FROM steel_grades
            WHERE grade = ?
            ORDER BY
                CASE WHEN link IS NOT NULL AND link != '' THEN 0 ELSE 1 END,
                CASE WHEN other LIKE '%zknives.com%' THEN 1 ELSE 0 END,
                id
        """, (grade_name,))

        instances = cursor.fetchall()
        keep_id = instances[0][0]

        print(f"\n{grade_name} ({count} duplicates):")
        print(f"  KEEP:   ID={keep_id}")

        for instance in instances[1:]:
            ids_to_delete.append(instance[0])
            print(f"  DELETE: ID={instance[0]}")

    print("\n" + "=" * 100)
    print(f"Total records to delete: {len(ids_to_delete)}")
    print(f"Database will shrink from {10702} to {10702 - len(ids_to_delete)} grades")

    if dry_run:
        print("\n[DRY RUN] No changes made. Run with dry_run=False to delete.")
        conn.close()
        return len(ids_to_delete)

    # Delete duplicates
    print("\nDeleting duplicates...")
    for id_to_delete in ids_to_delete:
        cursor.execute("DELETE FROM steel_grades WHERE id = ?", (id_to_delete,))

    conn.commit()

    # Verify
    cursor.execute("SELECT COUNT(*) FROM steel_grades")
    final_count = cursor.fetchone()[0]

    print(f"\n[SUCCESS] Deleted {len(ids_to_delete)} duplicate records")
    print(f"Final database size: {final_count} grades")

    conn.close()
    return len(ids_to_delete)

if __name__ == "__main__":
    # First run as dry-run
    dry_run = "--execute" not in sys.argv

    if dry_run:
        print("Running in DRY RUN mode. Add --execute flag to actually delete records.\n")

    remove_duplicates(dry_run=dry_run)
