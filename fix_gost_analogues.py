#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix GOST analogues separators using cross-reference analysis
Strategy: Use grades that correctly reference the target grade to build analogue vocabulary
"""
import sqlite3
import sys
import io
import re
from collections import Counter
from database.backup_manager import backup_before_modification

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def get_transliteration_variants(grade):
    """
    Get transliteration variants for Cyrillic grade names
    Examples:
      4Х5МФС → 4X5MFS, 4KH5MFS
      Х12МФ → X12MF, KH12MF
    """
    cyrillic_to_latin = {
        # Uppercase
        'А': 'A', 'В': 'B', 'С': 'S', 'Е': 'E', 'Н': 'H', 'К': 'K',
        'М': 'M', 'О': 'O', 'Р': 'P', 'Т': 'T', 'Х': 'X', 'У': 'U',
        'Ф': 'F', 'Л': 'L', 'Д': 'D', 'Б': 'B', 'Г': 'G', 'И': 'I',
        # Lowercase
        'а': 'a', 'в': 'b', 'с': 's', 'е': 'e', 'н': 'h', 'к': 'k',
        'м': 'm', 'о': 'o', 'р': 'p', 'т': 't', 'х': 'x', 'у': 'u',
        'ф': 'f', 'л': 'l', 'д': 'd', 'б': 'b', 'г': 'g', 'и': 'i'
    }

    variants = [grade]

    # Standard transliteration
    transliterated = grade
    for cyr, lat in cyrillic_to_latin.items():
        transliterated = transliterated.replace(cyr, lat)

    if transliterated != grade:
        variants.append(transliterated)
        if transliterated.upper() not in variants:
            variants.append(transliterated.upper())

    # Alternative transliteration with KH instead of X
    transliterated_alt = grade
    for cyr, lat in cyrillic_to_latin.items():
        transliterated_alt = transliterated_alt.replace(cyr, lat)
    # Replace X with KH
    transliterated_alt = transliterated_alt.replace('X', 'KH')

    if transliterated_alt not in variants:
        variants.append(transliterated_alt)
        if transliterated_alt.upper() not in variants:
            variants.append(transliterated_alt.upper())

    # Also try with C instead of S for С
    transliterated_c = grade
    for cyr in cyrillic_to_latin.keys():
        if cyr == 'С':
            transliterated_c = transliterated_c.replace(cyr, 'C')
        elif cyr == 'с':
            transliterated_c = transliterated_c.replace(cyr, 'c')
        else:
            transliterated_c = transliterated_c.replace(cyr, cyrillic_to_latin[cyr])

    if transliterated_c not in variants:
        variants.append(transliterated_c)

    return variants

def collect_analogue_vocabulary(target_grade, conn):
    """
    Collect all analogues from grades that reference target_grade
    Returns: Counter of analogues and their frequency
    """
    cursor = conn.cursor()

    # Get all transliteration variants
    variants = get_transliteration_variants(target_grade)

    print(f'  Transliteration variants: {", ".join(variants)}')

    # Find all grades that reference any variant
    analogue_counter = Counter()
    total_references = 0

    for variant in variants:
        # Search in analogues column (case-insensitive)
        # Only in grades that have pipe separators
        cursor.execute('''
            SELECT grade, analogues
            FROM steel_grades
            WHERE analogues LIKE ?
            AND analogues LIKE '%|%'
        ''', (f'%{variant}%',))

        results = cursor.fetchall()

        for ref_grade, ref_analogues in results:
            # Split analogues by pipe
            analogue_list = [a.strip() for a in ref_analogues.split('|') if a.strip()]

            # Check if variant is actually in the list (exact match)
            found = False
            for analogue in analogue_list:
                if analogue.upper() == variant.upper():
                    found = True
                    break

            if found:
                total_references += 1
                # Add all analogues to counter
                for analogue in analogue_list:
                    # Skip the variant itself
                    if analogue.upper() not in [v.upper() for v in variants]:
                        analogue_counter[analogue] += 1

    print(f'  Found {total_references} cross-references with {len(analogue_counter)} unique analogues')

    return analogue_counter

def split_analogues_using_vocabulary(analogues_str, vocabulary, min_frequency=2):
    """
    Split analogues string using vocabulary built from cross-references

    Args:
        analogues_str: String with analogues separated by spaces
        vocabulary: Counter of known analogues
        min_frequency: Minimum frequency to consider an analogue reliable

    Returns:
        List of separated analogues
    """
    if not vocabulary:
        # Fallback to simple space split
        return analogues_str.split()

    # Filter vocabulary by frequency
    reliable_analogues = {grade for grade, count in vocabulary.items() if count >= min_frequency}

    # Also include all analogues (even with freq=1) for better coverage
    all_analogues = set(vocabulary.keys())

    # Sort by length (longest first) to avoid partial matches
    sorted_analogues = sorted(all_analogues, key=len, reverse=True)

    matched_grades = []
    remaining_str = analogues_str

    # Try to match each known analogue
    for analogue in sorted_analogues:
        # Use word boundary regex for exact match
        # But be careful with special characters
        escaped_analogue = re.escape(analogue)

        # Try exact match with word boundaries
        pattern = r'\b' + escaped_analogue + r'\b'

        match = re.search(pattern, remaining_str, re.IGNORECASE)
        if match:
            matched_grades.append(analogue)
            # Remove matched analogue from string
            remaining_str = re.sub(pattern, '', remaining_str, count=1, flags=re.IGNORECASE).strip()

    # Handle remaining unmatched parts
    remaining_str = ' '.join(remaining_str.split())  # Normalize spaces

    if remaining_str and len(remaining_str) > 1:
        # Split by spaces and add as individual grades
        remaining_parts = remaining_str.split()
        for part in remaining_parts:
            if len(part) > 1 and part not in matched_grades:
                matched_grades.append(part)

    return matched_grades

def fix_analogues(dry_run=True):
    """Fix analogues for grades without pipe separators"""

    conn = sqlite3.connect('database/steel_database.db')
    cursor = conn.cursor()

    # Get all grades without pipe separators
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

    for i, (grade, analogues, standard) in enumerate(grades_without_pipes, 1):
        # Skip if analogues is too short (probably correct)
        if len(analogues) < 10:
            continue

        print(f'{i}. {grade} ({standard})')
        print(f'   Original ({len(analogues)} chars): {analogues[:80]}{"..." if len(analogues) > 80 else ""}')

        # Collect vocabulary from cross-references
        vocabulary = collect_analogue_vocabulary(grade, conn)

        if not vocabulary:
            print(f'   ⚠️ No cross-references found, skipping')
            continue

        # Split analogues using vocabulary
        split_result = split_analogues_using_vocabulary(analogues, vocabulary, min_frequency=2)

        if split_result and len(split_result) > 1:
            new_analogues = '|'.join(split_result)
            print(f'   ✅ Split into {len(split_result)} analogues')
            print(f'   First 10: {" | ".join(split_result[:10])}{"..." if len(split_result) > 10 else ""}')

            updates.append((grade, new_analogues))
        else:
            print(f'   ⚠️ Could not split reliably')

        print()

    print()
    print('=' * 100)
    print(f'Summary: {len(updates)} grades can be fixed')
    print('=' * 100)

    if not dry_run and updates:
        print('\nApplying updates...')
        for grade, new_analogues in updates:
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
        backup_before_modification(reason='fix_gost_analogues')

    updated_count = fix_analogues(dry_run)

    print(f'\nTotal grades that can be fixed: {updated_count}')

    if dry_run:
        print('\n[INFO] This was a preview. Run with --execute to apply changes.')
