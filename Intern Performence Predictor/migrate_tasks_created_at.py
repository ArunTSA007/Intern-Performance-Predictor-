import sqlite3
import datetime
import os

DATABASE = 'database.db'

def migrate():
    if not os.path.exists(DATABASE):
        print(f"Database {DATABASE} not found!")
        return

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    try:
        # Add created_at column
        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN created_at TEXT")
            print("Added 'created_at' column to tasks table.")
            
            # Backfill with current time so existing entries aren't null
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(f"UPDATE tasks SET created_at = '{current_time}' WHERE created_at IS NULL")
            print("Backfilled 'created_at' for existing records.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("'created_at' column already exists.")
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
