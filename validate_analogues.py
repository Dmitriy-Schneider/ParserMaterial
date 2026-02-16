#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validate analogues - check if all analogue references exist in database
"""
import sqlite3
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

conn = sqlite3.connect('database/steel_database.db')
cursor = conn.cursor()

# Get all unique grade names (for validation)
cursor.execute('SELECT DISTINCT grade FROM steel_grades')
all_grades = {row[0] for row in cursor.fetchall()}

print(f'Total unique grades in database: {len(all_grades)}')
print()

# Get all grades with analogues
cursor.execute('''
    SELECT grade, analogues
    FROM steel_grades
    WHERE analogues IS NOT NULL
    AND analogues != ''
    AND analogues LIKE '%|%'
''')

all_with_analogues = cursor.fetchall()

print(f'Checking {len(all_with_analogues)} grades with analogues...')
print()

invalid_references = []
total_analogues = 0
invalid_count = 0

for grade, analogues in all_with_analogues:
    analogue_list = [a.strip() for a in analogues.split('|') if a.strip()]

    for analogue in analogue_list:
        total_analogues += 1

        # Check if analogue exists in database
        if analogue not in all_grades:
            invalid_count += 1
            invalid_references.append({
                'grade': grade,
                'invalid_analogue': analogue
            })

print('=' * 100)
print('=== Validation Results ===')
print('=' * 100)
print(f'Total analogues checked: {total_analogues:,}')
print(f'Valid analogues (exist in DB): {total_analogues - invalid_count:,} ({(total_analogues - invalid_count) / total_analogues * 100:.1f}%)')
print(f'Invalid analogues (NOT in DB): {invalid_count:,} ({invalid_count / total_analogues * 100:.1f}%)')
print()

if invalid_count > 0:
    print(f'Found {invalid_count} invalid analogue references')
    print()
    print('Examples (first 50):')

    # Group by invalid analogue to see which are most common
    from collections import Counter
    invalid_analogue_counter = Counter()
    for item in invalid_references:
        invalid_analogue_counter[item['invalid_analogue']] += 1

    print()
    print('Most common invalid analogues:')
    for analogue, count in invalid_analogue_counter.most_common(50):
        print(f'  {analogue:40s} (referenced {count:3d} times)')

    print()
    print('Sample of grades with invalid analogues (first 20):')
    seen_grades = set()
    count = 0
    for item in invalid_references:
        if item['grade'] not in seen_grades and count < 20:
            seen_grades.add(item['grade'])
            count += 1
            print(f'  {item["grade"]:30s} → invalid: {item["invalid_analogue"]}')

conn.close()
