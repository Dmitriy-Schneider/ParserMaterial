"""Rebuild all analogues from scratch using all data sources"""
import sqlite3
import csv
from pathlib import Path
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*100)
print("REBUILDING ANALOGUES FROM ALL SOURCES")
print("="*100)

# Step 1: Restore analogues from CSV export (contains zknives data)
print("\nStep 1: Restoring analogues from CSV export (zknives data)...")
csv_export_path = Path(__file__).parent.parent / 'database' / 'steel_database_export_20251029_153843.csv'

with open(csv_export_path, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f, delimiter=';')
    for row in reader:
        grade = row['grade']
        analogues = row['analogues']
        if analogues:
            cursor.execute("UPDATE steel_grades SET analogues = ? WHERE grade = ?",
                          (analogues, grade))

conn.commit()

cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE analogues IS NOT NULL AND analogues != ''")
restored_count = cursor.fetchone()[0]
print(f"Restored {restored_count} grades with zknives analogues")

# Step 2: Now ADD analogues from CSV files (complement, not replace)
print("\nStep 2: Adding analogues from CSV files to complement zknives data...")

# Step 3: Build analogue relationships from CSV files
print("\nStep 3: Building analogue relationships from CSV files...")

# Dictionary: grade_name -> set of analogues
analogue_map = defaultdict(set)

# Function to add bidirectional relationship
def add_relationship(grade1, grade2):
    if grade1 and grade2 and grade1 != grade2:
        analogue_map[grade1].add(grade2)
        analogue_map[grade2].add(grade1)

# CSV files to process (EXCLUDING Марки сталей.csv and Ножевые.csv)
csv_files = [
    ('Марки ВЭМ.csv', 'vem'),
    ('Аустенитные стали.csv', 'austenitic'),
    ('Дуплексные стали.csv', 'duplex'),
    ('Мартенситные.csv', 'martensitic'),
    ('Спец сплавы.csv', 'special'),
    ('Ферритные стали.csv', 'ferritic'),
]

for csv_file, category in csv_files:
    csv_path = Path(__file__).parent.parent / csv_file

    if not csv_path.exists():
        print(f"  WARNING: {csv_file} not found, skipping")
        continue

    print(f"\n  Processing: {csv_file}")

    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            if category == 'vem':
                # Марки ВЭМ: columns are Bohler, Uddeholm, Buderus, EN
                # Skip first line (header: "ХИМИЧЕСКИЙ СОСТАВ, %")
                f.readline()
                reader = csv.DictReader(f, delimiter=';')
                rows_processed = 0
                relationships_added = 0
                for row in reader:
                    rows_processed += 1
                    if rows_processed <= 1:  # Skip header row
                        continue
                    grades = []
                    for col in ['Bohler', 'Uddeholm', 'Buderus', 'EN']:
                        grade = row.get(col, '').strip().replace('®', '')
                        if grade:
                            grades.append(grade)

                    # Add all pairwise relationships
                    for i, g1 in enumerate(grades):
                        for g2 in grades[i+1:]:
                            add_relationship(g1, g2)
                            relationships_added += 1

                print(f"    Rows: {rows_processed}, Relationships: {relationships_added}")

            elif category in ['austenitic', 'duplex', 'martensitic', 'ferritic', 'special']:
                # Stainless steels: Марка AISI | UNS | EN
                reader = csv.DictReader(f, delimiter='|')
                for row in reader:
                    grades = []
                    for col in ['Марка AISI', 'UNS', 'EN']:
                        grade = row.get(col, '').strip().replace('®', '')
                        if grade:
                            grades.append(grade)

                    # Add all pairwise relationships
                    for i, g1 in enumerate(grades):
                        for g2 in grades[i+1:]:
                            add_relationship(g1, g2)

        print(f"    OK Processed {csv_file}")

    except Exception as e:
        print(f"    ERROR Error processing {csv_file}: {e}")

print(f"\n  Total grades with analogues: {len(analogue_map)}")

# Step 4: Merge new analogues with existing ones
print("\nStep 4: Merging CSV analogues with existing zknives analogues...")

# Get all grades in database
cursor.execute("SELECT grade, analogues FROM steel_grades")
db_data = {row[0]: row[1] for row in cursor.fetchall()}

updated_count = 0
new_grades_count = 0

for grade, new_analogues in analogue_map.items():
    # Filter analogues - only include those that exist in database
    valid_new_analogues = set([a for a in new_analogues if a in db_data])

    if not valid_new_analogues:
        continue

    if grade in db_data:
        # Merge with existing analogues
        existing_analogues_str = db_data[grade]
        if existing_analogues_str:
            existing_analogues = set(existing_analogues_str.split())
        else:
            existing_analogues = set()

        # Combine existing and new (remove duplicates)
        combined_analogues = existing_analogues | valid_new_analogues

        # Sort and join
        analogues_str = ' '.join(sorted(combined_analogues))

        # Update only if changed
        if analogues_str != existing_analogues_str:
            cursor.execute("UPDATE steel_grades SET analogues = ? WHERE grade = ?",
                          (analogues_str, grade))
            updated_count += 1
    else:
        # This grade doesn't exist in database - create it
        analogues_str = ' '.join(sorted(valid_new_analogues))
        cursor.execute("""
            INSERT INTO steel_grades (grade, analogues)
            VALUES (?, ?)
        """, (grade, analogues_str))
        new_grades_count += 1

    if (updated_count + new_grades_count) % 500 == 0:
        print(f"  Processed {updated_count + new_grades_count} grades...")

conn.commit()

print(f"\n  Merged analogues for {updated_count} existing grades")
print(f"  Created {new_grades_count} new grades")

# Step 5: Verify results
print("\nStep 5: Verification...")

cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE analogues IS NOT NULL AND analogues != ''")
with_analogues = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM steel_grades")
total = cursor.fetchone()[0]

print(f"  Total grades in database: {total}")
print(f"  Grades with analogues: {with_analogues}")

# Check specific grades
print("\n  Checking specific grades:")
for grade_name in ['#20', 'Conqueror SuperClean', '1.2343', 'ExStahl SuperClean']:
    cursor.execute("SELECT analogues FROM steel_grades WHERE grade = ?", (grade_name,))
    r = cursor.fetchone()
    if r and r[0]:
        ana_count = len(r[0].split())
        ana_preview = r[0][:80] + "..." if len(r[0]) > 80 else r[0]
        print(f"    {grade_name}: {ana_count} analogues")
        print(f"      {ana_preview}")
    else:
        print(f"    {grade_name}: NO ANALOGUES or NOT FOUND")

conn.close()

print("\n" + "="*100)
print("ANALOGUE REBUILD COMPLETE")
print("="*100)
print("\nNOTE: This rebuild includes ONLY relationships from CSV files.")
print("zknives analogues were NOT included (they were in the original database).")
print("If you want zknives analogues too, need to re-parse zknives or restore from backup.")
