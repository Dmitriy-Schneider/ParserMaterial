#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix analogues separators for GOST grades
Use cross-reference analysis to properly split analogues
"""
import sqlite3
import sys
import io
import re
from database.backup_manager import backup_before_modification

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def get_all_grades():
    """Get all unique grade names from database"""
    conn = sqlite3.connect('database/steel_database.db')
    cursor = conn.cursor()

    cursor.execute('SELECT DISTINCT grade FROM steel_grades ORDER BY grade')
    grades = [row[0] for row in cursor.fetchall()]

    conn.close()
    return grades

def find_cross_references(target_grade, all_grades_dict):
    """
    Find all grades that reference target_grade in their analogues
    Returns list of (grade, analogues_list) where analogues are already split by |
    """
    references = []

    # Нормализуем целевую марку (убираем пробелы, приводим к верхнему регистру)
    target_normalized = target_grade.upper().replace(' ', '').replace('-', '')

    # Также ищем транслитерированные варианты (Х->X, К->K, М->M и т.д.)
    cyrillic_to_latin = {
        'А': 'A', 'В': 'B', 'С': 'C', 'Е': 'E', 'Н': 'H', 'К': 'K',
        'М': 'M', 'О': 'O', 'Р': 'P', 'Т': 'T', 'Х': 'X', 'У': 'U'
    }

    target_transliterated = target_grade.upper()
    for cyr, lat in cyrillic_to_latin.items():
        target_transliterated = target_transliterated.replace(cyr, lat)
    target_transliterated = target_transliterated.replace(' ', '').replace('-', '')

    for grade, analogues in all_grades_dict.items():
        if analogues and '|' in analogues:
            # Разбиваем аналоги по |
            analogue_list = [a.strip() for a in analogues.split('|') if a.strip()]

            # Проверяем каждый аналог
            for analogue in analogue_list:
                analogue_normalized = analogue.upper().replace(' ', '').replace('-', '')

                # Проверяем совпадение (точное или транслитерированное)
                if (analogue_normalized == target_normalized or
                    analogue_normalized == target_transliterated):
                    references.append((grade, analogue_list))
                    break

    return references

def split_analogues_by_cross_reference(target_grade, analogues_str, all_grades_dict, all_unique_grades):
    """
    Split analogues string using cross-reference analysis

    Strategy:
    1. Find all grades that reference target_grade
    2. Extract neighboring grades from their analogue lists
    3. Use this information to identify valid grade names in analogues_str
    4. Split analogues_str properly
    """
    if not analogues_str or analogues_str.strip() == '':
        return []

    # Step 1: Find cross-references
    cross_refs = find_cross_references(target_grade, all_grades_dict)

    if not cross_refs:
        # No cross-references found - fallback to simple space split
        print(f'  ⚠️ No cross-references found for {target_grade}')
        return analogues_str.split()

    # Step 2: Extract potential grade names from cross-references
    # Создаем словарь: какие марки встречаются вместе с нашей целевой маркой
    neighbor_grades = set()

    for ref_grade, ref_analogue_list in cross_refs:
        # Добавляем все аналоги из этой ссылки
        for analogue in ref_analogue_list:
            if analogue != target_grade:
                neighbor_grades.add(analogue)

    print(f'  Found {len(cross_refs)} cross-references with {len(neighbor_grades)} unique neighboring grades')

    # Step 3: Try to match these grades in analogues_str
    matched_grades = []
    remaining_str = analogues_str

    # Сортируем по длине (от длинных к коротким) чтобы избежать partial matches
    sorted_neighbors = sorted(neighbor_grades, key=len, reverse=True)

    for neighbor in sorted_neighbors:
        # Проверяем точное совпадение (case-insensitive, с границами слова)
        pattern = r'\b' + re.escape(neighbor) + r'\b'
        if re.search(pattern, remaining_str, re.IGNORECASE):
            matched_grades.append(neighbor)
            # Удаляем найденную марку из строки
            remaining_str = re.sub(pattern, '', remaining_str, flags=re.IGNORECASE).strip()

    # Step 4: Check if there are unmatched parts
    # Очищаем remaining_str от лишних пробелов
    remaining_str = ' '.join(remaining_str.split())

    if remaining_str and len(remaining_str) > 2:
        # Возможно, есть еще марки которые не были в cross-references
        # Попробуем найти их среди всех известных марок
        for grade in all_unique_grades:
            if len(grade) > 2:  # Игнорируем короткие марки (например, "A3")
                pattern = r'\b' + re.escape(grade) + r'\b'
                if re.search(pattern, remaining_str, re.IGNORECASE):
                    if grade not in matched_grades:
                        matched_grades.append(grade)
                        remaining_str = re.sub(pattern, '', remaining_str, flags=re.IGNORECASE).strip()

    # Step 5: Add remaining unmatched parts as individual grades (fallback)
    if remaining_str and len(remaining_str) > 1:
        # Разбиваем по пробелам и добавляем как отдельные марки
        remaining_parts = remaining_str.split()
        for part in remaining_parts:
            if len(part) > 1 and part not in matched_grades:
                matched_grades.append(part)

    return matched_grades

def analyze_fix_strategy(dry_run=True):
    """Analyze and fix analogues separators"""

    conn = sqlite3.connect('database/steel_database.db')
    cursor = conn.cursor()

    # Get all grades with analogues
    cursor.execute('''
        SELECT grade, analogues
        FROM steel_grades
        WHERE analogues IS NOT NULL
        AND analogues != ''
    ''')
    all_records = cursor.fetchall()

    # Build dictionary: grade -> analogues (only for grades with pipes)
    grades_with_pipes = {}
    grades_without_pipes = {}

    for grade, analogues in all_records:
        if analogues and '|' in analogues:
            grades_with_pipes[grade] = analogues
        elif analogues:
            grades_without_pipes[grade] = analogues

    # Get list of all unique grade names (for matching)
    all_unique_grades = set()
    cursor.execute('SELECT DISTINCT grade FROM steel_grades')
    all_unique_grades = {row[0] for row in cursor.fetchall()}

    print(f'Total grades with analogues: {len(all_records)}')
    print(f'  With pipes: {len(grades_with_pipes)}')
    print(f'  Without pipes: {len(grades_without_pipes)}')
    print()

    # Analyze problematic cases
    print('=' * 100)
    print('=== Analysis of Grades Without Separators ===')
    print('=' * 100)

    updates = []

    for i, (grade, analogues) in enumerate(grades_without_pipes.items(), 1):
        print(f'\n{i}. {grade}')
        print(f'   Original analogues ({len(analogues)} chars): {analogues[:80]}...' if len(analogues) > 80 else f'   Original analogues: {analogues}')

        # Try to split using cross-reference analysis
        split_result = split_analogues_by_cross_reference(
            grade, analogues, grades_with_pipes, all_unique_grades
        )

        if split_result and len(split_result) > 1:
            new_analogues = '|'.join(split_result)
            print(f'   ✅ Split into {len(split_result)} grades: {" | ".join(split_result[:5])}{"..." if len(split_result) > 5 else ""}')

            updates.append((grade, analogues, new_analogues, len(split_result)))
        else:
            print(f'   ⚠️ Could not split reliably (keeping as-is)')

        # Limit analysis to first 50 for dry run
        if dry_run and i >= 50:
            print(f'\n... (showing first 50, total {len(grades_without_pipes)})')
            break

    print()
    print('=' * 100)
    print(f'Summary: {len(updates)} grades can be fixed')
    print('=' * 100)

    if not dry_run and updates:
        print('\nApplying updates...')
        for grade, old_analogues, new_analogues, count in updates:
            cursor.execute(
                'UPDATE steel_grades SET analogues = ? WHERE grade = ?',
                (new_analogues, grade)
            )
            print(f'✅ Updated {grade}: {count} analogues')

        conn.commit()
        print(f'\n[SUCCESS] Updated {len(updates)} grades')
    elif dry_run:
        print('\n[DRY RUN] Changes not applied')

    conn.close()
    return len(updates)

if __name__ == '__main__':
    dry_run = '--execute' not in sys.argv

    if dry_run:
        print('=' * 100)
        print('PREVIEW MODE (DRY RUN)')
        print('Add --execute flag to apply changes')
        print('=' * 100)
    else:
        print('=' * 100)
        print('EXECUTION MODE')
        print('=' * 100)
        backup_before_modification(reason='fix_analogues_separators')

    updated_count = analyze_fix_strategy(dry_run)

    print(f'\nTotal grades that can be fixed: {updated_count}')

    if dry_run:
        print('\n[INFO] This was a preview. Run with --execute to apply changes.')
