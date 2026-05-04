import sqlite3
import os

DATABASE = 'database.db'

def migrate():
    if not os.path.exists(DATABASE):
        print(f"Database {DATABASE} not found!")
        return

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    try:
        # Add submission column
        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN submission TEXT")
            print("Added 'submission' column to tasks table.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("'submission' column already exists.")
            else:
                raise e

        # Add submitted_at column
        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN submitted_at TEXT")
            print("Added 'submitted_at' column to tasks table.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("'submitted_at' column already exists.")
            else:
                raise e

        conn.commit()
        print("Migration completed successfully.")

    except Exception as e:
        print(f"An error occurred during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
