import sqlite3
import os

DATABASE = "database.db"

def check_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    print("-" * 20)
    print("DIAGNOSTICS")
    print("-" * 20)
    
    # Check Tasks
    cursor.execute("SELECT id, student_id, title, status FROM tasks WHERE status = 'pending'")
    pending_tasks = cursor.fetchall()
    print(f"Total pending tasks: {len(pending_tasks)}")
    
    # Check Students
    cursor.execute("SELECT id, name FROM students")
    students = cursor.fetchall()
    student_ids = [s[0] for s in students]
    print(f"Total students: {len(students)}")
    
    # Check IR
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='internship_registrations'")
    if cursor.fetchone():
        cursor.execute("SELECT id, student_id FROM internship_registrations WHERE status = 'Pending'")
        pending_ir = cursor.fetchall()
        print(f"Total pending Internship Registrations (IR): {len(pending_ir)}")
        for ir in pending_ir:
            if ir[1] not in student_ids:
                print(f"  ORPHAN IR: ID={ir[0]}, StudentID={ir[1]}")
    else:
        print("Table 'internship_registrations' does not exist.")

    for t in pending_tasks:
        if t[1] not in student_ids:
            print(f"  ORPHAN TASK: ID={t[0]}, Title='{t[2]}', StudentID={t[1]}")
    
    conn.close()

if __name__ == "__main__":
    check_db()
