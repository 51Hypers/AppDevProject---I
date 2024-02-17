import datetime
from io import BytesIO
import pandas as pd
from matplotlib import pyplot as plt
from nit import app, db
from flask import render_template, render_template_string, request, redirect, send_file, url_for, session, flash
from models import User, Section, Book, UserBook
from sqlalchemy.orm.exc import NoResultFound


# DECORATORS
from flask import redirect, url_for, session
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# <-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------> #


# INDEX VIEWS
@app.route('/')
def index():
    return render_template('home_page/index.html')

from flask import session  # Import session

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('home_page/login.html')
    else:
        username = request.form['username']
        password = request.form['password']

        user = db.session.query(User).filter(User.username == username, User.password == password).first()
        if user:
            # Store the user ID in session
            session['user_id'] = user.id

            if user.is_admin:
                return redirect(url_for('admin_dashboard'))  # Ensure the URL is correct
            elif user.is_librarian:
                return redirect(url_for('librarian_dashboard'))  # Ensure the URL is correct
            else:
                return redirect(url_for('user_dashboard'))  # Ensure the URL is correct
        else:
            flash('User does not exist or invalid credentials', 'error')  # Corrected the flow here
            return redirect(url_for('login'))


@app.route('/sign_up', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('home_page/sign_up.html')
    else:
        username_exists = db.session.query(User).filter(User.username == request.form['username']).first()
        email_exists = db.session.query(User).filter(User.email == request.form['email']).first()

        if username_exists:
            return render_template('home_page/sign_up.html', error='Username already in use')
        elif email_exists:
            return render_template('home_page/sign_up.html', error='Email already in use')
        else:
            user = User(
                username=request.form['username'],
                email=request.form['email'],
                password=request.form['password'],
            )
            db.session.add(user)
            db.session.commit()
            return redirect(url_for('user_dashboard'))  


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


# <-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------> #


# BOOKS VIEWS
@app.route('/dashboards/user_dashboard')
def user_dashboard():
    return render_template('dashboards/user_dashboard.html')


@app.route('/books', methods=['GET'])
def list_all_books():
    books = Book.query.order_by('name').all()
    sections = db.session.query(Section).all()
    authors = db.session.query(Book).distinct(Book.author).all()
    return render_template(
        'books/books.html', books=books, sections=sections, authors=authors
    )


@app.route('/books/<filter>', methods=['GET'])
def list_books_by_filter(filter: str):
    section_id = request.args.get('section_id')
    author = request.args.get('author')
    if filter == 'section':
        section = db.session.query(Section).filter(Section.id == section_id).one()
        books = db.session.query(Book).filter(Book.section_id == section_id).all()
    elif filter == 'author':
        books = db.session.query(Book).filter(Book.author == author).all()
    else:
        return render_template('404_template.html', error='Invalid Filter')

    return render_template(
        'books/books_filter.html', books=books, section=section, author=author
    )


@app.route('/books/view/<book_id>', methods=['GET'])
def view_book_details(book_id: int):
    book = db.session.query(Book).filter(Book.id == book_id).one()
    return render_template('books/book_view.html', book=book)


@app.route('/my_books', methods=['GET'])
def view_borrowed_books():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please login to view your books', 'error')
        return redirect(url_for('login'))

    borrowed_books = db.session.query(UserBook).filter_by(user_id=user_id, returned=False).all()
    return render_template('users/my_books.html', borrowed_books=borrowed_books)


@app.route('/books/request/<int:book_id>', methods=['POST', 'GET'])
def request_book(book_id):
    user_id = session.get('user_id')  # Assuming `current_user` keeps track of the logged-in user

    # Check if the user has already requested the maximum number of books
    active_requests = UserBook.query.filter_by(user_id=user_id, is_returned=False).count()
    if active_requests >= 5:
        flash('You have reached the maximum number of book requests.', 'error')
        return redirect(url_for('list_all_books'))

    # Check if the book is already requested and not returned
    book_request = UserBook.query.filter_by(book_id=book_id, user_id=user_id, is_returned=False).first()
    if book_request:
        flash('You have already requested this book.', 'error')
        return redirect(url_for('list_all_books'))

    # Create a new book request
    new_request = UserBook(user_id=user_id, book_id=book_id)
    db.session.add(new_request)
    db.session.commit()
 
    flash('Book request submitted successfully!', 'success')
    return render_template_string('<h1> Request Submission Successful!<h1>')


@app.route('/books/return/<int:user_book_id>', methods=['POST'])
@login_required
def return_book(user_book_id):
    user_book = UserBook.query.filter_by(id=user_book_id, user_id=session.get('user_id')).first()
    if not user_book:
        flash('Book return request is invalid.', 'error')
        return redirect(url_for('view_borrowed_books'))

    if user_book.is_returned():
        flash('This book has already been returned.', 'error')
    else:
        user_book.t_return = datetime.utcnow()
        db.session.commit()
        flash('Book returned successfully!', 'success')

    return redirect(url_for('view_borrowed_books'))


@app.route('/books/deadlines')
def view_borrowed_books_with_deadlines():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please login to view your books and deadlines', 'error')
        return redirect(url_for('login'))

    borrowed_books = db.session.query(UserBook, Book).join(Book, UserBook.book_id == Book.id).filter(UserBook.user_id == user_id, UserBook.t_return == None).all()

    books_with_deadlines = []
    for user_book, book in borrowed_books:
        # Calculate the deadline (14 days after the request by default)
        default_deadline = user_book.t_request + datetime.timedelta(days=14)
        deadline = user_book.due_date if user_book.due_date else default_deadline
        days_until_deadline = (deadline - datetime.utcnow()).days
        books_with_deadlines.append({
            'book': book,
            'deadline': deadline,
            'days_until_deadline': days_until_deadline
        })

    return render_template('users/books_with_deadlines.html', books_with_deadlines=books_with_deadlines)


@app.route('/requested_books')
def requested_books():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to view requested books.', 'error')
        return redirect(url_for('login'))

    # Query for books that the current user has requested and are awaiting approval
    requested_books = db.session.query(UserBook, Book).join(Book, UserBook.book_id == Book.id)\
                      .filter(UserBook.user_id == user_id, UserBook.is_approved == False, UserBook.is_rejected == False).all()

    return render_template('users/requested_books.html', requested_books=requested_books)


@app.route('/books/finished')
def view_finished_books():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please login to view your finished books', 'error')
        return redirect(url_for('login'))

    finished_books = db.session.query(UserBook, Book).join(Book, UserBook.book_id == Book.id).filter(UserBook.user_id == user_id, UserBook.t_return != None).all()

    return render_template('users/finished_books.html', finished_books=finished_books)


@app.route('/books/finished/by-section')
def view_finished_books_by_section():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please login to view your finished books by section', 'error')
        return redirect(url_for('login'))

    finished_books = db.session.query(UserBook, Book, Section).join(Book, UserBook.book_id == Book.id).join(Section, Book.section_id == Section.id).filter(UserBook.user_id == user_id, UserBook.t_return != None).all()
    
    # Organizing books by their sections
    books_by_section = {}
    for user_book, book, section in finished_books:
        if section.name not in books_by_section:
            books_by_section[section.name] = []
        books_by_section[section.name].append({'book': book, 'user_book': user_book})

    return render_template('users/finished_books_by_section.html', books_by_section=books_by_section)


@app.route('/user/stats')
def user_stats():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please login', 'error')
        return redirect(url_for('login'))  # Assuming there's a 'login' view to redirect to

    user_books = UserBook.query.filter(UserBook.user_id == user_id, UserBook.t_return != None).all()
    if not user_books:
        # If no books have been finished, return a message indicating no data is available
        return render_template_string("<h1>No User Data Available!</h1>")

    books = [Book.query.get(ub.book_id) for ub in user_books if ub.t_return is not None]

    # Prepare data for graphs
    if books:
        df = pd.DataFrame([{'section': book.section.name, 'return_month': ub.t_return.month} for ub, book in zip(user_books, books) if ub.t_return is not None])
        if not df.empty:
            month_counts = df['return_month'].value_counts().sort_index()
            section_counts = df['section'].value_counts()

            # Plotting
            fig, axs = plt.subplots(2, 1, figsize=(10, 10))

            # Monthly frequency
            axs[0].bar(month_counts.index, month_counts.values, color='skyblue')
            axs[0].set_title('Monthly Book Reading Frequency')
            axs[0].set_xlabel('Month')
            axs[0].set_ylabel('Books Read')

            # Section interest
            axs[1].pie(section_counts, labels=section_counts.index, autopct='%1.1f%%')
            axs[1].set_title('Interest in Sections')

            # Save plot to a bytes buffer
            buf = BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)

            return send_file(buf, mimetype='image/png')
    # If the DataFrame is empty (i.e., no books or no returned books), show a message
    return render_template_string("<h1>No User Data Available!</h1>")


# <-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------> #


# LIBRARIAN VIEWS
@app.route('/user', methods=['GET'])
def list_all_users():
    users = db.session.query(User).filter(User.is_librarian == False).filter(User.is_admin == False).all()
    return render_template('librarian/all_users.html', users=users)

@app.route('/users/<user_id>', methods=['GET'])
def view_user_detail(user_id: int):
    user = db.session.query(User).filter(User.id == user_id).one()
    unapproved_requests = db.session.query(UserBook).join(Book, Book.id == UserBook.book_id).filter(UserBook.user_id == user_id).filter(UserBook.is_approved == False).all()
    rejected_requests = db.session.query(UserBook).join(Book, Book.id == UserBook.book_id).filter(UserBook.user_id == user_id).filter(UserBook.is_rejected == True).all()
    returned_user_books = db.session.query(UserBook).join(Book, Book.id == UserBook.book_id).filter(UserBook.user_id == user_id).filter(UserBook.t_return is not None).all()
    unreturned_user_books = db.session.query(UserBook).join(Book, Book.id == UserBook.book_id).filter(UserBook.user_id == user_id).filter(UserBook.is_approved == True).filter(UserBook.t_return is None).all()

    return render_template(
        'librarian/user_detail.html', user=user, unapproved_requests=unapproved_requests, 
        returned_user_books=returned_user_books, unreturned_user_books=unreturned_user_books, rejected_requests=rejected_requests
    )

@app.route('/requests', methods=['GET'])
def list_all_requests():
    unapproved_requests = db.session.query(UserBook).join(Book, Book.id == UserBook.user_id).join(User, User.id == UserBook.user_id).filter(UserBook.is_approved == False).filter(UserBook.is_rejected == False).all()
    rejected_requests = db.session.query(UserBook).join(Book, Book.id == UserBook.user_id).join(User, User.id == UserBook.user_id).filter(UserBook.is_rejected == False).all()
    return render_template('librarian/requests.html', unapproved_requests=unapproved_requests, rejected_requests=rejected_requests)

@app.route('/stats')
def get_books_stats():
    if request.args.get('books'):
        userbooks = db.session.query(UserBook).join(Book).all()
    elif request.args.get('users'):
        userbooks = db.session.query(UserBook).join(User).all()
    else:
        return render_template('404_template.html', error='Invalid Stats Request')
    return render_template('librarian/book_stats.html', userbooks=userbooks)

@app.route('/request/<action>', methods=['POST'])
def approve_book_request(action: str):
    userbook_id = request.form['userbook_id']
    userbook: UserBook = db.session.query(UserBook).filter(UserBook.id == userbook_id).one()
    if action == 'approve':
        userbook.approve_book_request()
    else:
        userbook.reject_book_request()
    return redirect(url_for('requests'))

@app.route('/add-book', methods=['GET', 'POST'])
def add_book():
    if request.method == 'GET':
        return render_template('librarian/add_book.html')
    else:
        book = Book(
            name=request.form['name'],
            content=request.form['content'],
            author=request.form['author'],
            section_id=request.form['section_id']
        )
        db.session.add(book)
        db.session.commit()

        book: Book = db.session.query(Book).filter(Book.name == request.form['name']).one()
        return redirect(url_for(f'books/view/{book.id}'))

@app.route('/add-section', methods=['GET', 'POST'])
def add_section():
    if request.method == 'GET':
        return render_template('librarian/add_book.html')
    else:
        section = Section(
            name=request.form['name'],
            desc=request.form['desc']
        )
        db.session.add(section)
        db.session.commit()

        section: Section = db.session.query(Section).filter_by(Section.name == request.form['name'])
        return redirect(url_for(f'books/section?section_id={section.id}'))


# ADMIN VIEWS
@app.route('/admin/users', methods=['GET'])
def list_all_users_for_admin():
    users_query = db.session.query(User).filter(User.is_admin == False)
    if not request.args.get('show_librarians'):
        users_query = users_query.filter(User.is_librarian == False)
    return render_template('admin/all_users.html', users=users_query.all())

@app.route('/admin/grant_librarian', methods=['POST'])
def make_librarian_grant():
    user_id = request.form['user_id']
    user: User = db.session.query(User).filter(User.id == user_id).one()
    user.grant_librarian_access()
    return redirect(url_for('admin/users'))

@app.route('/admin/revoke_librarian', methods=['POST'])
def make_librarian_revoke():
    user_id = request.form['user_id']
    user: User = db.session.query(User).filter(User.id == user_id).one()
    user.revoke_librarian_access()
    return redirect(url_for('admin/users'))


# DASHBOARDS


if __name__ == "__main__":
    app.run(debug=True, port=8080)