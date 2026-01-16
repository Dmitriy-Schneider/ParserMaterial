"""Diagnose Standard column issues"""
import sqlite3
import re
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*100)
print("DIAGNOSIS OF STANDARD COLUMN ISSUES")
print("="*100)

# 1. DIN grades with format "1.XXXX" (W-Nr)
print("\n1. DIN W-Nr grades (format: 1.XXXX):")
print("-" * 100)

cursor.execute("""
    SELECT grade, standard
    FROM steel_grades
    WHERE grade LIKE '1.%'
      AND grade NOT LIKE '%[a-zA-Z]%'
      AND (standard LIKE '%DIN%' OR standard LIKE '%W-Nr%')
""")

wnr_grades = cursor.fetchall()
print(f"   Found {len(wnr_grades)} W-Nr grades")

# Check what standards they have
wnr_standards = {}
for grade, standard in wnr_grades[:20]:  # Show first 20
    if standard not in wnr_standards:
        wnr_standards[standard] = []
    wnr_standards[standard].append(grade)

print("\n   Current Standard values:")
for std, grades in sorted(wnr_standards.items()):
    print(f"   '{std}': {len([g for g, s in wnr_grades if s == std])} grades")
    print(f"      Examples: {', '.join(grades[:3])}")

# Count how many need fixing
needs_fix_wnr = 0
for grade, standard in wnr_grades:
    if standard and 'W-Nr (DIN)' not in standard:
        needs_fix_wnr += 1

print(f"\n   -> Need to fix: {needs_fix_wnr} grades")
print(f"      Should be: 'W-Nr (DIN), Германия'")

# 2. DIN grades alphanumeric (without dots)
print("\n2. DIN alphanumeric grades (format: X155CrVMo121, etc.):")
print("-" * 100)

cursor.execute("""
    SELECT grade, standard
    FROM steel_grades
    WHERE standard LIKE '%DIN%'
      AND grade NOT LIKE '1.%'
      AND (grade LIKE '%[a-zA-Z]%' OR standard LIKE '%DIN ' || grade || '%')
    LIMIT 100
""")

din_alpha_grades = cursor.fetchall()

# Filter to find duplicates
duplicates = []
for grade, standard in din_alpha_grades:
    if standard and grade.upper() in standard.upper().replace(' ', ''):
        duplicates.append((grade, standard))

print(f"   Found {len(duplicates)} DIN grades with duplicated grade name in Standard")

if duplicates:
    print("\n   Examples of duplicates:")
    for grade, standard in duplicates[:10]:
        print(f"   {grade:20s} -> '{standard}'")
        print(f"   {'':20s}    Should be: 'DIN, Германия'")

# 3. AISI grades with duplicated grade name
print("\n3. AISI grades with duplicated grade name:")
print("-" * 100)

cursor.execute("""
    SELECT grade, standard
    FROM steel_grades
    WHERE standard LIKE '%AISI%'
""")

aisi_grades = cursor.fetchall()
print(f"   Found {len(aisi_grades)} AISI grades total")

# Find duplicates
aisi_duplicates = []
for grade, standard in aisi_grades:
    if standard and grade in standard and standard != 'AISI, США':
        aisi_duplicates.append((grade, standard))

print(f"   Found {len(aisi_duplicates)} AISI grades with duplicated grade name")

if aisi_duplicates:
    print("\n   Examples:")
    for grade, standard in aisi_duplicates[:15]:
        print(f"   {grade:20s} -> '{standard}'")
        print(f"   {'':20s}    Should be: 'AISI, США'")

# Summary
print("\n" + "="*100)
print("SUMMARY")
print("="*100)
print(f"1. W-Nr grades (1.XXXX) needing fix: {needs_fix_wnr}")
print(f"2. DIN alphanumeric grades with duplicates: {len(duplicates)}")
print(f"3. AISI grades with duplicates: {len(aisi_duplicates)}")
print(f"\nTotal issues to fix: {needs_fix_wnr + len(duplicates) + len(aisi_duplicates)}")

conn.close()
