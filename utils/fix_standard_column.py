"""Fix Standard column issues"""
import sqlite3
import re
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*100)
print("FIXING STANDARD COLUMN")
print("="*100)

# Counters
fixed_wnr = 0
fixed_din_duplicates = 0
fixed_aisi_duplicates = 0

# 1. Fix W-Nr grades (format: N.NNNN - digit.digits, no letters)
print("\n1. Fixing W-Nr grades (format: N.NNNN)...")
print("-" * 100)

# Get all grades with dot that are purely numeric
cursor.execute("""
    SELECT grade, standard
    FROM steel_grades
    WHERE grade LIKE '%.%'
      AND (standard LIKE '%DIN%' OR standard LIKE '%W-Nr%')
""")

wnr_grades = cursor.fetchall()

for grade, standard in wnr_grades:
    # Check if grade is purely numeric (digits and dot only)
    if re.match(r'^\d+\.\d+$', grade):
        # Check if already correct
        if standard != 'W-Nr (DIN), Германия':
            cursor.execute(
                "UPDATE steel_grades SET standard = ? WHERE grade = ?",
                ('W-Nr (DIN), Германия', grade)
            )
            fixed_wnr += 1

            if fixed_wnr <= 5:  # Show first 5 examples
                print(f"   {grade:20s}: '{standard}' -> 'W-Nr (DIN), Германия'")

print(f"\n   Fixed {fixed_wnr} W-Nr grades")

# 2. Fix DIN alphanumeric grades - remove duplicated grade name
print("\n2. Fixing DIN grades with duplicated grade name...")
print("-" * 100)

cursor.execute("""
    SELECT grade, standard
    FROM steel_grades
    WHERE standard LIKE '%DIN%'
      AND standard != 'DIN, Германия'
      AND standard != 'W-Nr (DIN), Германия'
""")

din_grades = cursor.fetchall()

for grade, standard in din_grades:
    if not standard:
        continue

    # Check if grade name is duplicated in standard
    # Examples: "DIN X155CRVMO121" or "DIN 2.4360"
    if grade.upper() in standard.upper().replace(' ', ''):
        # Remove duplicate, keep only "DIN, Германия"
        cursor.execute(
            "UPDATE steel_grades SET standard = ? WHERE grade = ?",
            ('DIN, Германия', grade)
        )
        fixed_din_duplicates += 1

        if fixed_din_duplicates <= 5:  # Show first 5 examples
            print(f"   {grade:20s}: '{standard}' -> 'DIN, Германия'")

print(f"\n   Fixed {fixed_din_duplicates} DIN grades")

# 3. Fix AISI grades - remove duplicated grade name
print("\n3. Fixing AISI grades with duplicated grade name...")
print("-" * 100)

cursor.execute("""
    SELECT grade, standard
    FROM steel_grades
    WHERE standard LIKE '%AISI%'
      AND standard != 'AISI, США'
""")

aisi_grades = cursor.fetchall()

for grade, standard in aisi_grades:
    if not standard:
        continue

    # Check if grade name is in standard (e.g., "AISI H11" should be "AISI")
    if grade in standard:
        # Remove duplicate, keep only "AISI, США"
        cursor.execute(
            "UPDATE steel_grades SET standard = ? WHERE grade = ?",
            ('AISI, США', grade)
        )
        fixed_aisi_duplicates += 1

        if fixed_aisi_duplicates <= 5:  # Show first 5 examples
            print(f"   {grade:20s}: '{standard}' -> 'AISI, США'")

print(f"\n   Fixed {fixed_aisi_duplicates} AISI grades")

# Commit changes
conn.commit()

# Summary
print("\n" + "="*100)
print("SUMMARY")
print("="*100)
print(f"1. W-Nr grades (N.NNNN) fixed: {fixed_wnr}")
print(f"2. DIN grades (remove duplicates) fixed: {fixed_din_duplicates}")
print(f"3. AISI grades (remove duplicates) fixed: {fixed_aisi_duplicates}")
print(f"\nTotal fixes: {fixed_wnr + fixed_din_duplicates + fixed_aisi_duplicates}")
print("\nChanges committed to database.")

conn.close()
