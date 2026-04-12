from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from config import Config
from models import db, User
from routes.auth import auth_bp
from routes.books import books_bp
from routes.student import student_bp
from routes.admin import admin_bp

mail = Mail()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    mail.init_app(app)

    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    app.register_blueprint(auth_bp)
    app.register_blueprint(books_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)

    with app.app_context():
        db.create_all()
        _migrate_db()
        _seed_demo_data()

    return app


def _migrate_db():
    """Add new columns to existing SQLite tables without dropping data."""
    from sqlalchemy import text
    with db.engine.connect() as conn:
        # Helper: check if a column exists in a table
        def has_col(table, col):
            rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            return any(r[1] == col for r in rows)

        # users: phone_number
        if not has_col('users', 'phone_number'):
            conn.execute(text("ALTER TABLE users ADD COLUMN phone_number VARCHAR(20)"))

        # loans: fine_charged, fine_paid
        if not has_col('loans', 'fine_charged'):
            conn.execute(text("ALTER TABLE loans ADD COLUMN fine_charged FLOAT"))
        if not has_col('loans', 'fine_paid'):
            conn.execute(text("ALTER TABLE loans ADD COLUMN fine_paid BOOLEAN NOT NULL DEFAULT 0"))

        conn.commit()

    # notifications table is created by db.create_all() above
    # (it's a new table so it'll be created automatically if missing)


def _seed_demo_data():
    from models import User, Book, BookCopy
    if User.query.first():
        return  # already seeded

    # Demo librarian
    librarian = User(name='Admin Librarian', email='admin@libraflow.com',
                     role='librarian', employee_id='EMP001')
    librarian.set_password('admin123')
    db.session.add(librarian)

    # Demo student
    student = User(name='Arayan Khanani', email='student@libraflow.com',
                   role='student', student_id='STU001')
    student.set_password('student123')
    db.session.add(student)

    # Demo books
    sample_books = [
        ('978-0-13-468599-1', 'Clean Code', 'Robert C. Martin', 'Programming', 'Prentice Hall', 3),
        ('978-0-13-235088-4', 'The Pragmatic Programmer', 'David Thomas', 'Programming', 'Addison-Wesley', 2),
        ('978-0-596-51774-8', 'JavaScript: The Good Parts', 'Douglas Crockford', 'Web Development', "O'Reilly", 2),
        ('978-0-13-110362-7', 'The C Programming Language', 'Brian Kernighan', 'Programming', 'Prentice Hall', 1),
        ('978-0-07-352332-4', 'Introduction to Algorithms', 'Thomas Cormen', 'Algorithms', 'MIT Press', 2),
        ('978-0-13-597022-4', 'Design Patterns', 'Gang of Four', 'Software Engineering', 'Addison-Wesley', 2),
        ('978-1-49-195016-0', 'Flask Web Development', 'Miguel Grinberg', 'Web Development', "O'Reilly", 3),
        ('978-0-13-235428-8', 'Head First Design Patterns', 'Eric Freeman', 'Software Engineering', "O'Reilly", 2),
    ]

    for isbn, title, author, category, publisher, copies in sample_books:
        book = Book(isbn=isbn, title=title, author=author,
                    category=category, publisher=publisher)
        db.session.add(book)
        db.session.flush()
        for i in range(copies):
            copy = BookCopy(
                copy_code=f'{isbn}-{i+1:03d}',
                barcode=f'BC{isbn.replace("-", "")}{i+1:03d}',
                status='available',
                shelf_location=f'Shelf {category[0]}{i+1}',
                book_id=book.id
            )
            db.session.add(copy)

    db.session.commit()


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
