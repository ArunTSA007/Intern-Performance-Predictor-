import sqlite3
import os

DATABASE = "database.db"

def test_duplication_prevention():
    print("Testing duplication prevention...")
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Get a student
    cursor.execute("SELECT id FROM students LIMIT 1")
    student_id = cursor.fetchone()
    if not student_id:
        print("No students found to test.")
        return
    student_id = student_id[0]
    
    task_title = "Test Duplicate Task"
    due_date = "2026-12-31"
    
    # Try logic similar to admin_routes.py
    def check_and_insert():
        cursor.execute(
            "SELECT id FROM tasks WHERE student_id = ? AND title = ? AND due_date = ? AND status != 'completed'",
            (student_id, task_title, due_date),
        )
        if cursor.fetchone():
            return False

        cursor.execute(
            "INSERT INTO tasks (student_id, title, description, due_date, status) VALUES (?, ?, ?, ?, 'pending')",
            (student_id, task_title, "Test Desc", due_date),
        )
        return True

    # 1. Insert first time
    res1 = check_and_insert()
    print(f"First insertion: {'Success' if res1 else 'Failed'}")
    
    # 2. Try duplicate
    res2 = check_and_insert()
    print(f"Second insertion (duplicate): {'Success' if not res2 else 'FAILED (should have failed)'}")
    
    # Cleanup
    cursor.execute("DELETE FROM tasks WHERE title = ?", (task_title,))
    conn.commit()
    conn.close()

def test_quick_completion():
    print("\nTesting quick completion logic...")
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM students LIMIT 1")
    student_id = cursor.fetchone()[0]
    
    # Create a task
    cursor.execute(
        "INSERT INTO tasks (student_id, title, description, due_date, status) VALUES (?, 'Test Completion', 'Desc', '2026-12-31', 'pending')",
        (student_id,),
    )
    task_id = cursor.lastrowid
    conn.commit()
    
    # Simulate quick_task_completed logic
    cursor.execute("UPDATE tasks SET submission = 'Marked as completed by intern', status = 'submitted' WHERE id = ?", (task_id,))
    conn.commit()
    
    # Verify
    cursor.execute("SELECT status, submission FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    print(f"Updated status: {row[0]}")
    print(f"Updated submission: {row[1]}")
    
    # Cleanup
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    if os.path.exists(DATABASE):
        test_duplication_prevention()
        test_quick_completion()
    else:
        print("Database not found.")
