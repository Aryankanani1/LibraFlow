"""
Run this script once to populate the database with real-world books.
Usage: python seed_books.py
"""
from app import create_app
from models import db, Book, BookCopy

BOOKS = [
    # Programming
    ("978-0-13-468599-1", "Clean Code",                          "Robert C. Martin",      "Programming",        "Prentice Hall",    3),
    ("978-0-13-235088-4", "The Pragmatic Programmer",            "David Thomas",          "Programming",        "Addison-Wesley",   2),
    ("978-0-13-110362-7", "The C Programming Language",          "Brian Kernighan",       "Programming",        "Prentice Hall",    2),
    ("978-0-13-597022-4", "Design Patterns",                     "Gang of Four",          "Programming",        "Addison-Wesley",   2),
    ("978-0-13-235428-8", "Head First Design Patterns",          "Eric Freeman",          "Programming",        "O'Reilly",         2),
    ("978-0-13-486809-7", "Refactoring",                         "Martin Fowler",         "Programming",        "Addison-Wesley",   2),
    ("978-0-13-703769-0", "Working Effectively with Legacy Code","Michael Feathers",      "Programming",        "Prentice Hall",    1),
    ("978-1-49-195016-0", "Flask Web Development",               "Miguel Grinberg",       "Web Development",    "O'Reilly",         3),
    ("978-1-491-91205-8", "Learning Python",                     "Mark Lutz",             "Programming",        "O'Reilly",         3),
    ("978-1-491-94600-8", "Python Cookbook",                     "David Beazley",         "Programming",        "O'Reilly",         2),
    ("978-1-491-95037-1", "Fluent Python",                       "Luciano Ramalho",       "Programming",        "O'Reilly",         2),
    ("978-1-491-91205-9", "Python for Data Analysis",            "Wes McKinney",          "Data Science",       "O'Reilly",         2),
    ("978-0-596-51774-8", "JavaScript: The Good Parts",          "Douglas Crockford",     "Web Development",    "O'Reilly",         2),
    ("978-1-491-95202-3", "You Don't Know JS",                   "Kyle Simpson",          "Web Development",    "O'Reilly",         2),
    ("978-1-491-92706-9", "Learning JavaScript Design Patterns", "Addy Osmani",           "Web Development",    "O'Reilly",         2),
    ("978-1-617-29209-4", "React in Action",                     "Mark Tielens Thomas",   "Web Development",    "Manning",          2),
    ("978-1-617-29441-8", "Node.js in Action",                   "Alex Young",            "Web Development",    "Manning",          2),

    # Algorithms & Data Structures
    ("978-0-07-352332-4", "Introduction to Algorithms",          "Thomas Cormen",         "Algorithms",         "MIT Press",        2),
    ("978-0-13-276643-2", "Algorithms",                          "Robert Sedgewick",      "Algorithms",         "Addison-Wesley",   2),
    ("978-0-13-110362-8", "Data Structures and Algorithms",      "Alfred Aho",            "Algorithms",         "Addison-Wesley",   2),
    ("978-0-262-03384-8", "The Algorithm Design Manual",         "Steven Skiena",         "Algorithms",         "Springer",         1),
    ("978-0-13-211620-2", "Cracking the Coding Interview",       "Gayle McDowell",        "Algorithms",         "CareerCup",        3),

    # Software Engineering
    ("978-0-201-63361-0", "The Mythical Man-Month",              "Frederick Brooks",      "Software Engineering","Addison-Wesley",  2),
    ("978-0-13-235088-5", "Code Complete",                       "Steve McConnell",       "Software Engineering","Microsoft Press", 2),
    ("978-0-13-468599-2", "A Philosophy of Software Design",     "John Ousterhout",       "Software Engineering","Yaknyam Press",   2),
    ("978-0-13-597022-5", "Software Engineering",                "Ian Sommerville",       "Software Engineering","Pearson",         3),
    ("978-0-201-83595-3", "The Clean Coder",                     "Robert C. Martin",      "Software Engineering","Prentice Hall",   2),
    ("978-0-13-235088-6", "Clean Architecture",                  "Robert C. Martin",      "Software Engineering","Prentice Hall",   2),
    ("978-0-321-12521-7", "Domain-Driven Design",                "Eric Evans",            "Software Engineering","Addison-Wesley",  1),
    ("978-1-492-05220-3", "Fundamentals of Software Architecture","Mark Richards",        "Software Engineering","O'Reilly",        2),

    # Databases
    ("978-1-449-37216-0", "Learning MySQL",                      "Seyed Tahaghoghi",      "Databases",          "O'Reilly",         2),
    ("978-1-491-91796-1", "SQL Cookbook",                        "Anthony Molinaro",      "Databases",          "O'Reilly",         2),
    ("978-1-449-34551-5", "MongoDB: The Definitive Guide",       "Kristina Chodorow",     "Databases",          "O'Reilly",         2),
    ("978-0-13-235088-7", "Database System Concepts",            "Abraham Silberschatz",  "Databases",          "McGraw-Hill",      3),
    ("978-1-449-34022-0", "Redis in Action",                     "Josiah Carlson",        "Databases",          "Manning",          1),

    # Operating Systems & Networks
    ("978-0-13-359162-0", "Operating System Concepts",           "Abraham Silberschatz",  "Operating Systems",  "Wiley",            3),
    ("978-0-13-600338-8", "Modern Operating Systems",            "Andrew Tanenbaum",      "Operating Systems",  "Pearson",          2),
    ("978-0-13-211646-2", "Computer Networks",                   "Andrew Tanenbaum",      "Networking",         "Pearson",          2),
    ("978-0-07-352332-5", "Computer Networking: A Top-Down Approach","James Kurose",      "Networking",         "Pearson",          2),
    ("978-0-13-235088-8", "Unix Network Programming",            "W. Richard Stevens",    "Networking",         "Prentice Hall",    1),

    # Cybersecurity
    ("978-1-492-05617-1", "Hacking: The Art of Exploitation",    "Jon Erickson",          "Cybersecurity",      "No Starch Press",  2),
    ("978-1-593-27892-7", "The Web Application Hacker's Handbook","Dafydd Stuttard",      "Cybersecurity",      "Wiley",            2),
    ("978-1-449-35573-6", "Cybersecurity and Cyberwar",          "P.W. Singer",           "Cybersecurity",      "Oxford Press",     2),
    ("978-1-492-09774-8", "Threat Modeling",                     "Adam Shostack",         "Cybersecurity",      "Wiley",            1),

    # Machine Learning & AI
    ("978-0-262-03384-9", "Deep Learning",                       "Ian Goodfellow",        "Machine Learning",   "MIT Press",        2),
    ("978-1-491-91205-0", "Hands-On Machine Learning",           "Aurélien Géron",        "Machine Learning",   "O'Reilly",         3),
    ("978-1-617-29435-7", "Deep Learning with Python",           "François Chollet",      "Machine Learning",   "Manning",          2),
    ("978-1-491-96229-9", "Natural Language Processing with Python","Steven Bird",        "Machine Learning",   "O'Reilly",         2),
    ("978-0-262-03512-5", "Artificial Intelligence: A Modern Approach","Stuart Russell", "Machine Learning",   "Pearson",          2),
    ("978-1-491-91205-1", "Python Machine Learning",             "Sebastian Raschka",     "Machine Learning",   "Packt",            2),

    # Mathematics for CS
    ("978-0-262-53219-0", "Mathematics for Computer Science",    "Eric Lehman",           "Mathematics",        "MIT Press",        2),
    ("978-0-13-197023-2", "Discrete Mathematics",                "Kenneth Rosen",         "Mathematics",        "McGraw-Hill",      3),
    ("978-0-13-110362-9", "Linear Algebra and Its Applications", "Gilbert Strang",        "Mathematics",        "Wellesley",        2),
    ("978-0-201-55802-9", "Concrete Mathematics",                "Ronald Graham",         "Mathematics",        "Addison-Wesley",   1),

    # Cloud & DevOps
    ("978-1-492-03495-7", "Kubernetes: Up and Running",          "Brendan Burns",         "DevOps",             "O'Reilly",         2),
    ("978-1-491-91035-1", "Docker: Up and Running",              "Sean Kane",             "DevOps",             "O'Reilly",         2),
    ("978-1-492-07827-3", "Terraform: Up and Running",           "Yevgeniy Brikman",      "DevOps",             "O'Reilly",         2),
    ("978-1-491-92701-4", "The DevOps Handbook",                 "Gene Kim",              "DevOps",             "IT Revolution",    2),
    ("978-0-13-235088-9", "Site Reliability Engineering",        "Niall Murphy",          "DevOps",             "O'Reilly",         2),

    # Classic CS
    ("978-0-201-89685-5", "The Art of Computer Programming Vol.1","Donald Knuth",         "Computer Science",   "Addison-Wesley",   1),
    ("978-0-13-110362-0", "Structure and Interpretation of Programs","Harold Abelson",    "Computer Science",   "MIT Press",        2),
    ("978-0-262-13472-9", "Compilers: Principles, Techniques",   "Alfred Aho",            "Computer Science",   "Addison-Wesley",   2),
    ("978-0-13-597022-6", "Computer Organization and Design",    "David Patterson",       "Computer Science",   "Morgan Kaufmann",  2),
]


def seed():
    app = create_app()
    with app.app_context():
        added = 0
        skipped = 0
        for isbn, title, author, category, publisher, copies in BOOKS:
            if Book.query.filter_by(isbn=isbn).first():
                skipped += 1
                continue
            book = Book(isbn=isbn, title=title, author=author,
                        category=category, publisher=publisher)
            db.session.add(book)
            db.session.flush()
            for i in range(copies):
                copy = BookCopy(
                    copy_code=f'{isbn}-{i+1:03d}',
                    barcode=f'BC{isbn.replace("-","")}{i+1:03d}',
                    status='available',
                    shelf_location=f'{category[:2].upper()}-{i+1}',
                    book_id=book.id
                )
                db.session.add(copy)
            added += 1

        db.session.commit()
        print(f"Done! Added {added} books, skipped {skipped} (already exist).")
        print(f"Total books in DB: {Book.query.count()}")
        print(f"Total copies in DB: {BookCopy.query.count()}")


if __name__ == '__main__':
    seed()
