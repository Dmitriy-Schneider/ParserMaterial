"""
Fix short analogues errors
Remove short grade names (like '10', '2', '3', etc.) from analogues of high-alloy steels
"""
import sqlite3
import re
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*100)
print("FIXING SHORT ANALOGUES ERRORS")
print("="*100)

# List of short analogues that are incorrectly added (from previous analysis)
# These are mostly GOST carbon/low-alloy steels that got mixed with stainless steels
SHORT_ANALOGUES_TO_REMOVE = [
    '1', '2', '3', '10', '20', '25', '27', '30', '35', '37',
    '45', '50', '60', '75', '718', '760'
]

print(f"\nShort analogues to remove: {SHORT_ANALOGUES_TO_REMOVE}")
print(f"Total: {len(SHORT_ANALOGUES_TO_REMOVE)} different short analogues")

# Find all grades with these short analogues
cursor.execute("""
    SELECT id, grade, standard, c, cr, ni, analogues
    FROM steel_grades
    WHERE analogues IS NOT NULL AND analogues != ''
    ORDER BY grade
""")

fixed_count = 0
total_removals = 0

for row in cursor.fetchall():
    grade_id, grade, standard, c, cr, ni, analogues = row

    # Split analogues
    analogue_list = analogues.split() if analogues else []

    # Check if current grade is high-alloy (Cr > 5%)
    try:
        cr_val = float(cr.split('-')[0].replace(',', '.')) if cr and '-' in str(cr) else float(cr) if cr else 0
    except:
        cr_val = 0

    # Only fix high-alloy grades (Cr > 5%)
    if cr_val <= 5:
        continue

    # Remove short analogues that shouldn't be there
    original_count = len(analogue_list)
    cleaned_analogues = []

    for analogue in analogue_list:
        if analogue in SHORT_ANALOGUES_TO_REMOVE:
            # Check if this analogue actually exists and is low-alloy
            cursor.execute("SELECT standard, c, cr FROM steel_grades WHERE grade = ?", (analogue,))
            ana_data = cursor.fetchone()

            if ana_data:
                ana_standard, ana_c, ana_cr = ana_data

                # Parse analogue Cr
                try:
                    ana_cr_str = str(ana_cr) if ana_cr else '0'
                    ana_cr_val = float(ana_cr_str.split('-')[0].replace(',', '.').replace('до ', '').replace('≤', '').replace('≈', '').strip()) if ana_cr_str and ana_cr_str not in ['None', '', 'null'] else 0
                except:
                    ana_cr_val = 0

                # If analogue has low Cr (<2%), remove it from high-alloy grade
                if ana_cr_val < 2:
                    total_removals += 1
                    print(f"  Removing '{analogue}' from {grade} (Cr {cr} -> analogue Cr {ana_cr})")
                    continue

        # Keep this analogue
        cleaned_analogues.append(analogue)

    # Update if changes were made
    if len(cleaned_analogues) != original_count:
        new_analogues = ' '.join(cleaned_analogues) if cleaned_analogues else None

        cursor.execute("UPDATE steel_grades SET analogues = ? WHERE id = ?",
                      (new_analogues, grade_id))
        fixed_count += 1

        if fixed_count <= 20:  # Show first 20 examples
            print(f"\n{fixed_count}. Fixed: {grade}")
            print(f"   Old analogues: {analogues[:100]}...")
            print(f"   New analogues: {new_analogues[:100] if new_analogues else 'None'}...")

# Commit changes
conn.commit()

print("\n" + "="*100)
print("SUMMARY")
print("="*100)
print(f"Total grades fixed: {fixed_count}")
print(f"Total short analogues removed: {total_removals}")
print(f"\nChanges committed to database!")
print("="*100)

# Verify specific grade (304)
cursor.execute("SELECT analogues FROM steel_grades WHERE grade = '304'")
result = cursor.fetchone()
if result:
    print(f"\nVerification - Grade 304 analogues:")
    print(f"  {result[0][:150]}...")
    if '10' in result[0].split():
        print("  ERROR: '10' still present!")
    else:
        print("  OK: '10' removed successfully")

conn.close()
