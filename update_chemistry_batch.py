"""
Update chemical composition for grades from splav-kharkov in batches
"""
import sys
from pathlib import Path
import re
import time
sys.path.append(str(Path(__file__).parent))

from parsers.splav_kharkov_advanced import SplavKharkovParser
from database_schema import get_connection

def update_chemistry_batch(batch_size=100, start_from=0):
    """Update chemistry in batches"""
    # Get all grades from splav-kharkov without chemistry
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT grade, link FROM steel_grades
        WHERE link LIKE '%splav-kharkov%'
        AND c IS NULL AND si IS NULL AND mn IS NULL
        ORDER BY grade
        LIMIT ? OFFSET ?
    """, (batch_size, start_from))
    grades = cursor.fetchall()
    conn.close()

    if not grades:
        print(f"No more grades to update (checked from offset {start_from})")
        return 0

    print(f"=" * 80)
    print(f"Batch: {start_from+1} to {start_from+len(grades)}")
    print(f"=" * 80)

    parser = SplavKharkovParser()
    updated = 0
    errors = 0
    with_other = 0

    for i, (grade, link) in enumerate(grades, 1):
        match = re.search(r'name_id=(\d+)', link)
        if not match:
            continue

        name_id = int(match.group(1))

        try:
            sys.stdout.write(f"[{start_from+i}] {grade:20}...")
            sys.stdout.flush()

            grade_data = parser.parse_grade_page(name_id, grade)
            if not grade_data:
                print(" FAIL")
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
                print(f" OK [Other: {comp.get('other')[:30]}]")
                with_other += 1
            else:
                print(" OK")
            updated += 1

        except Exception as e:
            print(f" ERROR: {str(e)[:50]}")
            errors += 1

        time.sleep(1)

    print(f"\nBatch complete: Updated {updated}, Errors {errors}, With Other: {with_other}")
    return len(grades)

if __name__ == '__main__':
    batch_size = 100
    offset = 0
    total_updated = 0

    while True:
        processed = update_chemistry_batch(batch_size, offset)
        if processed == 0:
            break
        total_updated += processed
        offset += batch_size
        print(f"\nTotal processed so far: {total_updated}\n")

    print("=" * 80)
    print(f"Complete! Total processed: {total_updated}")
