"""
Update Standard column for splav-kharkov grades
Extracts GOST from chemistry section (not from other parts of page)
"""
import sys
from pathlib import Path
import time
import re
import logging

sys.path.append(str(Path(__file__).parent.parent))

from parsers.splav_kharkov_advanced import SplavKharkovParser
import sqlite3

# Setup logging to file only
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('update_splav_standards.log', encoding='utf-8')
    ]
)

logging.info("="*100)
logging.info("UPDATING STANDARD COLUMN FOR SPLAV-KHARKOV GRADES")
logging.info("="*100)

# Get all splav grades
db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
    SELECT grade, link, standard
    FROM steel_grades
    WHERE link LIKE '%splav%'
    ORDER BY id
""")
splav_grades = cursor.fetchall()

logging.info(f"Found {len(splav_grades)} splav-kharkov grades")
logging.info("Starting update...")

# Create parser (suppress its logging to console)
parser_logger = logging.getLogger('parsers.splav_kharkov_advanced')
parser_logger.setLevel(logging.WARNING)

parser = SplavKharkovParser()

updated = 0
skipped = 0
errors = 0

for i, (grade, link, current_standard) in enumerate(splav_grades, 1):
    # Extract name_id from link
    match = re.search(r'name_id=(\d+)', link)
    if not match:
        logging.error(f"[{i}/{len(splav_grades)}] {grade} - no name_id in link")
        errors += 1
        continue

    name_id = int(match.group(1))

    try:
        # Parse grade page to get correct standard
        grade_data = parser.parse_grade_page(name_id, grade)

        if grade_data and grade_data['standard']:
            new_standard = grade_data['standard']

            # Only update if new standard is BETTER (has specific GOST number)
            # Don't update if new standard is generic "GOST, Россия" and old has specific number

            # Check if new standard has specific GOST number
            has_gost_number = bool(re.search(r'ГОСТ\s+\d+', new_standard) or
                                  re.search(r'ГОСТ\s+Р?\s*\d+', new_standard))

            # Check if current standard has specific number
            current_has_number = bool(re.search(r'ГОСТ\s+\d+', current_standard) or
                                     re.search(r'ГОСТ\s+Р?\s*\d+', current_standard))

            # Update only if:
            # 1. New is different from current AND
            # 2. (New has specific number OR current doesn't have number)
            should_update = (new_standard != current_standard and
                           (has_gost_number or not current_has_number))

            if should_update:
                # Update in database
                cursor.execute("UPDATE steel_grades SET standard = ? WHERE grade = ?",
                             (new_standard, grade))
                conn.commit()

                updated += 1
                if updated <= 50:  # Log first 50 changes
                    logging.info(f"[{i}/{len(splav_grades)}] {grade}: {current_standard} -> {new_standard}")
            else:
                skipped += 1
                # Log if we're skipping a downgrade
                if new_standard != current_standard and current_has_number and not has_gost_number:
                    if updated + skipped <= 100:  # Log first 100
                        logging.warning(f"[{i}/{len(splav_grades)}] {grade}: SKIPPED downgrade {current_standard} -> {new_standard}")
        else:
            logging.warning(f"[{i}/{len(splav_grades)}] {grade} - failed to parse standard")
            errors += 1

    except Exception as e:
        logging.error(f"[{i}/{len(splav_grades)}] {grade} - {e}")
        errors += 1

    # Rate limiting
    time.sleep(2)

    # Progress report every 100 grades
    if i % 100 == 0:
        logging.info(f"PROGRESS: {i}/{len(splav_grades)} | Updated: {updated}, Skipped: {skipped}, Errors: {errors}")

conn.close()

logging.info("="*100)
logging.info("COMPLETE")
logging.info("="*100)
logging.info(f"Total processed: {len(splav_grades)}")
logging.info(f"Updated: {updated}")
logging.info(f"Skipped (same standard): {skipped}")
logging.info(f"Errors: {errors}")

print(f"Complete! Updated {updated} grades. Check update_splav_standards.log for details.")
