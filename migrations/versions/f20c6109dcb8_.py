"""empty message

Revision ID: f20c6109dcb8
Revises: 2fa484cb6546
Create Date: 2024-02-23 19:40:03.327556

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f20c6109dcb8'
down_revision = '2fa484cb6546'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('userbook', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_revoked', sa.Boolean(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('userbook', schema=None) as batch_op:
        batch_op.drop_column('is_revoked')

    # ### end Alembic commands ###
