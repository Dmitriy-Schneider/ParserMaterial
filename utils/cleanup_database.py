"""
Database cleanup utility
Removes duplicates and fixes invalid analogues
"""

import sqlite3
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from database_schema import get_connection


def count_elements(grade_data: dict) -> int:
    """Count how many chemical elements are specified"""
    elements = ['c', 'cr', 'mo', 'v', 'w', 'co', 'ni', 'mn', 'si', 's', 'p', 'cu', 'nb', 'n']
    count = 0
    for elem in elements:
        value = grade_data.get(elem)
        if value and str(value).strip() not in ['', 'None', 'null', 'N/A']:
            count += 1
    return count


def remove_duplicates():
    """Remove duplicate steel grades, keeping the most complete one"""
    conn = get_connection()
    cursor = conn.cursor()

    # Find all duplicates
    cursor.execute('''
        SELECT grade, COUNT(*) as count
        FROM steel_grades
        GROUP BY grade
        HAVING count > 1
    ''')

    duplicates = cursor.fetchall()

    print(f"Found {len(duplicates)} grades with duplicates")

    removed_count = 0

    for grade, count in duplicates:
        print(f"\nProcessing '{grade}' ({count} copies)...")

        # Get all records for this grade
        cursor.execute('''
            SELECT id, grade, base, c, cr, mo, v, w, co, ni, mn, si, s, p, cu, nb, n,
                   tech, standard, manufacturer, analogues, link
            FROM steel_grades
            WHERE grade = ?
        ''', (grade,))

        records = cursor.fetchall()

        # Score each record (more filled elements = higher score)
        scored_records = []
        for record in records:
            record_dict = {
                'id': record[0],
                'grade': record[1],
                'base': record[2],
                'c': record[3],
                'cr': record[4],
                'mo': record[5],
                'v': record[6],
                'w': record[7],
                'co': record[8],
                'ni': record[9],
                'mn': record[10],
                'si': record[11],
                's': record[12],
                'p': record[13],
                'cu': record[14],
                'nb': record[15],
                'n': record[16],
                'tech': record[17],
                'standard': record[18],
                'manufacturer': record[19],
                'analogues': record[20],
                'link': record[21]
            }

            score = count_elements(record_dict)

            # Bonus for having standard or manufacturer
            if record_dict.get('standard'):
                score += 2
            if record_dict.get('manufacturer'):
                score += 1
            if record_dict.get('analogues'):
                score += 1

            scored_records.append((score, record_dict))

        # Sort by score (highest first)
        scored_records.sort(reverse=True, key=lambda x: x[0])

        # Keep the best one, delete others
        best_record = scored_records[0][1]
        print(f"  Keeping ID {best_record['id']} (score: {scored_records[0][0]})")

        for score, record in scored_records[1:]:
            print(f"  Deleting ID {record['id']} (score: {score})")
            cursor.execute('DELETE FROM steel_grades WHERE id = ?', (record['id'],))
            removed_count += 1

    conn.commit()
    conn.close()

    print(f"\n[OK] Removed {removed_count} duplicate records")
    return removed_count


def fix_analogues():
    """Fix invalid analogues (remove self-references and clean up)"""
    conn = get_connection()
    cursor = conn.cursor()

    # Get all grades with analogues
    cursor.execute('SELECT id, grade, analogues FROM steel_grades WHERE analogues IS NOT NULL AND analogues != ""')
    records = cursor.fetchall()

    print(f"\nChecking {len(records)} grades with analogues...")

    fixed_count = 0

    for id, grade, analogues in records:
        if not analogues:
            continue

        # Split analogues
        analogue_list = analogues.replace(',', ' ').split()

        # Remove self-reference
        original_count = len(analogue_list)
        analogue_list = [a for a in analogue_list if a.strip() != grade.strip()]

        # Remove duplicates
        analogue_list = list(dict.fromkeys(analogue_list))  # Preserve order

        if len(analogue_list) != original_count:
            new_analogues = ' '.join(analogue_list) if analogue_list else None

            cursor.execute('UPDATE steel_grades SET analogues = ? WHERE id = ?',
                         (new_analogues, id))

            print(f"Fixed '{grade}': {original_count} -> {len(analogue_list) if analogue_list else 0} analogues")
            fixed_count += 1

    conn.commit()
    conn.close()

    print(f"\n[OK] Fixed {fixed_count} analogue entries")
    return fixed_count


def get_statistics():
    """Get database statistics"""
    conn = get_connection()
    cursor = conn.cursor()

    # Total count
    cursor.execute('SELECT COUNT(*) FROM steel_grades')
    total = cursor.fetchone()[0]

    # By standard
    cursor.execute('''
        SELECT standard, COUNT(*) as count
        FROM steel_grades
        GROUP BY standard
        ORDER BY count DESC
    ''')
    standards = cursor.fetchall()

    conn.close()

    print("\n=== Database Statistics ===")
    print(f"Total grades: {total:,}")
    print("\nBy standard:")
    for std, count in standards[:10]:
        std_name = std if std else 'Unknown'
        print(f"  {std_name}: {count}")


def main():
    """Main cleanup process"""
    print("ParserSteel Database Cleanup")
    print("=" * 50)

    # Step 1: Remove duplicates
    print("\n[1/3] Removing duplicates...")
    removed = remove_duplicates()

    # Step 2: Fix analogues
    print("\n[2/3] Fixing analogues...")
    fixed = fix_analogues()

    # Step 3: Show statistics
    print("\n[3/3] Final statistics...")
    get_statistics()

    print("\n" + "=" * 50)
    print(f"[OK] Cleanup complete!")
    print(f"  - Removed {removed} duplicates")
    print(f"  - Fixed {fixed} analogue entries")


if __name__ == '__main__':
    main()
