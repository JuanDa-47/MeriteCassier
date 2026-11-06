import os
import sqlite3
import sys
import tempfile

import pytest

# La base de datos de prueba va a una carpeta temporal (nunca toca meritecasier.db)
RUTA_DB = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["MERITECASIER_DB"] = RUTA_DB
os.environ["SECRET_KEY"] = "clave-de-pruebas"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402


@pytest.fixture
def client():
    if os.path.exists(RUTA_DB):
        os.remove(RUTA_DB)
    app_module.init_db()
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def post(client, url, **datos):
    """POST con el token CSRF de la sesión, como haría el navegador."""
    with client.session_transaction() as s:
        s.setdefault("csrf_token", "token-de-prueba")
        datos["csrf_token"] = s["csrf_token"]
    return client.post(url, data=datos)


def registrar(client, nombre="Ana"):
    post(client, "/registro", nombre=nombre)


def dar_puntos(uid, puntos):
    db = sqlite3.connect(RUTA_DB)
    db.execute("UPDATE usuarios SET puntos=? WHERE id=?", (puntos, uid))
    db.commit()
    db.close()


def consultar(sql, params=()):
    db = sqlite3.connect(RUTA_DB)
    fila = db.execute(sql, params).fetchone()
    db.close()
    return fila
