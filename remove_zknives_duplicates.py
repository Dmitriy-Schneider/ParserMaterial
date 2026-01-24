#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Remove duplicates with zknives.com in Standard and records without links"""
import sqlite3
import sys
import io
from database.backup_manager import backup_before_modification

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def remove_zknives_and_no_link_duplicates(dry_run=True):
    """Remove records with 'zknives.com' in Standard or without links when better versions exist"""

    if not dry_run:
        print("Creating backup...")
        backup_before_modification(reason="remove_zknives_duplicates")

    conn = sqlite3.connect('database/steel_database.db')
    cursor = conn.cursor()

    # Find all grades
    cursor.execute("SELECT DISTINCT REPLACE(REPLACE(grade, '\u00a0', ' '), '\xc2\xa0', ' ') as normalized FROM steel_grades")
    all_normalized = cursor.fetchall()

    ids_to_delete = []

    print("Analyzing grades for deletion...\n")
    print("=" * 100)

    for (normalized_grade,) in all_normalized:
        # Find all variants of this grade (including non-breaking spaces)
        cursor.execute("""
            SELECT id, grade, link, standard
            FROM steel_grades
            WHERE REPLACE(REPLACE(grade, '\u00a0', ' '), '\xc2\xa0', ' ') = ?
            ORDER BY
                CASE WHEN link IS NOT NULL AND link != '' THEN 0 ELSE 1 END,
                CASE WHEN standard LIKE '%zknives.com%' THEN 1 ELSE 0 END,
                id
        """, (normalized_grade,))

        variants = cursor.fetchall()

        if len(variants) > 1:
            # Keep first (best) variant
            keep_id = variants[0][0]

            print(f"\nGrade: {normalized_grade}")
            print(f"  KEEP:   ID={variants[0][0]:5d} Grade=\"{variants[0][1]}\" Link={bool(variants[0][2])} Standard=\"{variants[0][3][:40] if variants[0][3] else 'NULL'}\"")

            for variant in variants[1:]:
                should_delete = False
                reason = []

                # Delete if has zknives.com in standard
                if variant[3] and 'zknives.com' in variant[3]:
                    should_delete = True
                    reason.append("zknives.com in Standard")

                # Delete if no link
                if not variant[2]:
                    should_delete = True
                    reason.append("no link")

                # Delete if has non-breaking space
                if '\u00a0' in variant[1] or '\xc2\xa0' in str(variant[1].encode()):
                    should_delete = True
                    reason.append("non-breaking space")

                if should_delete:
                    ids_to_delete.append(variant[0])
                    print(f"  DELETE: ID={variant[0]:5d} Grade=\"{variant[1]}\" Link={bool(variant[2])} Reason: {', '.join(reason)}")

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

    remove_zknives_and_no_link_duplicates(dry_run=dry_run)
