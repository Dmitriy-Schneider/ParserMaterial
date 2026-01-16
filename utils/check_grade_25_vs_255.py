"""Check grade 25 vs 255 issue in duplex steels"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*100)
print("CHECKING GRADE 25 vs 255 ISSUE")
print("="*100)

# Check grade 25
print("\n1. Grade 25 (carbon steel):")
cursor.execute("SELECT grade, standard, c, cr, ni, mo FROM steel_grades WHERE grade = '25'")
r = cursor.fetchone()
if r:
    print(f"   Standard: {r[1]}")
    print(f"   Composition: C={r[2]}, Cr={r[3]}, Ni={r[4]}, Mo={r[5]}")
else:
    print("   NOT FOUND")

# Check grade 255
print("\n2. Grade 255 (duplex/super duplex stainless):")
cursor.execute("SELECT grade, standard, c, cr, ni, mo, analogues FROM steel_grades WHERE grade = '255'")
r = cursor.fetchone()
if r:
    print(f"   Standard: {r[1]}")
    print(f"   Composition: C={r[2]}, Cr={r[3]}, Ni={r[4]}, Mo={r[5]}")
    print(f"   Analogues: {r[6][:150]}...")
else:
    print("   NOT FOUND")

# Check duplex steels 1.4501 and 1.4507
print("\n" + "="*100)
print("DUPLEX STEELS WITH '25' IN ANALOGUES")
print("="*100)

cursor.execute("""
    SELECT grade, standard, c, cr, ni, mo, analogues
    FROM steel_grades
    WHERE grade IN ('1.4501', '1.4507')
""")

for row in cursor.fetchall():
    grade, standard, c, cr, ni, mo, analogues = row
    print(f"\nGrade: {grade}")
    print(f"  Standard: {standard}")
    print(f"  Composition: C={c}, Cr={cr}, Ni={ni}, Mo={mo}")
    print(f"  Analogues: {analogues[:200]}...")

    # Check if '25' is in analogues
    if analogues and ' 25 ' in f' {analogues} ':
        print(f"  ERROR: Contains '25' (carbon steel) - should be '255' (duplex)")

# Find all duplex/super duplex steels with '25' in analogues
print("\n" + "="*100)
print("ALL GRADES WITH '25' IN ANALOGUES (potential errors)")
print("="*100)

cursor.execute("""
    SELECT grade, standard, c, cr, ni, mo, analogues
    FROM steel_grades
    WHERE analogues LIKE '% 25 %' OR analogues LIKE '25 %' OR analogues LIKE '% 25'
    ORDER BY grade
""")

results = cursor.fetchall()
print(f"\nTotal grades with '25' in analogues: {len(results)}")

for row in results[:20]:
    grade, standard, c, cr, ni, mo, analogues = row
    print(f"\nGrade: {grade}")
    print(f"  Standard: {standard}")

    # Check if it's duplex/super duplex (high Cr, low Ni, some Mo)
    try:
        cr_val = float(cr.split('-')[0].replace(',', '.')) if cr and '-' in str(cr) else float(cr) if cr else 0
        ni_val = float(ni.split('-')[0].replace(',', '.')) if ni and '-' in str(ni) else float(ni) if ni else 0

        is_duplex = cr_val > 20 and ni_val < 15  # Duplex typically: Cr 20-28%, Ni 3-8%

        if is_duplex:
            print(f"  Type: DUPLEX/SUPER DUPLEX (Cr={cr}, Ni={ni})")
            print(f"  ERROR: '25' should likely be '255'")
        else:
            print(f"  Type: Regular steel (Cr={cr}, Ni={ni})")
    except:
        print(f"  Type: Unknown (Cr={cr}, Ni={ni})")

    print(f"  Analogues: {analogues[:150]}...")

conn.close()
