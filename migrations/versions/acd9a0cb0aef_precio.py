"""Precio

Revision ID: acd9a0cb0aef
Revises: 8331111a9a70
Create Date: 2024-06-24 14:33:29.063597

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'acd9a0cb0aef'
down_revision = '8331111a9a70'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('actividad_turistica', schema=None) as batch_op:
        batch_op.drop_column('precio_referencial')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('actividad_turistica', schema=None) as batch_op:
        batch_op.add_column(sa.Column('precio_referencial', sa.VARCHAR(length=100), autoincrement=False, nullable=True))

    # ### end Alembic commands ###
