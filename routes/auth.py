from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_librarian():
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('student.dashboard'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            if user.is_librarian():
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('student.dashboard'))
        flash('Invalid email or password.', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role = request.form.get('role', 'student')
        student_id = request.form.get('student_id', '').strip()
        employee_id = request.form.get('employee_id', '').strip()
        phone_number = request.form.get('phone_number', '').strip()

        # Librarian registration requires the staff invite code
        if role == 'librarian':
            code = request.form.get('librarian_code', '').strip()
            if code != current_app.config.get('LIBRARIAN_CODE'):
                flash('Invalid staff registration code. Contact your administrator.', 'danger')
                return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('register.html')

        user = User(name=name, email=email, role=role,
                    student_id=student_id or None,
                    employee_id=employee_id or None,
                    phone_number=phone_number or None)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')
