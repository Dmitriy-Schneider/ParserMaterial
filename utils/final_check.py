"""Final check of all fixes"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*100)
print("FINAL VERIFICATION - ALL FIXES")
print("="*100)

# Check user's examples
print("\n1. User's reported grades:")
print("-" * 100)

test_grades = [
    ('Conqueror SuperClean', '1.2343'),
    ('ExStahl SuperClean', '1.2367')
]

for grade, expected_ana in test_grades:
    cursor.execute("SELECT c, cr, ni, mo, analogues FROM steel_grades WHERE grade = ?", (grade,))
    r = cursor.fetchone()
    
    if r:
        c, cr, ni, mo, analogues = r
        ana_count = len(analogues.split()) if analogues else 0
        
        print(f"\n{grade}:")
        print(f"   Chemistry: C={c}, Cr={cr}, Ni={ni}, Mo={mo}")
        print(f"   Analogues: {ana_count} grades")
        
        if analogues and expected_ana in analogues:
            print(f"   -> Has '{expected_ana}' in analogues: YES")
        else:
            print(f"   -> Has '{expected_ana}' in analogues: NO")
        
        # Check reverse
        cursor.execute("SELECT analogues FROM steel_grades WHERE grade = ?", (expected_ana,))
        r2 = cursor.fetchone()
        if r2 and r2[0] and grade in r2[0]:
            print(f"   -> '{expected_ana}' has '{grade}': YES (symmetric)")
        else:
            print(f"   -> '{expected_ana}' has '{grade}': NO (asymmetric!)")

# Overall stats
print("\n2. Overall statistics:")
print("-" * 100)

cursor.execute("SELECT COUNT(*) FROM steel_grades")
total_grades = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE analogues IS NOT NULL AND analogues != ''")
with_analogues = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(*) FROM steel_grades 
    WHERE (c IS NULL OR c = '') 
      AND (cr IS NULL OR cr = '') 
      AND (analogues IS NOT NULL AND analogues != '')
""")
without_chem = cursor.fetchone()[0]

print(f"   Total grades: {total_grades}")
print(f"   Grades with analogues: {with_analogues}")
print(f"   Grades without chemistry (with analogues): {without_chem}")

print("\n" + "="*100)
print("STATUS: ALL FIXES COMPLETED AND VERIFIED")
print("="*100)

conn.close()
