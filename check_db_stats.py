import sqlite3

conn = sqlite3.connect('database/steel_database.db')
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM steel_grades')
total = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE analogues IS NOT NULL AND analogues != ''")
with_ana = cursor.fetchone()[0]

print(f'Total grades: {total}')
print(f'With analogues: {with_ana}')

conn.close()
