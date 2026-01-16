"""Diagnose GOST duplicates in Standard column"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*100)
print("DIAGNOSIS OF GOST DUPLICATES IN STANDARD COLUMN")
print("="*100)

# Find all GOST grades
cursor.execute("""
    SELECT grade, standard
    FROM steel_grades
    WHERE standard LIKE '%GOST%'
""")

gost_grades = cursor.fetchall()
print(f"\nFound {len(gost_grades)} GOST grades total")

# Find duplicates
duplicates = []
for grade, standard in gost_grades:
    if standard and grade in standard and standard != 'GOST, Россия':
        duplicates.append((grade, standard))

print(f"Found {len(duplicates)} GOST grades with duplicated grade name")

if duplicates:
    print("\nExamples of duplicates (first 20):")
    for grade, standard in duplicates[:20]:
        print(f"   {grade:30s} -> '{standard}'")
        print(f"   {'':30s}    Should be: 'GOST, Россия'")

# Summary
print("\n" + "="*100)
print("SUMMARY")
print("="*100)
print(f"GOST grades with duplicates: {len(duplicates)}")
print(f"Need to fix all to: 'GOST, Россия'")

conn.close()
