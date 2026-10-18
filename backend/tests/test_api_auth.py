"""Tes API auth: /api/v1/auth/register, /login, /me (FR-1)."""

from sqlalchemy import select

from app.models.user import User

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"


def _register(client, email="budi@contoh.com", password="rahasia123", nama="Budi"):
    return client.post(REGISTER, json={"nama": nama, "email": email, "password": password})


def _login(client, email="budi@contoh.com", password="rahasia123"):
    return client.post(LOGIN, json={"email": email, "password": password})


# ---------- register ----------

def test_register_berhasil_tanpa_field_password(client, db):
    r = _register(client)
    assert r.status_code == 201
    body = r.json()
    assert set(body) == {"id_user", "nama", "email"}
    assert body["nama"] == "Budi"
    assert body["email"] == "budi@contoh.com"
    # password tersimpan sebagai hash bcrypt, bukan plaintext
    user = db.get(User, body["id_user"])
    assert user.password != "rahasia123" and user.password.startswith("$2")


def test_register_email_disimpan_huruf_kecil(client, db):
    r = _register(client, email="Budi.Santoso@Contoh.COM")
    assert r.status_code == 201
    assert r.json()["email"] == "budi.santoso@contoh.com"
    assert db.scalar(select(User.email)) == "budi.santoso@contoh.com"


def test_register_email_duplikat_beda_huruf_409(client):
    assert _register(client, email="budi@contoh.com").status_code == 201
    r = _register(client, email="BUDI@Contoh.com")
    assert r.status_code == 409
    assert r.json()["detail"] == "Email sudah terdaftar"


def test_register_password_kurang_dari_8_karakter_422(client):
    assert _register(client, password="pendek1").status_code == 422


def test_register_password_lebih_dari_72_byte_422(client):
    # 37 karakter "é" = 74 byte UTF-8: lolos min_length, ditolak batas byte bcrypt
    r = _register(client, password="é" * 37)
    assert r.status_code == 422


def test_register_password_tepat_72_byte_diterima(client):
    assert _register(client, password="a" * 72).status_code == 201


def test_register_email_tidak_valid_422(client):
    assert _register(client, email="bukan-email").status_code == 422


def test_register_nama_kosong_422(client):
    assert _register(client, nama="").status_code == 422


# ---------- login ----------

def test_login_berhasil_mengembalikan_token(client):
    _register(client)
    r = _login(client)
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_email_beda_huruf_tetap_berhasil(client):
    _register(client)
    assert _login(client, email="BUDI@contoh.com").status_code == 200


def test_login_password_salah_401(client):
    _register(client)
    r = _login(client, password="salahsalah")
    assert r.status_code == 401
    assert r.json()["detail"] == "Email atau password salah"


def test_login_email_tidak_dikenal_401(client):
    assert _login(client, email="hantu@contoh.com").status_code == 401


def test_login_password_lebih_dari_72_byte_401_bukan_500(client):
    # bcrypt >= 5 melempar ValueError untuk password > 72 byte; login harus tetap menjawab 401
    _register(client)
    r = _login(client, password="x" * 100)
    assert r.status_code == 401


# ---------- /me ----------

def test_me_dengan_token_200(client, auth_headers):
    headers = auth_headers(email="siti@contoh.com", nama="Siti")
    r = client.get(ME, headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "siti@contoh.com"
    assert r.json()["nama"] == "Siti"


def test_me_tanpa_token_401(client):
    r = client.get(ME)
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


def test_me_token_sampah_401(client):
    assert client.get(ME, headers={"Authorization": "Bearer bukan.token.jwt"}).status_code == 401


def test_me_token_user_yang_sudah_dihapus_401(client, db, auth_headers):
    headers = auth_headers(email="hapus@contoh.com")
    db.delete(db.scalar(select(User).where(User.email == "hapus@contoh.com")))
    db.commit()
    assert client.get(ME, headers=headers).status_code == 401


def test_auth_headers_membuat_dua_user_berbeda(client, auth_headers):
    a = client.get(ME, headers=auth_headers()).json()
    b = client.get(ME, headers=auth_headers()).json()
    assert a["id_user"] != b["id_user"]
