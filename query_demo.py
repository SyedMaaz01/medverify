import sqlite3

conn = sqlite3.connect('medverify.db')
c = conn.cursor()
c.execute("SELECT name, drap_license_no, password_hash, role FROM manufacturers LIMIT 5")
print("All Users:")
for row in c.fetchall():
    print(f"  Name: {row[0]}")
    print(f"  DRAP License: {row[1]}")
    print(f"  Role: {row[3]}")
    print()
conn.close()
