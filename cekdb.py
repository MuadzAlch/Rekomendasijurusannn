import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

print("==== Users ====")
for row in cursor.execute("SELECT * FROM users"):
    print(row)

print("\n==== Requests ====")
for row in cursor.execute("SELECT * FROM requests"):
    print(row)

conn.close()
