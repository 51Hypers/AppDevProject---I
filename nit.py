from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from faker import Faker
import random
import os
app = Flask(__name__)
UPLOAD_FOLDER = 'static\pdfs'

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///library.db"
app.config["SECRET_KEY"] = "427a3ec270bc25fe4e143d65f43f3f72"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['UPLOAD_FOLDER'] = 'static\pdfs'

db = SQLAlchemy(app=app)
migrate = Migrate(app=app, db=db)

from models import Book, Section
fk = Faker()

pdf_folder = 'static\pdfs'
pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith('.pdf')]


@app.cli.command('populate')
def populate():
    for _ in range(8):
        section = Section(
            name=fk.word(),
            desc=fk.sentence()
        )
        print(f"Added section with {section.name}, {section.desc[1]}")
        db.session.add(section)
        db.session.commit()
        used_files = set()
        for _ in range(0, 12):
            pdf_file = random.choice(pdf_files)
            while pdf_file in used_files:
                pdf_file = random.choice(pdf_files)
            used_files.add(pdf_file)
            book = Book(
                name=fk.company(),
                content=os.path.join(pdf_folder, pdf_file),
                author=fk.name(),
                section_id=section.id,
                price=random.randint(100, 500)
            )
            db.session.add(book)
            db.session.commit()
            print(f"added book with {book.name}, {book.content}, {book.author}, {book.price}")
