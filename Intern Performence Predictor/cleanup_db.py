import sqlite3
import os

DATABASE = "database.db"

def cleanup():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    print("Deleting orphaned tasks...")
    cursor.execute("""
        DELETE FROM tasks 
        WHERE student_id NOT IN (SELECT id FROM students)
    """)
    tasks_deleted = cursor.rowcount
    print(f"Deleted {tasks_deleted} orphaned tasks.")
    
    print("Deleting orphaned internship registrations...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='internship_registrations'")
    if cursor.fetchone():
        cursor.execute("""
            DELETE FROM internship_registrations 
            WHERE student_id NOT IN (SELECT id FROM students)
        """)
        ir_deleted = cursor.rowcount
        print(f"Deleted {ir_deleted} orphaned internship registrations.")
    
    conn.commit()
    conn.close()
    print("Cleanup complete.")

if __name__ == "__main__":
    cleanup()
