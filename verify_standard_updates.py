import sqlite3

conn = sqlite3.connect('database/steel_database.db')
cursor = conn.cursor()

print("="*100)
print("VERIFICATION: Standard Column with Country Information")
print("="*100)

# Get total statistics
cursor.execute("SELECT COUNT(*) FROM steel_grades")
total = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE standard LIKE '%,%'")
with_country = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE standard IS NOT NULL AND standard != ''")
with_standard = cursor.fetchone()[0]

print(f"\nTotal grades: {total}")
print(f"With Standard: {with_standard}")
print(f"With country info (contains comma): {with_country}")
print(f"Without country info: {with_standard - with_country}")

# Show examples of each type
print("\n" + "="*100)
print("SAMPLE STANDARDS WITH COUNTRY:")
print("="*100)

cursor.execute("""
    SELECT DISTINCT standard
    FROM steel_grades
    WHERE standard LIKE '%,%'
    ORDER BY standard
    LIMIT 20
""")

for (standard,) in cursor.fetchall():
    print(f"  {standard}")

# Show standards without country (if any)
print("\n" + "="*100)
print("STANDARDS WITHOUT COUNTRY (should be empty or minimal):")
print("="*100)

cursor.execute("""
    SELECT DISTINCT standard, COUNT(*) as count
    FROM steel_grades
    WHERE standard IS NOT NULL
      AND standard != ''
      AND standard NOT LIKE '%,%'
    GROUP BY standard
    ORDER BY count DESC
    LIMIT 10
""")

no_country = cursor.fetchall()
if no_country:
    for standard, count in no_country:
        print(f"  {standard}: {count} grades")
else:
    print("  None - All standards have country info!")

# Show sample grades with their standards
print("\n" + "="*100)
print("SAMPLE GRADES WITH STANDARDS:")
print("="*100)

cursor.execute("""
    SELECT grade, standard
    FROM steel_grades
    WHERE standard IS NOT NULL AND standard != ''
    ORDER BY RANDOM()
    LIMIT 15
""")

for grade, standard in cursor.fetchall():
    print(f"  {grade}: {standard}")

conn.close()
