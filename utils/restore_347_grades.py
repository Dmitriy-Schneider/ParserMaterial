#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Restore 347 and 347H grades
=============================
These are real AISI grades that were incorrectly deleted
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

db_path = 'database/steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*80)
print("RESTORING 347 and 347H GRADES")
print("="*80)

# Get composition from S34700
cursor.execute("""
    SELECT c, si, mn, cr, mo, ni, v, w, co, cu, nb, n, s, p, other_elements
    FROM steel_grades WHERE grade = 'S34700'
""")
s34700_comp = cursor.fetchone()

# Get analogues from S34700
cursor.execute("SELECT analogues FROM steel_grades WHERE grade = 'S34700'")
s34700_analogues = cursor.fetchone()[0] or ""

# Get analogues from 1.4550
cursor.execute("SELECT analogues FROM steel_grades WHERE grade = '1.4550'")
_1_4550_analogues = cursor.fetchone()[0] or ""

print("\nS34700 composition:")
print(f"  C={s34700_comp[0]}, Cr={s34700_comp[3]}, Ni={s34700_comp[5]}, Nb={s34700_comp[10]}")

print(f"\nS34700 analogues: {s34700_analogues}")
print(f"1.4550 analogues: {_1_4550_analogues}")

# Combine analogues from both sources
all_analogues = set()
for a in s34700_analogues.split():
    if a and a not in ['347/347H']:
        all_analogues.add(a)
for a in _1_4550_analogues.split():
    if a and a not in ['347/347H']:
        all_analogues.add(a)

# Add each other as analogues
all_analogues.add('347H')  # For 347
analogues_347 = ' '.join(sorted(all_analogues))

all_analogues_347h = all_analogues.copy()
all_analogues_347h.remove('347H')
all_analogues_347h.add('347')
analogues_347h = ' '.join(sorted(all_analogues_347h))

# Create 347
print("\n1. Creating 347...")
cursor.execute("""
    INSERT INTO steel_grades (
        grade, c, si, mn, cr, mo, ni, v, w, co, cu, nb, n, s, p,
        other_elements, analogues, standard
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    '347',
    s34700_comp[0],   # c
    s34700_comp[1],   # si
    s34700_comp[2],   # mn
    s34700_comp[3],   # cr
    s34700_comp[4],   # mo
    s34700_comp[5],   # ni
    s34700_comp[6],   # v
    s34700_comp[7],   # w
    s34700_comp[8],   # co
    s34700_comp[9],   # cu
    s34700_comp[10],  # nb
    s34700_comp[11],  # n
    s34700_comp[12],  # s
    s34700_comp[13],  # p
    s34700_comp[14],  # other_elements
    analogues_347,
    'AISI 347, США'
))
print(f"  Created 347 with {len(all_analogues)} analogues")

# Create 347H
print("\n2. Creating 347H...")
cursor.execute("""
    INSERT INTO steel_grades (
        grade, c, si, mn, cr, mo, ni, v, w, co, cu, nb, n, s, p,
        other_elements, analogues, standard
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    '347H',
    s34700_comp[0],   # c
    s34700_comp[1],   # si
    s34700_comp[2],   # mn
    s34700_comp[3],   # cr
    s34700_comp[4],   # mo
    s34700_comp[5],   # ni
    s34700_comp[6],   # v
    s34700_comp[7],   # w
    s34700_comp[8],   # co
    s34700_comp[9],   # cu
    s34700_comp[10],  # nb
    s34700_comp[11],  # n
    s34700_comp[12],  # s
    s34700_comp[13],  # p
    s34700_comp[14],  # other_elements
    analogues_347h,
    'AISI 347H, США'
))
print(f"  Created 347H with {len(all_analogues_347h)} analogues")

# Update S34700 and 1.4550 to include 347 and 347H
print("\n3. Updating S34700 analogues...")
cursor.execute("SELECT analogues FROM steel_grades WHERE grade = 'S34700'")
s34700_anl = cursor.fetchone()[0] or ""
new_s34700_anl = (s34700_anl.replace('347/347H', '') + ' 347 347H').strip()
new_s34700_anl = ' '.join(new_s34700_anl.split())  # Remove duplicate spaces
cursor.execute("UPDATE steel_grades SET analogues = ? WHERE grade = 'S34700'", (new_s34700_anl,))
print(f"  Updated S34700")

print("\n4. Updating 1.4550 analogues...")
cursor.execute("SELECT analogues FROM steel_grades WHERE grade = '1.4550'")
_1_4550_anl = cursor.fetchone()[0] or ""
new_1_4550_anl = (_1_4550_anl.replace('347/347H', '') + ' 347 347H').strip()
new_1_4550_anl = ' '.join(new_1_4550_anl.split())
cursor.execute("UPDATE steel_grades SET analogues = ? WHERE grade = '1.4550'", (new_1_4550_anl,))
print(f"  Updated 1.4550")

# Commit
conn.commit()

# Verify
print("\n" + "="*80)
print("VERIFICATION")
print("="*80)
cursor.execute("SELECT grade, standard, analogues FROM steel_grades WHERE grade IN ('347', '347H') ORDER BY grade")
for grade, standard, analogues in cursor.fetchall():
    print(f"\n{grade}:")
    print(f"  Standard: {standard}")
    print(f"  Analogues: {' '.join(analogues.split()[:10])}...")

cursor.execute("SELECT COUNT(*) FROM steel_grades")
total = cursor.fetchone()[0]
print(f"\nTotal grades: {total}")

conn.close()
print("="*80)
