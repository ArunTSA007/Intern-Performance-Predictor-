import sqlite3
import os

DATABASE = "c:/Users/acer/Desktop/College/PROJECT/backend/database.db"

def check_duplicates():
    if not os.path.exists(DATABASE):
        print(f"Database not found at {DATABASE}")
        return

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    query = "SELECT student_id, title, COUNT(*) FROM tasks GROUP BY student_id, title HAVING COUNT(*) > 1;"
    cursor.execute(query)
    duplicates = cursor.fetchall()
    
    if duplicates:
        print("Found duplicate tasks:")
        for student_id, title, count in duplicates:
            print(f"Student ID: {student_id}, Title: {title}, Count: {count}")
    else:
        print("No duplicate tasks found in the database.")
    
    conn.close()

if __name__ == "__main__":
    check_duplicates()
