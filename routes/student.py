from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Book, BookCopy, Loan, Reservation, Review, Notification
from functools import wraps
import json
from notifications import notify_loan_issued

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
    notify_loan_issued(loan)
    flash(f'Book issued! Due date: {due_date.strftime("%B %d, %Y")}', 'success')
    return redirect(url_for('student.dashboard'))


@student_bp.route('/books/<int:book_id>/review', methods=['GET', 'POST'])
@login_required
@student_required
def review_book(book_id):
    book = Book.query.get_or_404(book_id)

    # Only allow review if student has returned this book at least once
    borrowed = Loan.query.join(BookCopy).filter(
        BookCopy.book_id == book_id,
        Loan.student_id == current_user.id,
        Loan.status == 'returned'
    ).first()
    if not borrowed:
        flash('You can only review books you have returned.', 'warning')
        return redirect(url_for('student.search'))

    existing = Review.query.filter_by(student_id=current_user.id, book_id=book_id).first()

    if request.method == 'POST':
        rating = int(request.form.get('rating', 0))
        comment = request.form.get('comment', '').strip()
        if rating < 1 or rating > 5:
            flash('Please select a rating between 1 and 5.', 'danger')
            return render_template('student/review.html', book=book, existing=existing)

        if existing:
            existing.rating = rating
            existing.comment = comment
            existing.created_at = datetime.now(timezone.utc)
            flash('Your review has been updated.', 'success')
        else:
            review = Review(student_id=current_user.id, book_id=book_id,
                            rating=rating, comment=comment)
            db.session.add(review)
            flash('Review submitted! Thank you.', 'success')

        db.session.commit()
        return redirect(url_for('student.history'))

    return render_template('student/review.html', book=book, existing=existing)


@student_bp.route('/books/<int:book_id>')
@login_required
@student_required
def book_detail(book_id):
    book = Book.query.get_or_404(book_id)
    reviews = book.reviews.order_by(Review.created_at.desc()).all()
    user_review = Review.query.filter_by(student_id=current_user.id, book_id=book_id).first()
    borrowed = Loan.query.join(BookCopy).filter(
        BookCopy.book_id == book_id,
        Loan.student_id == current_user.id,
        Loan.status == 'returned'
    ).first()
    return render_template('student/book_detail.html', book=book,
                           reviews=reviews, user_review=user_review,
                           can_review=bool(borrowed))


@student_bp.route('/map')
@login_required
@student_required
def map():
    # Section metadata: icon, display name
    SECTION_META = {
        'Programming':         'code-2',
        'Web Development':     'globe',
        'Software Engineering':'settings-2',
        'Algorithms':          'binary',
        'Machine Learning':    'cpu',
        'Data Science':        'bar-chart-2',
        'Databases':           'database',
        'Computer Science':    'monitor',
        'Cybersecurity':       'shield',
        'DevOps':              'git-branch',
        'Operating Systems':   'layers',
        'Networking':          'network',
        'Mathematics':         'calculator',
        'General':             'book',
        'Computers':           'laptop',
    }

    all_books = Book.query.order_by(Book.category, Book.title).all()

    # Build section data
    section_map = {}
    for book in all_books:
        cat = book.category
        if cat not in section_map:
            section_map[cat] = {'books': [], 'available': 0, 'total_copies': 0}
        copies = book.copies.all()
        avail  = sum(1 for c in copies if c.is_available())
        shelf  = copies[0].shelf_location if copies else ''
        section_map[cat]['books'].append({
            'id':        book.id,
            'title':     book.title,
            'author':    book.author,
            'shelf':     shelf,
            'available': avail,
            'total':     len(copies),
        })
        section_map[cat]['available']    += avail
        section_map[cat]['total_copies'] += len(copies)

    sections = []
    for cat, data in sorted(section_map.items()):
        first_copy = BookCopy.query.join(Book).filter(Book.category == cat).first()
        shelf_prefix = first_copy.shelf_location if first_copy else '—'
        sections.append({
            'category':    cat,
            'icon':        SECTION_META.get(cat, '📚'),
            'book_count':  len(data['books']),
            'available':   data['available'],
            'shelf_prefix': shelf_prefix,
        })

    books_json = json.dumps({cat: data['books'] for cat, data in section_map.items()})

    # Handle search highlight
    query = request.args.get('q', '').strip()
    highlight_category = None
    highlight_title = None
    highlight_msg = None

    if query:
        book = Book.query.filter(Book.title.ilike(f'%{query}%')).first()
        if book:
            highlight_category = book.category
            highlight_title = query
            copy = book.copies.first()
            shelf = copy.shelf_location if copy else '—'
            highlight_msg = f'"{book.title}" is in the {book.category} section — Shelf {shelf}'
        else:
            highlight_msg = f'No book found matching "{query}"'

    return render_template('student/map.html',
                           sections=sections,
                           books_json=books_json,
                           highlight_category=highlight_category,
                           highlight_title=highlight_title,
                           highlight_msg=highlight_msg)


@student_bp.route('/notifications')
@login_required
@student_required
def notifications():
    all_notifs = current_user.notifications.order_by(
        Notification.sent_at.desc()
    ).limit(100).all()
    # Mark all as read
    unread = current_user.notifications.filter_by(read=False).all()
    for n in unread:
        n.read = True
    if unread:
        db.session.commit()
    return render_template('student/notifications.html', notifications=all_notifs)
