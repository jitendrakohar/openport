"""empty message

Revision ID: 1095bc122dd6
Revises: 1f5354d0e38f
Create Date: 2014-12-06 17:44:37.716333

"""

# revision identifiers, used by Alembic.
revision = '1095bc122dd6'
down_revision = '1f5354d0e38f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('sessions', sa.Column('app_port', sa.Integer(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    #op.drop_column('sessions', 'app_port')
    pass
    ### end Alembic commands ###