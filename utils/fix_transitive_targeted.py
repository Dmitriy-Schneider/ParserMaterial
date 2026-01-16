"""Targeted transitive analogues - multiple passes for grades with few analogues"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*100)
print("TARGETED TRANSITIVE ANALOGUES FIX")
print("="*100)

# Multiple passes
num_passes = 3

for pass_num in range(num_passes):
    print(f"\nPass {pass_num + 1}/{num_passes}...")
    print("-" * 100)
    
    # Find grades with < 20 analogues
    cursor.execute("""
        SELECT grade, analogues
        FROM steel_grades
        WHERE analogues IS NOT NULL AND analogues != ''
    """)
    
    all_grades = cursor.fetchall()
    
    updates = {}
    
    for grade, analogues in all_grades:
        ana_list = analogues.split() if analogues else []
        
        if len(ana_list) < 20 and len(ana_list) > 0:
            # Take all analogues from first analogue
            first_ana = ana_list[0]
            
            cursor.execute("SELECT analogues FROM steel_grades WHERE grade = ?", (first_ana,))
            donor_result = cursor.fetchone()
            
            if donor_result and donor_result[0]:
                donor_list = donor_result[0].split()
                
                # Merge
                merged = set(ana_list) | set(donor_list)
                merged.discard(grade)  # Remove self
                
                if len(merged) > len(ana_list):
                    updates[grade] = ' '.join(sorted(merged))
    
    # Apply updates
    for grade, new_analogues in updates.items():
        cursor.execute("UPDATE steel_grades SET analogues = ? WHERE grade = ?", (new_analogues, grade))
    
    conn.commit()
    
    print(f"  Updated {len(updates)} grades")

print("\n" + "="*100)
print("CHECKING RESULTS")
print("="*100)

# Check specific examples
for test_grade in ['Conqueror SuperClean', 'ExStahl SuperClean', '1.2343', '1.2367']:
    cursor.execute("SELECT analogues FROM steel_grades WHERE grade = ?", (test_grade,))
    r = cursor.fetchone()
    if r and r[0]:
        count = len(r[0].split())
        print(f"{test_grade:30s} - {count} analogues")
    else:
        print(f"{test_grade:30s} - NOT FOUND")

conn.close()
print("\nDone!")
