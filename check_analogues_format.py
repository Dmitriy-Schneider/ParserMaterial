#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('database/steel_database.db')
cursor = conn.cursor()

# Records with analogues
cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE analogues IS NOT NULL AND analogues != ''")
total_with_analogues = cursor.fetchone()[0]

# Records WITHOUT pipe separator
cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE analogues IS NOT NULL AND analogues != '' AND analogues NOT LIKE '%|%'")
without_pipe = cursor.fetchone()[0]

# Records WITH pipe separator
with_pipe = total_with_analogues - without_pipe

print(f"Total records with analogues: {total_with_analogues}")
print(f"  With pipe separator (|): {with_pipe} ({with_pipe/total_with_analogues*100:.1f}%)")
print(f"  WITHOUT pipe separator: {without_pipe} ({without_pipe/total_with_analogues*100:.1f}%)")

# Show examples without pipe - SHORT
cursor.execute("""
    SELECT grade, analogues
    FROM steel_grades
    WHERE analogues IS NOT NULL AND analogues != '' AND analogues NOT LIKE '%|%'
    AND LENGTH(analogues) < 30
    LIMIT 5
""")

print("\nExamples WITHOUT pipe separator (SHORT - likely OK):")
for grade, analogues in cursor.fetchall():
    print(f"  {grade}: {analogues}")

# Show examples without pipe - LONG (problematic)
cursor.execute("""
    SELECT grade, analogues
    FROM steel_grades
    WHERE analogues IS NOT NULL AND analogues != '' AND analogues NOT LIKE '%|%'
    AND LENGTH(analogues) > 50
    ORDER BY LENGTH(analogues) DESC
    LIMIT 10
""")

print("\nExamples WITHOUT pipe separator (LONG - likely PROBLEMATIC):")
for grade, analogues in cursor.fetchall():
    print(f"  {grade}: {analogues[:100]}...")

# Count problematic (long without pipe)
cursor.execute("""
    SELECT COUNT(*)
    FROM steel_grades
    WHERE analogues IS NOT NULL AND analogues != '' AND analogues NOT LIKE '%|%'
    AND LENGTH(analogues) > 50
""")
problematic_count = cursor.fetchone()[0]
print(f"\nProblematic (long analogues without |): {problematic_count}")

conn.close()
