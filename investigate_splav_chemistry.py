"""
Investigate why splav-kharkov grades don't have chemistry
"""
import sqlite3

conn = sqlite3.connect('database/steel_database.db')
cursor = conn.cursor()

print("="*100)
print("INVESTIGATING SPLAV-KHARKOV CHEMISTRY ISSUE")
print("="*100)

# Get splav grades
cursor.execute("""
    SELECT grade, c, cr, mo, v, link, standard
    FROM steel_grades
    WHERE link LIKE '%splav%'
    ORDER BY id ASC
    LIMIT 20
""")

print("\nFirst 20 splav-kharkov grades:")
print("="*100)

for grade, c, cr, mo, v, link, standard in cursor.fetchall():
    print(f"{grade}:")
    print(f"  C={c or 'NO'}, Cr={cr or 'NO'}, Mo={mo or 'NO'}, V={v or 'NO'}")
    print(f"  Link: {link}")
    print(f"  Standard: {standard}")
    print()

# Check if ANY splav grade has chemistry
cursor.execute("""
    SELECT COUNT(*)
    FROM steel_grades
    WHERE link LIKE '%splav%'
      AND (c IS NOT NULL AND c != '')
""")
with_chem = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE link LIKE '%splav%'")
total_splav = cursor.fetchone()[0]

print("="*100)
print(f"splav-kharkov grades with chemistry: {with_chem} out of {total_splav}")
print("="*100)

if with_chem > 0:
    print("\nGrades WITH chemistry:")
    cursor.execute("""
        SELECT grade, c, cr
        FROM steel_grades
        WHERE link LIKE '%splav%'
          AND (c IS NOT NULL AND c != '')
        LIMIT 10
    """)
    for grade, c, cr in cursor.fetchall():
        print(f"  {grade}: C={c}, Cr={cr or 'NO'}")
else:
    print("\nNO splav-kharkov grades have chemistry!")
    print("This means parser is not extracting chemistry AT ALL.")

# Check if parser is even running
print("\n" + "="*100)
print("THEORY:")
print("="*100)
print("1. If parser extracts chemistry in test but not in DB,")
print("   then either:")
print("   a) Parser is NOT running the parse_grade_page() method")
print("   b) Parser is running but pages don't have chemistry tables")
print("   c) Parser is running but chemistry extraction is failing silently")

conn.close()
