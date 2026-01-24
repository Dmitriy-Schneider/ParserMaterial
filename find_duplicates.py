#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find and analyze duplicate steel grades"""
import sqlite3
import sys
import io

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def find_duplicates():
    conn = sqlite3.connect('database/steel_database.db')
    cursor = conn.cursor()

    # Find grades with duplicates
    cursor.execute("""
        SELECT grade, COUNT(*) as count
        FROM steel_grades
        GROUP BY grade
        HAVING COUNT(*) > 1
        ORDER BY COUNT(*) DESC, grade
    """)

    duplicates = cursor.fetchall()
    print(f"Found {len(duplicates)} grades with duplicates")
    print("=" * 100)

    total_to_delete = 0

    for grade_name, count in duplicates:
        print(f"\nGrade: {grade_name} ({count} duplicates)")
        print("-" * 100)

        # Get all instances of this grade
        cursor.execute("""
            SELECT id, grade, link, other, standard, manufacturer
            FROM steel_grades
            WHERE grade = ?
            ORDER BY
                CASE WHEN link IS NOT NULL AND link != '' THEN 0 ELSE 1 END,
                CASE WHEN other LIKE '%zknives.com%' THEN 1 ELSE 0 END,
                id
        """, (grade_name,))

        instances = cursor.fetchall()

        # First instance will be kept (based on priority sorting)
        keep_id = instances[0][0]

        print(f"  KEEP   ID={instances[0][0]:5d} | Link: {instances[0][2][:50] if instances[0][2] else 'NULL':50s} | Other: {instances[0][3][:30] if instances[0][3] else 'NULL':30s}")

        for instance in instances[1:]:
            print(f"  DELETE ID={instance[0]:5d} | Link: {instance[2][:50] if instance[2] else 'NULL':50s} | Other: {instance[3][:30] if instance[3] else 'NULL':30s}")
            total_to_delete += 1

    print("\n" + "=" * 100)
    print(f"Total duplicates found: {len(duplicates)} grades")
    print(f"Total records to delete: {total_to_delete}")
    print(f"Database will shrink from {10702} to {10702 - total_to_delete} grades")

    conn.close()
    return total_to_delete

if __name__ == "__main__":
    find_duplicates()
