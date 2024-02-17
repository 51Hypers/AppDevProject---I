from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired

class SearchBooksForm(FlaskForm):
    query = StringField('Search', validators=[DataRequired()])
    filter_type = SelectField('Filter By', choices=[('section', 'Section'), ('author', 'Author'), ('all', 'All')], default='all')
    submit = SubmitField('Search')
