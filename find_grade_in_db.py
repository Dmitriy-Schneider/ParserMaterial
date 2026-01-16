import sqlite3
import re

conn = sqlite3.connect('database/steel_database.db')
cursor = conn.cursor()

# Find 4Х3ВМФ
grade = '4Х3ВМФ'
cursor.execute("SELECT grade, link, standard, c, cr, analogues FROM steel_grades WHERE grade = ?", (grade,))
result = cursor.fetchone()

if result:
    print(f"Found {grade} in database:")
    print(f"  Grade: {result[0]}")
    print(f"  Link: {result[1]}")
    print(f"  Standard: {result[2]}")
    print(f"  C: {result[3]}")
    print(f"  Cr: {result[4]}")
    print(f"  Analogues: {result[5]}")

    # Extract name_id from link
    if result[1]:
        match = re.search(r'name_id=(\d+)', result[1])
        if match:
            print(f"\n  name_id: {match.group(1)}")
else:
    print(f"{grade} NOT FOUND in database")

    # Try partial match
    print("\nSearching for similar grades...")
    cursor.execute("SELECT grade FROM steel_grades WHERE grade LIKE ? LIMIT 10", (f'%4Х3%',))
    for row in cursor.fetchall():
        print(f"  {row[0]}")

# Check if H10 and T20810 exist
print("\n" + "="*80)
print("Checking target analogues:")
for target in ['H10', 'T20810']:
    cursor.execute("SELECT grade, standard FROM steel_grades WHERE grade = ?", (target,))
    result = cursor.fetchone()
    if result:
        print(f"  {target}: EXISTS (Standard: {result[1]})")
    else:
        print(f"  {target}: NOT FOUND")

conn.close()
