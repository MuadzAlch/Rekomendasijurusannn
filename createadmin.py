import sqlite3
import hashlib

# Koneksi ke database
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Data admin
username = "admin"
password = "admin123"  # ganti sesuai keinginan
hashed = hashlib.sha256(password.encode()).hexdigest()
role = "admin"

# Insert admin
try:
    cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                   (username, hashed, role))
    conn.commit()
    print("Akun admin berhasil dibuat ✅")
except sqlite3.IntegrityError:
    print("Username admin sudah ada ❌")
finally:
    conn.close()
