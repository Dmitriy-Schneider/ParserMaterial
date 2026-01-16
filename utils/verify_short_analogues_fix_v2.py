"""Verify short analogues fix - improved version with exact word matching"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*100)
print("VERIFICATION OF SHORT ANALOGUES FIX (EXACT WORD MATCHING)")
print("="*100)

# Check grade 304
print("\n1. Checking grade 304 (user reported):")
cursor.execute("SELECT grade, standard, analogues FROM steel_grades WHERE grade = '304'")
r = cursor.fetchone()

if r:
    grade, standard, analogues = r
    print(f"   Grade: {grade}")
    print(f"   Standard: {standard}")
    print(f"   Analogues: {analogues[:200] if analogues else 'None'}...")

    # Check if '10' is present as standalone word
    analogue_list = analogues.split() if analogues else []
    if '10' in analogue_list:
        print(f"   ERROR: '10' still present in analogues!")
    else:
        print(f"   OK: '10' removed successfully!")

# Check other high-alloy grades with short analogues
SHORT_ANALOGUES = ['1', '2', '3', '10', '20', '25', '27', '30', '35', '37', '45', '50', '60', '75', '718', '760']

print("\n2. Checking all high-alloy grades for short analogues:")

def parse_cr(cr_value):
    """Parse Cr value to float"""
    if not cr_value:
        return 0
    try:
        cr_str = str(cr_value[0]) if isinstance(cr_value, tuple) else str(cr_value)
        if '-' in cr_str:
            cr_str = cr_str.split('-')[0]
        return float(cr_str.replace(',', '.'))
    except:
        return 0

error_count = 0
error_details = {}

# Get all grades with analogues
cursor.execute("SELECT grade, cr, analogues FROM steel_grades WHERE analogues IS NOT NULL AND analogues != ''")
all_grades = cursor.fetchall()

print(f"   Checking {len(all_grades)} grades with analogues...")

for grade, cr, analogues in all_grades:
    # Parse Cr content
    cr_val = parse_cr((cr,))

    # Only check high-alloy grades (Cr > 5%)
    if cr_val <= 5:
        continue

    # Split analogues by space and check for exact matches
    analogue_list = analogues.split() if analogues else []

    for short_ana in SHORT_ANALOGUES:
        if short_ana in analogue_list:
            # Verify it's a low-alloy steel by checking in database
            cursor.execute("SELECT cr FROM steel_grades WHERE grade = ?", (short_ana,))
            ana_result = cursor.fetchone()

            if ana_result:
                ana_cr_val = parse_cr(ana_result)

                # If the analogue is low-alloy (Cr < 2%), it's an error
                if ana_cr_val < 2:
                    error_count += 1

                    if short_ana not in error_details:
                        error_details[short_ana] = []

                    error_details[short_ana].append({
                        'grade': grade,
                        'cr': cr_val,
                        'analogue_cr': ana_cr_val
                    })

# Print results
print(f"\n3. Detailed results:")

if error_count == 0:
    print("   OK: No short analogues found in high-alloy steels!")
else:
    print(f"   ERROR: Found {error_count} cases of short analogues in high-alloy steels:")

    for short_ana, cases in sorted(error_details.items()):
        print(f"\n   Short analogue '{short_ana}' found in {len(cases)} grades:")

        # Show first 5 examples
        for i, case in enumerate(cases[:5]):
            print(f"      - {case['grade']} (Cr={case['cr']:.1f}%) has '{short_ana}' (Cr={case['analogue_cr']:.2f}%)")

        if len(cases) > 5:
            print(f"      ... and {len(cases) - 5} more cases")

# Summary
print("\n" + "="*100)
print("SUMMARY")
print("="*100)

if error_count == 0:
    print("   ALL FIXED: No short analogues found in high-alloy steels!")
    print("   The fix was successful.")
else:
    print(f"   ERROR: {error_count} cases still have short analogues!")
    print("   Need additional investigation.")

conn.close()
