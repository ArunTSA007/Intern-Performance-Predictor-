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
    send_file,
)
from database import (
    DATABASE,
    is_intern_logged_in,
    calculate_overall_performance_score,
    calculate_average_task_mark,
)
from email_utils import send_registration_email


intern_bp = Blueprint("intern", __name__)


@intern_bp.route("/student/dashboard", endpoint="intern_dashboard")
def intern_dashboard():
    if not is_intern_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    assigned_tasks = []
    suggested_courses = []
    today_attendance_status = "Not Recorded"
    overall_performance_data = {"overall_score": 0, "category": "N/A"}
    student_profile_data = {}
    attendance_percentage = 0

    cursor.execute(
        "SELECT id, name, email FROM students WHERE user_id = ?",
        (session["user_id"],),
    )
    student_data_row = cursor.fetchone()

    if student_data_row:
        current_student_db_id = student_data_row[0]

        student_profile_data = {
            "id": current_student_db_id,
            "name": student_data_row[1],
            "email": student_data_row[2],
        }

        cursor.execute(
            """
            SELECT title, description, due_date, status, mark, id
            FROM tasks
            WHERE student_id = ?
            ORDER BY due_date
            """,
            (current_student_db_id,),
        )
        assigned_tasks = cursor.fetchall()

        cursor.execute("SELECT name FROM courses ORDER BY name")
        suggested_internships = [row[0] for row in cursor.fetchall()]

        today_date = datetime.now().strftime("%Y-%m-%d")
        cursor.execute(
            """
            SELECT status
            FROM attendance
            WHERE student_id = ? AND date = ?
            """,
            (current_student_db_id, today_date),
        )
        attendance_result = cursor.fetchone()
        if attendance_result:
            today_attendance_status = attendance_result[0]

        cursor.execute(
            """
            SELECT COUNT(*) FROM attendance WHERE student_id = ?
            """,
            (current_student_db_id,),
        )
        total_days = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*) FROM attendance
            WHERE student_id = ? AND status = 'present'
            """,
            (current_student_db_id,),
        )
        present_days = cursor.fetchone()[0]

        if total_days > 0:
            attendance_percentage = round((present_days / total_days) * 100, 2)

        overall_performance_data = calculate_overall_performance_score(
            current_student_db_id
        )

    conn.close()

    return render_template(
        "intern_dashboard.html",
        username=session["username"],
        tasks=assigned_tasks,
        suggested_internships=suggested_internships,
        today_attendance_status=today_attendance_status,
        predicted_performance=overall_performance_data["category"],
        overall_score=overall_performance_data["overall_score"],
        attendance_percentage=attendance_percentage,
        student_profile_data=student_profile_data,
    )


@intern_bp.route("/student/tasks", endpoint="intern_tasks")
def intern_tasks():
    if not is_intern_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM students WHERE user_id = ?", (session["user_id"],))
    student_id_row = cursor.fetchone()
    tasks = []
    if student_id_row:
        current_student_db_id = student_id_row[0]
        # ✅ NEW: Select id, submission, submitted_at, and marks
        cursor.execute(
            """
            SELECT id, title, description, due_date, status, mark, submission, submitted_at 
            FROM tasks 
            WHERE student_id = ? 
            ORDER BY due_date
            """,
            (current_student_db_id,),
        )
        tasks = cursor.fetchall()
    conn.close()
    return render_template(
        "intern_tasks.html", username=session["username"], tasks=tasks
    )


@intern_bp.route("/student/submit-task/<int:task_id>", methods=["POST"], endpoint="submit_task")
def submit_task(task_id):
    if not is_intern_logged_in():
        return redirect(url_for("auth.login"))

    submission_content = request.form.get("submission_content")
    
    if not submission_content:
        flash("Please provide submission details or a link.", "error")
        return redirect(url_for("intern.intern_tasks"))

    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Verify task belongs to student
        cursor.execute("SELECT id FROM students WHERE user_id = ?", (session["user_id"],))
        student_id = cursor.fetchone()[0]
        
        cursor.execute("SELECT id FROM tasks WHERE id = ? AND student_id = ?", (task_id, student_id))
        if not cursor.fetchone():
            flash("Invalid task.", "error")
            conn.close()
            return redirect(url_for("intern.intern_tasks"))

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute(
            """
            UPDATE tasks 
            SET submission = ?, submitted_at = ?, status = 'submitted' 
            WHERE id = ?
            """,
            (submission_content, timestamp, task_id)
        )
        conn.commit()
        flash("Task submitted successfully! 🚀", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error submitting task: {e}", "error")
    finally:
        conn.close()

@intern_bp.route("/student/task-completed/<int:task_id>", methods=["POST"], endpoint="quick_task_completed")
def quick_task_completed(task_id):
    if not is_intern_logged_in():
        return redirect(url_for("auth.login"))

    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Verify task belongs to student and is pending
        cursor.execute("SELECT id FROM students WHERE user_id = ?", (session["user_id"],))
        student_id = cursor.fetchone()[0]
        
        cursor.execute("SELECT id, status FROM tasks WHERE id = ? AND student_id = ?", (task_id, student_id))
        task = cursor.fetchone()
        if not task:
            flash("Invalid task.", "error")
            conn.close()
            return redirect(url_for("intern.intern_tasks"))
        
        if task[1] != 'pending':
            flash("Task is already submitted or completed.", "info")
            conn.close()
            return redirect(url_for("intern.intern_tasks"))

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute(
            """
            UPDATE tasks 
            SET submission = 'Marked as completed by intern', submitted_at = ?, status = 'submitted' 
            WHERE id = ?
            """,
            (timestamp, task_id)
        )
        conn.commit()
        flash("Task marked as completed! Admin will review it. ✅", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error marking task: {e}", "error")
    finally:
        conn.close()

    return redirect(request.referrer or url_for("intern.intern_tasks"))


@intern_bp.route("/student/attendance", endpoint="intern_attendance")
def intern_attendance():
    if not is_intern_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM students WHERE user_id = ?", (session["user_id"],))
    student_id_row = cursor.fetchone()
    attendance_records = []
    if student_id_row:
        current_student_db_id = student_id_row[0]
        cursor.execute(
            "SELECT date, status FROM attendance WHERE student_id = ? ORDER BY date DESC",
            (current_student_db_id,),
        )
        attendance_records = cursor.fetchall()
    conn.close()
    return render_template(
        "intern_attendance.html",
        username=session["username"],
        attendance_records=attendance_records,
    )


@intern_bp.route("/student/courses", endpoint="intern_courses")
def intern_courses():
    if not is_intern_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM courses ORDER BY name")
    suggested_internships = [row[0] for row in cursor.fetchall()]
    conn.close()
    return render_template(
        "intern_courses.html",
        username=session["username"],
        suggested_courses=suggested_internships,
    )


@intern_bp.route("/student/performance", endpoint="intern_performance")
def intern_performance():
    if not is_intern_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM students WHERE user_id = ?", (session["user_id"],))
    student_id_row = cursor.fetchone()

    performance_data = None
    average_task_mark = 0.0
    if student_id_row:
        current_student_db_id = student_id_row[0]
        performance_data = calculate_overall_performance_score(current_student_db_id)
        average_task_mark = calculate_average_task_mark(current_student_db_id)

    conn.close()
    return render_template(
        "intern_performance.html",
        username=session["username"],
        performance_data=performance_data,
        average_task_mark=round(average_task_mark, 2),
    )


@intern_bp.route("/student/profile", endpoint="intern_profile")
def intern_profile():
    if not is_intern_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT s.unique_student_id, s.name, s.email, c.name, s.profile_pic FROM students s LEFT JOIN courses c ON s.course_id = c.id WHERE s.user_id = ?",
        (session["user_id"],),
    )
    profile_data = cursor.fetchone()
    conn.close()

    student_profile = {}
    if profile_data:
        student_profile = {
            "unique_student_id": profile_data[0],
            "name": profile_data[1],
            "email": profile_data[2],
            "course": profile_data[3] if profile_data[3] else "Not Assigned",
            "profile_pic": profile_data[4]
        }
    return render_template(
        "intern_profile.html",
        username=session["username"],
        student_profile=student_profile,
    )


@intern_bp.route("/student/feedback", endpoint="intern_feedback")
def intern_feedback():
    if not is_intern_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM students WHERE user_id = ?", (session["user_id"],))
    student_id_row = cursor.fetchone()
    feedback_records = []
    if student_id_row:
        current_student_db_id = student_id_row[0]
        cursor.execute(
            """
            SELECT f.comments, f.score, f.feedback_date, t.title AS task_title, u.username AS admin_username, f.id AS feedback_id, f.feedback_category
            FROM feedback f
            LEFT JOIN tasks t ON f.task_id = t.id
            JOIN users u ON f.admin_id = u.id
            WHERE f.student_id = ? ORDER BY f.feedback_date DESC
            """,
            (current_student_db_id,),
        )
        feedback_records = cursor.fetchall()
    conn.close()
    return render_template(
        "intern_feedback.html",
        username=session["username"],
        feedback_records=feedback_records,
    )


@intern_bp.route("/student/send-feedback", methods=["GET", "POST"], endpoint="intern_send_feedback")
def intern_send_feedback():
    if not is_intern_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if request.method == "POST":
        subject = request.form["subject"]
        message = request.form["message"]

        cursor.execute(
            "SELECT id FROM students WHERE user_id = ?", (session["user_id"],)
        )
        student_id_row = cursor.fetchone()
        if student_id_row:
            student_id = student_id_row[0]
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    "INSERT INTO student_feedback_to_admin (student_id, subject, message, timestamp) VALUES (?, ?, ?, ?)",
                    (student_id, subject, message, timestamp),
                )
                conn.commit()
                flash(
                    "Your feedback has been sent to the admin successfully!",
                    "success",
                )
                return redirect(url_for("intern_send_feedback"))
            except Exception as e:
                conn.rollback()
                flash(
                    f"An error occurred while sending feedback: {e}",
                    "error",
                )
        else:
            flash(
                "Could not find your student profile. Please contact support.",
                "error",
            )
        conn.close()
        return redirect(url_for("intern_send_feedback"))

    conn.close()
    return render_template(
        "intern_send_feedback.html",
        username=session["username"],
    )


@intern_bp.route("/student/leave-permission", methods=["GET", "POST"], endpoint="intern_leave_permission")
def intern_leave_permission():
    if not is_intern_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM students WHERE user_id = ?", (session["user_id"],))
    student_row = cursor.fetchone()
    student_id = student_row[0]

    if request.method == "POST":
        from_date = request.form.get("from_date")
        to_date = request.form.get("to_date")
        leave_type = request.form.get("leave_type")
        reason = request.form.get("reason")

        if not from_date or not to_date or not leave_type or not reason:
            flash("All fields required!", "error")
            return redirect(url_for("intern_leave_permission"))

        cursor.execute(
            """
            INSERT INTO leave_requests
            (student_id, from_date, to_date, leave_type, reason, status)
            VALUES (?, ?, ?, ?, ?, 'Pending')
            """,
            (student_id, from_date, to_date, leave_type, reason),
        )

        conn.commit()
        flash("Leave request submitted successfully ✅", "success")
        return redirect(url_for("intern_leave_permission"))

    cursor.execute(
        """
        SELECT from_date, to_date, leave_type, reason, status
        FROM leave_requests
        WHERE student_id = ?
        ORDER BY id DESC
        """,
        (student_id,),
    )
    leave_requests = cursor.fetchall()

    conn.close()

    return render_template(
        "intern_leave_permission.html",
        username=session["username"],
        leave_requests=leave_requests,
    )



@intern_bp.route("/intern/course/<course_name>", endpoint="intern_course_details")
def intern_course_details(course_name):
    if "role" not in session:
        return redirect(url_for("auth.login"))
    if session.get("role") != "intern":
        return redirect(url_for("auth.login"))

    return render_template("course_details.html", course_name=course_name)


@intern_bp.route("/student/register-internship/<course_name>", methods=["POST"], endpoint="register_internship")
def register_internship(course_name):
    if not is_intern_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    try:
        # Get student ID
        cursor.execute("SELECT id FROM students WHERE user_id = ?", (session["user_id"],))
        student_id = cursor.fetchone()[0]

        # Get course ID
        cursor.execute("SELECT id FROM courses WHERE name = ?", (course_name,))
        course_row = cursor.fetchone()
        if not course_row:
            flash("Internship program not found.", "error")
            return redirect(url_for("intern.intern_courses"))
        
        course_id = course_row[0]

        # Check if already registered
        cursor.execute(
            "SELECT id FROM internship_registrations WHERE student_id = ? AND course_id = ?",
            (student_id, course_id)
        )
        if cursor.fetchone():
            flash(f"You have already registered for the {course_name} internship.", "info")
            return redirect(url_for("intern.intern_courses"))

        # Register
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO internship_registrations (student_id, course_id, registered_at, status) VALUES (?, ?, ?, 'Pending')",
            (student_id, course_id, timestamp)
        )
        conn.commit()

        # Send confirmation email
        cursor.execute("SELECT name, email FROM students WHERE id = ?", (student_id,))
        student_info = cursor.fetchone()
        if student_info:
            send_registration_email(student_info[1], student_info[0], course_name)

        flash(f"Successfully registered for {course_name}! The admin has been notified. 🚀", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error during registration: {e}", "error")
    finally:
        conn.close()

    return redirect(url_for("intern.intern_courses"))


@intern_bp.route("/student/edit-profile", methods=["GET", "POST"], endpoint="intern_edit_profile")
def intern_edit_profile():
    if not is_intern_logged_in():
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, name, email, phone_number, gender, dob, address, linkedin_url, github_url, profile_pic FROM students WHERE user_id = ?",
        (session["user_id"],),
    )
    student = cursor.fetchone()
    student_id = student[0]

    if request.method == "POST":
        import json
        from werkzeug.utils import secure_filename
        from flask import current_app

        # Gather form data
        new_data = {
            "name": request.form.get("name"),
            "email": request.form.get("email"),
            "phone_number": request.form.get("phone_number"),
            "gender": request.form.get("gender"),
            "dob": request.form.get("dob"),
            "address": request.form.get("address"),
            "linkedin_url": request.form.get("linkedin_url"),
            "github_url": request.form.get("github_url"),
        }

        # Handle profile pic upload
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                # Use a temporary prefix for requests
                unique_filename = f"req_{student_id}_{filename}"
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename))
                new_data["profile_pic"] = unique_filename
        
        # Check if there are actual changes (optional, but good practice)
        # For now, just submit whatever is in the form

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                """
                INSERT INTO profile_update_requests (student_id, changed_data, requested_at)
                VALUES (?, ?, ?)
                """,
                (student_id, json.dumps(new_data), timestamp),
            )
            conn.commit()
            flash("Profile update request submitted for admin approval.", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Error submitting request: {e}", "error")
        
        conn.close()
        return redirect(url_for("intern.intern_profile"))

    # Convert tuple to dict for easy access in template
    student_data = {
        "name": student[1],
        "email": student[2],
        "phone_number": student[3],
        "gender": student[4],
        "dob": student[5],
        "address": student[6],
        "linkedin_url": student[7],
        "github_url": student[8],
        "profile_pic": student[9],
    }

    conn.close()
    return render_template("intern_edit_profile.html", student=student_data)

