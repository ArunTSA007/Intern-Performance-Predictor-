import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# SMTP Configuration - Update these with actual credentials
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "predictor9099@gmail.com"
SENDER_PASSWORD = "iiiqowbcbfmfbkla"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: 'Inter', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
        .container {{ width: 100%; max-width: 600px; margin: 0 auto; padding: 20px; box-sizing: border-box; }}
        .header {{ background: #2563eb; padding: 30px; border-radius: 12px 12px 0 0; text-align: center; color: white; }}
        .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 12px 12px; border: 1px solid #e5e7eb; border-top: none; }}
        .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #6b7280; }}
        .button {{ display: inline-block; padding: 12px 24px; background: #2563eb; color: #ffffff !important; text-decoration: none; border-radius: 6px; font-weight: 600; margin-top: 20px; }}
        .info-box {{ background: white; padding: 15px; border-radius: 8px; border: 1px solid #e5e7eb; margin: 20px 0; }}
        h2 {{ margin-top: 0; color: #1e40af; }}
        @media only screen and (max-width: 480px) {{
            .container {{ padding: 10px; }}
            .header, .content {{ padding: 20px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Intern Panel</h1>
        </div>
        <div class="content">
            {content}
        </div>
        <div class="footer">
            &copy; 2026 Intern Performance Predictor Team
        </div>
    </div>
</body>
</html>
"""

def send_email(receiver_email, subject, html_content):
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = receiver_email
        msg['Subject'] = subject
        
        full_html = HTML_TEMPLATE.format(content=html_content)
        msg.attach(MIMEText(full_html, 'html'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, receiver_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"❌ Failed to send email to {receiver_email}: {e}")
        return False

def send_registration_email(receiver_email, intern_name, course_name):
    subject = f"Registration Confirmation: {course_name} Internship"
    content = f"""
        <h2>Registration Received!</h2>
        <p>Dear <strong>{intern_name}</strong>,</p>
        <p>Thank you for registering for the <strong>{course_name}</strong> internship program.</p>
        <p>Your registration is currently under review. We will notify you once it's approved.</p>
        <a href="http://localhost:5000/login" class="button" style="color: #ffffff;">Visit Portal</a>
    """
    if send_email(receiver_email, subject, content):
        print(f"✅ Confirmation email sent to {receiver_email}")
        return True
    return False

def send_task_assignment_email(receiver_email, intern_name, task_title, due_date):
    subject = f"New Task Assigned: {task_title}"
    content = f"""
        <h2>New Task Assigned</h2>
        <p>Dear <strong>{intern_name}</strong>,</p>
        <p>A new task has been assigned to you:</p>
        <div class="info-box">
            <p><strong>Task:</strong> {task_title}</p>
            <p><strong>Due Date:</strong> {due_date}</p>
        </div>
        <p>Please log in to your dashboard to view the full details and start work.</p>
        <a href="http://localhost:5000/intern-tasks" class="button" style="color: #ffffff;">View Task</a>
    """
    if send_email(receiver_email, subject, content):
        print(f"✅ Task notification email sent to {receiver_email}")
        return True
    return False

def send_welcome_email(receiver_email, intern_name, unique_id, temp_password):
    subject = "Welcome to Intern Performance Predictor - Login Credentials"
    content = f"""
        <h2>Welcome, {intern_name}!</h2>
        <p>Your account has been created. Use the following credentials to log in:</p>
        <div class="info-box">
            <p><strong>Email/Username:</strong> {unique_id}</p>
            <p><strong>Temporary Password:</strong> {temp_password}</p>
        </div>
        <p>Please change your password after your first login.</p>
        <a href="http://localhost:5000/login" class="button" style="color: #ffffff;">Login Now</a>
    """
    if send_email(receiver_email, subject, content):
        print(f"✅ Welcome email sent to {receiver_email}")
        return True
    return False
