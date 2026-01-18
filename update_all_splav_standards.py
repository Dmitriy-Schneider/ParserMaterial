"""
Full update: Update Standard for all splav-kharkov grades with generic GOST
"""
import sys
from pathlib import Path
import time
import re
import sqlite3
import logging

sys.path.append(str(Path(__file__).parent))

from parsers.splav_kharkov_advanced import SplavKharkovParser

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('update_all_standards.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Get database connection
db_path = Path(__file__).parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all splav grades with generic GOST
cursor.execute("""
    SELECT grade, link, standard
    FROM steel_grades
    WHERE link LIKE '%splav%' AND standard = 'GOST, Россия'
    ORDER BY id
""")
grades_to_update = cursor.fetchall()

total = len(grades_to_update)
logging.info(f"Starting full update for {total} grades with generic GOST")
logging.info("="*80)

parser = SplavKharkovParser()

updated = 0
skipped = 0
errors = 0

for i, (grade, link, current_standard) in enumerate(grades_to_update, 1):
    logging.info(f"\n[{i}/{total}] Processing: {grade}")

    # Extract name_id from link
    match = re.search(r'name_id=(\d+)', link)
    if not match:
        logging.error(f"  No name_id in link")
        errors += 1
        continue

    name_id = int(match.group(1))

    try:
        # Parse grade page
        grade_data = parser.parse_grade_page(name_id, grade)

        if grade_data and grade_data['standard']:
            new_standard = grade_data['standard']

            # Check if new has specific GOST number
            has_gost_number = bool(re.search(r'ГОСТ\s+\d+', new_standard))

            if new_standard != current_standard and has_gost_number:
                # Update database
                cursor.execute("UPDATE steel_grades SET standard = ? WHERE grade = ?",
                             (new_standard, grade))
                conn.commit()
                logging.info(f"  {current_standard} -> {new_standard} [UPDATED]")
                updated += 1
            else:
                logging.info(f"  {new_standard} [SKIPPED - no specific GOST]")
                skipped += 1
        else:
            logging.warning(f"  Failed to parse")
            errors += 1

    except Exception as e:
        logging.error(f"  ERROR: {e}")
        errors += 1

    # Progress report every 50 grades
    if i % 50 == 0:
        logging.info(f"\n{'='*80}")
        logging.info(f"PROGRESS: {i}/{total} ({i*100//total}%)")
        logging.info(f"Updated: {updated}, Skipped: {skipped}, Errors: {errors}")
        logging.info(f"{'='*80}")

    # Rate limiting
    time.sleep(2)

conn.close()

logging.info(f"\n{'='*80}")
logging.info("FINAL RESULTS:")
logging.info(f"{'='*80}")
logging.info(f"Total processed: {total}")
logging.info(f"Updated: {updated}")
logging.info(f"Skipped: {skipped}")
logging.info(f"Errors: {errors}")
logging.info(f"Success rate: {updated*100//total if total > 0 else 0}%")
