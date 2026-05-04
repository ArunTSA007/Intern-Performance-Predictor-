from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)
import sqlite3

from database import DATABASE


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/", endpoint="index")
def index():
    """Landing route – check session and redirect to appropriate dashboard or login."""
    if "user_id" in session and "role" in session:
        if session["role"] == "admin":
            return redirect(url_for("admin.admin_dashboard"))
        elif session["role"] == "intern":
            return redirect(url_for("intern.intern_dashboard"))
    
    # If not logged in, or session is invalid, clear and go to login
    session.clear()
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"], endpoint="login")
def login():
    if request.method == "GET":
        # If already logged in, redirect to dashboard instead of clearing session
        if "user_id" in session and "role" in session:
            if session["role"] == "admin":
                return redirect(url_for("admin.admin_dashboard"))
            elif session["role"] == "intern":
                return redirect(url_for("intern.intern_dashboard"))
    
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        # Role is now determined by the database, not user selection

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        # Check credentials (username or email)
        cursor.execute(
            "SELECT id, username, role FROM users WHERE username = ? AND password = ?",
            (username, password),
        )
        user = cursor.fetchone()

        if not user:
            # Try to find user by email in students table
            cursor.execute("SELECT user_id FROM students WHERE email = ?", (username,))
            student_user = cursor.fetchone()
            if student_user:
                user_id = student_user[0]
                cursor.execute(
                    "SELECT id, username, role FROM users WHERE id = ? AND password = ?",
                    (user_id, password),
                )
                user = cursor.fetchone()

        conn.close()

        if user:
            session["user_id"] = user[0]
            session["username"] = user[1]
            session["role"] = user[2]
            
            if session["role"] == "admin":
                return redirect(url_for("admin.admin_dashboard"))
            elif session["role"] == "intern":
                return redirect(url_for("intern.intern_dashboard"))
            else:
                # Fallback or unknown role
                flash("Unknown role assigned to user.", "error")
                return redirect(url_for("auth.login"))
        else:
            flash("Invalid credentials", "error")
            return render_template("login.html")

    return render_template("login.html")


@auth_bp.route("/logout", endpoint="logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))

@auth_bp.route("/about")
def about():
    """About page describing the website's mission and vision."""
    return render_template("about.html")

@auth_bp.route("/contact", methods=["GET", "POST"])
def contact():
    """Contact page with contact details and feedback form."""
    if request.method == "POST":
        # Form fields might include name, email, feedback
        # In a real app, this would be saved to a database or sent via email.
        # For now, we will flash a success message.
        flash("Thank you for your feedback! We appreciate your suggestions for future enhancements.", "success")
        return redirect(url_for("auth.contact"))
    return render_template("contact.html")

