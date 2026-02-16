#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze analogues separator problem
Find GOST grades without pipe separators
"""
import sqlite3
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

conn = sqlite3.connect('database/steel_database.db')
cursor = conn.cursor()

# Get all grades with analogues
cursor.execute('''
    SELECT grade, analogues, standard
    FROM steel_grades
    WHERE analogues IS NOT NULL
    AND analogues != ''
''')
all_with_analogues = cursor.fetchall()

# Split into with/without pipes
with_pipes = []
without_pipes = []

for grade, analogues, standard in all_with_analogues:
    if analogues and '|' in analogues:
        with_pipes.append((grade, analogues, standard))
    else:
        without_pipes.append((grade, analogues, standard))

print(f'Марки С разделителями |: {len(with_pipes)}')
print(f'Марки БЕЗ разделителей: {len(without_pipes)}')
print()

# Show grades without pipes
print('=' * 100)
print('=== Марки БЕЗ разделителей (все) ===')
print('=' * 100)
for i, (grade, analogues, standard) in enumerate(without_pipes, 1):
    short_analogues = analogues[:80] + '...' if len(analogues) > 80 else analogues
    print(f'{i:3d}. {grade:25s} | {standard[:30]:30s} | {short_analogues}')

print()
print('=' * 100)
print('=== Примеры марок С разделителями (для сравнения) ===')
print('=' * 100)

# Show examples with pipes
for i, (grade, analogues, standard) in enumerate(with_pipes[:5], 1):
    print(f'\n{i}. {grade} ({standard})')
    analogue_list = [a.strip() for a in analogues.split('|') if a.strip()]
    print(f'   Количество аналогов: {len(analogue_list)}')
    print(f'   Первые 10: {" | ".join(analogue_list[:10])}')

conn.close()
