"""Verify GOST duplicates fix"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*100)
print("VERIFICATION OF GOST DUPLICATES FIX")
print("="*100)

# Check for remaining duplicates
cursor.execute("""
    SELECT grade, standard
    FROM steel_grades
    WHERE standard LIKE '%GOST%'
      AND standard != 'GOST, Россия'
""")

remaining = cursor.fetchall()

# Filter to actual duplicates (where grade is in standard)
duplicates = []
for grade, standard in remaining:
    if standard and grade in standard:
        duplicates.append((grade, standard))

print(f"\nChecking GOST grades...")
print("-" * 100)

if len(duplicates) == 0:
    print("   OK: No GOST grades with duplicated grade names found!")
else:
    print(f"   ERROR: Found {len(duplicates)} GOST grades with duplicates:")
    for grade, standard in duplicates[:10]:
        print(f"      {grade:30s} -> '{standard}'")

# Show example of correct standard
cursor.execute("SELECT grade, standard FROM steel_grades WHERE grade = '02Х18Н11'")
r = cursor.fetchone()
if r:
    print(f"\nExample: {r[0]} -> '{r[1]}' (should be 'GOST, Россия')")

# Summary
print("\n" + "="*100)
print("SUMMARY")
print("="*100)

if len(duplicates) == 0:
    print("   OK: ALL GOST GRADES VERIFIED SUCCESSFULLY!")
    print("   No duplicates found in Standard column.")
else:
    print(f"   ERROR: Found {len(duplicates)} remaining duplicates")

conn.close()
