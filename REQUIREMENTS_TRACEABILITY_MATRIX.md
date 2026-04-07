# Requirements Traceability Matrix — LibraFlow

**Project**: LibraFlow – Library Book Management System  
**Team**: Jeel Chauhan | Arayan Khanani | Pavithra Parameswaran | Krishna Akula  
**Generated**: 2026-04-07

---

## Functional Requirements

| Req ID  | Requirement Description                        | Priority | Actor            | Use Case Diagram         | Class Diagram                        | Sequence Diagram                    | Source Module              | Status      |
|---------|------------------------------------------------|----------|------------------|--------------------------|--------------------------------------|-------------------------------------|----------------------------|-------------|
| FR-01   | User login with email and password             | High     | Student, Admin   | UC1, AC1                 | User.login(), LibraryManagementSystem.login() | Book Reservation Flow (auth step)  | routes/auth.py             | Implemented |
| FR-02   | Student logout                                 | High     | Student          | UC1 (extend)             | User.logout()                        | —                                   | routes/auth.py             | Implemented |
| FR-03   | Student search books by title/author/category  | High     | Student          | UC2                      | Catalog.searchByTitle/Author/Category(), Book | Book Reservation Flow (search step) | routes/books.py           | Implemented |
| FR-04   | Student view borrowing history                 | Medium   | Student          | UC3                      | Student.viewBorrowingHistory(), Loan | —                                   | routes/student.py          | Implemented |
| FR-05   | Student view user dashboard                    | Medium   | Student          | UC4                      | Student, Loan, Reservation           | —                                   | routes/student.py          | Implemented |
| FR-06   | Student borrow/issue book                      | High     | Student          | UC5 (includes UC7)       | Student, Loan, BookCopy              | Book Reservation & Issue Flow       | routes/student.py          | Implemented |
| FR-07   | Student return book                            | High     | Student          | UC6                      | Student, Loan.markReturned()         | Book Return Flow                    | routes/student.py          | Implemented |
| FR-08   | Check book availability                        | High     | Student, Admin   | UC7                      | BookCopy.isAvailable(), LibraryManagementSystem.checkAvailability() | Book Reservation Flow (availability check) | routes/books.py | Implemented |
| FR-09   | Student reserve book                           | High     | Student          | UC8 (includes UC7)       | Student.reserveBook(), Reservation.create(), BookCopy | Book Reservation Flow (reservation step) | routes/student.py | Implemented |
| FR-10   | Admin add books to catalog                     | High     | Admin/Librarian  | AC2                      | Librarian.addBook(), Book, BookCopy, Catalog | —                                | routes/admin.py            | Implemented |
| FR-11   | Admin manage books (edit/delete)               | High     | Admin/Librarian  | AC3                      | Librarian.manageBook(), Book, BookCopy | —                                  | routes/admin.py            | Implemented |
| FR-12   | Admin track overdue books                      | High     | Admin/Librarian  | AC4                      | LibraryManagementSystem.trackOverdueBooks(), Loan.isOverdue() | Overdue Check Flow | routes/admin.py        | Implemented |
| FR-13   | Admin generate reports                         | Medium   | Admin/Librarian  | AC5                      | Librarian.generateReport(), Report.generate() | Report Generation Flow            | routes/admin.py            | Implemented |
| FR-14   | Admin manage admin panel / dashboard           | Medium   | Admin/Librarian  | AC6                      | LibraryManagementSystem, Librarian   | —                                   | routes/admin.py            | Implemented |
| FR-15   | Admin scan barcode                             | Medium   | Admin/Librarian  | AC7 (extends AC8, AC9)   | BookCopy.barcode                     | —                                   | routes/admin.py            | Implemented |
| FR-16   | Admin issue book to student                    | High     | Admin/Librarian  | AC8 (extended by AC7)    | Librarian, Loan, BookCopy            | Book Reservation & Issue Flow       | routes/admin.py            | Implemented |
| FR-17   | Admin accept returned book                     | High     | Admin/Librarian  | AC9 (extended by AC7)    | Librarian, Loan.markReturned(), BookCopy | Book Return Flow               | routes/admin.py            | Implemented |
| FR-18   | Admin approve reservation requests             | High     | Admin/Librarian  | AC10                     | Librarian.approveRequest(), Reservation | Book Reservation Flow (approve step) | routes/admin.py         | Implemented |

---

## Non-Functional Requirements

| Req ID  | Requirement Description                        | Category        | Design Decision                                  | Status      |
|---------|------------------------------------------------|-----------------|--------------------------------------------------|-------------|
| NFR-01  | Web-based accessible system                    | Accessibility   | Flask web server, browser-based UI               | Implemented |
| NFR-02  | Real-time book availability                    | Performance     | DB-level status field on BookCopy, queried live  | Implemented |
| NFR-03  | User-friendly interface                        | Usability       | Responsive HTML/CSS UI, role-based dashboards    | Implemented |
| NFR-04  | Secure authentication                          | Security        | Password hashing (werkzeug), Flask session       | Implemented |
| NFR-05  | Data persistence                               | Reliability     | SQLite via SQLAlchemy ORM                        | Implemented |
| NFR-06  | Role-based access control                      | Security        | Role field on User, route-level decorators       | Implemented |
| NFR-07  | Barcode scanning / smart features              | Functionality   | Barcode field on BookCopy, scan-by-barcode route | Implemented |

---

## Module-to-Class Mapping

| Module                    | Classes Covered                                      |
|---------------------------|------------------------------------------------------|
| routes/auth.py            | User (login/logout)                                  |
| routes/books.py           | Book, BookCopy, Catalog                              |
| routes/student.py         | Student, Loan, Reservation                           |
| routes/admin.py           | Librarian, Loan, Reservation, Report, BookCopy       |
| models.py                 | All: User, Book, BookCopy, Loan, Reservation, Report |

---

## Use Case to Sequence Diagram Traceability

| Use Case                   | Sequence Flow Covered                                  |
|----------------------------|--------------------------------------------------------|
| UC2 + UC8 + AC8            | Book Reservation and Issue Flow (full flow)            |
| UC6 + AC9 + AC4 + AC5      | Book Return, Overdue Check, and Report Flow            |
| UC1 / AC1                  | Authentication (pre-condition for all flows)           |

---

*This matrix was generated from analysis of the PlantUML source files in `04_Source_Files/` and the project requirements document (`software-engineering.pdf`).*
