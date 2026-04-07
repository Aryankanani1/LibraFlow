from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Book, BookCopy, Loan, Reservation
from functools import wraps

student_bp = Blueprint('student', __name__, url_prefix='/student')


def student_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_student():
            flash('Access restricted to students.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    active_loans = current_user.loans_as_student.filter_by(status='active').all()
    pending_reservations = current_user.reservations.filter_by(status='pending').all()
    recent_history = current_user.loans_as_student.order_by(Loan.issue_date.desc()).limit(5).all()
    overdue = [l for l in active_loans if l.is_overdue()]
    return render_template('student/dashboard.html',
                           active_loans=active_loans,
                           pending_reservations=pending_reservations,
                           recent_history=recent_history,
                           overdue=overdue)


@student_bp.route('/search')
@login_required
@student_required
def search():
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')
    books = []
    if query:
        books = current_user.search_books(query, search_type)
    return render_template('student/search.html', books=books, query=query, search_type=search_type)


@student_bp.route('/history')
@login_required
@student_required
def history():
    loans = current_user.view_borrowing_history()
    return render_template('student/history.html', loans=loans)


@student_bp.route('/reserve/<int:copy_id>', methods=['POST'])
@login_required
@student_required
def reserve(copy_id):
    reservation, message = current_user.reserve_book(copy_id)
    if reservation:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    return redirect(url_for('student.search'))


@student_bp.route('/reservations')
@login_required
@student_required
def reservations():
    all_reservations = current_user.reservations.order_by(
        Reservation.request_date.desc()
    ).all()
    return render_template('student/reservations.html', reservations=all_reservations)


@student_bp.route('/reservations/<int:reservation_id>/cancel', methods=['POST'])
@login_required
@student_required
def cancel_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.student_id != current_user.id:
        flash('Not authorized.', 'danger')
        return redirect(url_for('student.reservations'))
    if reservation.status not in ('pending', 'approved'):
        flash('Cannot cancel this reservation.', 'warning')
        return redirect(url_for('student.reservations'))
    reservation.cancel()
    flash('Reservation cancelled.', 'info')
    return redirect(url_for('student.reservations'))


@student_bp.route('/borrow/<int:copy_id>', methods=['POST'])
@login_required
@student_required
def borrow(copy_id):
    copy = BookCopy.query.get_or_404(copy_id)
    if not copy.is_available():
        flash('This copy is not available for borrowing.', 'danger')
        return redirect(url_for('student.search'))
    due_date = datetime.now(timezone.utc) + timedelta(days=14)
    loan = Loan(
        student_id=current_user.id,
        copy_id=copy.id,
        issue_date=datetime.now(timezone.utc),
        due_date=due_date,
        status='active'
    )
    copy.status = 'issued'
    db.session.add(loan)
    db.session.commit()
    flash(f'Book issued! Due date: {due_date.strftime("%B %d, %Y")}', 'success')
    return redirect(url_for('student.dashboard'))
