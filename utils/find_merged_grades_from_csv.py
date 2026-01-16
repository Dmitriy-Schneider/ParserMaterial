"""
Find and analyze merged grades imported from CSV files (grades without links)
"""
import sqlite3
import re
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

def get_connection():
    """Get database connection"""
    db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
    return sqlite3.connect(db_path)

def find_merged_grades():
    """Find all merged grades from CSV imports (no links)"""
    conn = get_connection()
    cursor = conn.cursor()

    # Get all grades without links (imported from CSV)
    cursor.execute("""
        SELECT grade, standard, analogues, link
        FROM steel_grades
        WHERE link IS NULL OR link = '' OR link = 'N/A'
        ORDER BY grade
    """)

    grades_without_links = cursor.fetchall()

    print(f"Total grades without links (from CSV): {len(grades_without_links)}\n")
    print("="*100)

    # Patterns for merged grades
    patterns = [
        # Pattern 1: 1.XXXX + YYYY (e.g., 1.17301045 = 1.1730 + 1045)
        (r'^(1\.\d{4})(\d+)$', 'Decimal pattern (1.XXXX + digits)'),

        # Pattern 2: 1.XXXX + LetterDigits (e.g., 1.2063145Cr6 = 1.2063 + 145Cr6)
        (r'^(1\.\d{4})(\d+[A-Za-z]\d*)$', 'Decimal pattern (1.XXXX + alphanumeric)'),

        # Pattern 3: Digits + Letters (e.g., 1.2345H11 = 1.2345 + H11)
        (r'^(1\.\d{4})([A-Z]\d+)$', 'Decimal pattern (1.XXXX + letter+digits)'),

        # Pattern 4: Grade ~ASP XXXX (e.g., 1.3345 ~ASP 2023 = 1.3345 + ASP 2023)
        (r'^([\d\.]+)\s*~?\s*(ASP\s+\d+)$', 'ASP pattern (grade ~ASP number)'),

        # Pattern 5: Grade -ASP XXXX
        (r'^([\d\.]+)\s*-\s*(ASP\s+\d+)$', 'ASP pattern (grade -ASP number)'),
    ]

    merged_to_delete = []
    merged_to_split = []

    for grade, standard, analogues, link in grades_without_links:
        # Check each pattern
        for pattern, description in patterns:
            match = re.match(pattern, grade, re.IGNORECASE)
            if match:
                part1 = match.group(1)
                part2 = match.group(2).strip()

                # Check if both parts exist in database
                cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE grade = ?", (part1,))
                has_part1 = cursor.fetchone()[0] > 0

                cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE grade = ?", (part2,))
                has_part2 = cursor.fetchone()[0] > 0

                # Check if parts have links
                cursor.execute("SELECT link FROM steel_grades WHERE grade = ?", (part1,))
                part1_link = cursor.fetchone()
                part1_has_link = part1_link and part1_link[0] and part1_link[0] not in ['', 'N/A', None]

                cursor.execute("SELECT link FROM steel_grades WHERE grade = ?", (part2,))
                part2_link = cursor.fetchone()
                part2_has_link = part2_link and part2_link[0] and part2_link[0] not in ['', 'N/A', None]

                if has_part1 and has_part2:
                    # Both parts exist - DELETE merged grade
                    merged_to_delete.append({
                        'grade': grade,
                        'pattern': description,
                        'part1': part1,
                        'part2': part2,
                        'part1_has_link': part1_has_link,
                        'part2_has_link': part2_has_link,
                        'standard': standard,
                        'analogues': analogues
                    })
                else:
                    # At least one part missing - SPLIT and create
                    merged_to_split.append({
                        'grade': grade,
                        'pattern': description,
                        'part1': part1,
                        'part2': part2,
                        'has_part1': has_part1,
                        'has_part2': has_part2,
                        'standard': standard,
                        'analogues': analogues
                    })
                break

    # Report: Grades to DELETE
    print("\n" + "="*100)
    print(f"MERGED GRADES TO DELETE (both parts exist): {len(merged_to_delete)}")
    print("="*100)

    for item in merged_to_delete:
        print(f"\nGrade: {item['grade']}")
        print(f"  Pattern: {item['pattern']}")
        print(f"  Part1: {item['part1']} (has link: {item['part1_has_link']})")
        print(f"  Part2: {item['part2']} (has link: {item['part2_has_link']})")
        print(f"  Standard: {item['standard']}")
        print(f"  Action: DELETE (both parts exist in DB)")

    # Report: Grades to SPLIT
    print("\n" + "="*100)
    print(f"MERGED GRADES TO SPLIT (parts missing): {len(merged_to_split)}")
    print("="*100)

    for item in merged_to_split:
        print(f"\nGrade: {item['grade']}")
        print(f"  Pattern: {item['pattern']}")
        print(f"  Part1: {item['part1']} (exists: {item['has_part1']})")
        print(f"  Part2: {item['part2']} (exists: {item['has_part2']})")
        print(f"  Standard: {item['standard']}")
        print(f"  Action: SPLIT and create missing parts")

    conn.close()

    return merged_to_delete, merged_to_split


if __name__ == "__main__":
    print("Searching for merged grades from CSV imports (no links)...\n")
    to_delete, to_split = find_merged_grades()

    print("\n" + "="*100)
    print("SUMMARY:")
    print(f"  Grades to DELETE: {len(to_delete)}")
    print(f"  Grades to SPLIT: {len(to_split)}")
    print("="*100)
