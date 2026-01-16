import sqlite3

conn = sqlite3.connect('database/steel_database.db')
cursor = conn.cursor()

print("="*100)
print("CHECKING FOR MISSING DATA IN DATABASE")
print("="*100)

# Get total statistics
cursor.execute("SELECT COUNT(*) FROM steel_grades")
total = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE standard IS NULL OR standard = ''")
no_standard = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE c IS NULL OR c = ''")
no_chemistry = cursor.fetchone()[0]

print(f"\nTotal grades: {total}")
print(f"WITHOUT Standard: {no_standard} ({no_standard*100/total:.1f}%)")
print(f"WITHOUT chemistry (C): {no_chemistry} ({no_chemistry*100/total:.1f}%)")

# Check specific grade from splav (Х12МФ)
print("\n" + "="*100)
print("CHECKING Х12МФ from splav-kharkov:")
print("="*100)

cursor.execute("""
    SELECT grade, standard, c, cr, mo, v, w, analogues
    FROM steel_grades
    WHERE grade = 'Х12МФ'
""")
row = cursor.fetchone()
if row:
    grade, standard, c, cr, mo, v, w, analogues = row
    print(f"Grade: {grade}")
    print(f"Standard: {standard or 'MISSING'}")
    print(f"C: {c or 'MISSING'}")
    print(f"Cr: {cr or 'MISSING'}")
    print(f"Mo: {mo or 'MISSING'}")
    print(f"V: {v or 'MISSING'}")
    print(f"W: {w or 'MISSING'}")
    print(f"Analogues: {analogues or 'MISSING'}")
else:
    print("NOT FOUND in database!")

# Sample grades WITHOUT Standard column
print("\n" + "="*100)
print("SAMPLE GRADES WITHOUT STANDARD (first 20):")
print("="*100)

cursor.execute("""
    SELECT grade, c, cr, link
    FROM steel_grades
    WHERE standard IS NULL OR standard = ''
    LIMIT 20
""")

for grade, c, cr, link in cursor.fetchall():
    source = "zknives" if link and "zknives" in link else "splav" if link and "splav" in link else "unknown"
    print(f"  {grade} (source: {source}) - C: {c or 'MISSING'}, Cr: {cr or 'MISSING'}")

# Sample grades WITHOUT chemistry
print("\n" + "="*100)
print("SAMPLE GRADES WITHOUT CHEMISTRY (first 20):")
print("="*100)

cursor.execute("""
    SELECT grade, standard, link
    FROM steel_grades
    WHERE (c IS NULL OR c = '') AND (cr IS NULL OR cr = '')
    LIMIT 20
""")

for grade, standard, link in cursor.fetchall():
    source = "zknives" if link and "zknives" in link else "splav" if link and "splav" in link else "unknown"
    print(f"  {grade} (source: {source}) - Standard: {standard or 'MISSING'}")

# Check by source
print("\n" + "="*100)
print("STATISTICS BY SOURCE:")
print("="*100)

# zknives
cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE link LIKE '%zknives%'")
zknives_total = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE link LIKE '%zknives%' AND (standard IS NULL OR standard = '')")
zknives_no_std = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE link LIKE '%zknives%' AND (c IS NULL OR c = '')")
zknives_no_chem = cursor.fetchone()[0]

print(f"\nzknives.com:")
print(f"  Total: {zknives_total}")
print(f"  Without Standard: {zknives_no_std} ({zknives_no_std*100/zknives_total:.1f}% if zknives_total else 0)")
print(f"  Without chemistry: {zknives_no_chem} ({zknives_no_chem*100/zknives_total:.1f}% if zknives_total else 0)")

# splav
cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE link LIKE '%splav%'")
splav_total = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE link LIKE '%splav%' AND (standard IS NULL OR standard = '')")
splav_no_std = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE link LIKE '%splav%' AND (c IS NULL OR c = '')")
splav_no_chem = cursor.fetchone()[0]

print(f"\nsplav-kharkov.com:")
print(f"  Total: {splav_total}")
print(f"  Without Standard: {splav_no_std} ({splav_no_std*100/splav_total:.1f}% if splav_total else 0)")
print(f"  Without chemistry: {splav_no_chem} ({splav_no_chem*100/splav_total:.1f}% if splav_total else 0)")

conn.close()
