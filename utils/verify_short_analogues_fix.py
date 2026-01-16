"""Verify short analogues fix"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*100)
print("VERIFICATION OF SHORT ANALOGUES FIX")
print("="*100)

# Check grade 304
print("\n1. Checking grade 304 (user reported):")
cursor.execute("SELECT grade, standard, analogues FROM steel_grades WHERE grade = '304'")
r = cursor.fetchone()

if r:
    grade, standard, analogues = r
    print(f"   Grade: {grade}")
    print(f"   Standard: {standard}")
    print(f"   Analogues: {analogues[:200]}...")

    # Check if '10' is present
    analogue_list = analogues.split() if analogues else []
    if '10' in analogue_list:
        print(f"   ERROR: '10' still present in analogues!")
    else:
        print(f"   OK: '10' removed successfully!")

# Check other high-alloy grades with short analogues
SHORT_ANALOGUES = ['1', '2', '3', '10', '20', '25', '27', '30', '35', '37', '45', '50', '60', '75', '718', '760']

print("\n2. Checking all high-alloy grades for short analogues:")

error_count = 0
for short_ana in SHORT_ANALOGUES:
    cursor.execute("""
        SELECT COUNT(*)
        FROM steel_grades
        WHERE analogues LIKE '% ' || ? || ' %'
           OR analogues LIKE ? || ' %'
           OR analogues LIKE '% ' || ?
           OR analogues = ?
    """, (short_ana, short_ana, short_ana, short_ana))

    count = cursor.fetchone()[0]

    if count > 0:
        print(f"   '{short_ana}': Still found in {count} grades (ERROR)")
        error_count += count

        # Show examples
        cursor.execute("""
            SELECT grade, cr, analogues
            FROM steel_grades
            WHERE (analogues LIKE '% ' || ? || ' %'
               OR analogues LIKE ? || ' %'
               OR analogues LIKE '% ' || ?
               OR analogues = ?)
              AND cr IS NOT NULL
            LIMIT 3
        """, (short_ana, short_ana, short_ana, short_ana))

        examples = cursor.fetchall()
        for ex_grade, ex_cr, ex_ana in examples:
            # Check if high-alloy
            try:
                cr_val = float(ex_cr.split('-')[0].replace(',', '.')) if ex_cr and '-' in str(ex_cr) else float(ex_cr) if ex_cr else 0
            except:
                cr_val = 0

            if cr_val > 5:
                print(f"      Example: {ex_grade} (Cr={ex_cr}) has '{short_ana}'")

# Summary
print("\n" + "="*100)
print("SUMMARY")
print("="*100)

if error_count == 0:
    print("   ALL FIXED: No short analogues found in high-alloy steels!")
else:
    print(f"   ERROR: {error_count} grades still have short analogues!")

conn.close()
