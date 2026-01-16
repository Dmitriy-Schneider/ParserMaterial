"""Copy chemistry from analogues to grades without chemistry"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*100)
print("COPYING CHEMISTRY FROM ANALOGUES")
print("="*100)

# Get all chemical element columns
chem_columns = ['c', 'cr', 'ni', 'mo', 'v', 'w', 'co', 'mn', 'si', 's', 'p', 'cu', 'nb', 'n', 'other_elements']

# Find grades without chemistry but with analogues
cursor.execute("""
    SELECT grade, analogues
    FROM steel_grades
    WHERE (c IS NULL OR c = '')
      AND (cr IS NULL OR cr = '')
      AND (ni IS NULL OR ni = '')
      AND (mo IS NULL OR mo = '')
      AND (analogues IS NOT NULL AND analogues != '')
""")

grades_without_chem = cursor.fetchall()

print(f"\nFound {len(grades_without_chem)} grades without chemistry\n")

fixed_count = 0

for grade, analogues in grades_without_chem:
    if not analogues:
        continue
    
    ana_list = analogues.split()
    
    # Try to find first analogue with chemistry
    donor_grade = None
    donor_chem = None
    
    for analogue in ana_list[:10]:  # Check first 10 analogues
        # Get chemistry from analogue
        query = f"SELECT {', '.join(chem_columns)} FROM steel_grades WHERE grade = ?"
        cursor.execute(query, (analogue,))
        ana_chem = cursor.fetchone()
        
        if ana_chem and any(ana_chem[:4]):  # Has at least one of C, Cr, Ni, Mo
            donor_grade = analogue
            donor_chem = ana_chem
            break
    
    if donor_grade and donor_chem:
        # Copy chemistry
        set_parts = []
        values = []
        
        for i, col in enumerate(chem_columns):
            if donor_chem[i]:
                set_parts.append(f"{col} = ?")
                values.append(donor_chem[i])
        
        if set_parts:
            values.append(grade)
            update_query = f"UPDATE steel_grades SET {', '.join(set_parts)} WHERE grade = ?"
            cursor.execute(update_query, values)
            
            fixed_count += 1
            
            if fixed_count <= 10:
                print(f"{fixed_count}. {grade:30s} <- copied from {donor_grade}")
                print(f"   C={donor_chem[0]}, Cr={donor_chem[1]}, Ni={donor_chem[2]}, Mo={donor_chem[3]}")

conn.commit()

print(f"\n{'.'*100}")
print(f"Total grades fixed: {fixed_count}")
print("="*100)

conn.close()
