#!/usr/bin/env python3
"""Quick script to check 'other' column data in database"""

import sqlite3
import sys

def check_other_column():
    try:
        conn = sqlite3.connect('database/steel_database.db')
        cursor = conn.cursor()

        # Check if column exists
        cursor.execute("PRAGMA table_info(steel_grades)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'other' not in columns:
            print("ERROR: 'other' column does not exist!")
            return

        print("[OK] 'other' column exists in database\n")

        # Count records with Other data
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN other IS NOT NULL AND other != '' THEN 1 ELSE 0 END) as with_other
            FROM steel_grades
        """)
        total, with_other = cursor.fetchone()

        print(f"Total grades in database: {total}")
        print(f"Grades with Other data: {with_other}")
        print(f"Percentage: {(with_other/total*100):.2f}%\n")

        # Show sample records
        cursor.execute("""
            SELECT grade, other
            FROM steel_grades
            WHERE other IS NOT NULL AND other != ''
            LIMIT 10
        """)

        print("Sample records with Other data:")
        print("-" * 80)
        for row in cursor.fetchall():
            other_text = row[1][:100] if len(row[1]) > 100 else row[1]
            print(f"{row[0]}: {other_text}")

        conn.close()

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_other_column()
