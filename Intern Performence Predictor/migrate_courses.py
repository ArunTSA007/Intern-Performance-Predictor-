import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")

def migrate_db():
    print(f"Connecting to database at {DATABASE}...")
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    try:
        # Check if columns exist
        cursor.execute("PRAGMA table_info(courses)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "description" not in columns:
            print("Adding 'description' column to 'courses' table...")
            cursor.execute("ALTER TABLE courses ADD COLUMN description TEXT")
        else:
            print("'description' column already exists.")

        if "duration" not in columns:
            print("Adding 'duration' column to 'courses' table...")
            cursor.execute("ALTER TABLE courses ADD COLUMN duration TEXT")
        else:
            print("'duration' column already exists.")

        conn.commit()
        print("Migration completed successfully.")
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_db()
