"""
Update chemical composition for all grades from splav-kharkov
"""
import sys
from pathlib import Path
import re
import time
sys.path.append(str(Path(__file__).parent))

from parsers.splav_kharkov_advanced import SplavKharkovParser
from database_schema import get_connection

def update_all_chemistry():
    """Update chemistry for all splav-kharkov grades"""
    # Get all grades from splav-kharkov
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT grade, link FROM steel_grades
        WHERE link LIKE '%splav-kharkov%'
        ORDER BY grade
    """)
    grades = cursor.fetchall()
    conn.close()

    print(f"Found {len(grades)} grades from splav-kharkov to update")
    print("=" * 80)

    parser = SplavKharkovParser()

    updated = 0
    errors = 0
    skipped = 0

    for i, (grade, link) in enumerate(grades, 1):
        # Extract name_id from link
        match = re.search(r'name_id=(\d+)', link)
        if not match:
            print(f"[{i}/{len(grades)}] Skipping {grade} - no name_id in link")
            skipped += 1
            continue

        name_id = int(match.group(1))

        try:
            print(f"[{i}/{len(grades)}] Updating {grade} (name_id={name_id})...", end=' ')

            # Parse grade page
            grade_data = parser.parse_grade_page(name_id, grade)

            if not grade_data:
                print("ERROR - failed to fetch")
                errors += 1
                continue

            # Update in database
            comp = grade_data['composition']

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE steel_grades
                SET c = ?, cr = ?, ni = ?, mo = ?, v = ?, w = ?, co = ?,
                    mn = ?, si = ?, cu = ?, nb = ?, n = ?, s = ?, p = ?,
                    standard = ?, tech = ?
                WHERE grade = ?
            """, (
                comp.get('c'), comp.get('cr'), comp.get('ni'), comp.get('mo'),
                comp.get('v'), comp.get('w'), comp.get('co'), comp.get('mn'),
                comp.get('si'), comp.get('cu'), comp.get('nb'), comp.get('n'),
                comp.get('s'), comp.get('p'), grade_data['standard'],
                comp.get('other'), grade
            ))
            conn.commit()
            conn.close()

            other_info = f", OTHER: {comp.get('other')}" if comp.get('other') else ""
            print(f"OK{other_info}")
            updated += 1

        except Exception as e:
            print(f"ERROR - {e}")
            errors += 1

        # Rate limiting
        time.sleep(1)

        # Periodic stats
        if i % 100 == 0:
            print(f"\nProgress: {i}/{len(grades)} - Updated: {updated}, Errors: {errors}, Skipped: {skipped}\n")

    print("\n" + "=" * 80)
    print("Update complete!")
    print(f"Total processed: {len(grades)}")
    print(f"Updated: {updated}")
    print(f"Errors: {errors}")
    print(f"Skipped: {skipped}")
    print("=" * 80)

if __name__ == '__main__':
    update_all_chemistry()
