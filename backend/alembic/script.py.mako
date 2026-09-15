"""${template_name}
${sqlalchemy_dialect}

${timestamp}

${revision}

${down_revision}

"""
from alembic import op
import sqlalchemy as sa

revision = '${revision}'
down_revision = '${down_revision}'
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
