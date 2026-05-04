import os

target_str = '''    <!-- Advanced Footer with animated background and links -->
    <footer class="footer">
        <div class="container">
            <div class="footer-links">
                <a
                    href="{% if session.role == 'admin' %}{{ url_for('admin.admin_dashboard') }}{% else %}{{ url_for('intern.intern_dashboard') }}{% endif %}">Home</a>
                <a href="#">About</a>
                <a href="#">Contact</a>
                <a href="#">Privacy Policy</a>
            </div>
            <p>&copy; 2026 Intern Student Performance Predictor. All rights reserved.</p>
        </div>
    </footer>'''

replacement_str = '''    <!-- Advanced Footer with animated background and links -->
    <footer class="footer">
        <div class="container">
            <div class="footer-links">
                <a href="{{ url_for('auth.index') }}">Home</a>
                <a href="{{ url_for('auth.about') }}">About</a>
                <a href="{{ url_for('auth.contact') }}">Contact</a>
                <a href="#">Privacy Policy</a>
            </div>
            <p>&copy; 2026 Intern Student Performance Predictor. All rights reserved.</p>
        </div>
    </footer>'''

target_str2 = '''    <!-- Advanced Footer with animated background and links -->
    <footer class="footer">
        <div class="container">
            <div class="footer-links">
                <a href="{% if session.role == 'admin' %}{{ url_for('admin.admin_dashboard') }}{% else %}{{ url_for('intern.intern_dashboard') }}{% endif %}">Home</a>
                <a href="#">About</a>
                <a href="#">Contact</a>
                <a href="#">Privacy Policy</a>
            </div>
            <p>&copy; 2026 Intern Student Performance Predictor. All rights reserved.</p>
        </div>
    </footer>'''

templates_dir = 'templates'
count = 0
for filename in os.listdir(templates_dir):
    if filename.endswith('.html') and filename not in ['base.html', 'about.html', 'contact.html', 'login.html']:
        filepath = os.path.join(templates_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        new_content = content.replace(target_str, replacement_str)
        new_content = new_content.replace(target_str2, replacement_str)
        
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            count += 1
            print(f'Updated {filename}')

print(f'Total files updated: {count}')
