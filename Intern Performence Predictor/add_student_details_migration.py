import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")

def migrate():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    columns_to_add = [
        ("phone_number", "TEXT"),
        ("profile_pic", "TEXT"),
        ("gender", "TEXT"),
        ("dob", "TEXT"),
        ("address", "TEXT"),
        ("linkedin_url", "TEXT"),
        ("github_url", "TEXT")
    ]

    print("Checking for new columns...")
    
    # Get existing columns
    cursor.execute("PRAGMA table_info(students)")
    existing_columns = [row[1] for row in cursor.fetchall()]

    for col_name, col_type in columns_to_add:
        if col_name not in existing_columns:
            print(f"Adding column: {col_name}")
            try:
                cursor.execute(f"ALTER TABLE students ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError as e:
                print(f"Error adding {col_name}: {e}")
        else:
            print(f"Column {col_name} already exists.")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
