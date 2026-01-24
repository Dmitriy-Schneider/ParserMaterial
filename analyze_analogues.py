#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze analogues column for incorrect links"""
import sqlite3
import sys
import io

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def analyze_analogues():
    conn = sqlite3.connect('database/steel_database.db')
    cursor = conn.cursor()

    # Get all grades for lookup
    cursor.execute("SELECT grade FROM steel_grades")
    all_grades = {row[0] for row in cursor.fetchall()}
    print(f"Total grades in database: {len(all_grades)}")

    # Analyze analogues
    cursor.execute("""
        SELECT id, grade, analogues
        FROM steel_grades
        WHERE analogues IS NOT NULL AND analogues != ''
    """)

    records_with_analogues = cursor.fetchall()
    print(f"Records with analogues: {len(records_with_analogues)}\n")

    issues_found = []
    problematic_analogues = set()

    for record_id, grade, analogues in records_with_analogues:
        if not analogues:
            continue

        # Split by |
        analogue_list = [a.strip() for a in analogues.split('|') if a.strip()]

        for analogue in analogue_list:
            # Check if analogue exists in database
            if analogue not in all_grades:
                issues_found.append({
                    'id': record_id,
                    'grade': grade,
                    'missing_analogue': analogue
                })
                problematic_analogues.add(analogue)

    print(f"Found {len(issues_found)} analogue references that don't exist in database")
    print(f"Unique missing analogues: {len(problematic_analogues)}\n")

    # Show most common problematic analogues
    from collections import Counter
    analogue_counts = Counter([issue['missing_analogue'] for issue in issues_found])

    print("Top 30 missing analogues:")
    print("=" * 100)
    for analogue, count in analogue_counts.most_common(30):
        # Check if similar grade exists (case-insensitive or with spaces)
        similar_found = []
        analogue_normalized = analogue.replace(' ', '').replace('-', '').upper()

        for existing_grade in all_grades:
            existing_normalized = existing_grade.replace(' ', '').replace('-', '').upper()
            if existing_normalized == analogue_normalized and existing_grade != analogue:
                similar_found.append(existing_grade)

        similar_text = f" -> Similar: {', '.join(similar_found[:3])}" if similar_found else ""
        print(f"{count:4d}x  {analogue:40s}{similar_text}")

    # Save detailed report
    with open('analogues_issues_report.txt', 'w', encoding='utf-8') as f:
        f.write(f"Analogues Analysis Report\n")
        f.write(f"=" * 100 + "\n")
        f.write(f"Total records analyzed: {len(records_with_analogues)}\n")
        f.write(f"Issues found: {len(issues_found)}\n")
        f.write(f"Unique missing analogues: {len(problematic_analogues)}\n\n")

        f.write(f"All missing analogues:\n")
        f.write(f"-" * 100 + "\n")
        for analogue, count in sorted(analogue_counts.items(), key=lambda x: -x[1]):
            f.write(f"{count:4d}x  {analogue}\n")

        f.write(f"\n\nDetailed list:\n")
        f.write(f"-" * 100 + "\n")
        for issue in issues_found[:100]:  # First 100
            f.write(f"Grade: {issue['grade']:40s} -> Missing: {issue['missing_analogue']}\n")

    print(f"\nDetailed report saved to: analogues_issues_report.txt")

    conn.close()

if __name__ == "__main__":
    analyze_analogues()
