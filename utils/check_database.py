#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check Database State
====================
Verify database state after cleanup
"""

import sqlite3

db_path = 'database/steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*80)
print("DATABASE STATE CHECK")
print("="*80)

# Total grades
cursor.execute("SELECT COUNT(*) FROM steel_grades")
total = cursor.fetchone()[0]
print(f"\nTotal grades: {total}")

# Grades with links
cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE link IS NOT NULL AND link != ''")
with_links = cursor.fetchone()[0]
print(f"Grades with links: {with_links}")

# Grades with analogues
cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE analogues IS NOT NULL AND analogues != ''")
with_analogues = cursor.fetchone()[0]
print(f"Grades with analogues: {with_analogues}")

# Count by standard
print("\nGrades by Standard (top 15):")
cursor.execute("""
    SELECT standard, COUNT(*) as cnt
    FROM steel_grades
    WHERE standard IS NOT NULL AND standard != ''
    GROUP BY standard
    ORDER BY cnt DESC
    LIMIT 15
""")
for standard, count in cursor.fetchall():
    print(f"  {standard:<30} {count:>5} grades")

# Check for remaining incorrect standards
print("\nChecking for incorrect Standard values...")
cursor.execute("""
    SELECT DISTINCT standard FROM steel_grades
    WHERE standard LIKE '%(%' OR standard LIKE '%Extended%'
""")
incorrect = cursor.fetchall()
if incorrect:
    print(f"  WARNING: Found {len(incorrect)} incorrect standards:")
    for std in incorrect[:10]:
        print(f"    - {std[0]}")
else:
    print("  [+] No incorrect standards found")

# Examples
print("\nExamples of recent fixes:")
cursor.execute("""
    SELECT grade, standard, analogues FROM steel_grades
    WHERE grade IN ('T11347', 'M47', '1.2316', '420J2', '347', '347H', '1.5634', '75Ni8')
    ORDER BY grade
""")
for grade, standard, analogues in cursor.fetchall():
    print(f"\n{grade}:")
    print(f"  Standard: {standard}")
    if analogues:
        print(f"  Analogues: {' '.join(analogues.split()[:10])}...")
    else:
        print(f"  Analogues: None")

conn.close()
print("\n" + "="*80)
