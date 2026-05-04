import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")

def migrate():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    print("Creating profile_update_requests table...")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profile_update_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        changed_data TEXT NOT NULL,
        status TEXT DEFAULT 'pending', 
        requested_at TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id)
    )
    """)

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
