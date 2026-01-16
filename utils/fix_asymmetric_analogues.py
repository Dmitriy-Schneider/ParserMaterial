"""Fix asymmetric analogue relationships - make them bidirectional"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*100)
print("FIXING ASYMMETRIC ANALOGUE RELATIONSHIPS")
print("="*100)

# Get all grades with analogues
cursor.execute("SELECT grade, analogues FROM steel_grades WHERE analogues IS NOT NULL AND analogues != ''")
all_grades = cursor.fetchall()

print(f"\nProcessing {len(all_grades)} grades...\n")

fixed_count = 0
updates = {}  # grade -> set of analogues to add

for grade, analogues in all_grades:
    if not analogues:
        continue
    
    ana_list = analogues.split()
    
    for analogue in ana_list:
        # Check if analogue has grade in its analogues
        cursor.execute("SELECT analogues FROM steel_grades WHERE grade = ?", (analogue,))
        ana_result = cursor.fetchone()
        
        if ana_result:
            ana_analogues = ana_result[0].split() if ana_result[0] else []
            
            if grade not in ana_analogues:
                # Need to add grade to analogue's analogues
                if analogue not in updates:
                    updates[analogue] = set(ana_analogues)
                
                updates[analogue].add(grade)
                fixed_count += 1

print(f"Found {fixed_count} asymmetric relationships to fix")
print(f"Updating {len(updates)} grades...\n")

# Apply updates
update_count = 0
for grade, new_analogues_set in updates.items():
    # Get current analogues
    cursor.execute("SELECT analogues FROM steel_grades WHERE grade = ?", (grade,))
    current = cursor.fetchone()
    current_list = current[0].split() if current and current[0] else []
    
    new_analogues_str = ' '.join(sorted(new_analogues_set))
    
    cursor.execute("UPDATE steel_grades SET analogues = ? WHERE grade = ?", (new_analogues_str, grade))
    update_count += 1
    
    added_count = len(new_analogues_set) - len(current_list)
    
    if update_count <= 10:
        print(f"{update_count}. {grade:30s} - added {added_count} new analogues (was {len(current_list)}, now {len(new_analogues_set)})")

conn.commit()

print(f"\n{'.'*100}")
print(f"Total asymmetric relationships fixed: {fixed_count}")
print(f"Total grades updated: {update_count}")
print("="*100)

conn.close()
