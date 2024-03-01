"""empty message

Revision ID: 20c5280bebd9
Revises: f20c6109dcb8
Create Date: 2024-03-01 16:48:15.054242

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20c5280bebd9'
down_revision = 'f20c6109dcb8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('payinfo',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=50), nullable=False),
    sa.Column('book_id', sa.Integer(), nullable=False),
    sa.Column('transaction_id', sa.String(length=100), nullable=False),
    sa.ForeignKeyConstraint(['book_id'], ['book.id'], ),
    sa.ForeignKeyConstraint(['username'], ['user.username'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('payinfo')
    # ### end Alembic commands ###