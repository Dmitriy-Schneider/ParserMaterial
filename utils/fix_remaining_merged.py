#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix Remaining Merged Grades
============================
Manually fix grades that weren't caught by automatic script:
1. 1.563475Ni8 (pattern didn't match)
2. 347/347H (parts don't exist in DB)
"""

import sqlite3
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

db_path = 'database/steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*80)
print("FIXING REMAINING MERGED GRADES")
print("="*80)

# 1. Fix 1.563475Ni8
print("\n1. Checking 1.563475Ni8...")
cursor.execute("SELECT id, analogues FROM steel_grades WHERE grade = '1.563475Ni8'")
result = cursor.fetchone()

if result:
    grade_id, analogues = result
    print(f"  Found: 1.563475Ni8 (id={grade_id})")
    print(f"  Analogues: {analogues}")

    # Check if 1.5634 and 75Ni8 exist
    cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE grade = '1.5634'")
    has_1_5634 = cursor.fetchone()[0] > 0
    cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE grade = '75Ni8'")
    has_75Ni8 = cursor.fetchone()[0] > 0

    print(f"  1.5634 exists: {has_1_5634}")
    print(f"  75Ni8 exists: {has_75Ni8}")

    if has_1_5634 and has_75Ni8:
        print("  ACTION: Link 1.5634 <-> 75Ni8 and delete 1.563475Ni8")

        # Link 1.5634 and 75Ni8
        cursor.execute("SELECT analogues FROM steel_grades WHERE grade = '1.5634'")
        analogues_1_5634 = cursor.fetchone()[0] or ""
        if '75Ni8' not in analogues_1_5634:
            new_analogues = (analogues_1_5634 + ' 75Ni8').strip()
            cursor.execute("UPDATE steel_grades SET analogues = ? WHERE grade = '1.5634'", (new_analogues,))
            print("  Added 75Ni8 to 1.5634 analogues")

        cursor.execute("SELECT analogues FROM steel_grades WHERE grade = '75Ni8'")
        analogues_75Ni8 = cursor.fetchone()[0] or ""
        if '1.5634' not in analogues_75Ni8:
            new_analogues = (analogues_75Ni8 + ' 1.5634').strip()
            cursor.execute("UPDATE steel_grades SET analogues = ? WHERE grade = '75Ni8'", (new_analogues,))
            print("  Added 1.5634 to 75Ni8 analogues")

        # Remove 1.563475Ni8 from all analogue lists
        cursor.execute("SELECT id, grade, analogues FROM steel_grades WHERE analogues LIKE '%1.563475Ni8%'")
        for gid, gname, ganalogues in cursor.fetchall():
            analogue_list = ganalogues.split()
            if '1.563475Ni8' in analogue_list:
                analogue_list.remove('1.563475Ni8')
                new_analogues = ' '.join(analogue_list) if analogue_list else None
                cursor.execute("UPDATE steel_grades SET analogues = ? WHERE id = ?", (new_analogues, gid))
                print(f"  Removed 1.563475Ni8 from {gname}")

        # Delete 1.563475Ni8
        cursor.execute("DELETE FROM steel_grades WHERE grade = '1.563475Ni8'")
        print("  DELETED: 1.563475Ni8")
    else:
        print("  SKIP: Parts don't exist")
else:
    print("  NOT FOUND")

# 2. Fix 347/347H
print("\n2. Checking 347/347H...")
cursor.execute("SELECT id, analogues FROM steel_grades WHERE grade = '347/347H'")
result = cursor.fetchone()

if result:
    grade_id, analogues = result
    print(f"  Found: 347/347H (id={grade_id})")
    print(f"  Analogues: {analogues}")

    # Check if 347 and 347H exist
    cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE grade = '347'")
    has_347 = cursor.fetchone()[0] > 0
    cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE grade = '347H'")
    has_347H = cursor.fetchone()[0] > 0

    print(f"  347 exists: {has_347}")
    print(f"  347H exists: {has_347H}")

    if not has_347 and not has_347H:
        print("  ACTION: Simply delete 347/347H (parts don't exist)")

        # Remove 347/347H from all analogue lists
        cursor.execute("SELECT id, grade, analogues FROM steel_grades WHERE analogues LIKE '%347/347H%'")
        for gid, gname, ganalogues in cursor.fetchall():
            analogue_list = ganalogues.split()
            if '347/347H' in analogue_list:
                analogue_list.remove('347/347H')
                new_analogues = ' '.join(analogue_list) if analogue_list else None
                cursor.execute("UPDATE steel_grades SET analogues = ? WHERE id = ?", (new_analogues, gid))
                print(f"  Removed 347/347H from {gname}")

        # Delete 347/347H
        cursor.execute("DELETE FROM steel_grades WHERE grade = '347/347H'")
        print("  DELETED: 347/347H")
    else:
        print("  SKIP: Will process normally")
else:
    print("  NOT FOUND")

# Commit changes
conn.commit()

# Verify
print("\n" + "="*80)
print("VERIFICATION")
print("="*80)
cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE grade IN ('1.563475Ni8', '347/347H')")
remaining = cursor.fetchone()[0]
print(f"Remaining problematic grades: {remaining}")

cursor.execute("SELECT COUNT(*) FROM steel_grades")
total = cursor.fetchone()[0]
print(f"Total grades: {total}")

conn.close()
print("="*80)
