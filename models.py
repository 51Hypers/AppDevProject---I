from datetime import datetime, timedelta

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, String,
                        Text)
from sqlalchemy.orm import Relationship
from sqlalchemy import CheckConstraint
from nit import db

class User(db.Model):
    __table_name__ = "user"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    t_register = Column(DateTime, default=datetime.utcnow)
    is_librarian = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    is_author = Column(Boolean, default=False)  # New column for indicating if user is an author

    user_books = db.relationship('UserBook', back_populates='user', lazy=True)

    def __init__(
            self, id: str = None, username: str = None, password: str = None, email: str = None, t_register: datetime = None, is_librarian: bool = None, is_admin: bool = None, is_author: bool = None
    ) -> None:
        self.id = id
        self.username = username
        self.password = password
        self.email = email
        self.t_register = t_register
        self.is_librarian = is_librarian
        self.is_admin = is_admin
        self.is_author = is_author
    def grant_librarian_access(self):
        self.is_librarian = True
        db.session.commit()
    
    def revoke_librarian_access(self):
        self.is_librarian = False
        db.session.commit()
        
class LibrarianRequest(db.Model):
    __tablename__ = "librarian_request"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(50), nullable=False)

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password = password

class Book(db.Model):
    __table_name__ = "book"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    author = Column(String(100), nullable=False)
    section_id = Column(Integer, ForeignKey('section.id'), nullable=False)
    price = Column(Integer)  # Assuming price is an integer

    def __init__(
            self, id: int = None, name: str = None, content: str = None, author: str = None, section_id: int = None, price: int = None
    ) -> None:
        self.id = id
        self.name = name
        self.content = content
        self.author = author
        self.section_id = section_id
        self.price = price

    user_books = db.relationship('UserBook', back_populates='book', lazy=True)



class Section(db.Model):
    __tablename__ = "section"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    desc = Column(Text, nullable=True)

    books = db.relationship('Book', backref='section', lazy=True)

    def __init__(
            self, id: int = None, name: str = None, desc: str = None
    ) -> None:
        self.id = id
        self.name = name
        self.desc = desc

class UserBook(db.Model):
    __tablename__ = "userbook"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    book_id = Column(Integer, ForeignKey('book.id'), nullable=False)
    t_request = Column(DateTime, default=datetime.utcnow, nullable=False)
    t_return = Column(DateTime, nullable=True)
    t_deadline = Column(DateTime, nullable=True)
    is_approved = Column(Boolean, default=False)
    is_rejected = Column(Boolean, default=False)
    is_revoked = Column(Boolean, default=False)  # New column for revoking access

    def __init__(
            self, id: int = None, user_id: int = None, book_id: int = None, t_request: datetime = None, t_return: datetime = None, is_approved: bool = None, is_rejected: bool = None, is_revoked: bool = None
    ) -> None:
        self.id = id
        self.user_id = user_id
        self.book_id = book_id
        self.t_request = t_request
        self.t_return = t_return
        self.is_approved = is_approved
        self.is_rejected = is_rejected
        self.is_revoked = is_revoked

    def is_returned(self):
        return self.t_return is not None
    
    def approve_book_request(self):
        self.is_approved = True
        db.session.commit()
    
    def reject_book_request(self):
        self.is_rejected = True
        db.session.commit()
    
    def approve_book_request(self):
        self.is_approved = True
        self.t_deadline = datetime.utcnow() + timedelta(days=14)
        db.session.commit()
    
    user = db.relationship('User', back_populates='user_books')
    book = db.relationship('Book', back_populates='user_books')

class Feedback(db.Model):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    book_id = Column(Integer, ForeignKey('book.id'), nullable=False)
    rating = Column(Integer, nullable=False)
    feedback_text = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 5', name='check_rating'),
    )

    def __init__(
            self, id: int = None, user_id: int = None, book_id: int = None, rating: int = None, feedback_text: str = None
    ) -> None:
        self.id = id
        self.user_id = user_id
        self.book_id = book_id
        self.rating = rating
        self.feedback_text = feedback_text

    user = db.relationship('User')
    book = db.relationship('Book')


class PayInfo(db.Model):
    __tablename__ = "payinfo"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), ForeignKey('user.username'), nullable=False)
    book_id = Column(Integer, ForeignKey('book.id'), nullable=False)
    transaction_id = Column(String(100), nullable=False)

    def __init__(
            self, id: int = None, username: str = None, book_id: int = None, transaction_id: str = None
    ) -> None:
        self.id = id
        self.username = username
        self.book_id = book_id
        self.transaction_id = transaction_id

    user = db.relationship('User', backref='payinfos')
    book = db.relationship('Book', backref='payinfos')
