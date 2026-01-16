#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check remaining slash grades in database
"""

import sqlite3

db_path = 'database/steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*80)
print("CHECKING REMAINING SLASH GRADES")
print("="*80)

# Get all slash grades
cursor.execute("""
    SELECT grade, standard, analogues FROM steel_grades
    WHERE grade LIKE '%/%'
    ORDER BY grade
""")

slash_grades = cursor.fetchall()

print(f"\nFound {len(slash_grades)} grades with slash:")

for grade, standard, analogues in slash_grades:
    print(f"\n{grade}:")
    print(f"  Standard: {standard}")
    print(f"  Analogues: {analogues}")

    # Try to split
    parts = grade.split('/')
    print(f"  Would split into: {' + '.join(parts)}")

    # Check if parts exist
    for part in parts:
        part = part.strip()
        cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE grade = ?", (part,))
        exists = cursor.fetchone()[0] > 0
        print(f"    {part}: {'EXISTS' if exists else 'NOT FOUND'}")

    # These look like brand names with alternative names, not split grades
    # Examples: "CALMAX / CARMO" - these are Uddeholm brand names
    #           "SVX360/Gr" - Hitachi grade with variant

print("\n" + "="*80)
print("ANALYSIS")
print("="*80)
print("These grades look like:")
print("  - Brand names with alternatives (CALMAX / CARMO)")
print("  - Grade variants (SVX360/Gr, SVX360/So)")
print("  - Should probably keep as-is or split case-by-case")

conn.close()
print("="*80)
