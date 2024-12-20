"""empty message

Revision ID: a8606ffea47d
Revises: a111a794926f
Create Date: 2024-07-08 22:38:09.376528

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a8606ffea47d'
down_revision = 'a111a794926f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('visita_evento',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('evento_id', sa.Integer(), nullable=False),
    sa.Column('fecha_registro', sa.DateTime(), nullable=False),
    sa.Column('fecha_visita', sa.Date(), nullable=False),
    sa.Column('valoracion', sa.Integer(), nullable=False),
    sa.Column('reseña', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['evento_id'], ['evento.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['usuario.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('foto_visita_evento',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('visita_evento_id', sa.Integer(), nullable=False),
    sa.Column('data', sa.LargeBinary(), nullable=False),
    sa.Column('mimetype', sa.String(length=120), nullable=False),
    sa.Column('filename', sa.String(length=120), nullable=False),
    sa.ForeignKeyConstraint(['visita_evento_id'], ['visita_evento.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('foto_visita_evento')
    op.drop_table('visita_evento')
    # ### end Alembic commands ###
