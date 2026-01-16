"""Find grades without chemical composition but with analogues"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*100)
print("GRADES WITHOUT CHEMISTRY BUT WITH ANALOGUES")
print("="*100)

# Find grades without chemistry (no C, Cr, Ni, Mo, etc.)
cursor.execute("""
    SELECT grade, standard, analogues
    FROM steel_grades
    WHERE (c IS NULL OR c = '')
      AND (cr IS NULL OR cr = '')
      AND (ni IS NULL OR ni = '')
      AND (mo IS NULL OR mo = '')
      AND (analogues IS NOT NULL AND analogues != '')
    ORDER BY grade
""")

grades_without_chem = cursor.fetchall()

print(f"\nFound {len(grades_without_chem)} grades without chemistry but with analogues\n")

# Show first 20 examples
for i, (grade, standard, analogues) in enumerate(grades_without_chem[:20]):
    analogue_list = analogues.split()[:5]  # First 5 analogues
    print(f"{i+1}. {grade:30s} (Standard: {standard})")
    print(f"   Analogues: {', '.join(analogue_list)}...")
    
    # Check if first analogue has chemistry
    if analogue_list:
        first_ana = analogue_list[0]
        cursor.execute("SELECT c, cr, ni FROM steel_grades WHERE grade = ?", (first_ana,))
        ana_chem = cursor.fetchone()
        if ana_chem and any(ana_chem):
            print(f"   -> First analogue '{first_ana}' HAS chemistry: C={ana_chem[0]}, Cr={ana_chem[1]}, Ni={ana_chem[2]}")
        else:
            print(f"   -> First analogue '{first_ana}' also has NO chemistry")
    print()

if len(grades_without_chem) > 20:
    print(f"... and {len(grades_without_chem) - 20} more grades\n")

print("="*100)
print("SUMMARY")
print("="*100)
print(f"Grades without chemistry but with analogues: {len(grades_without_chem)}")

conn.close()
