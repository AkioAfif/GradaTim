"""Fixture bersama: DB SQLite in-memory per tes, TestClient, user login, dan pengaman LLM."""

import itertools
from datetime import date

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registrasi semua tabel ke Base.metadata)
from app.core import waktu
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services import ai_service

HARI_INI_TES = date(2026, 10, 5)  # Senin

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


@event.listens_for(engine, "connect")
def _aktifkan_foreign_key(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def _skema_baru():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _bcrypt_cepat(monkeypatch):
    """Cost bcrypt minimum di tes saja (default 12 → ~0,2 detik per hash); kode produksi tidak berubah."""
    gensalt_asli = bcrypt.gensalt
    monkeypatch.setattr(bcrypt, "gensalt", lambda rounds=4, prefix=b"2b": gensalt_asli(rounds, prefix))


@pytest.fixture(autouse=True)
def _blokir_llm(monkeypatch):
    """Tidak ada tes yang boleh memanggil LLM sungguhan. Tes dekomposisi menimpa mock ini."""

    def _dilarang(*args, **kwargs):
        raise AssertionError("LLM tidak boleh dipanggil di tes")

    monkeypatch.setattr(ai_service, "decompose_goal", _dilarang)


@pytest.fixture
def hari_ini_beku(monkeypatch) -> date:
    """Bekukan `waktu.hari_ini()` ke Senin 5 Oktober 2026."""
    monkeypatch.setattr(waktu, "hari_ini", lambda: HARI_INI_TES)
    return HARI_INI_TES


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    def _get_db_tes():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_db_tes
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


_nomor_user = itertools.count(1)


@pytest.fixture
def auth_headers(client):
    """Factory: daftar + login user baru, kembalikan header Authorization.

    Setiap panggilan membuat user berbeda (untuk tes isolasi antar user).
    """

    def _buat(email: str | None = None, password: str = "rahasia123", nama: str = "Pengguna Tes") -> dict:
        email = email or f"user{next(_nomor_user)}@contoh.com"
        r = client.post("/api/v1/auth/register", json={"nama": nama, "email": email, "password": password})
        assert r.status_code == 201, r.text
        r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _buat
