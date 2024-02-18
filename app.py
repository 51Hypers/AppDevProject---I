import datetime
from io import BytesIO
import pandas as pd
from matplotlib import pyplot as plt
from sqlalchemy import Null, or_
from nit import app, db
from flask import render_template, render_template_string, request, redirect, send_file, url_for, session, flash
from models import User, Section, Book, UserBook
from sqlalchemy.orm.exc import NoResultFound
from models import LibrarianRequest
from datetime import datetime, timedelta


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


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'GET':
        return render_template('admin_login.html')  # Admin login form
    else:
        password = request.form['password']
        if password == '1':  # Replace 'your_admin_password' with your actual admin password
            librarian_requests = LibrarianRequest.query.all()
            return render_template('admin_panel.html', librarian_requests=librarian_requests)
        else:
            return render_template('admin_login.html', error='Invalid password')

@app.route('/admin/action', methods=['POST'])
def admin_action():
    action = request.form['action']
    librarian_request_id = request.form['librarian_request_id']
    librarian_request = LibrarianRequest.query.get(librarian_request_id)

    if action == 'accept':
        librarian = User(
            username=librarian_request.username,
            email=librarian_request.email,
            password=librarian_request.password,
            is_librarian=True
        )
        db.session.add(librarian)
    db.session.delete(librarian_request)
    db.session.commit()

    librarian_requests = LibrarianRequest.query.all()
    return render_template('admin_panel.html', librarian_requests=librarian_requests)

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


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('home_page/signup.html')
    elif request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        if User.query.filter_by(username=username).first():
            return render_template('home_page/signup.html', error='Username already exists')
        if User.query.filter_by(email=email).first():
            return render_template('home_page/signup.html', error='Email already exists')

        if role == 'user':
            new_user = User(username=username, email=email, password=password, is_librarian=False)
            db.session.add(new_user)
        elif role == 'librarian':
            new_librarian_request = LibrarianRequest(username=username, email=email, password=password)
            db.session.add(new_librarian_request)

        db.session.commit()
        return redirect(url_for('login'))



@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


# <-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------> #


# BOOKS VIEWS
@app.route('/dashboards/user_dashboard')
def user_dashboard():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please login to view your dashboard.', 'error')
        return redirect(url_for('login'))

    borrowed_books = db.session.query(UserBook, Book).join(Book, UserBook.book_id == Book.id).filter(UserBook.user_id == user_id, UserBook.t_return == None, UserBook.is_approved == True).all()
    now = datetime.utcnow()
    books_revoked = False
    deadline_warning_issued = False

    for user_book, book in borrowed_books:
        if user_book.t_deadline and now > user_book.t_deadline:
            user_book.is_approved = False
            books_revoked = True
        elif user_book.t_deadline and user_book.t_deadline - now <= timedelta(days=1):
            deadline_warning_issued = True

    if books_revoked:
        db.session.commit()
        flash('Access to one or more overdue books has been revoked. Please return them as soon as possible.', 'warning')
    
    if deadline_warning_issued:
        flash('Warning: One or more of your borrowed books are due within the next day. Please return them on time to avoid losing access.', 'warning')

    return render_template('dashboards/user_dashboard.html', borrowed_books=borrowed_books)


@app.route('/books', methods=['GET'])
def list_all_books():
    books = Book.query.order_by('name').all()
    sections = db.session.query(Section).all()
    authors = db.session.query(Book).distinct(Book.author).all()
    return render_template(
        'books/books.html', books=books, sections=sections, authors=authors
    )


@app.route('/books/filter', methods=['GET'])
def list_books_by_filter():
    filter_type = request.args.get('filter_type', 'all')
    query = request.args.get('query', '')

    sections = Section.query.all()

    if filter_type == 'section':
        section_id = request.args.get('section_id')
        books = Book.query.filter(Book.section_id == section_id).all()
    elif filter_type == 'author':
        books = Book.query.filter(Book.author.ilike(f"%{query}%")).all()
    else:
        books = Book.query.filter(or_(Book.name.ilike(f"%{query}%"), Book.author.ilike(f"%{query}%"))).all()

    return render_template('books/books_filter.html', books=books, sections=sections, filter_type=filter_type, query=query)


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
 
    # flash('Book request submitted successfully!', 'success')
    return render_template_string('<h1> Request Submission Successful!<h1>')


@app.route('/books/deadlines')
def view_borrowed_books_with_deadlines():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please login to view your books and deadlines', 'error')
        return redirect(url_for('login'))

    borrowed_books = db.session.query(UserBook, Book) \
        .join(Book, UserBook.book_id == Book.id) \
        .filter(UserBook.user_id == user_id, UserBook.is_approved == True, UserBook.t_return == None) \
        .order_by(UserBook.t_deadline.asc()) \
        .all()

    books_with_deadlines = []
    for user_book, book in borrowed_books:
        # Ensure that there is a deadline date before attempting subtraction
        if user_book.t_deadline:
            days_until_deadline = (user_book.t_deadline - datetime.utcnow()).days
        else:
            # Handle case where t_deadline is None; you might set a default or skip
            # For example, using a default deadline of 14 days from now
            default_deadline = datetime.utcnow() + timedelta(days=14)
            days_until_deadline = (default_deadline - datetime.utcnow()).days

        books_with_deadlines.append({
            'book': book,
            'deadline': user_book.t_deadline or default_deadline,  # Use t_deadline if available, otherwise default
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
    requested_books = db.session.query(UserBook, Book).join(Book)\
                  .filter(UserBook.user_id == user_id, UserBook.is_approved == False, UserBook.is_rejected == False).all()
    print(requested_books)

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


@app.route('/books/return/<int:userbook_id>', methods=['POST'])
def return_book(userbook_id):
    userbook = db.session.query(UserBook).filter_by(id=userbook_id).first()
    if userbook:
        # Book is being returned now
        userbook.t_return = datetime.utcnow()
        
        # Check if the book is returned after the deadline
        if datetime.utcnow() > userbook.t_deadline:
            # Setting is_approved to False to indicate revoking borrowing privileges due to late return
            userbook.is_approved = False
            flash('Returned late. Borrowing privileges have been revoked.', 'error')
        else:
            flash('Book returned successfully.', 'success')
        db.session.commit()
    else:
        flash('Book return failed. Invalid request.', 'error')
    
    return redirect(url_for('view_borrowed_books_with_deadlines'))


# <-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------> #


# LIBRARIAN VIEWS
@app.route('/dashboards/librarian_dashboard')
def librarian_dashboard():
    borrowed_books = db.session.query(UserBook, Book, User).join(Book, UserBook.book_id == Book.id).join(User, UserBook.user_id == User.id).filter(UserBook.t_return == None, UserBook.is_approved == True, User.is_librarian == False, User.is_admin == False).all()
    now = datetime.utcnow()
    books_revoked = False
    deadline_warning_issued = False

    for user_book, book, user in borrowed_books:
        if user_book.t_deadline and now > user_book.t_deadline:
            user_book.is_approved = False
            books_revoked = True
        elif user_book.t_deadline and user_book.t_deadline - now <= timedelta(days=1):
            deadline_warning_issued = True

    if books_revoked:
        db.session.commit()
        flash('Access has been revoked for overdue books borrowed by users. Please ensure they are returned.', 'warning')
    
    if deadline_warning_issued:
        flash('Warning: Some users have borrowed books that are due within the next day. Please remind them to return on time.', 'warning')

    return render_template('dashboards/librarian_dashboard.html', borrowed_books=borrowed_books)


@app.route('/user', methods=['GET'])
def list_all_users():
    users = db.session.query(User).filter(User.is_librarian == False).filter(User.is_admin == False).all()
    return render_template('librarian/all_users.html', users=users)


@app.route('/users/details', methods=['GET'])
def view_users_details():
    users = User.query.filter(User.is_librarian == False, User.is_admin == False).all()
    if not users:
        return render_template('librarian/user_details.html', message="There are no active users registered.")

    for user in users:
        user.unapproved_requests = UserBook.query.filter_by(user_id=user.id, is_approved=False, is_rejected=False).all()
        user.approved_requests = UserBook.query.filter_by(user_id=user.id, is_approved=True).all()
        user.rejected_requests = UserBook.query.filter_by(user_id=user.id, is_rejected=True).all()
        user.returned_books = UserBook.query.filter(UserBook.user_id == user.id, UserBook.t_return.isnot(None)).all()
        user.unreturned_books = UserBook.query.filter_by(user_id=user.id, is_approved=True, t_return=None).all()

    return render_template('librarian/user_details.html', users=users)


@app.route('/requests', methods=['GET'])
def list_all_requests():
    unapproved_requests = db.session.query(UserBook).join(Book, Book.id == UserBook.book_id).join(User, User.id == UserBook.user_id).filter(UserBook.is_approved == False, UserBook.is_rejected == False).all()
    rejected_requests = db.session.query(UserBook).join(Book, Book.id == UserBook.book_id).join(User, User.id == UserBook.user_id).filter(UserBook.is_rejected == True).all()
    return render_template('librarian/requests.html', unapproved_requests=unapproved_requests, rejected_requests=rejected_requests)

from flask import render_template

from flask import render_template

from flask import render_template

@app.route('/stats')
def get_books_stats():
    requested_books = UserBook.query.filter_by(is_approved=False, is_rejected=False).all()
    borrowed_books = UserBook.query.filter_by(is_approved=True, is_returned=False).all()
    all_books = Book.query.all()

    return render_template('librarian/book_stats.html', requested_books=requested_books, borrowed_books=borrowed_books, all_books=all_books, Book=Book)




@app.route('/request/<action>', methods=['POST'])
def approve_book_request(action: str):
    userbook_id = request.form['userbook_id']
    userbook: UserBook = db.session.query(UserBook).filter(UserBook.id == userbook_id).one()
    if action == 'approve':
        userbook.approve_book_request()
    else:
        userbook.reject_book_request()
    return redirect(url_for('list_all_requests'))

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


# <-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------> #


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