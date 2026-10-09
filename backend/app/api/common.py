"""Helper bersama untuk router v1: kepemilikan baris dan validasi ulang hasil PATCH."""

from typing import Any, TypeVar

from fastapi import HTTPException, status
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.user import User

ModelT = TypeVar("ModelT", bound=Base)
SchemaT = TypeVar("SchemaT", bound=BaseModel)


def ambil_milik_user(db: Session, model: type[ModelT], id_baris: int, user: User, detail: str) -> ModelT:
    """Ambil baris milik `user` berdasarkan primary key, atau 404.

    Baris milik user lain juga dijawab 404 (bukan 403) supaya keberadaannya tidak bocor.
    Hanya untuk model yang punya kolom `id_user`.
    """
    baris = db.get(model, id_baris)
    if baris is None or baris.id_user != user.id_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    return baris


def validasi_gabungan(schema: type[SchemaT], baris: Any, perubahan: BaseModel) -> SchemaT:
    """Gabungkan nilai tersimpan dengan field yang dikirim di PATCH, lalu validasi ulang dengan
    schema Create. Hasil gabungan yang tidak valid dijawab 422 seperti body yang tidak valid."""
    data = {field: getattr(baris, field) for field in schema.model_fields}
    data.update(perubahan.model_dump(exclude_unset=True))
    try:
        return schema.model_validate(data)
    except ValidationError as e:
        errors = e.errors(include_url=False, include_context=False)
        raise RequestValidationError([{**err, "loc": ("body", *err["loc"])} for err in errors]) from e
