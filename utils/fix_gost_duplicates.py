"""Fix GOST duplicates in Standard column"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*100)
print("FIXING GOST DUPLICATES IN STANDARD COLUMN")
print("="*100)

# Find all GOST grades with duplicates
cursor.execute("""
    SELECT grade, standard
    FROM steel_grades
    WHERE standard LIKE '%GOST%'
      AND standard != 'GOST, Россия'
""")

gost_grades = cursor.fetchall()

fixed_count = 0

print("\nFixing GOST grades...")
print("-" * 100)

for grade, standard in gost_grades:
    if not standard:
        continue

    # Check if grade name is duplicated in standard
    if grade in standard:
        # Fix to "GOST, Россия"
        cursor.execute(
            "UPDATE steel_grades SET standard = ? WHERE grade = ?",
            ('GOST, Россия', grade)
        )
        fixed_count += 1

        if fixed_count <= 10:  # Show first 10 examples
            print(f"   {grade:30s}: '{standard}' -> 'GOST, Россия'")

# Commit changes
conn.commit()

# Summary
print("\n" + "="*100)
print("SUMMARY")
print("="*100)
print(f"GOST grades fixed: {fixed_count}")
print("\nChanges committed to database.")

conn.close()
