"""
Add Standard column for existing grades from zknives and CSV imports
"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'

print("="*100)
print("ADDING STANDARD COLUMN TO EXISTING GRADES")
print("="*100)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Helper function to detect standard from grade name
def detect_standard(grade_name):
    """Detect standard from grade name patterns"""
    import re

    # Check for different patterns
    patterns = [
        # EN standards: 1.2343, 1.4301, etc.
        (r'^\d\.\d{4}', 'EN, Европа'),

        # AISI: 304, 316, 420, etc. (3-4 digits, sometimes with L suffix)
        (r'^[1-9]\d{2,3}[LH]?$', 'AISI, США'),

        # DIN: X30Cr13, X5CrNi18-10, etc.
        (r'^X\d+', 'DIN, Германия'),

        # JIS: SUS304, SKD11, SKH51, etc.
        (r'^(SUS|SK[DHST]|SCM|SNCM)\d+', 'JIS, Япония'),

        # GB/T: 9SiCr, 8MnS, etc. (Chinese steels)
        (r'^\d+[A-Z][a-z]+\d*', 'GB/T, Китай'),

        # UNS: N02200, S30400, etc.
        (r'^[A-Z]\d{5}', 'UNS, США'),

        # Russian GOST (Cyrillic): Х12МФ, 20Х13, etc.
        (r'[А-Я]', 'GOST, Россия'),
    ]

    for pattern, standard in patterns:
        if re.search(pattern, grade_name):
            return standard

    # Default - international database
    return 'zknives.com, Международная база'

# Step 1: Add Standard for zknives grades based on grade name patterns
print("\nStep 1: Adding Standard for zknives.com grades...")

cursor.execute("""
    SELECT id, grade
    FROM steel_grades
    WHERE link LIKE '%zknives%'
      AND (standard IS NULL OR standard = '')
""")
zknives_grades = cursor.fetchall()

print(f"  Found {len(zknives_grades)} zknives grades without Standard")

updated = 0
for grade_id, grade_name in zknives_grades:
    standard = detect_standard(grade_name)
    cursor.execute("UPDATE steel_grades SET standard = ? WHERE id = ?", (standard, grade_id))
    updated += 1

    if updated <= 10:  # Show first 10
        print(f"    {grade_name} -> {standard}")

conn.commit()
print(f"  Updated {updated} zknives grades")

# Step 2: Add Standard for CSV import grades
print("\nStep 2: Adding Standard for CSV import grades...")

cursor.execute("""
    SELECT id, grade
    FROM steel_grades
    WHERE (link IS NULL OR link = '')
      AND (standard IS NULL OR standard = '')
""")
csv_grades = cursor.fetchall()

print(f"  Found {len(csv_grades)} CSV grades without Standard")

updated = 0
for grade_id, grade_name in csv_grades:
    standard = detect_standard(grade_name)
    cursor.execute("UPDATE steel_grades SET standard = ? WHERE id = ?", (standard, grade_id))
    updated += 1

    if updated <= 10:  # Show first 10
        print(f"    {grade_name} -> {standard}")

conn.commit()
print(f"  Updated {updated} CSV grades")

# Step 3: Verify
print("\n" + "="*100)
print("VERIFICATION:")
print("="*100)

cursor.execute("SELECT COUNT(*) FROM steel_grades")
total = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE standard IS NULL OR standard = ''")
no_standard = cursor.fetchone()[0]

print(f"\nTotal grades: {total}")
print(f"Without Standard: {no_standard} ({no_standard*100/total:.1f}%)")
print(f"With Standard: {total - no_standard} ({(total-no_standard)*100/total:.1f}%)")

# Show samples
print("\nSample grades from each source:")

for source_pattern, source_name in [
    ('%zknives%', 'zknives.com'),
    ('%splav%', 'splav-kharkov.com'),
    ('', 'CSV import')
]:
    if source_pattern:
        cursor.execute("""
            SELECT grade, standard, c
            FROM steel_grades
            WHERE link LIKE ?
            LIMIT 3
        """, (source_pattern,))
    else:
        cursor.execute("""
            SELECT grade, standard, c
            FROM steel_grades
            WHERE (link IS NULL OR link = '')
            LIMIT 3
        """)

    print(f"\n{source_name}:")
    for grade, standard, c in cursor.fetchall():
        print(f"  {grade}: Standard={standard or 'MISSING'}, C={c or 'MISSING'}")

conn.close()

print("\n" + "="*100)
print("COMPLETE")
print("="*100)
