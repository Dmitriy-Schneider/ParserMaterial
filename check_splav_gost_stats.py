"""
Check how many splav grades have specific GOST numbers vs generic GOST
"""
import sqlite3
import re

conn = sqlite3.connect('database/steel_database.db')
cursor = conn.cursor()

# Get total grades in DB
cursor.execute("SELECT COUNT(*) FROM steel_grades")
total_db = cursor.fetchone()[0]

# Get all splav grades
cursor.execute("""
    SELECT grade, standard
    FROM steel_grades
    WHERE link LIKE '%splav%'
""")
splav_grades = cursor.fetchall()

print("="*100)
print("DATABASE STATISTICS")
print("="*100)
print(f"Всего марок в БД: {total_db:,}")
print(f"\nМарок от splav-kharkov: {len(splav_grades):,}")
print("\n" + "="*100)
print("SPLAV-KHARKOV GOST STATISTICS")
print("="*100)

total = len(splav_grades)
has_specific_gost = 0
has_generic_gost = 0
no_standard = 0

specific_examples = []
generic_examples = []

for grade, standard in splav_grades:
    if not standard:
        no_standard += 1
    elif re.search(r'ГОСТ\s+\d+', standard) or re.search(r'ГОСТ\s+Р\s*\d+', standard):
        has_specific_gost += 1
        if len(specific_examples) < 10:
            specific_examples.append((grade, standard))
    else:
        has_generic_gost += 1
        if len(generic_examples) < 10:
            generic_examples.append((grade, standard))

print(f"\nTotal splav grades: {total}")
print(f"With specific GOST number: {has_specific_gost} ({has_specific_gost*100/total:.1f}%)")
print(f"With generic GOST: {has_generic_gost} ({has_generic_gost*100/total:.1f}%)")
print(f"Without standard: {no_standard} ({no_standard*100/total:.1f}%)")

print("\n" + "="*100)
print("EXAMPLES WITH SPECIFIC GOST NUMBER:")
print("="*100)
for grade, standard in specific_examples:
    print(f"  {grade}: {standard}")

print("\n" + "="*100)
print("EXAMPLES WITH GENERIC GOST:")
print("="*100)
for grade, standard in generic_examples:
    print(f"  {grade}: {standard}")

# Check 4Х5МФС specifically
print("\n" + "="*100)
print("SPECIFIC CHECK: 4Х5МФС")
print("="*100)
cursor.execute("SELECT standard FROM steel_grades WHERE grade = ?", ('4Х5МФС',))
result = cursor.fetchone()
if result:
    standard = result[0]
    print(f"Current: {standard}")

    has_number = bool(re.search(r'ГОСТ\s+\d+', standard) or re.search(r'ГОСТ\s+Р\s*\d+', standard))
    print(f"Has specific number: {has_number}")

    if '5950' in standard:
        print("STATUS: CORRECT (has GOST 5950)")
    elif '1133' in standard:
        print("STATUS: WRONG (has GOST 1133-71, should be GOST 5950)")
    else:
        print("STATUS: GENERIC (should be GOST 5950)")

conn.close()
