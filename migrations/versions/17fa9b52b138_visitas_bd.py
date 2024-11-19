"""Visitas bd

Revision ID: 17fa9b52b138
Revises: f653bd4c66f8
Create Date: 2024-07-01 20:36:32.507694

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '17fa9b52b138'
down_revision = 'f653bd4c66f8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('foto_visita', schema=None) as batch_op:
        batch_op.add_column(sa.Column('data', sa.LargeBinary(), nullable=False))
        batch_op.add_column(sa.Column('mimetype', sa.String(length=120), nullable=False))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('foto_visita', schema=None) as batch_op:
        batch_op.drop_column('mimetype')
        batch_op.drop_column('data')

    # ### end Alembic commands ###