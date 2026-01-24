#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check for analogues that don't exist in Grade column"""
import sqlite3
import sys
import io
from collections import Counter

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_missing_analogues():
    conn = sqlite3.connect('database/steel_database.db')
    cursor = conn.cursor()

    # Get all grades
    cursor.execute("SELECT grade FROM steel_grades")
    all_grades = {row[0] for row in cursor.fetchall()}
    print(f"Total grades in database: {len(all_grades)}\n")

    # Get records with analogues
    cursor.execute("""
        SELECT id, grade, analogues
        FROM steel_grades
        WHERE analogues IS NOT NULL AND analogues != '' AND analogues LIKE '%|%'
    """)

    records = cursor.fetchall()
    print(f"Checking {len(records)} records with pipe-separated analogues...")

    missing_refs = []
    missing_counter = Counter()

    for record_id, grade, analogues in records:
        # Split by |
        analogue_list = [a.strip() for a in analogues.split('|') if a.strip()]

        # Check which don't exist
        for analogue in analogue_list:
            if analogue not in all_grades:
                missing_refs.append({
                    'id': record_id,
                    'grade': grade,
                    'missing_analogue': analogue
                })
                missing_counter[analogue] += 1

    print(f"\nFound {len(missing_refs)} missing references")
    print(f"Unique missing analogues: {len(missing_counter)}\n")

    print("Top 50 most common missing analogues:")
    print("=" * 100)
    for analogue, count in missing_counter.most_common(50):
        print(f"{count:4d}x  {analogue}")

    # Save detailed report
    with open('missing_analogues_report.txt', 'w', encoding='utf-8') as f:
        f.write(f"Missing Analogues Report\n")
        f.write(f"=" * 100 + "\n\n")
        f.write(f"Total missing references: {len(missing_refs)}\n")
        f.write(f"Unique missing analogues: {len(missing_counter)}\n\n")

        f.write(f"All missing analogues (sorted by frequency):\n")
        f.write(f"-" * 100 + "\n")
        for analogue, count in sorted(missing_counter.items(), key=lambda x: -x[1]):
            f.write(f"{count:4d}x  {analogue}\n")

        f.write(f"\n\nGrades with missing analogues:\n")
        f.write(f"-" * 100 + "\n")
        current_grade = None
        for ref in sorted(missing_refs, key=lambda x: x['grade']):
            if ref['grade'] != current_grade:
                f.write(f"\n{ref['grade']}:\n")
                current_grade = ref['grade']
            f.write(f"  - {ref['missing_analogue']}\n")

    print(f"\nDetailed report saved to: missing_analogues_report.txt")

    conn.close()

if __name__ == "__main__":
    check_missing_analogues()
