"""SQLAlchemy entities - time_constraint.py"""

from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TimeConstraint(Base):
    __tablename__ = "time_constraint"

    id_constraint: Mapped[int] = mapped_column(primary_key=True, index=True)
