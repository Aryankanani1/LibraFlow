from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, User, Book, BookCopy, Loan, Reservation, Report, Review, Notification
from functools import wraps
import urllib.request
import urllib.parse
import json
import ssl
import certifi
from notifications import (
    notify_loan_issued, notify_loan_returned,
    notify_reservation_approved, notify_reservation_rejected,
    notify_overdue_reminder, notify_fine_paid,
)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def librarian_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_librarian():
            flash('Access restricted to librarians.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/dashboard')
@login_required
@librarian_required
def dashboard():
    total_books = Book.query.count()
    total_copies = BookCopy.query.count()
    available_copies = BookCopy.query.filter_by(status='available').count()
    active_loans = Loan.query.filter_by(status='active').count()
    pending_reservations = Reservation.query.filter_by(status='pending').count()
    overdue_loans = [l for l in Loan.query.filter_by(status='active').all() if l.is_overdue()]
    recent_loans = Loan.query.order_by(Loan.issue_date.desc()).limit(10).all()
    return render_template('admin/dashboard.html',
                           total_books=total_books,
                           total_copies=total_copies,
                           available_copies=available_copies,
                           active_loans=active_loans,
                           pending_reservations=pending_reservations,
                           overdue_loans=overdue_loans,
                           recent_loans=recent_loans)


# ── Book Management ──────────────────────────────────────────────────────────

@admin_bp.route('/books')
@login_required
@librarian_required
def books():
    query = request.args.get('q', '').strip()
    if query:
        all_books = Book.query.filter(
            (Book.title.ilike(f'%{query}%')) |
            (Book.author.ilike(f'%{query}%')) |
            (Book.isbn.ilike(f'%{query}%'))
        ).all()
    else:
        all_books = Book.query.order_by(Book.title).all()
    return render_template('admin/books.html', books=all_books, query=query)


@admin_bp.route('/books/add', methods=['GET', 'POST'])
@login_required
@librarian_required
def add_book():
    if request.method == 'POST':
        isbn = request.form.get('isbn', '').strip()
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        category = request.form.get('category', '').strip()
        publisher = request.form.get('publisher', '').strip()
        shelf_location = request.form.get('shelf_location', '').strip()
        num_copies = int(request.form.get('num_copies', 1))

        if not all([isbn, title, author, category]):
            flash('ISBN, title, author, and category are required.', 'danger')
            return render_template('admin/add_book.html')

        book = current_user.add_book(isbn, title, author, category, publisher, num_copies, shelf_location)
        flash(f'Book "{book.title}" added with {num_copies} copy/copies.', 'success')
        return redirect(url_for('admin.books'))

    return render_template('admin/add_book.html')


@admin_bp.route('/books/<int:book_id>/edit', methods=['GET', 'POST'])
@login_required
@librarian_required
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)
    if request.method == 'POST':
        book.title = request.form.get('title', book.title).strip()
        book.author = request.form.get('author', book.author).strip()
        book.category = request.form.get('category', book.category).strip()
        book.publisher = request.form.get('publisher', book.publisher).strip()
        db.session.commit()
        flash('Book updated.', 'success')
        return redirect(url_for('admin.books'))
    return render_template('admin/edit_book.html', book=book)


@admin_bp.route('/books/<int:book_id>/delete', methods=['POST'])
@login_required
@librarian_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    db.session.delete(book)
    db.session.commit()
    flash(f'Book "{book.title}" deleted.', 'info')
    return redirect(url_for('admin.books'))


# ── Loan Management ──────────────────────────────────────────────────────────

@admin_bp.route('/loans')
@login_required
@librarian_required
def loans():
    status = request.args.get('status', 'all')
    if status == 'active':
        all_loans = Loan.query.filter_by(status='active').order_by(Loan.issue_date.desc()).all()
    elif status == 'returned':
        all_loans = Loan.query.filter_by(status='returned').order_by(Loan.return_date.desc()).all()
    elif status == 'overdue':
        all_loans = [l for l in Loan.query.filter_by(status='active').all() if l.is_overdue()]
    else:
        all_loans = Loan.query.order_by(Loan.issue_date.desc()).all()
    return render_template('admin/loans.html', loans=all_loans, status=status)


@admin_bp.route('/loans/issue', methods=['GET', 'POST'])
@login_required
@librarian_required
def issue_book():
    if request.method == 'POST':
        barcode = request.form.get('barcode', '').strip()
        student_email = request.form.get('student_email', '').strip().lower()
        days = int(request.form.get('loan_days', 14))

        copy = BookCopy.query.filter_by(barcode=barcode).first()
        student = User.query.filter_by(email=student_email, role='student').first()

        if not copy:
            flash('Barcode not found.', 'danger')
            return render_template('admin/issue_book.html')
        if not student:
            flash('Student not found.', 'danger')
            return render_template('admin/issue_book.html')
        if not copy.is_available() and copy.status != 'reserved':
            flash(f'Copy is currently {copy.status}.', 'danger')
            return render_template('admin/issue_book.html')

        due_date = datetime.now(timezone.utc) + timedelta(days=days)
        loan = Loan(
            student_id=student.id,
            copy_id=copy.id,
            librarian_id=current_user.id,
            issue_date=datetime.now(timezone.utc),
            due_date=due_date,
            status='active'
        )
        copy.status = 'issued'
        # Fulfil any matching reservation
        reservation = Reservation.query.filter_by(
            student_id=student.id, copy_id=copy.id, status='approved'
        ).first()
        if reservation:
            reservation.status = 'fulfilled'

        db.session.add(loan)
        db.session.commit()
        notify_loan_issued(loan)
        flash(f'Book issued to {student.name}. Due: {due_date.strftime("%B %d, %Y")}', 'success')
        return redirect(url_for('admin.loans'))

    return render_template('admin/issue_book.html')


@admin_bp.route('/loans/<int:loan_id>/return', methods=['POST'])
@login_required
@librarian_required
def return_book(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    if loan.status != 'active':
        flash('This loan is already closed.', 'warning')
        return redirect(url_for('admin.loans'))
    loan.mark_returned()
    notify_loan_returned(loan)
    fine = loan.fine_charged or 0.0
    if fine > 0:
        flash(f'Book returned. Fine charged: ${fine:.2f}', 'warning')
    else:
        flash('Book returned successfully. No fines.', 'success')
    return redirect(url_for('admin.loans'))


# ── Reservation Management ───────────────────────────────────────────────────

@admin_bp.route('/reservations')
@login_required
@librarian_required
def reservations():
    status = request.args.get('status', 'pending')
    if status == 'all':
        all_reservations = Reservation.query.order_by(Reservation.request_date.desc()).all()
    else:
        all_reservations = Reservation.query.filter_by(status=status).order_by(
            Reservation.request_date.desc()
        ).all()
    return render_template('admin/reservations.html', reservations=all_reservations, status=status)


@admin_bp.route('/reservations/<int:reservation_id>/approve', methods=['POST'])
@login_required
@librarian_required
def approve_reservation(reservation_id):
    reservation, message = current_user.approve_request(reservation_id)
    if reservation:
        notify_reservation_approved(reservation)
        flash(message, 'success')
    else:
        flash(message, 'danger')
    return redirect(url_for('admin.reservations'))


@admin_bp.route('/reservations/<int:reservation_id>/reject', methods=['POST'])
@login_required
@librarian_required
def reject_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.status == 'pending':
        reservation.status = 'cancelled'
        if reservation.copy:
            reservation.copy.status = 'available'
        db.session.commit()
        notify_reservation_rejected(reservation)
        flash('Reservation rejected.', 'info')
    return redirect(url_for('admin.reservations'))


# ── Reports ──────────────────────────────────────────────────────────────────

@admin_bp.route('/reports')
@login_required
@librarian_required
def reports():
    report_type = request.args.get('type', 'overdue')
    data = {}

    if report_type == 'overdue':
        active_loans = Loan.query.filter_by(status='active').all()
        data['loans'] = [l for l in active_loans if l.is_overdue()]
        report = current_user.generate_report('overdue')

    elif report_type == 'inventory':
        data['books'] = Book.query.order_by(Book.category, Book.title).all()
        report = current_user.generate_report('inventory')

    elif report_type == 'top_rated':
        all_books = Book.query.all()
        rated_books = [(b, b.avg_rating(), b.review_count()) for b in all_books if b.avg_rating()]
        data['books'] = sorted(rated_books, key=lambda x: (x[1], x[2]), reverse=True)
        report = current_user.generate_report('top_rated')

    elif report_type == 'most_borrowed':
        from sqlalchemy import func
        results = db.session.query(
            Book, func.count(Loan.id).label('borrow_count')
        ).join(BookCopy, Book.id == BookCopy.book_id)\
         .join(Loan, BookCopy.id == Loan.copy_id)\
         .group_by(Book.id)\
         .order_by(func.count(Loan.id).desc())\
         .limit(20).all()
        data['books'] = results
        report = current_user.generate_report('most_borrowed')

    elif report_type == 'activity':
        data['recent_loans'] = Loan.query.order_by(Loan.issue_date.desc()).limit(50).all()
        data['recent_reservations'] = Reservation.query.order_by(
            Reservation.request_date.desc()
        ).limit(20).all()
        report = current_user.generate_report('activity')

    else:
        data = {}
        report = None

    past_reports = Report.query.filter_by(
        librarian_id=current_user.id
    ).order_by(Report.generated_on.desc()).limit(20).all()

    return render_template('admin/reports.html',
                           report_type=report_type,
                           data=data,
                           past_reports=past_reports)


# ── Overdue Tracking ─────────────────────────────────────────────────────────

@admin_bp.route('/overdue')
@login_required
@librarian_required
def overdue():
    active_loans = Loan.query.filter_by(status='active').all()
    overdue_loans = [l for l in active_loans if l.is_overdue()]
    return render_template('admin/overdue.html', overdue_loans=overdue_loans)


# ── Barcode Scan API ─────────────────────────────────────────────────────────

@admin_bp.route('/scan', methods=['GET', 'POST'])
@login_required
@librarian_required
def scan_barcode():
    result = None
    if request.method == 'POST':
        barcode = request.form.get('barcode', '').strip()
        copy = BookCopy.query.filter_by(barcode=barcode).first()
        if copy:
            result = {
                'found': True,
                'copy_id': copy.id,
                'copy_code': copy.copy_code,
                'status': copy.status,
                'shelf_location': copy.shelf_location,
                'book': copy.book.get_details()
            }
        else:
            result = {'found': False, 'message': 'Barcode not found'}
    return render_template('admin/scan.html', result=result)


# ── Print Barcodes ───────────────────────────────────────────────────────────

@admin_bp.route('/books/<int:book_id>/print-barcodes')
@login_required
@librarian_required
def print_barcodes(book_id):
    book = Book.query.get_or_404(book_id)
    copies = book.copies.all()
    return render_template('admin/print_barcodes.html', book=book, copies=copies)


# ── Book Lookup API (Open Library — no rate limits, no API key) ───────────────

@admin_bp.route('/api/google-books')   # keep same URL so frontend JS still works
@login_required
@librarian_required
def google_books_lookup():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])

    ctx = ssl.create_default_context(cafile=certifi.where())
    clean = query.replace('-', '').replace(' ', '')
    results = []

    # ── ISBN lookup via Open Library ─────────────────────────────────────────
    if clean.isdigit() and len(clean) in (10, 13):
        url = f'https://openlibrary.org/api/books?bibkeys=ISBN:{clean}&format=json&jscmd=data'
        try:
            with urllib.request.urlopen(url, timeout=6, context=ctx) as resp:
                raw = json.loads(resp.read().decode())
            for key, book in raw.items():
                authors   = ', '.join(a.get('name', '') for a in book.get('authors', []))
                publishers = book.get('publishers', [])
                publisher  = publishers[0].get('name', '') if publishers else ''
                subjects   = book.get('subjects', [])
                category   = subjects[0].get('name', 'General').split('--')[0].strip() if subjects else 'General'
                cover      = book.get('cover', {}).get('medium', '')
                isbn_list  = book.get('identifiers', {}).get('isbn_13', book.get('identifiers', {}).get('isbn_10', [clean]))
                results.append({
                    'title':     book.get('title', ''),
                    'authors':   authors or 'Unknown',
                    'publisher': publisher,
                    'isbn':      isbn_list[0] if isbn_list else clean,
                    'category':  category,
                    'thumbnail': cover,
                })
        except Exception:
            pass
        return jsonify(results)

    # ── Title / keyword search via Open Library ───────────────────────────────
    url = 'https://openlibrary.org/search.json?' + urllib.parse.urlencode({
        'q': query, 'limit': 10, 'fields': 'title,author_name,publisher,isbn,subject,cover_i,first_publish_year'
    })
    try:
        with urllib.request.urlopen(url, timeout=6, context=ctx) as resp:
            raw = json.loads(resp.read().decode())
    except Exception:
        return jsonify([])

    for doc in raw.get('docs', []):
        isbn_list = doc.get('isbn', [])
        isbn13 = next((i for i in isbn_list if len(i) == 13), '')
        isbn10 = next((i for i in isbn_list if len(i) == 10), '')
        isbn   = isbn13 or isbn10

        authors   = ', '.join(doc.get('author_name', ['Unknown']))
        publishers = doc.get('publisher', [])
        publisher  = publishers[0] if publishers else ''
        subjects   = doc.get('subject', [])
        category   = subjects[0].split('--')[0].strip() if subjects else 'General'
        cover_id   = doc.get('cover_i')
        thumbnail  = f'https://covers.openlibrary.org/b/id/{cover_id}-M.jpg' if cover_id else ''

        results.append({
            'title':     doc.get('title', ''),
            'authors':   authors,
            'publisher': publisher,
            'isbn':      isbn,
            'category':  category,
            'thumbnail': thumbnail,
        })

    return jsonify(results)


# ── Fine Management ──────────────────────────────────────────────────────────

@admin_bp.route('/fines')
@login_required
@librarian_required
def fines():
    unpaid = Loan.query.filter(
        Loan.fine_charged > 0,
        Loan.fine_paid == False  # noqa: E712
    ).order_by(Loan.return_date.desc()).all()
    paid = Loan.query.filter(
        Loan.fine_charged > 0,
        Loan.fine_paid == True  # noqa: E712
    ).order_by(Loan.return_date.desc()).limit(50).all()
    total_outstanding = sum(l.fine_charged for l in unpaid)
    total_collected   = sum(l.fine_charged for l in paid)
    return render_template('admin/fines.html',
                           unpaid=unpaid, paid=paid,
                           total_outstanding=total_outstanding,
                           total_collected=total_collected)


@admin_bp.route('/fines/<int:loan_id>/pay', methods=['POST'])
@login_required
@librarian_required
def pay_fine(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    if loan.fine_charged and not loan.fine_paid:
        loan.fine_paid = True
        db.session.commit()
        notify_fine_paid(loan)
        flash(f'Fine of ${loan.fine_charged:.2f} marked as paid for {loan.student.name}.', 'success')
    else:
        flash('No outstanding fine for this loan.', 'warning')
    return redirect(url_for('admin.fines'))


# ── Notification Log ─────────────────────────────────────────────────────────

@admin_bp.route('/notifications')
@login_required
@librarian_required
def notifications():
    ntype  = request.args.get('type', 'all')
    status = request.args.get('status', 'all')

    q = Notification.query
    if ntype != 'all':
        q = q.filter_by(type=ntype)
    if status != 'all':
        q = q.filter_by(status=status)
    all_notifs = q.order_by(Notification.sent_at.desc()).limit(200).all()

    counts = {
        'total':   Notification.query.count(),
        'sent':    Notification.query.filter_by(status='sent').count(),
        'pending': Notification.query.filter_by(status='pending').count(),
        'failed':  Notification.query.filter_by(status='failed').count(),
    }
    return render_template('admin/notifications.html',
                           notifications=all_notifs,
                           ntype=ntype, status=status, counts=counts)


@admin_bp.route('/notifications/send-overdue-reminders', methods=['POST'])
@login_required
@librarian_required
def send_overdue_reminders():
    active_loans = Loan.query.filter_by(status='active').all()
    overdue = [l for l in active_loans if l.is_overdue()]
    for loan in overdue:
        notify_overdue_reminder(loan)
    flash(f'Overdue reminders sent to {len(overdue)} student(s).', 'success')
    return redirect(url_for('admin.notifications'))


# ── Staff Management ─────────────────────────────────────────────────────────

@admin_bp.route('/staff')
@login_required
@librarian_required
def staff():
    librarians = User.query.filter_by(role='librarian').order_by(User.name).all()
    return render_template('admin/staff.html', librarians=librarians)
