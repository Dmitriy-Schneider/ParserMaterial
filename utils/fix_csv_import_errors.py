"""
Fix CSV import errors:
1. Delete merged grades where both parts exist
2. Fix analogues (25 → 255) in duplex steels
3. Fix Standard for grade 255
"""
import sqlite3
import re
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*100)
print("FIXING CSV IMPORT ERRORS")
print("="*100)

# ========== PART 1: DELETE MERGED GRADES ==========
print("\n1. DELETING MERGED GRADES (both parts exist)")
print("="*100)

merged_to_delete = [
    # Decimal + digits pattern
    '1.05351055', '1.06011060', '1.06031070', '1.06051075', '1.09049255',
    '1.12031055', '1.12211060', '1.12311070', '1.12481075', '1.12691086',
    '1.12741095', '1.15201070', '1.17301045', '1.210951100', '1.350552100',
    '1.50269255', '1.65114340', '1.71039254',
    # Decimal + alphanumeric pattern
    '1.2063145Cr6',
    # Decimal + letter+digits pattern
    '1.2067L3', '1.2080D3', '1.2345H11', '1.2363A2', '1.2378D7',
    '1.2519O7', '1.2550S1', '1.2825O1', '1.3302T15',
]

# Add ASP grades (with space, but equivalents exist without space)
asp_merged = []
cursor.execute("""
    SELECT grade FROM steel_grades
    WHERE grade LIKE '% ~ASP %' OR grade LIKE '% -ASP %' OR grade LIKE '%~ASP %'
""")
for row in cursor.fetchall():
    grade = row[0]
    # Check if version without space exists
    no_space = re.sub(r'\s*~?\s*(ASP\s+)', r'ASP', grade)
    no_space = re.sub(r'^([\d\.]+)\s+ASP', r'\1ASP', no_space)
    no_space = re.sub(r'\s+', '', no_space)  # Remove all spaces

    # Check 1.3345 part and ASP2023 part separately
    match = re.match(r'^([\d\.]+)\s*~?\s*(ASP\s*\d+)$', grade)
    if match:
        part1 = match.group(1)
        part2 = match.group(2).replace(' ', '')  # ASP2023 without space

        cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE grade = ?", (part1,))
        has_part1 = cursor.fetchone()[0] > 0

        cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE grade = ?", (part2,))
        has_part2 = cursor.fetchone()[0] > 0

        if has_part1 and has_part2:
            asp_merged.append(grade)
            print(f"  Found ASP merged: {grade} = {part1} + {part2}")

merged_to_delete.extend(asp_merged)

deleted_count = 0
for grade in merged_to_delete:
    cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE grade = ?", (grade,))
    exists = cursor.fetchone()[0] > 0

    if exists:
        cursor.execute("DELETE FROM steel_grades WHERE grade = ?", (grade,))
        deleted_count += 1
        print(f"  Deleted: {grade}")

print(f"\nTotal deleted: {deleted_count} merged grades")

# ========== PART 2: FIX ANALOGUES (25 -> 255) ==========
print("\n" + "="*100)
print("2. FIXING ANALOGUES: 25 -> 255 in duplex steels")
print("="*100)

# Find all grades with '25' in analogues
cursor.execute("""
    SELECT grade, standard, c, cr, ni, mo, analogues
    FROM steel_grades
    WHERE analogues LIKE '% 25 %' OR analogues LIKE '25 %' OR analogues LIKE '% 25'
    ORDER BY grade
""")

grades_with_25 = cursor.fetchall()

fixed_analogues_count = 0
for grade, standard, c, cr, ni, mo, analogues in grades_with_25:
    # Check if it's duplex/super duplex (high Cr, low Ni)
    try:
        cr_val = float(cr.split('-')[0].replace(',', '.')) if cr and '-' in str(cr) else float(cr) if cr else 0
        ni_val = float(ni.split('-')[0].replace(',', '.')) if ni and '-' in str(ni) else float(ni) if ni else 0

        is_duplex = cr_val > 20 and ni_val < 15  # Duplex typically: Cr 20-28%, Ni 3-8%

        if is_duplex and analogues:
            # Replace ' 25 ' with ' 255 ' (avoiding partial matches)
            new_analogues = analogues

            # Match start, middle, and end positions
            if analogues.startswith('25 '):
                new_analogues = '255 ' + new_analogues[3:]
            if ' 25 ' in new_analogues:
                new_analogues = new_analogues.replace(' 25 ', ' 255 ')
            if new_analogues.endswith(' 25'):
                new_analogues = new_analogues[:-3] + ' 255'

            if new_analogues != analogues:
                cursor.execute("UPDATE steel_grades SET analogues = ? WHERE grade = ?",
                             (new_analogues, grade))
                fixed_analogues_count += 1
                print(f"  Fixed: {grade}")
                print(f"    Old: {analogues[:100]}...")
                print(f"    New: {new_analogues[:100]}...")
    except Exception as e:
        print(f"  Skipped {grade}: {e}")

print(f"\nTotal fixed: {fixed_analogues_count} grades (25 -> 255)")

# ========== PART 3: FIX STANDARD FOR GRADE 255 ==========
print("\n" + "="*100)
print("3. FIXING STANDARD FOR GRADE 255")
print("="*100)

cursor.execute("SELECT grade, standard FROM steel_grades WHERE grade = '255'")
result = cursor.fetchone()

if result:
    grade, current_standard = result
    print(f"  Grade: {grade}")
    print(f"  Current Standard: {current_standard}")

    if not current_standard or current_standard in ['', 'None', 'null']:
        new_standard = "AISI 255, США"
        cursor.execute("UPDATE steel_grades SET standard = ? WHERE grade = '255'",
                     (new_standard,))
        print(f"  Updated Standard: {new_standard}")
    else:
        print(f"  Standard already set, no change needed")
else:
    print("  Grade 255 not found in database")

# ========== COMMIT CHANGES ==========
conn.commit()

print("\n" + "="*100)
print("SUMMARY")
print("="*100)
print(f"  Deleted merged grades: {deleted_count}")
print(f"  Fixed analogues (25->255): {fixed_analogues_count}")
print(f"  Fixed Standard for 255: YES")
print("\nChanges committed to database!")
print("="*100)

conn.close()
