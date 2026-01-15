#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check why grades weren't split
"""

import sqlite3
import re

db_path = 'database/steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all grades
cursor.execute("SELECT grade FROM steel_grades")
all_grades = set(row[0] for row in cursor.fetchall())

print("="*80)
print("CHECKING WHY GRADES WEREN'T SPLIT")
print("="*80)

# Check 1.563475Ni8
print("\n1. Checking 1.563475Ni8:")
match = re.match(r'^(1\.\d{4})(\d+[A-Za-z]\d*)$', '1.563475Ni8')
if match:
    part1, part2 = match.group(1), match.group(2)
    print(f"  Pattern matched: {part1} + {part2}")
    print(f"  Part 1 exists: {'1.5634' in all_grades}")
    print(f"  Part 2 exists: {'75Ni8' in all_grades}")
else:
    print("  Pattern did NOT match")

# Check 347/347H
print("\n2. Checking 347/347H:")
parts = '347/347H'.split('/')
print(f"  Split into: {parts}")
print(f"  Part 1 exists: {'347' in all_grades}")
print(f"  Part 2 exists: {'347H' in all_grades}")

# Search for similar grades
print("\n3. Searching for similar grades to 347:")
cursor.execute("SELECT grade FROM steel_grades WHERE grade LIKE '%347%' ORDER BY grade LIMIT 20")
for row in cursor.fetchall():
    print(f"  - {row[0]}")

# Check Standard for 1.563475Ni8
print("\n4. Checking 1.563475Ni8 details:")
cursor.execute("SELECT grade, standard, analogues FROM steel_grades WHERE grade = '1.563475Ni8'")
result = cursor.fetchone()
if result:
    print(f"  Grade: {result[0]}")
    print(f"  Standard: {result[1]}")
    print(f"  Analogues: {result[2]}")

conn.close()
print("="*80)
