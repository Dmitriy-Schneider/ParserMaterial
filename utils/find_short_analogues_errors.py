"""
Find short analogues errors (like '10' in stainless steel 304)
Short grade names (1-3 characters) should not appear in analogues of high-alloy steels
"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*100)
print("FINDING SHORT ANALOGUES ERRORS")
print("="*100)

# Find all grades with very short grade names in analogues (1-3 characters)
cursor.execute("""
    SELECT grade, standard, c, cr, ni, analogues
    FROM steel_grades
    WHERE analogues IS NOT NULL AND analogues != ''
    ORDER BY grade
""")

errors_found = []
short_grades = set()

for row in cursor.fetchall():
    grade, standard, c, cr, ni, analogues = row

    # Split analogues
    analogue_list = analogues.split() if analogues else []

    for analogue in analogue_list:
        # Check if analogue is very short (1-3 chars, all digits or simple letters)
        if len(analogue) <= 3 and analogue.isdigit():
            # Check if this grade actually exists in database
            cursor.execute("SELECT standard, c, cr, ni FROM steel_grades WHERE grade = ?", (analogue,))
            analogue_data = cursor.fetchone()

            if analogue_data:
                ana_standard, ana_c, ana_cr, ana_ni = analogue_data

                # Check if current grade is high-alloy (stainless, tool steel, etc.)
                try:
                    cr_val = float(cr.split('-')[0].replace(',', '.')) if cr and '-' in str(cr) else float(cr) if cr else 0
                except:
                    cr_val = 0

                try:
                    # Parse analogue Cr
                    ana_cr_str = str(ana_cr) if ana_cr else '0'
                    ana_cr_val = float(ana_cr_str.split('-')[0].replace(',', '.').replace('до ', '').replace('≤', '').replace('≈', '').strip()) if ana_cr_str and ana_cr_str not in ['None', '', 'null'] else 0
                except:
                    ana_cr_val = 0

                # If current grade has high Cr (>5%) but analogue has low Cr (<2%), it's likely an error
                if cr_val > 5 and ana_cr_val < 2:
                    errors_found.append({
                        'grade': grade,
                        'standard': standard,
                        'cr': cr,
                        'wrong_analogue': analogue,
                        'analogue_standard': ana_standard,
                        'analogue_cr': ana_cr,
                        'analogues_full': analogues[:200]
                    })
                    short_grades.add(analogue)

print(f"\nFound {len(errors_found)} grades with suspicious short analogues")
print(f"Unique short analogues causing errors: {len(short_grades)}")

# Group by wrong analogue
from collections import defaultdict
by_analogue = defaultdict(list)
for err in errors_found:
    by_analogue[err['wrong_analogue']].append(err['grade'])

print("\n" + "="*100)
print("SHORT ANALOGUES CAUSING ERRORS:")
print("="*100)

for short_ana, affected_grades in sorted(by_analogue.items()):
    cursor.execute("SELECT standard, c, cr, ni FROM steel_grades WHERE grade = ?", (short_ana,))
    ana_data = cursor.fetchone()

    if ana_data:
        ana_standard, ana_c, ana_cr, ana_ni = ana_data
        print(f"\nShort analogue: '{short_ana}'")
        print(f"  Actually is: {ana_standard}")
        print(f"  Composition: C={ana_c}, Cr={ana_cr}, Ni={ana_ni}")
        print(f"  Incorrectly appears in {len(affected_grades)} grades:")
        for g in affected_grades[:5]:
            print(f"    - {g}")
        if len(affected_grades) > 5:
            print(f"    ... and {len(affected_grades) - 5} more")

print("\n" + "="*100)
print("SAMPLE ERRORS:")
print("="*100)

for i, err in enumerate(errors_found[:10], 1):
    print(f"\n{i}. Grade: {err['grade']} ({err['standard']})")
    print(f"   Cr: {err['cr']}")
    print(f"   Wrong analogue: '{err['wrong_analogue']}' ({err['analogue_standard']}, Cr={err['analogue_cr']})")
    print(f"   Full analogues: {err['analogues_full']}...")

if len(errors_found) > 10:
    print(f"\n... and {len(errors_found) - 10} more errors")

conn.close()

print("\n" + "="*100)
print("SUMMARY")
print("="*100)
print(f"Total errors found: {len(errors_found)}")
print(f"Unique short analogues: {sorted(short_grades)}")
print("="*100)
