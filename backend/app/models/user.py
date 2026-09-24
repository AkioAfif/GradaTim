"""SQLAlchemy entities - user.py"""

from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "user"

    id_user: Mapped[int] = mapped_column(primary_key=True, index=True)
    nama: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password: Mapped[str] = mapped_column(String(255))  # hash, bukan plaintext

    goals: Mapped[list["Goal"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    time_constraints: Mapped[list["TimeConstraint"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    mood_questionnaires: Mapped[list["MoodQuestionnaire"]] = relationship(back_populates="user", cascade="all, delete-orphan")
