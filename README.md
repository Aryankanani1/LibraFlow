# LibraFlow — Library Management System

A web-based library management system built with Python Flask + SQLite.

**Team:** Jeel Chauhan | Arayan Khanani | Pavithra Parameswaran | Krishna Akula

---

## Features

**Student Portal**
- Login / Register
- Search books by title, author, or category
- Check real-time book availability
- Borrow / Reserve books
- View borrowing history with fine tracking
- Cancel reservations

**Admin / Librarian Panel**
- Dashboard with live stats (total books, active loans, overdue, pending requests)
- Add, edit, and delete books with multiple copies
- Issue books to students via barcode scan
- Accept returned books
- Approve / reject reservation requests
- Track overdue books with fine calculation ($1/day)
- Generate reports: Overdue, Inventory, Activity

---

## Tech Stack

| Layer    | Technology                  |
|----------|-----------------------------|
| Frontend | HTML, CSS, JavaScript       |
| Backend  | Python 3.x + Flask          |
| Database | SQLite via SQLAlchemy ORM   |
| Auth     | Flask-Login + Werkzeug hash |

---

## Setup & Run

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python app.py
```

Open `http://localhost:5000` in your browser.

**Demo credentials (auto-seeded on first run):**

| Role      | Email                      | Password    |
|-----------|----------------------------|-------------|
| Admin     | admin@libraflow.com        | admin123    |
| Student   | student@libraflow.com      | student123  |

---

## Project Structure

```
LibraFlow/
├── app.py                          # Flask app factory + demo data seed
├── config.py                       # Configuration
├── models.py                       # SQLAlchemy models (User, Book, BookCopy, Loan, Reservation, Report)
├── requirements.txt
├── routes/
│   ├── auth.py                     # Login, logout, register
│   ├── books.py                    # Book search & availability API
│   ├── student.py                  # Student dashboard, borrow, reserve, history
│   └── admin.py                    # Admin panel, issue/return, reports, scan
├── templates/
│   ├── base.html
│   ├── login.html / register.html
│   ├── student/                    # dashboard, search, history, reservations
│   └── admin/                      # dashboard, books, loans, reservations, reports, scan, overdue
├── static/
│   ├── css/style.css
│   └── js/main.js
├── REQUIREMENTS_TRACEABILITY_MATRIX.md
└── Library_Management_UML_Submission/
    ├── 01_Use_Case_Diagrams/
    ├── 02_Class_Diagram/
    ├── 03_Sequence_Diagrams/
    └── 04_Source_Files/            # PlantUML source (.puml)
```

---

## UML Diagrams

All diagrams are in `Library_Management_UML_Submission/`:
- **Use Case Diagram** — Student & Admin actors with all use cases
- **Class Diagram** — Full OOP model: User, Student, Librarian, Book, BookCopy, Catalog, Loan, Reservation, Report
- **Sequence Diagram** — Book Reservation & Issue flow + Book Return & Overdue Report flow

See `REQUIREMENTS_TRACEABILITY_MATRIX.md` for full requirement-to-implementation mapping.
