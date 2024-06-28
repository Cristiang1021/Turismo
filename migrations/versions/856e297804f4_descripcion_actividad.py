"""Descripcion actividad

Revision ID: 856e297804f4
Revises: d49bac861c98
Create Date: 2024-06-24 13:53:35.188722

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '856e297804f4'
down_revision = 'd49bac861c98'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('actividad_recomendada',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('actividad_id', sa.Integer(), nullable=False),
    sa.Column('motivo', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['actividad_id'], ['actividad_turistica.id'], ),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('actividad_turistica', schema=None) as batch_op:
        batch_op.add_column(sa.Column('descripcion', sa.Text(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('actividad_turistica', schema=None) as batch_op:
        batch_op.drop_column('descripcion')

    op.drop_table('actividad_recomendada')
    # ### end Alembic commands ###
