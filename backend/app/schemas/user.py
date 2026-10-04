"""Pydantic request/response schemas - user.py (FR-1)"""

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    nama: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def password_maks_72_byte(cls, value: str) -> str:
        # batas bcrypt: byte setelah ke-72 diabaikan, jadi tolak daripada diam-diam dipotong
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password maksimal 72 byte")
        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_user: int
    nama: str
    email: EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
