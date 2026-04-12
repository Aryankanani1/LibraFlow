from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'student' or 'librarian'
    student_id = db.Column(db.String(50), nullable=True)
    employee_id = db.Column(db.String(50), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    loans_as_student = db.relationship(
        'Loan', foreign_keys='Loan.student_id', backref='student', lazy='dynamic'
    )
    loans_as_librarian = db.relationship(
        'Loan', foreign_keys='Loan.librarian_id', backref='librarian', lazy='dynamic'
    )
    reservations = db.relationship('Reservation', backref='student', lazy='dynamic')
    reports = db.relationship('Report', backref='librarian', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_student(self):
        return self.role == 'student'

    def is_librarian(self):
        return self.role == 'librarian'

    # ---------- Student methods ----------
    def search_books(self, query, search_type='title'):
        if search_type == 'title':
            return Book.query.filter(Book.title.ilike(f'%{query}%')).all()
        elif search_type == 'author':
            return Book.query.filter(Book.author.ilike(f'%{query}%')).all()
        elif search_type == 'category':
            return Book.query.filter(Book.category.ilike(f'%{query}%')).all()
        return Book.query.filter(
            (Book.title.ilike(f'%{query}%')) |
            (Book.author.ilike(f'%{query}%')) |
            (Book.category.ilike(f'%{query}%'))
        ).all()

    def view_borrowing_history(self):
        return self.loans_as_student.order_by(Loan.issue_date.desc()).all()

    def reserve_book(self, copy_id):
        copy = BookCopy.query.filter_by(id=copy_id, status='available').first()
        if not copy:
            return None, 'Book copy not available'
        reservation = Reservation(
            student_id=self.id,
            copy_id=copy.id,
            request_date=datetime.now(timezone.utc),
            status='pending'
        )
        copy.status = 'reserved'
        db.session.add(reservation)
        db.session.commit()
        return reservation, 'Reservation submitted'

    # ---------- Librarian methods ----------
    def add_book(self, isbn, title, author, category, publisher, num_copies=1, shelf_location=''):
        book = Book.query.filter_by(isbn=isbn).first()
        if not book:
            book = Book(isbn=isbn, title=title, author=author,
                        category=category, publisher=publisher)
            db.session.add(book)
            db.session.flush()
        for i in range(num_copies):
            existing = BookCopy.query.filter_by(book_id=book.id).count()
            copy = BookCopy(
                copy_code=f'{isbn}-{existing + i + 1:03d}',
                barcode=f'BC{isbn}{existing + i + 1:03d}',
                status='available',
                shelf_location=shelf_location,
                book_id=book.id
            )
            db.session.add(copy)
        db.session.commit()
        return book

    def approve_request(self, reservation_id):
        reservation = Reservation.query.get(reservation_id)
        if not reservation or reservation.status != 'pending':
            return None, 'Invalid reservation'
        reservation.status = 'approved'
        db.session.commit()
        return reservation, 'Request approved'

    def generate_report(self, report_type):
        report = Report(
            report_type=report_type,
            generated_on=datetime.now(timezone.utc),
            librarian_id=self.id
        )
        db.session.add(report)
        db.session.commit()
        return report


class Book(db.Model):
    __tablename__ = 'books'

    id = db.Column(db.Integer, primary_key=True)
    isbn = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    publisher = db.Column(db.String(150))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    copies = db.relationship('BookCopy', backref='book', lazy='dynamic',
                             cascade='all, delete-orphan')

    def get_details(self):
        return {
            'id': self.id,
            'isbn': self.isbn,
            'title': self.title,
            'author': self.author,
            'category': self.category,
            'publisher': self.publisher,
            'available_copies': self.copies.filter_by(status='available').count(),
            'total_copies': self.copies.count(),
        }

    def available_copies_count(self):
        return self.copies.filter_by(status='available').count()

    def avg_rating(self):
        reviews = self.reviews.all()
        if not reviews:
            return None
        return round(sum(r.rating for r in reviews) / len(reviews), 1)

    def review_count(self):
        return self.reviews.count()


class BookCopy(db.Model):
    __tablename__ = 'book_copies'

    id = db.Column(db.Integer, primary_key=True)
    copy_code = db.Column(db.String(50), unique=True, nullable=False)
    barcode = db.Column(db.String(100), unique=True)
    status = db.Column(db.String(20), default='available')  # available, issued, reserved, lost
    shelf_location = db.Column(db.String(50))
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)

    loans = db.relationship('Loan', backref='copy', lazy='dynamic')
    reservations = db.relationship('Reservation', backref='copy', lazy='dynamic')

    def is_available(self):
        return self.status == 'available'


class Reservation(db.Model):
    __tablename__ = 'reservations'

    id = db.Column(db.Integer, primary_key=True)
    request_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(20), default='pending')  # pending, approved, cancelled, fulfilled
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    copy_id = db.Column(db.Integer, db.ForeignKey('book_copies.id'), nullable=False)

    def create(self):
        db.session.add(self)
        db.session.commit()

    def cancel(self):
        self.status = 'cancelled'
        if self.copy and self.copy.status == 'reserved':
            self.copy.status = 'available'
        db.session.commit()


class Loan(db.Model):
    __tablename__ = 'loans'

    id = db.Column(db.Integer, primary_key=True)
    issue_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    due_date = db.Column(db.DateTime, nullable=False)
    return_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='active')  # active, returned, overdue
    fine_charged = db.Column(db.Float, nullable=True)   # frozen at return time
    fine_paid = db.Column(db.Boolean, default=False, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    copy_id = db.Column(db.Integer, db.ForeignKey('book_copies.id'), nullable=False)
    librarian_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    def mark_returned(self):
        # Freeze the fine before changing status
        live = self._live_fine()
        self.fine_charged = live if live > 0 else None
        self.return_date = datetime.now(timezone.utc)
        self.status = 'returned'
        if self.copy:
            self.copy.status = 'available'
        db.session.commit()

    def is_overdue(self):
        if self.status == 'active':
            return datetime.now(timezone.utc) > self.due_date.replace(tzinfo=timezone.utc)
        return False

    def _live_fine(self):
        """Compute fine from today (only meaningful while loan is active/overdue)."""
        if self.status == 'active':
            due = self.due_date.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > due:
                delta = datetime.now(timezone.utc) - due
                return max(0, delta.days) * 1.0
        return 0.0

    def fine_amount(self):
        """Return the fine: frozen value for returned loans, live calc for active ones."""
        if self.fine_charged is not None:
            return self.fine_charged
        return self._live_fine()

    def outstanding_fine(self):
        """Fine still owed (0 if paid or no fine)."""
        if self.fine_paid:
            return 0.0
        return self.fine_charged or 0.0


class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)        # 1–5 stars
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)

    student = db.relationship('User', backref=db.backref('reviews', lazy='dynamic'))
    book = db.relationship('Book', backref=db.backref('reviews', lazy='dynamic'))


class Report(db.Model):
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    report_type = db.Column(db.String(50), nullable=False)
    generated_on = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    librarian_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def generate(self):
        db.session.add(self)
        db.session.commit()
        return self


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(10), nullable=False)    # 'email' | 'sms'
    subject = db.Column(db.String(200))
    message = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(20), default='sent')  # 'sent' | 'failed' | 'pending'
    read = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic'))
