#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify Database Fixes
=====================
Check if all fixes were applied correctly
"""

import sqlite3

db_path = 'database/steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*80)
print("VERIFYING DATABASE FIXES")
print("="*80)

# Check merged grades
print("\n1. Checking merged grades that should be DELETED:")
merged_grades = ['1.563475Ni8', '347/347H', 'T11347M47', '1.2316420J2', 'C100W1']
for grade in merged_grades:
    cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE grade = ?", (grade,))
    count = cursor.fetchone()[0]
    status = "EXISTS (BAD)" if count > 0 else "DELETED (OK)"
    print(f"  {grade:<20} {status}")

# Check split parts that should EXIST
print("\n2. Checking split parts that should EXIST:")
split_parts = [
    ('1.5634', '75Ni8'),
    ('347', '347H'),
    ('T11347', 'M47'),
    ('1.2316', '420J2'),
    ('C100', 'W1')
]
for part1, part2 in split_parts:
    cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE grade = ?", (part1,))
    count1 = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE grade = ?", (part2,))
    count2 = cursor.fetchone()[0]

    status1 = "EXISTS" if count1 > 0 else "MISSING"
    status2 = "EXISTS" if count2 > 0 else "MISSING"

    # Check if linked as analogues
    if count1 > 0 and count2 > 0:
        cursor.execute("SELECT analogues FROM steel_grades WHERE grade = ?", (part1,))
        analogues1 = cursor.fetchone()[0] or ""
        linked = "LINKED" if part2 in analogues1 else "NOT LINKED"
    else:
        linked = "N/A"

    print(f"  {part1:<10} {status1:<10} {part2:<10} {status2:<10} {linked}")

# Check Standard column
print("\n3. Checking Standard values:")
test_grades = ['1.5634', '75Ni8', '347', '347H', 'T11347', 'M47']
for grade in test_grades:
    cursor.execute("SELECT standard FROM steel_grades WHERE grade = ?", (grade,))
    result = cursor.fetchone()
    if result:
        standard = result[0] or "NULL"
        print(f"  {grade:<15} {standard}")
    else:
        print(f"  {grade:<15} NOT FOUND")

# Total count
cursor.execute("SELECT COUNT(*) FROM steel_grades")
total = cursor.fetchone()[0]
print(f"\nTotal grades in database: {total}")

conn.close()
print("="*80)
