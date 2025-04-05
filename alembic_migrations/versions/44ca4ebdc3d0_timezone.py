"""timezone

Revision ID: 44ca4ebdc3d0
Revises: 1e478bdc0e1a
Create Date: 2025-03-30 08:37:36.113115

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '44ca4ebdc3d0'
down_revision: Union[str, None] = '1e478bdc0e1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('timezone', sa.String(length=50), nullable=True, server_default='Europe/Moscow'))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'timezone')
    # ### end Alembic commands ###
