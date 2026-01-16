"""Add transitive analogues - optimized version
Only for grades with few analogues, copy from first "rich" analogue
"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*100)
print("ADDING TRANSITIVE ANALOGUES (OPTIMIZED)")
print("="*100)

# Find grades with few analogues (< 5)
cursor.execute("""
    SELECT grade, analogues
    FROM steel_grades
    WHERE analogues IS NOT NULL AND analogues != ''
""")

all_grades = cursor.fetchall()

print(f"\nAnalyzing {len(all_grades)} grades...\n")

# Filter grades with few analogues
poor_grades = []
for grade, analogues in all_grades:
    ana_list = analogues.split() if analogues else []
    if len(ana_list) < 5 and len(ana_list) > 0:
        poor_grades.append((grade, ana_list))

print(f"Found {len(poor_grades)} grades with < 5 analogues\n")

# For each poor grade, find a rich analogue and copy its analogues
fixed_count = 0

for grade, ana_list in poor_grades:
    # Find first analogue with many analogues
    donor_grade = None
    donor_analogues = []
    
    for analogue in ana_list[:5]:  # Check first 5
        cursor.execute("SELECT analogues FROM steel_grades WHERE grade = ?", (analogue,))
        result = cursor.fetchone()
        
        if result and result[0]:
            donor_ana_list = result[0].split()
            if len(donor_ana_list) > 10:  # Rich analogue
                donor_grade = analogue
                donor_analogues = donor_ana_list
                break
    
    if donor_grade and donor_analogues:
        # Merge: current + donor analogues
        merged = set(ana_list) | set(donor_analogues)
        merged.discard(grade)  # Remove self
        
        new_analogues_str = ' '.join(sorted(merged))
        
        cursor.execute("UPDATE steel_grades SET analogues = ? WHERE grade = ?", (new_analogues_str, grade))
        
        fixed_count += 1
        
        if fixed_count <= 15:
            print(f"{fixed_count}. {grade:30s} - copied from {donor_grade} (was {len(ana_list)}, now {len(merged)})")

conn.commit()

print(f"\n{'.'*100}")
print(f"Total grades enriched with transitive analogues: {fixed_count}")
print("="*100)

# Check specific examples
print("\nChecking specific examples:")
print("-" * 100)

for test_grade in ['Conqueror SuperClean', 'ExStahl']:
    cursor.execute("SELECT analogues FROM steel_grades WHERE grade = ?", (test_grade,))
    r = cursor.fetchone()
    if r and r[0]:
        ana_count = len(r[0].split())
        print(f"{test_grade:30s} - {ana_count} analogues")

conn.close()
