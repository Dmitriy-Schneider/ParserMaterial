#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test specific grades: 4Х5МФС and Х12МФ"""
import sqlite3
import sys
import io
import re
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

conn = sqlite3.connect('database/steel_database.db')
cursor = conn.cursor()

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

    # Alternative transliterations
    cyrillic_to_latin_alt = {
        'Х': 'KH', 'х': 'kh',  # X or KH
        'С': 'C', 'с': 'c'     # S or C
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

def collect_analogues(target_grade):
    variants = get_transliteration_variants(target_grade)
    print(f'Variants: {variants}')

    analogue_counter = Counter()
    total_refs = 0

    for variant in variants:
        cursor.execute('''
            SELECT grade, analogues
            FROM steel_grades
            WHERE analogues LIKE ?
            AND analogues LIKE '%|%'
        ''', (f'%{variant}%',))

        for ref_grade, ref_analogues in cursor.fetchall():
            analogue_list = [a.strip() for a in ref_analogues.split('|') if a.strip()]
            if any(a.upper() == variant.upper() for a in analogue_list):
                total_refs += 1
                for analogue in analogue_list:
                    if analogue.upper() not in [v.upper() for v in variants]:
                        analogue_counter[analogue] += 1

    print(f'Found {total_refs} cross-references with {len(analogue_counter)} unique analogues')
    return analogue_counter, total_refs

def split_using_vocabulary(analogues_str, vocabulary):
    """Split analogues using vocabulary"""
    # Sort by length (longest first)
    sorted_analogues = sorted(vocabulary.keys(), key=len, reverse=True)

    matched_grades = []
    remaining_str = analogues_str

    for analogue in sorted_analogues:
        escaped_analogue = re.escape(analogue)
        pattern = r'\b' + escaped_analogue + r'\b'

        match = re.search(pattern, remaining_str, re.IGNORECASE)
        if match:
            matched_grades.append(analogue)
            remaining_str = re.sub(pattern, '', remaining_str, count=1, flags=re.IGNORECASE).strip()

    # Handle remaining
    remaining_str = ' '.join(remaining_str.split())
    if remaining_str and len(remaining_str) > 1:
        remaining_parts = remaining_str.split()
        for part in remaining_parts:
            if len(part) > 1 and part not in matched_grades:
                matched_grades.append(part)

    return matched_grades, remaining_str

# Test 4Х5МФС
print('=' * 100)
print('=== 4Х5МФС ===')
print('=' * 100)
cursor.execute('SELECT analogues FROM steel_grades WHERE grade = ?', ('4Х5МФС',))
result = cursor.fetchone()
if result:
    orig = result[0]
    print(f'Original ({len(orig)} chars):')
    print(f'{orig}')
    print()

    vocab, total_refs = collect_analogues('4Х5МФС')
    print()
    print(f'Top 30 most common analogues:')
    for analogue, count in vocab.most_common(30):
        print(f'  {analogue:30s} (refs: {count:2d})')
    print()

    # Try to split
    split_result, remaining = split_using_vocabulary(orig, vocab)
    print(f'Split result: {len(split_result)} analogues')
    print('Analogues found:')
    for i, a in enumerate(split_result, 1):
        freq = vocab.get(a, 0)
        print(f'  {i:2d}. {a:30s} (freq: {freq:2d})')
    if remaining:
        print(f'\nUnmatched parts: {remaining}')
    print()

    # Show as pipe-separated
    new_analogues = '|'.join(split_result)
    print(f'New analogues string ({len(new_analogues)} chars):')
    print(new_analogues)

print()
print('=' * 100)
print('=== Х12МФ ===')
print('=' * 100)
cursor.execute('SELECT analogues FROM steel_grades WHERE grade = ?', ('Х12МФ',))
result = cursor.fetchone()
if result:
    orig = result[0]
    print(f'Original ({len(orig)} chars):')
    print(f'{orig}')
    print()

    vocab, total_refs = collect_analogues('Х12МФ')
    print()
    print(f'Top 30 most common analogues:')
    for analogue, count in vocab.most_common(30):
        print(f'  {analogue:30s} (refs: {count:2d})')
    print()

    # Try to split
    split_result, remaining = split_using_vocabulary(orig, vocab)
    print(f'Split result: {len(split_result)} analogues')
    print('Analogues found:')
    for i, a in enumerate(split_result, 1):
        freq = vocab.get(a, 0)
        print(f'  {i:2d}. {a:30s} (freq: {freq:2d})')
    if remaining:
        print(f'\nUnmatched parts: {remaining}')
    print()

    # Show as pipe-separated
    new_analogues = '|'.join(split_result)
    print(f'New analogues string ({len(new_analogues)} chars):')
    print(new_analogues)

conn.close()
