import sqlite3

conn = sqlite3.connect('database/steel_database.db')
cursor = conn.cursor()

cursor.execute("SELECT grade, standard FROM steel_grades WHERE grade = ?", ('4Х5МФС',))
result = cursor.fetchone()

if result:
    print(f"4Х5МФС: {result[1]}")
else:
    print("4Х5МФС not found")

conn.close()
