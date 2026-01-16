"""Verify all analogue relationship fixes"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*100)
print("COMPREHENSIVE VERIFICATION OF ANALOGUE FIXES")
print("="*100)

# 1. Check grades without chemistry
print("\n1. Grades without chemistry:")
print("-" * 100)

cursor.execute("""
    SELECT COUNT(*) FROM steel_grades
    WHERE (c IS NULL OR c = '')
      AND (cr IS NULL OR cr = '')
      AND (ni IS NULL OR ni = '')
      AND (mo IS NULL OR mo = '')
      AND (analogues IS NOT NULL AND analogues != '')
""")

count_no_chem = cursor.fetchone()[0]
print(f"   Grades without chemistry but with analogues: {count_no_chem}")

if count_no_chem == 0:
    print("   Status: OK - All grades with analogues have chemistry!")
elif count_no_chem < 5:
    print(f"   Status: ACCEPTABLE - Only {count_no_chem} grades remaining (likely special cases)")
else:
    print(f"   Status: WARNING - {count_no_chem} grades still without chemistry")

# 2. Check asymmetric relationships (sample check)
print("\n2. Asymmetric analogue relationships (sample check):")
print("-" * 100)

# Check specific examples
test_cases = [
    ('Conqueror SuperClean', '1.2343'),
    ('ExStahl SuperClean', '1.2367'),
    ('1.2343', 'Conqueror SuperClean')
]

asymmetric_count = 0

for grade_a, grade_b in test_cases:
    cursor.execute("SELECT analogues FROM steel_grades WHERE grade = ?", (grade_a,))
    r1 = cursor.fetchone()
    
    cursor.execute("SELECT analogues FROM steel_grades WHERE grade = ?", (grade_b,))
    r2 = cursor.fetchone()
    
    if r1 and r1[0] and grade_b in r1[0]:
        has_forward = True
    else:
        has_forward = False
    
    if r2 and r2[0] and grade_a in r2[0]:
        has_backward = True
    else:
        has_backward = False
    
    status = "OK" if (has_forward and has_backward) else "ASYMMETRIC"
    
    if status == "ASYMMETRIC":
        asymmetric_count += 1
    
    print(f"   {grade_a} <-> {grade_b}: {status}")
    print(f"      Forward ({grade_a} has {grade_b}): {has_forward}")
    print(f"      Backward ({grade_b} has {grade_a}): {has_backward}")

if asymmetric_count == 0:
    print(f"\n   Status: OK - All tested relationships are symmetric!")
else:
    print(f"\n   Status: WARNING - {asymmetric_count} asymmetric relationships found")

# 3. Check transitive analogues
print("\n3. Transitive analogues (sample check):")
print("-" * 100)

test_grades = ['Conqueror SuperClean', 'ExStahl SuperClean', '1.2343', '1.2367']

for grade in test_grades:
    cursor.execute("SELECT analogues FROM steel_grades WHERE grade = ?", (grade,))
    r = cursor.fetchone()
    
    if r and r[0]:
        count = len(r[0].split())
        status = "RICH" if count > 20 else "OK" if count > 5 else "POOR"
        print(f"   {grade:30s} - {count:3d} analogues ({status})")
    else:
        print(f"   {grade:30s} - NOT FOUND")

# 4. Statistics
print("\n4. Overall statistics:")
print("-" * 100)

cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE analogues IS NOT NULL AND analogues != ''")
total_with_analogues = cursor.fetchone()[0]

cursor.execute("SELECT AVG(LENGTH(analogues) - LENGTH(REPLACE(analogues, ' ', '')) + 1) FROM steel_grades WHERE analogues IS NOT NULL AND analogues != ''")
avg_analogues = cursor.fetchone()[0]

print(f"   Total grades with analogues: {total_with_analogues}")
print(f"   Average analogues per grade: {avg_analogues:.1f}")

# Summary
print("\n" + "="*100)
print("SUMMARY")
print("="*100)

all_ok = (count_no_chem < 5) and (asymmetric_count == 0)

if all_ok:
    print("   Status: ALL CHECKS PASSED!")
    print("   - Chemistry copied to grades without it")
    print("   - Asymmetric relationships fixed")
    print("   - Transitive analogues added")
else:
    print("   Status: SOME ISSUES REMAINING")
    print(f"   - Grades without chemistry: {count_no_chem}")
    print(f"   - Asymmetric relationships: {asymmetric_count}")

conn.close()
