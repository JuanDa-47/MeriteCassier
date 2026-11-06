import time

from conftest import consultar, dar_puntos, post, registrar


def puntos(uid=1):
    return consultar("SELECT puntos FROM usuarios WHERE id=?", (uid,))[0]


# ------------------------------------------------------------ acceso
def test_sin_sesion_redirige_a_registro(client):
    r = client.get("/")
    assert r.status_code == 302 and "/registro" in r.headers["Location"]


def test_registro_crea_usuario_con_cero_puntos(client):
    r = post(client, "/registro", nombre="  Ana  ")
    assert r.status_code == 302
    assert consultar("SELECT nombre, puntos FROM usuarios") == ("Ana", 0)


def test_registro_rechaza_nombre_vacio(client):
    post(client, "/registro", nombre="   ")
    assert consultar("SELECT COUNT(*) FROM usuarios")[0] == 0


# --------------------------------------------------------------- CSRF
def test_post_sin_token_csrf_es_rechazado(client):
    r = client.post("/registro", data={"nombre": "Ana"})
    assert r.status_code == 400
    assert consultar("SELECT COUNT(*) FROM usuarios")[0] == 0


# -------------------------------------------------------------- puntos
def test_gym_da_10_puntos(client):
    registrar(client)
    post(client, "/ganar", tipo="gym")
    assert puntos() == 10


def test_estudio_se_multiplica_por_horas(client):
    registrar(client)
    post(client, "/ganar", tipo="study", horas="2")
    assert puntos() == 10


def test_horas_se_limitan_al_maximo(client):
    registrar(client)
    post(client, "/ganar", tipo="ball", horas="99")
    assert puntos() == 15          # 3 h máximo x 5 puntos


def test_horas_invalidas_cuentan_como_una(client):
    registrar(client)
    post(client, "/ganar", tipo="study", horas="abc")
    assert puntos() == 5


def test_actividad_desconocida_no_da_puntos(client):
    registrar(client)
    post(client, "/ganar", tipo="hacker")
    assert puntos() == 0


# ------------------------------------------------------------ reservas
def test_reservar_sin_puntos_falla(client):
    registrar(client)
    post(client, "/reservar/A-01")
    assert consultar("SELECT estado FROM lockers WHERE id='A-01'")[0] == "libre"


def test_reservar_cobra_15_y_marca_el_locker(client):
    registrar(client)
    dar_puntos(1, 20)
    post(client, "/reservar/A-01")
    assert puntos() == 5
    assert consultar("SELECT estado, usuario_id FROM lockers WHERE id='A-01'") == ("reservado", 1)


def test_no_se_permiten_dos_reservas(client):
    registrar(client)
    dar_puntos(1, 40)
    post(client, "/reservar/A-01")
    post(client, "/reservar/A-03")
    assert puntos() == 25
    assert consultar("SELECT estado FROM lockers WHERE id='A-03'")[0] == "libre"


def test_no_se_puede_reservar_locker_ocupado_ni_en_mantenimiento(client):
    registrar(client)
    dar_puntos(1, 40)
    post(client, "/reservar/A-02")      # reservado por otra persona (demo)
    post(client, "/reservar/A-04")      # en mantenimiento (demo)
    assert puntos() == 40


def test_cancelar_libera_sin_reembolso(client):
    registrar(client)
    dar_puntos(1, 15)
    post(client, "/reservar/A-01")
    post(client, "/cancelar")
    assert consultar("SELECT estado, usuario_id FROM lockers WHERE id='A-01'") == ("libre", None)
    assert puntos() == 0


def test_reserva_expirada_se_libera_sola(client):
    registrar(client)
    dar_puntos(1, 15)
    post(client, "/reservar/A-01")
    import sqlite3
    from conftest import RUTA_DB
    db = sqlite3.connect(RUTA_DB)
    db.execute("UPDATE lockers SET expira_en=? WHERE id='A-01'", (int(time.time()) - 1,))
    db.commit()
    db.close()
    client.get("/lockers")
    assert consultar("SELECT estado FROM lockers WHERE id='A-01'")[0] == "libre"


# ------------------------------------------------------------- idiomas
def test_cambio_de_idioma(client):
    registrar(client)
    client.get("/idioma/en")
    assert b"Earn points" in client.get("/").data
    client.get("/idioma/fr")
    assert "Gagne des points".encode() in client.get("/").data


def test_idioma_desconocido_se_ignora(client):
    registrar(client)
    client.get("/idioma/xx")
    assert "Gana puntos".encode() in client.get("/").data


def test_las_reglas_se_leen_de_las_constantes(client):
    registrar(client)
    assert b"15 puntos" in client.get("/").data
