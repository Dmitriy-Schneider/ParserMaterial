"""
Update existing Standard column values to include country information
Examples:
- GOST -> GOST, Россия
- AISI -> AISI, США
- DIN -> DIN, Германия
"""
import sqlite3
import re
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'

print("="*100)
print("UPDATING STANDARD COLUMN WITH COUNTRY INFORMATION")
print("="*100)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all grades with Standard set
cursor.execute("SELECT id, grade, standard FROM steel_grades WHERE standard IS NOT NULL AND standard != ''")
rows = cursor.fetchall()

print(f"\nFound {len(rows)} grades with Standard column set")
print("\nUpdating...")

updated_count = 0
skip_count = 0

# Mapping of standards to countries
standard_mapping = {
    'GOST': 'GOST, Россия',
    'DIN': 'DIN, Германия',
    'EN': 'EN, Европа',
    'AISI': 'AISI, США',
    'ASTM': 'ASTM, США',
    'JIS': 'JIS, Япония',
    'GB': 'GB, Китай',
    'ISO': 'ISO, Международный',
    'SAE': 'SAE, США',
    'UNS': 'UNS, США',
}

for row_id, grade, standard in rows:
    # Skip if already has country (contains comma)
    if ',' in standard:
        skip_count += 1
        continue

    # Try to match exact standard
    updated_standard = None

    # Check if it's just a standard name without number
    if standard in standard_mapping:
        updated_standard = standard_mapping[standard]
    else:
        # Check if it matches a pattern like "GOST 12345-78" or "ГОСТ Р19903-74"
        # Check for Cyrillic ГОСТ first
        if standard.startswith('ГОСТ') or standard.startswith('ГОС'):
            updated_standard = f"{standard}, Россия"
        else:
            # Check other standards
            for std_prefix, std_with_country in standard_mapping.items():
                if standard.startswith(std_prefix):
                    # Extract the country part and add
                    country = std_with_country.split(', ')[1]
                    updated_standard = f"{standard}, {country}"
                    break

    if updated_standard:
        cursor.execute("UPDATE steel_grades SET standard = ? WHERE id = ?", (updated_standard, row_id))
        updated_count += 1

        if updated_count <= 10:  # Show first 10 examples
            print(f"  {grade}: '{standard}' -> '{updated_standard}'")

conn.commit()

print(f"\n" + "="*100)
print(f"COMPLETE")
print(f"="*100)
print(f"Total processed: {len(rows)}")
print(f"Updated: {updated_count}")
print(f"Skipped (already has country): {skip_count}")
print(f"Unchanged: {len(rows) - updated_count - skip_count}")

# Verify
cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE standard LIKE '%,%'")
with_country = cursor.fetchone()[0]
print(f"\nGrades with country in Standard: {with_country}")

# Show samples
print("\nSample updated records:")
cursor.execute("SELECT grade, standard FROM steel_grades WHERE standard LIKE '%,%' LIMIT 10")
for grade, standard in cursor.fetchall():
    print(f"  {grade}: {standard}")

conn.close()
