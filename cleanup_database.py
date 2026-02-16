#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cleanup database: remove special symbols, duplicates, and problematic records"""
import sqlite3
import sys
import io
from database.backup_manager import backup_before_modification

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def cleanup_database(dry_run=True):
    """Perform all cleanup operations"""

    if not dry_run:
        print("Creating backup before cleanup...")
        backup_before_modification(reason="database_cleanup")

    conn = sqlite3.connect('database/steel_database.db')
    cursor = conn.cursor()

    print("=" * 100)
    print("DATABASE CLEANUP ANALYSIS")
    print("=" * 100)

    # 1. Check Other column for "—" symbol
    print("\n1. Checking 'Other' column for '—' symbol...")
    cursor.execute("""
        SELECT id, grade, other
        FROM steel_grades
        WHERE other = '—' OR other = '-'
    """)
    other_dash_records = cursor.fetchall()
    print(f"   Found {len(other_dash_records)} records with only '—' or '-' in Other")
    for record in other_dash_records[:5]:
        print(f"   ID={record[0]:5d} Grade=\"{record[1]}\" Other=\"{record[2]}\"")
    if len(other_dash_records) > 5:
        print(f"   ... and {len(other_dash_records)-5} more")

    # 2. Check grades with ~ symbol
    print("\n2. Checking grades with '~' symbol...")
    cursor.execute("""
        SELECT id, grade, standard
        FROM steel_grades
        WHERE grade LIKE '%~%'
    """)
    tilde_records = cursor.fetchall()
    print(f"   Found {len(tilde_records)} grades with '~'")
    for record in tilde_records[:10]:
        print(f"   ID={record[0]:5d} Grade=\"{record[1]}\" Standard=\"{record[2][:40] if record[2] else 'NULL'}\"")
    if len(tilde_records) > 10:
        print(f"   ... and {len(tilde_records)-10} more")

    # 3. Check grades with zknives.com in Standard
    print("\n3. Checking grades with 'zknives.com' in Standard...")
    cursor.execute("""
        SELECT id, grade, standard
        FROM steel_grades
        WHERE standard LIKE '%zknives.com%'
    """)
    zknives_records = cursor.fetchall()
    print(f"   Found {len(zknives_records)} grades with zknives.com")
    for record in zknives_records[:10]:
        print(f"   ID={record[0]:5d} Grade=\"{record[1]}\" Standard=\"{record[2][:40]}\"")
    if len(zknives_records) > 10:
        print(f"   ... and {len(zknives_records)-10} more")

    # 4. Check specific doubled grades (with pattern matching for newlines)
    print("\n4. Checking specific doubled grades...")
    doubled_patterns = [
        ("1.4742%Alleima%4C54", "1.4742 Alleima® 4C54"),
        ("2.4969%2.4632", "2.4969 2.4632"),
        ("Nimonic%90%N07090", "Nimonic® 90 N07090")
    ]
    doubled_found = []
    for pattern, description in doubled_patterns:
        cursor.execute("SELECT id, grade, link FROM steel_grades WHERE grade LIKE ?", (pattern,))
        result = cursor.fetchone()
        if result:
            doubled_found.append(result)
            print(f"   FOUND: ID={result[0]:5d} Grade=\"{result[1]}\" Link={bool(result[2])}")
        else:
            print(f"   NOT FOUND: \"{description}\"")

    # 5. Check grades with ® and ™ symbols
    print("\n5. Checking grades with ® and ™ symbols...")
    cursor.execute("""
        SELECT id, grade
        FROM steel_grades
        WHERE grade LIKE '%®%' OR grade LIKE '%™%'
    """)
    trademark_records = cursor.fetchall()
    print(f"   Found {len(trademark_records)} grades with ® or ™")
    for record in trademark_records[:10]:
        print(f"   ID={record[0]:5d} Grade=\"{record[1]}\"")
    if len(trademark_records) > 10:
        print(f"   ... and {len(trademark_records)-10} more")

    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"Records to update (Other column): {len(other_dash_records)}")
    print(f"Records to delete (~ symbol): {len(tilde_records)}")
    print(f"Records to delete (zknives.com): {len(zknives_records)}")
    print(f"Records to delete (doubled grades): {len(doubled_found)}")
    print(f"Records to update (® and ™): {len(trademark_records)}")
    total_deletes = len(tilde_records) + len(zknives_records) + len(doubled_found)
    print(f"\nTotal to delete: {total_deletes}")
    print(f"Total to update: {len(other_dash_records) + len(trademark_records)}")

    if dry_run:
        print("\n[DRY RUN] No changes made. Run with --execute to apply.")
        conn.close()
        return

    # Apply changes
    print("\n" + "=" * 100)
    print("APPLYING CHANGES")
    print("=" * 100)

    # 1. Clean Other column
    print("\n1. Cleaning Other column...")
    cursor.execute("""
        UPDATE steel_grades
        SET other = NULL
        WHERE other = '—' OR other = '-'
    """)
    print(f"   Updated {cursor.rowcount} records")

    # 2. Delete grades with ~
    print("\n2. Deleting grades with '~'...")
    cursor.execute("DELETE FROM steel_grades WHERE grade LIKE '%~%'")
    print(f"   Deleted {cursor.rowcount} records")

    # 3. Delete grades with zknives.com
    print("\n3. Deleting grades with zknives.com...")
    cursor.execute("DELETE FROM steel_grades WHERE standard LIKE '%zknives.com%'")
    print(f"   Deleted {cursor.rowcount} records")

    # 4. Delete specific doubled grades
    print("\n4. Deleting doubled grades...")
    deleted_doubled = 0
    for pattern, description in doubled_patterns:
        cursor.execute("DELETE FROM steel_grades WHERE grade LIKE ?", (pattern,))
        if cursor.rowcount > 0:
            print(f"   Deleted: \"{description}\" (pattern: {pattern})")
            deleted_doubled += cursor.rowcount
    print(f"   Total deleted: {deleted_doubled}")

    # 5. Remove ® and ™ from grade names
    print("\n5. Removing ® and ™ symbols...")
    cursor.execute("""
        UPDATE steel_grades
        SET grade = REPLACE(REPLACE(grade, '®', ''), '™', '')
        WHERE grade LIKE '%®%' OR grade LIKE '%™%'
    """)
    print(f"   Updated {cursor.rowcount} records")

    conn.commit()

    # Final stats
    cursor.execute("SELECT COUNT(*) FROM steel_grades")
    final_count = cursor.fetchone()[0]

    print("\n" + "=" * 100)
    print(f"[SUCCESS] Cleanup complete")
    print(f"Final database size: {final_count} grades")
    print("=" * 100)

    conn.close()

if __name__ == "__main__":
    dry_run = "--execute" not in sys.argv

    if dry_run:
        print("Running in DRY RUN mode. Add --execute flag to apply changes.\n")

    cleanup_database(dry_run=dry_run)
