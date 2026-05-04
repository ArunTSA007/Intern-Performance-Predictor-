import sqlite3
import os

# Path to the database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")

def migrate():
    if not os.path.exists(DATABASE):
        print(f"Error: Database not found at {DATABASE}")
        return

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    print("Starting migration: Updating intern usernames to email addresses...")

    try:
        # 1. Fetch all interns and their emails
        cursor.execute("""
            SELECT s.user_id, s.email 
            FROM students s 
            JOIN users u ON s.user_id = u.id 
            WHERE u.role = 'intern'
        """)
        interns = cursor.fetchall()

        updated_count = 0
        for user_id, email in interns:
            if email:
                # 2. Update the username in the users table
                cursor.execute("UPDATE users SET username = ? WHERE id = ?", (email, user_id))
                updated_count += 1

        conn.commit()
        print(f"Successfully migrated {updated_count} intern accounts to use email login.")

    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
