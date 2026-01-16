"""Find asymmetric analogue relationships"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*100)
print("ASYMMETRIC ANALOGUE RELATIONSHIPS")
print("="*100)

# Check specific example: Conqueror SuperClean <-> 1.2343
print("\n1. Checking user's example: Conqueror SuperClean <-> 1.2343")
print("-" * 100)

cursor.execute("SELECT grade, analogues FROM steel_grades WHERE grade = 'Conqueror SuperClean'")
r = cursor.fetchone()
if r:
    grade, analogues = r
    ana_list = analogues.split() if analogues else []
    print(f"Conqueror SuperClean analogues: {', '.join(ana_list[:10])}...")
    
    if '1.2343' in ana_list:
        print("   -> Has 1.2343 in analogues: YES")
    else:
        print("   -> Has 1.2343 in analogues: NO (ERROR!)")

cursor.execute("SELECT grade, analogues FROM steel_grades WHERE grade = '1.2343'")
r = cursor.fetchone()
if r:
    grade, analogues = r
    ana_list = analogues.split() if analogues else []
    print(f"\n1.2343 analogues: {', '.join(ana_list[:10])}...")
    
    if 'Conqueror' in analogues or 'SuperClean' in analogues:
        print("   -> Has Conqueror SuperClean in analogues: YES")
    else:
        print("   -> Has Conqueror SuperClean in analogues: NO (ERROR!)")

# Find all asymmetric relationships
print("\n2. Finding all asymmetric relationships...")
print("-" * 100)

cursor.execute("SELECT grade, analogues FROM steel_grades WHERE analogues IS NOT NULL AND analogues != ''")
all_grades = cursor.fetchall()

asymmetric = []
checked_pairs = set()

for grade, analogues in all_grades[:500]:  # Check first 500 to avoid timeout
    if not analogues:
        continue
    
    ana_list = analogues.split()
    
    for analogue in ana_list[:20]:  # Check first 20 analogues
        pair_key = tuple(sorted([grade, analogue]))
        
        if pair_key in checked_pairs:
            continue
        
        checked_pairs.add(pair_key)
        
        # Check if analogue has grade in its analogues
        cursor.execute("SELECT analogues FROM steel_grades WHERE grade = ?", (analogue,))
        ana_result = cursor.fetchone()
        
        if ana_result and ana_result[0]:
            ana_analogues = ana_result[0].split()
            
            if grade not in ana_analogues:
                asymmetric.append((grade, analogue))

print(f"Found {len(asymmetric)} asymmetric relationships (checked {len(checked_pairs)} pairs)")

if asymmetric:
    print("\nExamples of asymmetric relationships (first 15):")
    for i, (grade_a, grade_b) in enumerate(asymmetric[:15]):
        print(f"   {i+1}. {grade_a} -> {grade_b} (but {grade_b} does NOT have {grade_a})")

print("\n" + "="*100)
print("SUMMARY")
print("="*100)
print(f"Grades without chemistry: 23")
print(f"Asymmetric analogue relationships found: {len(asymmetric)}")
print(f"\nNeed to:")
print("1. Copy chemistry from analogues to grades without chemistry")
print("2. Fix asymmetric relationships (make bidirectional)")
print("3. Add transitive analogues (if A->B and B->C, then A->C)")

conn.close()
