import os
import sqlite3
from datetime import datetime, date
from typing import Dict, Any

import numpy as np
from flask import session


# Path to SQLite database (same as old `DATABASE = 'database.db'`)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")


# --- Database Initialization ---
def init_db() -> None:
    """
    Create tables and seed basic data if they do not exist.
    This was extracted from the old `app.py` so that database
    setup is handled in a single, reusable module.
    """
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Informative logs for development
    if not os.path.exists(DATABASE):
        print("Creating new database...")
    else:
        print("Database already exists, checking schema...")

    # Core tables
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            total_expected_tasks INTEGER DEFAULT 10
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unique_student_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            course_id INTEGER,
            user_id INTEGER UNIQUE,

            internship_type TEXT,
            joining_date TEXT,
            ending_date TEXT,
            college_name TEXT,
            department TEXT,

            FOREIGN KEY (course_id) REFERENCES courses(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            course_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            due_date TEXT,
            status TEXT DEFAULT 'pending',
            mark REAL DEFAULT 0,
            submission TEXT,
            submitted_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id),
            UNIQUE(student_id, date)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            student_id INTEGER NOT NULL,
            admin_id INTEGER NOT NULL,
            score REAL,
            comments TEXT,
            feedback_date TEXT NOT NULL,
            feedback_category TEXT,
            FOREIGN KEY (task_id) REFERENCES tasks(id),
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (admin_id) REFERENCES users(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS leave_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            reason TEXT,
            from_date TEXT,
            to_date TEXT,
            status TEXT DEFAULT 'Pending',
            leave_type TEXT,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS student_feedback_to_admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS internship_registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            registered_at TEXT NOT NULL,
            status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'Viewed', 'Contacted')),
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS behaviour_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            rating INTEGER NOT NULL,
            admin_id INTEGER NOT NULL,
            UNIQUE(student_id, date)
        )
        """
    )

    # Seed admin user
    cursor.execute(
        "INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
        ("admin", "adminpass", "admin"),
    )

    # Seed example intern + student profile
    cursor.execute("SELECT id FROM users WHERE username = 'intern1'")
    intern1_user_id = cursor.fetchone()
    if not intern1_user_id:
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("intern1@example.com", "internpass", "intern"),
        )
        intern1_user_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO students (unique_student_id, name, email, user_id) "
            "VALUES (?, ?, ?, ?)",
            ("INT001", "Intern One", "intern1@example.com", intern1_user_id),
        )

    # Seed some internships
    cursor.execute(
        "INSERT OR IGNORE INTO courses (name, total_expected_tasks, description, duration) VALUES (?, ?, ?, ?)",
        ("AI & Machine Learning Internship", 10, "Focuses on building predictive models and deep learning applications.", "3 Months"),
    )
    cursor.execute(
        "INSERT OR IGNORE INTO courses (name, total_expected_tasks, description, duration) VALUES (?, ?, ?, ?)",
        ("Full Stack Web Development Internship", 12, "Building modern web apps using Python, Flask, and React.", "4 Months"),
    )
    cursor.execute(
        "INSERT OR IGNORE INTO courses (name, total_expected_tasks, description, duration) VALUES (?, ?, ?, ?)",
        ("Data Analytics & Visualization Internship", 8, "Analyze large datasets and create interactive dashboards.", "2 Months"),
    )
    cursor.execute(
        "INSERT OR IGNORE INTO courses (name, total_expected_tasks, description, duration) VALUES (?, ?, ?, ?)",
        ("Cybersecurity & Ethical Hacking Internship", 9, "Learn network security, penetration testing, and risk assessment.", "3 Months"),
    )
    cursor.execute(
        "INSERT OR IGNORE INTO courses (name, total_expected_tasks, description, duration) VALUES (?, ?, ?, ?)",
        ("Cloud Infrastructure (AWS/Azure) Internship", 7, "Deployment, scaling, and management of cloud resources.", "3 Months"),
    )

    # Link sample student to a course and seed tasks/attendance/feedback
    cursor.execute("SELECT id FROM courses WHERE name = 'Full Stack Web Development Internship'")
    web_dev_course_id = cursor.fetchone()[0]

    cursor.execute("SELECT id FROM students WHERE unique_student_id = 'INT001'")
    int001_student_row = cursor.fetchone()

    if int001_student_row:
        int001_student_id = int001_student_row[0]

        cursor.execute(
            "UPDATE students SET course_id = ? WHERE id = ?",
            (web_dev_course_id, int001_student_id),
        )

        # Sample tasks
        cursor.execute(
            "SELECT id FROM tasks WHERE student_id = ? AND title = ?",
            (int001_student_id, "Complete Flask Tutorial"),
        )
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO tasks (student_id, course_id, title, description, due_date, status, mark) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    int001_student_id,
                    web_dev_course_id,
                    "Complete Flask Tutorial",
                    "completed",
                    "2025-08-10",
                    "completed",
                    90,
                ),
            )

        cursor.execute(
            "SELECT id FROM tasks WHERE student_id = ? AND title = ?",
            (int001_student_id, "Research ML Models"),
        )
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO tasks (student_id, course_id, title, description, due_date, status, mark) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    int001_student_id,
                    web_dev_course_id,
                    "Research ML Models",
                    "Research different ML models for performance prediction.",
                    "2025-08-05",
                    "completed",
                    85,
                ),
            )

        cursor.execute(
            "SELECT id FROM tasks WHERE student_id = ? AND title = ?",
            (int001_student_id, "Build Simple API"),
        )
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO tasks (student_id, course_id, title, description, due_date, status, mark) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    int001_student_id,
                    web_dev_course_id,
                    "Build Simple API",
                    "Develop a basic REST API using Flask.",
                    "2025-08-15",
                    "pending",
                    0,
                ),
            )

        # Sample attendance
        for sample_date, status in [
            ("2025-07-20", "present"),
            ("2025-07-21", "present"),
            ("2025-07-22", "absent"),
        ]:
            cursor.execute(
                "SELECT id FROM attendance WHERE student_id = ? AND date = ?",
                (int001_student_id, sample_date),
            )
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)",
                    (int001_student_id, sample_date, status),
                )

        # Sample feedback + behaviour ratings
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        admin_user_id = cursor.fetchone()[0]

        cursor.execute(
            "SELECT id FROM feedback WHERE student_id = ? AND comments LIKE ?",
            (int001_student_id, "%Good work on Flask%"),
        )
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO feedback (student_id, admin_id, score, comments, feedback_date, feedback_category) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    int001_student_id,
                    admin_user_id,
                    8.5,
                    "Good work on Flask tutorial, keep it up!",
                    "2025-07-20",
                    "Good",
                ),
            )

        cursor.execute(
            "SELECT id FROM feedback WHERE student_id = ? AND comments LIKE ?",
            (int001_student_id, "%Excellent research skills%"),
        )
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO feedback (student_id, admin_id, score, comments, feedback_date, feedback_category) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    int001_student_id,
                    admin_user_id,
                    9.0,
                    "Excellent research skills demonstrated.",
                    "2025-07-25",
                    "Excellent",
                ),
            )

        for sample_date, rating in [("2025-07-20", 4), ("2025-07-21", 5)]:
            cursor.execute(
                "SELECT id FROM behaviour_ratings WHERE student_id = ? AND date = ?",
                (int001_student_id, sample_date),
            )
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO behaviour_ratings (student_id, date, rating, admin_id) "
                    "VALUES (?, ?, ?, ?)",
                    (int001_student_id, sample_date, rating, admin_user_id),
                )

        # Sample student-to-admin feedback
        cursor.execute(
            "SELECT id FROM student_feedback_to_admin WHERE student_id = ? AND subject = ?",
            (int001_student_id, "Website UI Suggestion"),
        )
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO student_feedback_to_admin (student_id, subject, message, timestamp) "
                "VALUES (?, ?, ?, ?)",
                (
                    int001_student_id,
                    "Website UI Suggestion",
                    "Consider making the navigation menu more prominent.",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )

        cursor.execute(
            "SELECT id FROM student_feedback_to_admin WHERE student_id = ? AND subject = ?",
            (int001_student_id, "Query about Task 3"),
        )
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO student_feedback_to_admin (student_id, subject, message, timestamp) "
                "VALUES (?, ?, ?, ?)",
                (
                    int001_student_id,
                    "Query about Task 3",
                    "Could you provide more examples for Task 3 requirements?",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )

    conn.commit()
    conn.close()


# --- Auth helper functions (still centralized here) ---
def is_admin_logged_in() -> bool:
    return session.get("role") == "admin"


def is_intern_logged_in() -> bool:
    return session.get("role") == "intern"


def get_student_credentials(student_db_id: int) -> Dict[str, Any]:
    """
    Retrieves the email (used as username), password, and name for a student.
    """
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT s.email, u.password, s.name, s.email
        FROM students s
        JOIN users u ON s.user_id = u.id
        WHERE s.id = ?
        """,
        (student_db_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "username": row[0],
            "password": row[1],
            "name": row[2],
            "email": row[3],
        }
    return {}


# --- Feature / analytics helpers ---
def calculate_attendance_rate(student_db_id: int) -> float:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM attendance WHERE student_id = ?", (student_db_id,)
    )
    total_days = cursor.fetchone()[0]
    cursor.execute(
        "SELECT COUNT(*) FROM attendance WHERE student_id = ? AND status = 'present'",
        (student_db_id,),
    )
    present_days = cursor.fetchone()[0]
    conn.close()
    return present_days / total_days if total_days > 0 else 0.0


def calculate_average_task_mark(student_db_id: int) -> float:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT AVG(mark) FROM tasks WHERE student_id = ? AND status = 'completed'",
        (student_db_id,),
    )
    avg_mark = cursor.fetchone()[0]
    conn.close()
    return avg_mark if avg_mark is not None else 0.0


def mark_online_attendance(student_db_id: int) -> None:
    today = date.today().strftime("%Y-%m-%d")
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO attendance (student_id, date, status)
        VALUES (?, ?, 'present')
        ON CONFLICT(student_id, date) DO NOTHING
        """,
        (student_db_id, today),
    )
    con.commit()
    con.close()


def calculate_average_feedback_score_numeric(student_db_id: int) -> float:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    feedback_category_map = {"Poor": 0, "Average": 1, "Good": 2, "Excellent": 3}
    cursor.execute(
        "SELECT feedback_category FROM feedback WHERE student_id = ?",
        (student_db_id,),
    )
    feedback_categories = cursor.fetchall()

    numeric_values = []
    for (category,) in feedback_categories:
        if category in feedback_category_map:
            numeric_values.append(feedback_category_map[category])

    conn.close()
    avg_numeric = np.mean(numeric_values) if numeric_values else 0.0
    return (avg_numeric / 3.0) * 100.0


def calculate_average_behaviour_rating(student_db_id: int) -> float:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT AVG(rating) FROM behaviour_ratings WHERE student_id = ?",
        (student_db_id,),
    )
    avg_rating = cursor.fetchone()[0]
    conn.close()
    return ((avg_rating - 1) / 4.0) * 100.0 if avg_rating is not None else 0.0


def calculate_course_completion_percentage(student_db_id: int) -> float:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("SELECT course_id FROM students WHERE id = ?", (student_db_id,))
    student_course_row = cursor.fetchone()
    if not student_course_row or student_course_row[0] is None:
        conn.close()
        return 0.0

    student_course_id = student_course_row[0]
    cursor.execute(
        "SELECT total_expected_tasks FROM courses WHERE id = ?", (student_course_id,)
    )
    total_expected_tasks = cursor.fetchone()[0]
    if total_expected_tasks == 0:
        conn.close()
        return 0.0

    cursor.execute(
        "SELECT COUNT(*) FROM tasks WHERE student_id = ? AND course_id = ? AND status = 'completed'",
        (student_db_id, student_course_id),
    )
    completed_tasks = cursor.fetchone()[0]
    conn.close()
    return (completed_tasks / total_expected_tasks) * 100.0


def calculate_overall_performance_score(student_db_id: int) -> Dict[str, Any]:
    weights = {
        "attendance": 0.20,
        "task_mark": 0.30,
        "behaviour": 0.15,
        "feedback": 0.20,
        "course_completion": 0.15,
    }

    attendance_score = calculate_attendance_rate(student_db_id) * 100
    task_mark_score = calculate_average_task_mark(student_db_id)
    behaviour_score = calculate_average_behaviour_rating(student_db_id)
    feedback_score = calculate_average_feedback_score_numeric(student_db_id)
    course_completion_score = calculate_course_completion_percentage(student_db_id)

    overall_score = (
        attendance_score * weights["attendance"]
        + task_mark_score * weights["task_mark"]
        + behaviour_score * weights["behaviour"]
        + feedback_score * weights["feedback"]
        + course_completion_score * weights["course_completion"]
    )
    overall_score = max(0, min(100, overall_score))

    if overall_score >= 90:
        category = "Excellent"
    elif overall_score >= 75:
        category = "Good"
    elif overall_score >= 50:
        category = "Average"
    else:
        category = "Poor"

    return {
        "overall_score": round(overall_score, 2),
        "category": category,
        "breakdown": {
            "attendance": {
                "value": round(attendance_score, 2),
                "weight": weights["attendance"],
            },
            "task_mark": {
                "value": round(task_mark_score, 2),
                "weight": weights["task_mark"],
            },
            "behaviour": {
                "value": round(behaviour_score, 2),
                "weight": weights["behaviour"],
            },
            "feedback": {
                "value": round(feedback_score, 2),
                "weight": weights["feedback"],
            },
            "course_completion": {
                "value": round(course_completion_score, 2),
                "weight": weights["course_completion"],
            },
        },
    }

