"""Verify CSV import fixes"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*100)
print("VERIFICATION OF CSV IMPORT FIXES")
print("="*100)

# Total grades
cursor.execute('SELECT COUNT(*) FROM steel_grades')
total = cursor.fetchone()[0]
print(f'\nTotal grades: {total}')

# Check deleted merged grades
print('\n' + '='*100)
print('1. CHECKING DELETED MERGED GRADES')
print('='*100)

deleted_grades = [
    '1.17301045', '1.2063145Cr6', '1.2345H11',
    '1.3345 ~ASP 2023', '1.3241\n~ASP 2060', '1.3244\n~ASP 2030'
]

all_deleted = True
for g in deleted_grades:
    cursor.execute('SELECT COUNT(*) FROM steel_grades WHERE grade = ?', (g,))
    exists = cursor.fetchone()[0] > 0
    status = "EXISTS (ERROR)" if exists else "DELETED (OK)"
    print(f'  {g[:30]:30} : {status}')
    if exists:
        all_deleted = False

print(f'\nResult: {"ALL DELETED" if all_deleted else "SOME STILL EXIST"}')

# Check duplex steels analogues
print('\n' + '='*100)
print('2. CHECKING DUPLEX STEELS ANALOGUES (should contain 255, not 25)')
print('='*100)

cursor.execute('SELECT grade, analogues FROM steel_grades WHERE grade IN ("1.4501", "1.4507", "S32506", "S32520")')
duplex_fixed = True
for row in cursor.fetchall():
    grade, analogues = row
    has_255 = '255' in analogues if analogues else False
    has_25_error = ' 25 ' in f' {analogues} ' if analogues else False

    print(f'\n  Grade: {grade}')
    print(f'  Analogues: {analogues[:80]}...')
    print(f'  Contains 255: {has_255}')
    print(f'  Contains 25 (error): {has_25_error}')

    if has_25_error:
        print('  Status: ERROR - still has "25" instead of "255"')
        duplex_fixed = False
    else:
        print('  Status: OK')

print(f'\nResult: {"ALL FIXED" if duplex_fixed else "ERRORS FOUND"}')

# Check grade 255
print('\n' + '='*100)
print('3. CHECKING GRADE 255 STANDARD')
print('='*100)

cursor.execute('SELECT grade, standard, analogues FROM steel_grades WHERE grade = "255"')
r = cursor.fetchone()

if r:
    grade, standard, analogues = r
    print(f'  Grade: {grade}')
    print(f'  Standard: {standard}')
    print(f'  Analogues: {analogues[:80]}...')

    if standard and 'AISI' in standard:
        print('  Status: OK - Standard is set to AISI')
    else:
        print('  Status: ERROR - Standard not set properly')
else:
    print('  Status: ERROR - Grade 255 not found!')

print('\n' + '='*100)
print('VERIFICATION COMPLETE')
print('='*100)

conn.close()
