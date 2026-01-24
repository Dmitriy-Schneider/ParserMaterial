#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Remove records without links if better versions with links exist"""
import sqlite3
import sys
import io
from database.backup_manager import backup_before_modification

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def normalize_grade(grade):
    """Normalize grade for comparison (case-insensitive, no spaces)"""
    if not grade:
        return ""
    # Remove spaces, non-breaking spaces, convert to uppercase
    return grade.replace(' ', '').replace('\u00a0', '').replace('\xa0', '').upper()

def remove_no_link_duplicates(dry_run=True):
    """Remove records without links when versions with links exist"""

    if not dry_run:
        print("Creating backup...")
        backup_before_modification(reason="remove_no_link_records")

    conn = sqlite3.connect('database/steel_database.db')
    cursor = conn.cursor()

    # Get all grades without links
    cursor.execute("""
        SELECT id, grade
        FROM steel_grades
        WHERE link IS NULL OR link = ''
    """)
    no_link_records = cursor.fetchall()

    print(f"Found {len(no_link_records)} records without links\n")
    print("=" * 100)

    ids_to_delete = []

    for record_id, grade in no_link_records:
        normalized = normalize_grade(grade)

        # Find records with same normalized grade but with links
        cursor.execute("""
            SELECT id, grade, link
            FROM steel_grades
            WHERE link IS NOT NULL AND link != ''
        """)

        has_link_version = False
        for other_id, other_grade, other_link in cursor.fetchall():
            if normalize_grade(other_grade) == normalized:
                has_link_version = True
                print(f"\nREMOVE: ID={record_id:5d} \"{grade}\" (no link)")
                print(f"  KEEP: ID={other_id:5d} \"{other_grade}\" (has link: {other_link[:50]})")
                ids_to_delete.append(record_id)
                break

    print("\n" + "=" * 100)
    print(f"Total records to delete: {len(ids_to_delete)}")

    if dry_run:
        print("\n[DRY RUN] No changes made. Run with --execute to delete.")
        conn.close()
        return len(ids_to_delete)

    # Delete records
    print("\nDeleting records...")
    for id_to_delete in ids_to_delete:
        cursor.execute("DELETE FROM steel_grades WHERE id = ?", (id_to_delete,))

    conn.commit()

    # Verify
    cursor.execute("SELECT COUNT(*) FROM steel_grades")
    final_count = cursor.fetchone()[0]

    print(f"\n[SUCCESS] Deleted {len(ids_to_delete)} records")
    print(f"Final database size: {final_count} grades")

    conn.close()
    return len(ids_to_delete)

if __name__ == "__main__":
    dry_run = "--execute" not in sys.argv

    if dry_run:
        print("Running in DRY RUN mode. Add --execute flag to delete.\n")

    remove_no_link_duplicates(dry_run=dry_run)
