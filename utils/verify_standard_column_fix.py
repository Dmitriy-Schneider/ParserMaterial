"""Verify Standard column fixes"""
import sqlite3
import re
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*100)
print("VERIFICATION OF STANDARD COLUMN FIXES")
print("="*100)

errors_found = 0

# 1. Check W-Nr grades (N.NNNN format)
print("\n1. Checking W-Nr grades (format: N.NNNN)...")
print("-" * 100)

cursor.execute("""
    SELECT grade, standard
    FROM steel_grades
    WHERE grade LIKE '%.%'
      AND (standard LIKE '%DIN%' OR standard LIKE '%W-Nr%')
""")

wnr_grades = cursor.fetchall()
wnr_errors = 0
wnr_pattern = r'^\d+\.\d+$'

for grade, standard in wnr_grades:
    if re.match(wnr_pattern, grade):  # Purely numeric with dot
        if standard != 'W-Nr (DIN), Германия':
            wnr_errors += 1
            if wnr_errors <= 5:
                print(f"   ERROR: {grade:20s} has '{standard}'")

wnr_count = len([g for g, s in wnr_grades if re.match(wnr_pattern, g)])
if wnr_errors == 0:
    print(f"   OK: All {wnr_count} W-Nr grades have correct standard")
else:
    print(f"   ERROR: Found {wnr_errors} W-Nr grades with incorrect standard")
    errors_found += wnr_errors

# 2. Check DIN grades for duplicates
print("\n2. Checking DIN grades for duplicated grade names...")
print("-" * 100)

cursor.execute("""
    SELECT grade, standard
    FROM steel_grades
    WHERE standard LIKE '%DIN%'
      AND standard != 'DIN, Германия'
      AND standard != 'W-Nr (DIN), Германия'
""")

din_grades = cursor.fetchall()
din_errors = 0

for grade, standard in din_grades:
    if standard and grade.upper() in standard.upper().replace(' ', ''):
        din_errors += 1
        if din_errors <= 5:
            print(f"   ERROR: {grade:20s} has '{standard}' (duplicate)")

if din_errors == 0:
    print(f"   OK: No DIN grades with duplicated grade names found")
else:
    print(f"   ERROR: Found {din_errors} DIN grades with duplicates")
    errors_found += din_errors

# 3. Check AISI grades for duplicates
print("\n3. Checking AISI grades for duplicated grade names...")
print("-" * 100)

cursor.execute("""
    SELECT grade, standard
    FROM steel_grades
    WHERE standard LIKE '%AISI%'
      AND standard != 'AISI, США'
""")

aisi_grades = cursor.fetchall()
aisi_errors = 0

for grade, standard in aisi_grades:
    if standard and grade in standard:
        aisi_errors += 1
        if aisi_errors <= 5:
            print(f"   ERROR: {grade:20s} has '{standard}' (duplicate)")

if aisi_errors == 0:
    print(f"   OK: No AISI grades with duplicated grade names found")
else:
    print(f"   ERROR: Found {aisi_errors} AISI grades with duplicates")
    errors_found += aisi_errors

# 4. Show examples of correct standards
print("\n4. Examples of correct standards:")
print("-" * 100)

# W-Nr example
cursor.execute("SELECT grade, standard FROM steel_grades WHERE grade = '1.2379'")
r = cursor.fetchone()
if r:
    print(f"   1.2379: '{r[1]}' (should be 'W-Nr (DIN), Германия')")

# DIN example  
cursor.execute("SELECT grade, standard FROM steel_grades WHERE grade = 'X155CrVMo121' LIMIT 1")
r = cursor.fetchone()
if r:
    print(f"   X155CrVMo121: '{r[1]}' (should be 'DIN, Германия')")

# AISI example
cursor.execute("SELECT grade, standard FROM steel_grades WHERE grade = 'H11'")
r = cursor.fetchone()
if r:
    print(f"   H11: '{r[1]}' (should be 'AISI, США')")

# Summary
print("\n" + "="*100)
print("SUMMARY")
print("="*100)

if errors_found == 0:
    print("   OK: ALL FIXES VERIFIED SUCCESSFULLY!")
    print("   No errors found in Standard column.")
else:
    print(f"   ERROR: Found {errors_found} remaining issues")
    print("   Please investigate and re-run fix script.")

conn.close()
