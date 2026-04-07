from flask import Blueprint, jsonify, request
from flask_login import login_required
from models import Book, BookCopy

books_bp = Blueprint('books', __name__, url_prefix='/api/books')


@books_bp.route('/search')
@login_required
def search():
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')

    if not query:
        books = Book.query.order_by(Book.title).limit(50).all()
    elif search_type == 'title':
        books = Book.query.filter(Book.title.ilike(f'%{query}%')).all()
    elif search_type == 'author':
        books = Book.query.filter(Book.author.ilike(f'%{query}%')).all()
    elif search_type == 'category':
        books = Book.query.filter(Book.category.ilike(f'%{query}%')).all()
    else:
        books = Book.query.filter(
            (Book.title.ilike(f'%{query}%')) |
            (Book.author.ilike(f'%{query}%')) |
            (Book.category.ilike(f'%{query}%'))
        ).all()

    return jsonify([b.get_details() for b in books])


@books_bp.route('/<int:book_id>/availability')
@login_required
def availability(book_id):
    book = Book.query.get_or_404(book_id)
    copies = book.copies.all()
    return jsonify({
        'book_id': book.id,
        'title': book.title,
        'available': book.available_copies_count(),
        'total': len(copies),
        'copies': [
            {
                'id': c.id,
                'copy_code': c.copy_code,
                'barcode': c.barcode,
                'status': c.status,
                'shelf_location': c.shelf_location
            } for c in copies
        ]
    })


@books_bp.route('/barcode/<barcode>')
@login_required
def by_barcode(barcode):
    copy = BookCopy.query.filter_by(barcode=barcode).first_or_404()
    return jsonify({
        'copy_id': copy.id,
        'copy_code': copy.copy_code,
        'barcode': copy.barcode,
        'status': copy.status,
        'shelf_location': copy.shelf_location,
        'book': copy.book.get_details()
    })
