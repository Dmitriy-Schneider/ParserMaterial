#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix remaining 866 grades without pipe separators
Use simple space-splitting for grades without cross-references
"""
import sqlite3
import sys
import io
import re
from database.backup_manager import backup_before_modification

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def simple_split_analogues(analogues_str):
    """
    Simple splitting by spaces
    Handles:
    - Regular spaces
    - Multi-word analogues (e.g., "MONEL alloy 400" → kept together)
    - Chemical formulas (e.g., "X10CrNiTi18-9" → single unit)
    """
    if not analogues_str or len(analogues_str) < 3:
        return []

    # Split by spaces
    parts = analogues_str.split()

    # Filter out very short parts (likely noise)
    filtered_parts = []
    for part in parts:
        # Skip very short parts unless they look like valid grades
        if len(part) >= 2 or part.isdigit():
            filtered_parts.append(part)

    return filtered_parts

def fix_all_remaining(dry_run=True):
    """Fix all grades without pipe separators"""

    conn = sqlite3.connect('database/steel_database.db')
    cursor = conn.cursor()

    # Get all grades WITHOUT pipe separators
    cursor.execute('''
        SELECT grade, analogues, standard
        FROM steel_grades
        WHERE analogues IS NOT NULL
        AND analogues != ''
        AND analogues NOT LIKE '%|%'
        ORDER BY grade
    ''')

    grades_without_pipes = cursor.fetchall()

    print(f'Total grades without pipe separators: {len(grades_without_pipes)}')
    print()

    updates = []
    skipped = []

    for i, (grade, analogues, standard) in enumerate(grades_without_pipes, 1):
        # Skip very short analogues (likely correct as-is)
        if len(analogues) < 5:
            skipped.append((grade, 'too short'))
            continue

        # Check if it's a simple single analogue (no spaces)
        if ' ' not in analogues:
            # Single analogue without spaces - likely correct
            skipped.append((grade, 'single analogue'))
            continue

        # Split by spaces
        split_result = simple_split_analogues(analogues)

        if split_result and len(split_result) > 1:
            new_analogues = '|'.join(split_result)
            updates.append((grade, analogues, new_analogues, len(split_result)))

            if dry_run and i <= 30:
                print(f'{i}. {grade} ({standard})')
                print(f'   Original ({len(analogues)} chars): {analogues[:80]}{"..." if len(analogues) > 80 else ""}')
                print(f'   ✅ Split into {len(split_result)} analogues')
                print(f'   First 10: {" | ".join(split_result[:10])}{"..." if len(split_result) > 10 else ""}')
                print()
        else:
            skipped.append((grade, 'could not split'))

    print()
    print('=' * 100)
    print(f'Summary:')
    print(f'  Total: {len(grades_without_pipes)} grades')
    print(f'  Can be fixed: {len(updates)} grades')
    print(f'  Skipped: {len(skipped)} grades')
    print('=' * 100)

    if not dry_run and updates:
        print('\nApplying updates...')
        for grade, old_analogues, new_analogues, count in updates:
            cursor.execute(
                'UPDATE steel_grades SET analogues = ? WHERE grade = ?',
                (new_analogues, grade)
            )

        conn.commit()
        print(f'[SUCCESS] Updated {len(updates)} grades')
    elif dry_run:
        print('[DRY RUN] Changes not applied')

    conn.close()
    return len(updates)

if __name__ == '__main__':
    dry_run = '--execute' not in sys.argv

    if dry_run:
        print('=' * 100)
        print('PREVIEW MODE (DRY RUN)')
        print('Add --execute flag to apply changes')
        print('=' * 100)
        print()
    else:
        print('=' * 100)
        print('EXECUTION MODE')
        print('=' * 100)
        print()
        backup_before_modification(reason='fix_remaining_analogues')

    updated_count = fix_all_remaining(dry_run)

    print(f'\nTotal grades that can be fixed: {updated_count}')

    if dry_run:
        print('\n[INFO] This was a preview. Run with --execute to apply changes.')
