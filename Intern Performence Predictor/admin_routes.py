import os
import sqlite3
from datetime import datetime

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
    current_app
)
from werkzeug.utils import secure_filename

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from database import (
    DATABASE,
    is_admin_logged_in,
    calculate_overall_performance_score,
    get_student_credentials,
)
from email_utils import send_task_assignment_email, send_welcome_email


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.app_context_processor
def inject_pending_counts():
    if not session.get("logged_in") or session.get("role") != "admin":
        return dict(pending_counts={})
    
    import sqlite3
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
    pending_tasks = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'submitted'")
    submitted_tasks = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM internship_registrations WHERE status = 'Pending'")
    pending_registrations = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM behaviour_ratings WHERE admin_id IS NULL") # Just an example, let's stick to what we have
    
    cursor.execute("SELECT COUNT(*) FROM feedback WHERE admin_id IS NULL") # Another example
    
    conn.close()
    
    return dict(
        pending_counts={
            "tasks": pending_tasks,
            "submitted": submitted_tasks,
            "registrations": pending_registrations
        }
    )


@admin_bp.route("/dashboard", endpoint="admin_dashboard")
def admin_dashboard():
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
    pending_tasks_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'submitted'")
    submitted_tasks_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
    completed_tasks_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM internship_registrations WHERE status = 'Pending'")
    pending_registrations_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM courses")
    total_internships = cursor.fetchone()[0]

    today_date = datetime.now().strftime("%Y-%m-%d")
    cursor.execute(
        "SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'present'",
        (today_date,),
    )
    today_present_count = cursor.fetchone()[0]
    cursor.execute(
        "SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'absent'",
        (today_date,),
    )
    today_absent_count = cursor.fetchone()[0]

    # Custom Reminder Logic
    current_weekday = datetime.now().weekday()  # Mon=0, Sun=6
    show_behaviour_reminder = current_weekday in [1, 3, 5]  # Tue, Thu, Sat
    
    unassigned_interns_count = 0
    if current_weekday != 6:  # Except Sunday
        cursor.execute(
            "SELECT COUNT(DISTINCT student_id) FROM tasks WHERE created_at LIKE ?",
            (today_date + "%",)
        )
        assigned_interns_count = cursor.fetchone()[0]
        unassigned_interns_count = max(0, total_students - assigned_interns_count)

    conn.close()
    return render_template(
        "admin_dashboard.html",
        username=session["username"],
        total_students=total_students,
        pending_tasks=pending_tasks_count,
        submitted_tasks=submitted_tasks_count,
        completed_tasks=completed_tasks_count,
        pending_registrations=pending_registrations_count,
        total_courses=total_internships,
        today_present_count=today_present_count,
        today_absent_count=today_absent_count,
        show_behaviour_reminder=show_behaviour_reminder,
        unassigned_interns_count=unassigned_interns_count,
    )


@admin_bp.route("/profile", endpoint="admin_profile")
def admin_profile():
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))
    return render_template("admin_profile.html", username=session["username"])


@admin_bp.route("/add-course", methods=["GET", "POST"], endpoint="add_courses")
def add_courses():
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if request.method == "POST":
        course_name = request.form["course_name"]
        total_expected_tasks = request.form.get("total_expected_tasks", 10)
        description = request.form.get("description", "")
        duration = request.form.get("duration", "")
        
        try:
            cursor.execute(
                "INSERT INTO courses (name, total_expected_tasks, description, duration) VALUES (?, ?, ?, ?)",
                (course_name, total_expected_tasks, description, duration),
            )
            conn.commit()
            flash(f'Internship program "{course_name}" added successfully!', "success")
        except sqlite3.IntegrityError:
            flash(f'Error: Internship program "{course_name}" already exists.', "error")
        except Exception as e:
            flash(f"An unexpected error occurred: {e}", "error")
        finally:
            conn.close()
            
        return redirect(url_for("admin.add_courses"))

    cursor.execute(
        "SELECT id, name, total_expected_tasks, description, duration FROM courses ORDER BY name"
    )
    existing_courses = cursor.fetchall()
    conn.close()

    return render_template(
        "add_courses.html",
        username=session["username"],
        existing_courses=existing_courses,
    )


@admin_bp.route("/edit-course/<int:course_id>", methods=["GET", "POST"], endpoint="edit_course")
def edit_course(course_id):
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if request.method == "POST":
        new_name = request.form["course_name"]
        new_total_tasks = request.form.get("total_expected_tasks", 10)
        new_description = request.form.get("description", "")
        new_duration = request.form.get("duration", "")

        try:
            cursor.execute(
                """
                UPDATE courses 
                SET name = ?, total_expected_tasks = ?, description = ?, duration = ? 
                WHERE id = ?
                """,
                (new_name, new_total_tasks, new_description, new_duration, course_id),
            )
            conn.commit()
            flash("Internship program updated successfully", "success")
        except sqlite3.IntegrityError:
            flash("Error: Internship name already exists.", "error")
        except Exception as e:
            flash(f"Error updating internship: {e}", "error")
        finally:
            conn.close()
            
        return redirect(url_for("admin.add_courses"))

    cursor.execute(
        "SELECT id, name, total_expected_tasks, description, duration FROM courses WHERE id = ?",
        (course_id,),
    )
    course = cursor.fetchone()
    conn.close()

    if not course:
        flash("Course not found", "error")
        return redirect(url_for("admin.add_courses"))

    return render_template("edit_course.html", course=course, username=session["username"])


@admin_bp.route("/delete-course/<int:course_id>", methods=["POST"], endpoint="delete_course")
def delete_course(course_id):
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM courses WHERE id = ?", (course_id,))
        conn.commit()
        flash("Internship program deleted successfully", "success")
    except Exception as e:
        flash(f"Error deleting internship: {e}", "error")
    finally:
        conn.close()

    return redirect(url_for("admin.add_courses"))


@admin_bp.route("/get_course_suggestions", endpoint="get_course_suggestions")
def get_course_suggestions():
    if not is_admin_logged_in():
        return jsonify([])

    query = request.args.get("q", "").lower()
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM courses WHERE LOWER(name) LIKE ? ORDER BY name LIMIT 10",
        (f"%{query}%",),
    )
    suggestions = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(suggestions)


@admin_bp.route("/course-validity", endpoint="course_validity")
def course_validity():
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))
    return render_template("course_validity.html", username=session["username"])


@admin_bp.route("/internship-registrations", endpoint="internship_registrations")
def internship_registrations():
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Get registrations with student and course info
    cursor.execute(
        """
        SELECT ir.id, s.name, s.unique_student_id, c.name, ir.registered_at, ir.status, s.email, s.phone_number
        FROM internship_registrations ir
        JOIN students s ON ir.student_id = s.id
        JOIN courses c ON ir.course_id = c.id
        ORDER BY ir.registered_at DESC
        """
    )
    registrations = cursor.fetchall()
    conn.close()

    return render_template(
        "admin_internship_registrations.html",
        username=session["username"],
        registrations=registrations
    )


@admin_bp.route("/handle-internship-registration/<int:reg_id>", methods=["POST"], endpoint="handle_internship_registration")
def handle_internship_registration(reg_id):
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))

    action = request.form.get("action")
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    try:
        if action in ['Viewed', 'Contacted']:
            cursor.execute(
                "UPDATE internship_registrations SET status = ? WHERE id = ?",
                (action, reg_id)
            )
            conn.commit()
            flash(f"Registration marked as {action}.", "success")
        elif action == "delete":
            cursor.execute("DELETE FROM internship_registrations WHERE id = ?", (reg_id,))
            conn.commit()
            flash("Registration record deleted.", "info")
    except Exception as e:
        conn.rollback()
        flash(f"Error handling registration: {e}", "error")
    finally:
        conn.close()

    return redirect(url_for("admin.internship_registrations"))


@admin_bp.route("/assignment", endpoint="assignment")
def assignment():
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))
    return render_template("assignment.html", username=session["username"])


@admin_bp.route("/add-task", methods=["GET", "POST"], endpoint="add_task")
def add_task():
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if request.method == "POST":
        assign_type = request.form["assign_type"]
        task_title = request.form["task_title"]
        task_description = request.form["task_description"]
        due_date = request.form["due_date"]

        try:
            if assign_type == "single":
                assigned_student_id = request.form["assigned_to"]
                cursor.execute(
                    "SELECT id, name, email FROM students WHERE unique_student_id=?",
                    (assigned_student_id,),
                )
                student = cursor.fetchone()

                if not student:
                    flash("Student not found", "error")
                    return redirect(url_for("admin.add_task"))

                # Check for duplicate
                cursor.execute(
                    "SELECT id FROM tasks WHERE student_id = ? AND title = ? AND due_date = ? AND status != 'completed'",
                    (student[0], task_title, due_date),
                )
                if cursor.fetchone():
                    flash(f"Task '{task_title}' is already assigned to this intern and is not yet completed.", "warning")
                    return redirect(url_for("admin.add_task"))

                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    """
                    INSERT INTO tasks (student_id, title, description, due_date, status, created_at)
                    VALUES (?, ?, ?, ?, 'pending', ?)
                    """,
                    (student[0], task_title, task_description, due_date, current_time),
                )
                
                # Send email notification
                send_task_assignment_email(student[2], student[1], task_title, due_date)

            elif assign_type == "all":
                cursor.execute("SELECT id, name, email FROM students")
                students = cursor.fetchall()
                assigned_count = 0
                for student in students:
                    # Check for duplicate
                    cursor.execute(
                        "SELECT id FROM tasks WHERE student_id = ? AND title = ? AND due_date = ? AND status != 'completed'",
                        (student[0], task_title, due_date),
                    )
                    if cursor.fetchone():
                        continue

                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute(
                        """
                        INSERT INTO tasks (student_id, title, description, due_date, status, created_at)
                        VALUES (?, ?, ?, ?, 'pending', ?)
                        """,
                        (student[0], task_title, task_description, due_date, current_time),
                    )
                    assigned_count += 1
                    # Send email notification
                    send_task_assignment_email(student[2], student[1], task_title, due_date)
                
                if assigned_count == 0 and len(students) > 0:
                    flash("All selected interns already have this task assigned.", "warning")
                    return redirect(url_for("admin.add_task"))

            conn.commit()
            flash("Task assigned successfully!", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Error: {e}", "error")
        finally:
            conn.close()

        return redirect(url_for("admin.add_task"))

    cursor.execute("SELECT unique_student_id, name FROM students ORDER BY name")
    students = cursor.fetchall()
    conn.close()

    return render_template(
        "add_task.html",
        username=session["username"],
        students=students,
    )


@admin_bp.route("/edit-task/<int:task_id>", methods=["GET", "POST"], endpoint="edit_task")
def edit_task(task_id):
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        due_date = request.form["due_date"]

        try:
            cursor.execute(
                """
                UPDATE tasks
                SET title = ?, description = ?, due_date = ?
                WHERE id = ?
                """,
                (title, description, due_date, task_id),
            )
            conn.commit()
            flash("Task updated successfully!", "success")
            return redirect(url_for("admin.admin_complete_tasks"))
        except Exception as e:
            conn.rollback()
            flash(f"Error updating task: {e}", "error")
        finally:
            conn.close()

    cursor.execute("SELECT id, title, description, due_date FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    conn.close()

    if not task:
        flash("Task not found", "error")
        return redirect(url_for("admin.admin_complete_tasks"))

    return render_template("edit_task.html", task=task, username=session["username"])


@admin_bp.route("/delete-task/<int:task_id>", methods=["POST"], endpoint="delete_task")
def delete_task(task_id):
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        flash("Task deleted successfully!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting task: {e}", "error")
    finally:
        conn.close()
    return redirect(request.referrer or url_for("admin.admin_complete_tasks"))


@admin_bp.route("/announcement", endpoint="announcement")
def announcement():
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))
    return render_template("announcement.html", username=session["username"])


@admin_bp.route("/add-student", methods=["GET", "POST"], endpoint="add_student")
def add_student():
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        # Auto-generate Student ID: INT + Timestamp (e.g., INT20250218123045)
        from datetime import datetime
        unique_student_id = f"INT{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        name = request.form["student_name"]
        email = request.form["student_email"]
        temp_password = request.form["temp_password"]
        assigned_course_name = request.form.get("assigned_course")

        internship_type = request.form["internship_type"]
        joining_date = request.form["joining_date"]
        ending_date = request.form["ending_date"]
        college_name = request.form["college_name"]
        department = request.form["department"]

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT id FROM users WHERE username = ?", (unique_student_id,)
            )
            if cursor.fetchone():
                flash("Error: Student ID already exists.", "error")
                conn.close()
                return redirect(url_for("admin.add_student"))

            cursor.execute("SELECT id FROM students WHERE email = ?", (email,))
            if cursor.fetchone():
                flash("Error: Email already exists.", "error")
                conn.close()
                return redirect(url_for("admin.add_student"))

            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (email, temp_password, "intern"),
            )
            user_id = cursor.lastrowid

            course_id = None
            assigned_course_name = request.form.get("course_name") # Assuming this field exists or needs to be retrieved
            
            # Retrieve course_id if course_name is provided
            if assigned_course_name:
                cursor.execute(
                    "SELECT id FROM courses WHERE name = ?",
                    (assigned_course_name,),
                )
                course = cursor.fetchone()
                if course:
                    course_id = course[0]

            profile_pic_filename = None
            if 'profile_pic' in request.files:
                file = request.files['profile_pic']
                if file and file.filename != '':
                    filename = secure_filename(file.filename)
                    # Use a unique prefix to avoid overwriting
                    unique_filename = f"{unique_student_id}_{filename}"
                    file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename))
                    profile_pic_filename = unique_filename

            cursor.execute(
                """
                INSERT INTO students (
                    unique_student_id, name, email, course_id, user_id,
                    internship_type, joining_date, ending_date,
                    college_name, department,
                    phone_number, gender, dob, address, linkedin_url, github_url,
                    profile_pic
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    unique_student_id,
                    name,
                    email,
                    course_id,
                    user_id,
                    internship_type,
                    joining_date,
                    ending_date,
                    college_name,
                    department,
                    request.form.get("phone_number"),
                    request.form.get("gender"),
                    request.form.get("dob"),
                    request.form.get("address"),
                    request.form.get("linkedin_url"),
                    request.form.get("github_url"),
                    profile_pic_filename
                ),
            )

            conn.commit()

            # Send welcome email with credentials
            send_welcome_email(email, name, email, temp_password)

            flash("Student added successfully", "success")
            return redirect(url_for("admin.student_list"))
        except Exception as e:
            conn.rollback()
            flash(f"Error: {e}", "error")
        finally:
            conn.close()

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM courses")
    courses = [row[0] for row in cursor.fetchall()]
    conn.close()

    return render_template("add_student.html", courses=courses)


@admin_bp.route("/student-list", endpoint="student_list")
def student_list():
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT s.unique_student_id, s.name, s.email, c.name AS course_name, s.id as student_db_id
        FROM students s
        LEFT JOIN courses c ON s.course_id = c.id
        ORDER BY s.name
        """
    )
    students_data = cursor.fetchall()
    conn.close()
    return render_template(
        "student_list.html",
        username=session["username"],
        students=students_data,
    )


@admin_bp.route("/resend-credentials/<int:student_id>", endpoint="resend_credentials")
def resend_credentials(student_id):
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))

    creds = get_student_credentials(student_id)
    if not creds:
        flash("Student details not found.", "error")
        return redirect(url_for("admin.student_list"))

    success = send_welcome_email(
        creds["email"], 
        creds["name"], 
        creds["username"], 
        creds["password"]
    )

    if success:
        flash(f"Login credentials resent to {creds['email']} ✅", "success")
    else:
        flash("Failed to send email. Please check SMTP settings.", "error")

    return redirect(url_for("admin.student_list"))


@admin_bp.route("/pending-tasks", endpoint="pending_tasks")
def pending_tasks():
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT t.title, s.name, t.due_date, t.status, t.id
        FROM tasks t
        JOIN students s ON t.student_id = s.id
        WHERE t.status = 'pending'
        ORDER BY t.due_date
        """
    )
    pending_tasks_data = cursor.fetchall()
    conn.close()
    return render_template(
        "pending_tasks.html",
        username=session["username"],
        pending_tasks=pending_tasks_data,
    )


@admin_bp.route("/attendance", methods=["GET", "POST"], endpoint="attendance")
def attendance():
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))

    selected_date = request.args.get(
        "selected_date", datetime.now().strftime("%Y-%m-%d")
    )

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT s.id, s.unique_student_id, s.name, a.status
        FROM students s
        LEFT JOIN attendance a ON s.id = a.student_id AND a.date = ?
        ORDER BY s.name
        """,
        (selected_date,),
    )
    attendance_records = cursor.fetchall()
    conn.close()

    return render_template(
        "attendance.html",
        username=session["username"],
        current_date=selected_date,
        attendance_records=attendance_records,
    )


@admin_bp.route("/mark-attendance", methods=["POST"], endpoint="mark_attendance")
def mark_attendance():
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))

    student_db_id = request.form["student_id"]
    date_value = request.form.get(
        "attendance_date", datetime.now().strftime("%Y-%m-%d")
    )
    status = request.form["status"]

    if not date_value:
        flash("Error: Attendance date was not provided.", "error")
        return redirect(url_for("admin.attendance"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    try:
        if status == "not_recorded":
            cursor.execute(
                "DELETE FROM attendance WHERE student_id = ? AND date = ?",
                (student_db_id, date_value),
            )
            flash(
                f"Attendance for student ID {student_db_id} on {date_value} cleared.",
                "info",
            )
        else:
            cursor.execute(
                "SELECT id FROM attendance WHERE student_id = ? AND date = ?",
                (student_db_id, date_value),
            )
            existing_record = cursor.fetchone()

            if existing_record:
                cursor.execute(
                    "UPDATE attendance SET status = ? WHERE id = ?",
                    (status, existing_record[0]),
                )
                flash(
                    f"Attendance for student ID {student_db_id} on {date_value} updated to {status}.",
                    "success",
                )
            else:
                cursor.execute(
                    "INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)",
                    (student_db_id, date_value, status),
                )
                flash(
                    f"Attendance for student ID {student_db_id} on {date_value} marked as {status}.",
                    "success",
                )
        conn.commit()
    except Exception as e:
        conn.rollback()
        flash(f"Error marking attendance: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for("admin.attendance", selected_date=date_value))


@admin_bp.route("/add-feedback", methods=["GET", "POST"], endpoint="add_feedback")
def add_feedback():
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT id, name, unique_student_id FROM students")
    students = cur.fetchall()

    if request.method == "POST":
        student_id = request.form.get("student_id")
        feedback_comments = request.form.get("feedback")

        cur.execute(
            """
            INSERT INTO feedback (student_id, admin_id, comments, feedback_date, feedback_category)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                student_id,
                session["user_id"],
                feedback_comments,
                datetime.now().strftime("%Y-%m-%d"),
                "Good",
            ),
        )

        conn.commit()
        flash("Feedback submitted successfully ✅", "success")
        return redirect(url_for("admin.add_feedback"))

    conn.close()
    return render_template(
        "add_feedback.html",
        students=students,
        username=session.get("username"),
    )


@admin_bp.route("/behaviour-rating", methods=["GET", "POST"], endpoint="add_behaviour_rating")
def add_behaviour_rating():
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM students")
    students = cur.fetchall()

    if request.method == "POST":
        student_id = request.form.get("student_id")
        rating = request.form.get("rating")
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not student_id or not rating:
            flash("Please select intern and rating", "error")
            return redirect(url_for("admin.add_behaviour_rating"))

        cur.execute(
            """
            INSERT INTO behaviour_ratings (student_id, date, rating, admin_id)
            VALUES (?, ?, ?, ?)
            """,
            (
                student_id,
                datetime.now().strftime("%Y-%m-%d"),
                rating,
                session["user_id"],
            ),
        )

        conn.commit()
        conn.close()

        flash("Behaviour rating saved successfully ✅", "success")
        return redirect(url_for("admin.add_behaviour_rating"))

    conn.close()
    return render_template(
        "add_behaviour_rating.html",
        students=students,
        username=session.get("username"),
    )


@admin_bp.route("/performance", endpoint="admin_performance_overview")
def admin_performance_overview():
    if session.get("role") != "admin":
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("SELECT id, unique_student_id, name FROM students")
    rows = cur.fetchall()
    conn.close()

    performance_summaries = []
    for r in rows:
        score = calculate_overall_performance_score(r[0])
        performance_summaries.append(
            {
                "unique_student_id": r[1],
                "name": r[2],
                "overall_score": score["overall_score"],
                "category": score["category"],
            }
        )

    return render_template(
        "admin_performance_overview.html",
        performance_summaries=performance_summaries,
    )


@admin_bp.route(
    "/view-student-feedback", endpoint="admin_view_student_feedback"
)
def admin_view_student_feedback():
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT sf.subject, sf.message, sf.timestamp, s.name AS student_name, s.unique_student_id
        FROM student_feedback_to_admin sf
        JOIN students s ON sf.student_id = s.id
        ORDER BY sf.timestamp DESC
        """
    )
    student_feedback_records = cursor.fetchall()
    conn.close()
    return render_template(
        "admin_view_student_feedback.html",
        username=session["username"],
        student_feedback_records=student_feedback_records,
    )


@admin_bp.route("/complete-tasks", methods=["GET", "POST"], endpoint="admin_complete_tasks")
def admin_complete_tasks():
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if request.method == "POST":
        tasks_to_update = 0
        for key, value in request.form.items():
            if key.startswith("completed_task_") and value == "on":
                task_id = key.replace("completed_task_", "")
                mark_key = f"mark_{task_id}"
                mark = request.form.get(mark_key, 0)

                try:
                    mark = float(mark)
                    if not (0 <= mark <= 100):
                        flash(
                            f"Warning: Mark for task {task_id} must be between 0 and 100. Not updated.",
                            "warning",
                        )
                        continue
                except ValueError:
                    flash(
                        f"Warning: Invalid mark for task {task_id}. Not updated.",
                        "warning",
                    )
                    continue

                try:
                    cursor.execute(
                        "UPDATE tasks SET status = 'completed', mark = ? WHERE id = ? AND status IN ('pending', 'submitted')",
                        (mark, task_id),
                    )
                    if cursor.rowcount > 0:
                        tasks_to_update += 1
                except Exception as e:
                    flash(f"Error updating task {task_id}: {e}", "error")

        conn.commit()
        if tasks_to_update > 0:
            flash(
                f"{tasks_to_update} task(s) marked as completed and marks assigned!",
                "success",
            )
        else:
            flash("No tasks were updated.", "info")

        conn.close()
        return redirect(url_for("admin.admin_complete_tasks"))

    cursor.execute(
        """
        SELECT t.id, t.title, t.description, t.due_date, s.name AS student_name, s.unique_student_id, t.submission, t.submitted_at, t.status
        FROM tasks t
        JOIN students s ON t.student_id = s.id
        WHERE t.status IN ('pending', 'submitted')
        ORDER BY t.status DESC, t.due_date, s.name
        """
    )
    pending_tasks = cursor.fetchall()
    conn.close()
    return render_template(
        "complete_tasks.html",
        username=session["username"],
        pending_tasks=pending_tasks,
    )


@admin_bp.route("/completed-tasks-list", endpoint="completed_tasks_list")
def completed_tasks_list():
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT t.id, t.title, t.description, t.due_date, s.name AS student_name, 
               s.unique_student_id, t.submission, t.submitted_at, t.mark, t.status
        FROM tasks t
        JOIN students s ON t.student_id = s.id
        WHERE t.status = 'completed'
        ORDER BY t.submitted_at DESC, s.name
        """
    )
    completed_tasks = cursor.fetchall()
    conn.close()

    return render_template(
        "completed_tasks_list.html",
        username=session["username"],
        completed_tasks=completed_tasks,
    )


@admin_bp.route("/leave-requests", endpoint="admin_leave_requests")
def admin_leave_requests():
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT lr.id, s.name, s.unique_student_id,
               lr.reason, lr.from_date, lr.to_date, lr.status
        FROM leave_requests lr
        JOIN students s ON lr.student_id = s.id
        ORDER BY lr.id DESC
        """
    )
    leave_requests = cursor.fetchall()
    conn.close()

    return render_template(
        "admin_leave_requests.html",
        leave_requests=leave_requests,
    )


@admin_bp.route(
    "/update-leave/<int:leave_id>/<string:action>",
    endpoint="update_leave_status",
)
def update_leave_status(leave_id, action):
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))

    if action not in ["Approved", "Rejected"]:
        return "Invalid Action"

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE leave_requests
        SET status = ?
        WHERE id = ?
        """,
        (action, leave_id),
    )
    conn.commit()
    conn.close()

    flash(f"Leave request {action} successfully ✅", "success")
    return redirect(url_for("admin.admin_leave_requests"))



@admin_bp.route("/edit-student/<string:student_id>", methods=["GET", "POST"], endpoint="edit_student")
def edit_student(student_id):
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))

    con = sqlite3.connect(DATABASE)
    cur = con.cursor()

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        college = request.form["college_name"]
        department = request.form["department"]

        # Internship Assignment
        assigned_course_name = request.form.get("course_name")
        course_id = None
        if assigned_course_name:
            cur.execute("SELECT id FROM courses WHERE name = ?", (assigned_course_name,))
            course_row = cur.fetchone()
            if course_row:
                course_id = course_row[0]

        # Other Details
        internship_type = request.form.get("internship_type")
        joining_date = request.form.get("joining_date")
        ending_date = request.form.get("ending_date")
        
        phone_number = request.form.get("phone_number")
        gender = request.form.get("gender")
        dob = request.form.get("dob")
        address = request.form.get("address")
        linkedin_url = request.form.get("linkedin_url")
        github_url = request.form.get("github_url")

        profile_pic_filename = None
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                unique_filename = f"{student_id}_{filename}"
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename))
                profile_pic_filename = unique_filename

        if profile_pic_filename:
            cur.execute(
                """
                UPDATE students
                SET name = ?, email = ?, college_name = ?, department = ?,
                    course_id = ?, internship_type = ?, joining_date = ?, ending_date = ?,
                    phone_number = ?, gender = ?, dob = ?, address = ?,
                    linkedin_url = ?, github_url = ?, profile_pic = ?
                WHERE unique_student_id = ?
                """,
                (name, email, college, department, course_id, internship_type, joining_date, ending_date, phone_number, gender, dob, address, linkedin_url, github_url, profile_pic_filename, student_id),
            )
        else:
            cur.execute(
                """
                UPDATE students
                SET name = ?, email = ?, college_name = ?, department = ?,
                    course_id = ?, internship_type = ?, joining_date = ?, ending_date = ?,
                    phone_number = ?, gender = ?, dob = ?, address = ?,
                    linkedin_url = ?, github_url = ?
                WHERE unique_student_id = ?
                """,
                (name, email, college, department, course_id, internship_type, joining_date, ending_date, phone_number, gender, dob, address, linkedin_url, github_url, student_id),
            )

        con.commit()
        con.close()

        flash("Student updated successfully", "success")
        return redirect(url_for("admin.student_list"))

    student = cur.execute(
        """
        SELECT s.unique_student_id, s.name, s.email, s.college_name, s.department,
               s.phone_number, s.gender, s.dob, s.address, s.linkedin_url, s.github_url, s.profile_pic,
               c.name as course_name, s.internship_type, s.joining_date, s.ending_date
        FROM students s
        LEFT JOIN courses c ON s.course_id = c.id
        WHERE s.unique_student_id = ?
        """,
        (student_id,),
    ).fetchone()

    cur.execute("SELECT name FROM courses ORDER BY name")
    courses = [row[0] for row in cur.fetchall()]

    con.close()
    return render_template("edit_student.html", student=student, courses=courses)


@admin_bp.route("/delete-student/<string:student_id>", methods=["POST"], endpoint="delete_student")
def delete_student(student_id):
    if not is_admin_logged_in():
        return redirect(url_for("auth.login"))

    con = sqlite3.connect(DATABASE)
    cur = con.cursor()

    try:
        # Get user_id before deleting student
        cur.execute("SELECT user_id FROM students WHERE unique_student_id = ?", (student_id,))
        result = cur.fetchone()
        
        if result:
            user_id = result[0]
            
            # Get the internal student id
            cur.execute("SELECT id FROM students WHERE unique_student_id = ?", (student_id,))
            internal_student_id = cur.fetchone()[0]
            
            # Cascade delete associated records
            cur.execute("DELETE FROM tasks WHERE student_id = ?", (internal_student_id,))
            cur.execute("DELETE FROM attendance WHERE student_id = ?", (internal_student_id,))
            cur.execute("DELETE FROM feedback WHERE student_id = ?", (internal_student_id,))
            cur.execute("DELETE FROM leave_requests WHERE student_id = ?", (internal_student_id,))
            cur.execute("DELETE FROM student_feedback_to_admin WHERE student_id = ?", (internal_student_id,))
            cur.execute("DELETE FROM behaviour_ratings WHERE student_id = ?", (internal_student_id,))
            cur.execute("DELETE FROM internship_registrations WHERE student_id = ?", (internal_student_id,))
            
            # Delete from students table
            cur.execute("DELETE FROM students WHERE unique_student_id = ?", (student_id,))
            
            # Delete from users table if user_id exists
            if user_id:
                cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
            
            con.commit()
            flash("Student and associated user account deleted successfully", "success")
        else:
            flash("Student not found", "error")
            
    except Exception as e:
        con.rollback()
        flash(f"Error deleting student: {e}", "error")
    finally:
        con.close()

    return redirect(url_for("admin.student_list"))

