"""SQLAlchemy entities - milestone.py"""

from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Milestone(Base):
    __tablename__ = "milestone"

    id_milestone: Mapped[int] = mapped_column(primary_key=True, index=True)
