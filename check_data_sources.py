import sqlite3

conn = sqlite3.connect('database/steel_database.db')
cursor = conn.cursor()

print("="*100)
print("DATABASE SOURCE ANALYSIS")
print("="*100)

# Check by source
sources = [
    ('%zknives%', 'zknives.com'),
    ('%splav%', 'splav-kharkov.com'),
    (None, 'No link (CSV import)')
]

for pattern, name in sources:
    if pattern:
        cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE link LIKE ?", (pattern,))
    else:
        cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE link IS NULL OR link = ''")

    total = cursor.fetchone()[0]

    if pattern:
        cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE link LIKE ? AND (standard IS NULL OR standard = '')", (pattern,))
    else:
        cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE (link IS NULL OR link = '') AND (standard IS NULL OR standard = '')")
    no_std = cursor.fetchone()[0]

    if pattern:
        cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE link LIKE ? AND (c IS NULL OR c = '')", (pattern,))
    else:
        cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE (link IS NULL OR link = '') AND (c IS NULL OR c = '')")
    no_chem = cursor.fetchone()[0]

    print(f"\n{name}:")
    print(f"  Total: {total}")
    if total > 0:
        print(f"  Without Standard: {no_std} ({no_std*100/total:.1f}%)")
        print(f"  Without chemistry: {no_chem} ({no_chem*100/total:.1f}%)")

    # Sample grades
    if total > 0 and total <= 5:
        if pattern:
            cursor.execute("SELECT grade, standard, c FROM steel_grades WHERE link LIKE ? LIMIT 3", (pattern,))
        else:
            cursor.execute("SELECT grade, standard, c FROM steel_grades WHERE (link IS NULL OR link = '') LIMIT 3")

        print(f"  Samples:")
        for grade, standard, c in cursor.fetchall():
            print(f"    - {grade}: Std={standard or 'NO'}, C={c or 'NO'}")

# Check specific known grades
print("\n" + "="*100)
print("CHECKING KNOWN GRADES:")
print("="*100)

test_grades = ['Х12МФ', '#20', '1.2343', 'Conqueror SuperClean']

for test_grade in test_grades:
    cursor.execute("""
        SELECT grade, standard, c, cr, mo, v, analogues, link
        FROM steel_grades
        WHERE grade = ?
    """, (test_grade,))
    row = cursor.fetchone()

    if row:
        grade, standard, c, cr, mo, v, analogues, link = row
        source = "zknives" if link and "zknives" in link else "splav" if link and "splav" in link else "CSV"
        print(f"\n{grade} (from {source}):")
        print(f"  Standard: {standard or 'MISSING'}")
        print(f"  Chemistry: C={c or 'NO'}, Cr={cr or 'NO'}, Mo={mo or 'NO'}, V={v or 'NO'}")
        print(f"  Analogues: {analogues[:50] + '...' if analogues and len(analogues) > 50 else analogues or 'MISSING'}")
    else:
        print(f"\n{test_grade}: NOT FOUND")

# Check when was data added
print("\n" + "="*100)
print("RECENT ADDITIONS:")
print("="*100)

cursor.execute("""
    SELECT grade, standard, c, link
    FROM steel_grades
    ORDER BY id DESC
    LIMIT 10
""")

print("\nLast 10 added grades:")
for grade, standard, c, link in cursor.fetchall():
    source = "zknives" if link and "zknives" in link else "splav" if link and "splav" in link else "CSV"
    print(f"  {grade} (from {source}): Std={standard or 'NO'}, C={c or 'NO'}")

conn.close()
