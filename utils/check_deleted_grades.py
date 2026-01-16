#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check ALL deleted grades to see if we deleted needed ones
"""

import sqlite3
import re

db_path = 'database/steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# List of ALL grades that were split/deleted
deleted_grades = [
    # From split_merged_grades.py
    'C100W1', 'X12F1', 'OCR12V2', 'XC48H1', 'X13T6', 'C75W1', 'R18F2', 'XC38H1',
    'T11304M4', 'T30102A2', 'T30103A3', 'T30104A4', 'T30107A7', 'T30108A8', 'T30109A9',
    'T11301M1', 'T11302M2', 'T11342M42', 'XVC5M48', 'T30110A10', 'T30401D1', 'T30403D3',
    'T30404D4', 'T30405D5', 'T31501O1', 'T31502O2', 'T31506O6', 'T31507O7', 'T41901S1',
    'T41902S2', 'T41904S4', 'T41906S6', 'T41907S7', 'T61201L1', 'T61202L2', 'T61206L6',
    'T61207L7', 'T72301W1', 'T72302W2', 'T72304W4', 'T72305W5', 'T72307W7', 'T11306M6',
    'T11310M10', 'T11330M30', 'T11333M33', 'T11334M34', 'T11336M36', 'T11341M41',
    'T11343M43', 'T11344M44', 'T11346M46', 'T11347M47', 'T12001T1', 'T12002T2',
    'T12004T4', 'T12005T5', 'T12006T6', 'T12008T8', 'T12015T15', 'T20811H11',
    'T20813H13', 'R12F3', 'R6M3', 'H12F1', '1.4125440C', '1.4535440C', '1.4112440B',
    '1.2834105V', '1.2442115W8', '1.2316420J2', '1.2838145V33',
    # From fix_remaining_merged.py
    '1.563475Ni8', '347/347H'
]

print("="*80)
print("CHECKING ALL DELETED GRADES")
print("="*80)

# Categorize by pattern
slash_grades = [g for g in deleted_grades if '/' in g]
decimal_grades = [g for g in deleted_grades if re.match(r'^\d\.\d+', g)]
t_number_letter = [g for g in deleted_grades if re.match(r'^T\d+[A-Z]\d+$', g)]
other_grades = [g for g in deleted_grades if g not in slash_grades + decimal_grades + t_number_letter]

print(f"\nTotal deleted: {len(deleted_grades)}")
print(f"  With slash (/): {len(slash_grades)}")
print(f"  Decimal pattern: {len(decimal_grades)}")
print(f"  T-number-letter: {len(t_number_letter)}")
print(f"  Other: {len(other_grades)}")

# Check slash grades - THESE ARE MOST SUSPICIOUS
print("\n" + "="*80)
print("SLASH GRADES (/) - NEED REVIEW")
print("="*80)
for grade in slash_grades:
    print(f"\n{grade}:")
    parts = grade.split('/')
    print(f"  Should be split into: {' + '.join(parts)}")

    # Check if we have similar grades in database
    for part in parts:
        cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE grade LIKE ?", (f"%{part}%",))
        count = cursor.fetchone()[0]
        if count > 0:
            cursor.execute("SELECT grade FROM steel_grades WHERE grade LIKE ? LIMIT 5", (f"%{part}%",))
            similar = [row[0] for row in cursor.fetchall()]
            print(f"  Similar to '{part}': {', '.join(similar)}")

# Check if there are OTHER grades with slash that we DIDN'T delete
print("\n" + "="*80)
print("OTHER SLASH GRADES IN DATABASE (NOT DELETED)")
print("="*80)
cursor.execute("SELECT grade, standard, analogues FROM steel_grades WHERE grade LIKE '%/%' ORDER BY grade")
remaining_slash = cursor.fetchall()
if remaining_slash:
    print(f"Found {len(remaining_slash)} slash grades still in database:")
    for grade, standard, analogues in remaining_slash:
        print(f"  {grade:<30} {standard}")
else:
    print("No slash grades remaining")

# For 347/347H specifically - check what S34700 and 1.4550 have
print("\n" + "="*80)
print("347/347H SPECIFIC CHECK")
print("="*80)
print("\nS34700 details:")
cursor.execute("SELECT standard, c, cr, ni, mo, v, w, co, mn, si, s, p, cu, nb, n, analogues FROM steel_grades WHERE grade = 'S34700'")
result = cursor.fetchone()
if result:
    print(f"  Standard: {result[0]}")
    print(f"  Composition: C={result[1]}, Cr={result[2]}, Ni={result[3]}, Mn={result[8]}, Si={result[9]}, Nb={result[13]}")
    print(f"  Analogues: {result[15]}")

print("\n1.4550 details:")
cursor.execute("SELECT standard, c, cr, ni, mo, v, w, co, mn, si, s, p, cu, nb, n, analogues FROM steel_grades WHERE grade = '1.4550'")
result = cursor.fetchone()
if result:
    print(f"  Standard: {result[0]}")
    print(f"  Composition: C={result[1]}, Cr={result[2]}, Ni={result[3]}, Mn={result[8]}, Si={result[9]}, Nb={result[13]}")
    print(f"  Analogues: {result[15]}")

conn.close()
print("\n" + "="*80)
