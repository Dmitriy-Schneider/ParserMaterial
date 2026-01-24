#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix analogues: verify links, remove duplicates"""
import sqlite3
import sys
import io
from database.backup_manager import backup_before_modification

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def fix_analogues(dry_run=True):
    """Fix analogues column: remove duplicates and verify references"""

    if not dry_run:
        print("Creating backup before fixing analogues...")
        backup_before_modification(reason="fix_analogues")

    conn = sqlite3.connect('database/steel_database.db')
    cursor = conn.cursor()

    # Get all grades for lookup
    cursor.execute("SELECT grade FROM steel_grades")
    all_grades = {row[0] for row in cursor.fetchall()}
    print(f"Total grades in database: {len(all_grades)}\n")

    # Get records with analogues
    cursor.execute("""
        SELECT id, grade, analogues
        FROM steel_grades
        WHERE analogues IS NOT NULL AND analogues != ''
    """)

    records = cursor.fetchall()
    print(f"Processing {len(records)} records with analogues...")
    print("=" * 100)

    updates_needed = []
    stats = {
        'total_processed': 0,
        'had_duplicates': 0,
        'had_missing': 0,
        'duplicates_removed': 0,
        'missing_refs': 0,
        'unchanged': 0
    }

    for record_id, grade, analogues in records:
        stats['total_processed'] += 1

        if '|' not in analogues:
            # No pipe separator - skip
            stats['unchanged'] += 1
            continue

        # Split by |
        analogue_list = [a.strip() for a in analogues.split('|') if a.strip()]

        # Remove duplicates (preserve order)
        seen = set()
        unique_analogues = []
        duplicates_found = []

        for analogue in analogue_list:
            if analogue not in seen:
                seen.add(analogue)
                unique_analogues.append(analogue)
            else:
                duplicates_found.append(analogue)

        # Check which analogues don't exist in database
        missing_analogues = [a for a in unique_analogues if a not in all_grades]

        # Track stats
        if duplicates_found:
            stats['had_duplicates'] += 1
            stats['duplicates_removed'] += len(duplicates_found)

        if missing_analogues:
            stats['had_missing'] += 1
            stats['missing_refs'] += len(missing_analogues)

        # Only update if duplicates were found (don't remove missing refs)
        if duplicates_found:
            new_analogues = '|'.join(unique_analogues)

            updates_needed.append({
                'id': record_id,
                'grade': grade,
                'old': analogues,
                'new': new_analogues,
                'duplicates': duplicates_found,
                'missing': missing_analogues
            })

    # Print results
    print(f"\nAnalysis Results:")
    print(f"  Total records processed: {stats['total_processed']}")
    print(f"  Records with duplicates: {stats['had_duplicates']} ({stats['duplicates_removed']} duplicates total)")
    print(f"  Records with missing refs: {stats['had_missing']} ({stats['missing_refs']} missing refs total)")
    print(f"  Records unchanged: {stats['unchanged']}")
    print(f"  Updates needed: {len(updates_needed)}")

    # Show examples
    if updates_needed:
        print(f"\nExample updates (first 10):")
        print("-" * 100)
        for update in updates_needed[:10]:
            print(f"\nGrade: {update['grade']} (ID={update['id']})")
            if update['duplicates']:
                print(f"  Duplicates removed: {', '.join(update['duplicates'])}")
            if update['missing']:
                print(f"  Missing in Grade: {', '.join(update['missing'][:5])}")
                if len(update['missing']) > 5:
                    print(f"    ... and {len(update['missing'])-5} more")

    # Save detailed report
    with open('analogues_fix_report.txt', 'w', encoding='utf-8') as f:
        f.write(f"Analogues Fix Report\n")
        f.write(f"=" * 100 + "\n\n")
        f.write(f"Statistics:\n")
        f.write(f"  Total records: {stats['total_processed']}\n")
        f.write(f"  With duplicates: {stats['had_duplicates']} ({stats['duplicates_removed']} total)\n")
        f.write(f"  With missing refs: {stats['had_missing']} ({stats['missing_refs']} total)\n")
        f.write(f"  Updates needed: {len(updates_needed)}\n\n")

        f.write(f"Detailed Changes:\n")
        f.write(f"-" * 100 + "\n")
        for update in updates_needed:
            f.write(f"\nGrade: {update['grade']} (ID={update['id']})\n")
            if update['duplicates']:
                f.write(f"  Duplicates: {', '.join(update['duplicates'])}\n")
            if update['missing']:
                f.write(f"  Missing: {', '.join(update['missing'])}\n")

    print(f"\nDetailed report saved to: analogues_fix_report.txt")

    if dry_run:
        print("\n[DRY RUN] No changes made. Run with --execute to apply fixes.")
        conn.close()
        return len(updates_needed)

    # Apply updates
    print(f"\nApplying {len(updates_needed)} updates...")
    for update in updates_needed:
        cursor.execute(
            "UPDATE steel_grades SET analogues = ? WHERE id = ?",
            (update['new'], update['id'])
        )

    conn.commit()
    print(f"[SUCCESS] Updated {len(updates_needed)} records")

    conn.close()
    return len(updates_needed)

if __name__ == "__main__":
    dry_run = "--execute" not in sys.argv

    if dry_run:
        print("Running in DRY RUN mode. Add --execute flag to apply changes.\n")

    fix_analogues(dry_run=dry_run)
