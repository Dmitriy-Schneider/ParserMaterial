"""
Update chemical composition for sample of grades from splav-kharkov (for testing)
"""
import sys
from pathlib import Path
import re
import time
sys.path.append(str(Path(__file__).parent))

from parsers.splav_kharkov_advanced import SplavKharkovParser
from database_schema import get_connection

def update_sample_chemistry(limit=50):
    """Update chemistry for sample of splav-kharkov grades"""
    # Get sample grades from splav-kharkov
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT grade, link FROM steel_grades
        WHERE link LIKE '%splav-kharkov%'
        ORDER BY grade
        LIMIT {limit}
    """)
    grades = cursor.fetchall()
    conn.close()

    print(f"Updating {len(grades)} sample grades from splav-kharkov")
    print("=" * 80)

    parser = SplavKharkovParser()

    updated = 0
    errors = 0
    with_other = 0

    for i, (grade, link) in enumerate(grades, 1):
        # Extract name_id from link
        match = re.search(r'name_id=(\d+)', link)
        if not match:
            continue

        name_id = int(match.group(1))

        try:
            print(f"[{i}/{len(grades)}] {grade}...", end=' ')

            grade_data = parser.parse_grade_page(name_id, grade)
            if not grade_data:
                print("FAIL")
                errors += 1
                continue

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

            if comp.get('other'):
                print(f"OK [OTHER: {comp.get('other')}]")
                with_other += 1
            else:
                print("OK")
            updated += 1

        except Exception as e:
            print(f"ERROR: {e}")
            errors += 1

        time.sleep(1)

    print("\n" + "=" * 80)
    print(f"Updated: {updated}/{len(grades)}")
    print(f"With OTHER elements: {with_other}")
    print(f"Errors: {errors}")

if __name__ == '__main__':
    update_sample_chemistry(50)
