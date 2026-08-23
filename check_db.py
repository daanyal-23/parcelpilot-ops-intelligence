import sqlite3

conn = sqlite3.connect("backend/parcelpilot.db")

print("TKT-505:")
print(
    conn.execute(
        "SELECT * FROM tickets WHERE ticket_id='TKT-505'"
    ).fetchone()
)

print("\nLatest actions:")
for row in conn.execute(
    "SELECT * FROM actions ORDER BY rowid DESC LIMIT 5"
):
    print(row)

conn.close()