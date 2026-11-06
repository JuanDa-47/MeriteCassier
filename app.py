"""MériteCasier - Reserva de lockers con puntos por actividad (EAN)."""
import os
import secrets
import sqlite3
import time
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urlparse

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   session, url_for)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("MERITECASIER_DB", os.path.join(BASE_DIR, "meritecasier.db"))


def _clave_secreta():
    """SECRET_KEY del entorno; si no existe, se genera una y se guarda en .secret_key."""
    clave = os.environ.get("SECRET_KEY")
    if clave:
        return clave
    ruta = os.path.join(BASE_DIR, ".secret_key")
    if os.path.exists(ruta):
        with open(ruta) as f:
            return f.read().strip()
    clave = secrets.token_hex(32)
    with open(ruta, "w") as f:
        f.write(clave)
    return clave


app = Flask(__name__)
app.secret_key = _clave_secreta()
app.permanent_session_lifetime = timedelta(days=30)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

# ---------------------------------------------------------------- reglas
# Cambia estos valores y los textos de la app se actualizan solos.
COSTO_LOCKER = 15              # puntos por reserva
DURACION = 2 * 3600            # segundos (turno de 2 horas)
MIN_SESION = 45                # minutos mínimos para gym / baile
MAX_HORAS = 3                  # máximo de horas por registro en estudio / ball pit
# actividad -> (puntos, ¿se multiplica por horas?)
ACTIVIDADES = {
    "gym":   (10, False),
    "dance": (10, False),
    "study": (5, True),
    "ball":  (5, True),
}
ZONAS = {"zG": "A", "zD": "B", "zS": "C"}   # zona -> prefijo del ID

# Valores que se insertan en los textos con {cost}, {hours}, etc.
PARAMS = {
    "cost": COSTO_LOCKER, "hours": DURACION // 3600, "min": MIN_SESION,
    **{nombre: pts for nombre, (pts, _) in ACTIVIDADES.items()},
}

TEXTOS = {
    "es": {
        "tag": "Deporte por felicidad, locker por comodidad.",
        "hi": "Hola", "pts": "puntos", "goal": "Un locker cuesta {cost} puntos ({hours} horas)",
        "tabH": "Inicio", "tabL": "Lockers", "tabM": "Mi reserva",
        "earn": "Gana puntos", "scan": "Escanear código", "hours": "horas",
        "gym": "Gimnasio", "gymS": "+{gym} por sesión (mín. {min} min)",
        "dance": "Zona de baile", "danceS": "+{dance} por sesión (mín. {min} min)",
        "study": "Salas de estudio", "studyS": "+{study} por hora",
        "ball": "Ball pit (patio)", "ballS": "+{ball} por hora",
        "hist": "Actividad reciente", "none": "Aún no hay actividad. Escanea el código de un espacio.",
        "regT": "Crea tu cuenta",
        "regP": "Gana puntos usando los espacios de la universidad y reserva tu locker.",
        "regN": "Tu nombre", "regB": "Empezar",
        "free": "Libre", "res": "Reservado", "mnt": "En mantenimiento", "mine": "Tuyo",
        "zG": "Bloque A – Gym", "zD": "Zona de baile", "zS": "Salas de estudio",
        "tip": "Toca un locker libre para reservarlo ({cost} puntos, {hours} horas).",
        "noRes": "No tienes ninguna reserva activa.", "book": "Reservar un locker",
        "myL": "Tu locker", "until": "Válido hasta", "cancel": "Cancelar reserva (sin reembolso)",
        "okEarn": "Ganaste", "okRes": "Locker reservado: ", "noPts": "Te faltan puntos. Necesitas {cost}.",
        "hasRes": "Ya tienes una reserva activa.", "taken": "Ese locker ya no está disponible.",
        "cancelled": "Reserva cancelada.", "badName": "Escribe tu nombre.",
        "rules": "Reglas",
        "rulesT": "Un locker = {cost} puntos por {hours} horas. La prioridad depende de tu participación, no de quién llega primero.",
        "demo": "Modo demo: el escaneo del QR se simula con un botón.",
        "logGym": "Gimnasio", "logDance": "Zona de baile", "logStudy": "Salas de estudio",
        "logBall": "Ball pit", "logReserve": "Locker",
    },
    "fr": {
        "tag": "Le sport pour le bonheur, le casier pour le confort.",
        "hi": "Salut", "pts": "points", "goal": "Un casier coûte {cost} points ({hours} heures)",
        "tabH": "Accueil", "tabL": "Casiers", "tabM": "Ma réservation",
        "earn": "Gagne des points", "scan": "Scanner le code", "hours": "heures",
        "gym": "Gymnase", "gymS": "+{gym} par séance ({min} min min.)",
        "dance": "Zone de danse", "danceS": "+{dance} par séance ({min} min min.)",
        "study": "Salles d’étude", "studyS": "+{study} par heure",
        "ball": "Ball pit (patio)", "ballS": "+{ball} par heure",
        "hist": "Activité récente", "none": "Pas encore d’activité. Scanne le code d’un espace.",
        "regT": "Crée ton compte",
        "regP": "Gagne des points dans les espaces de l’université et réserve ton casier.",
        "regN": "Ton prénom", "regB": "Commencer",
        "free": "Libre", "res": "Réservé", "mnt": "En maintenance", "mine": "À toi",
        "zG": "Bloc A – Gym", "zD": "Zone de danse", "zS": "Salles d’étude",
        "tip": "Touche un casier libre pour le réserver ({cost} points, {hours} heures).",
        "noRes": "Tu n’as pas de réservation active.", "book": "Réserver un casier",
        "myL": "Ton casier", "until": "Valable jusqu’à", "cancel": "Annuler la réservation (sans remboursement)",
        "okEarn": "Tu as gagné", "okRes": "Casier réservé : ", "noPts": "Il te manque des points. Il faut {cost} points.",
        "hasRes": "Tu as déjà une réservation active.", "taken": "Ce casier n’est plus disponible.",
        "cancelled": "Réservation annulée.", "badName": "Écris ton prénom.",
        "rules": "Règles",
        "rulesT": "Un casier = {cost} points pour {hours} heures. La priorité dépend de ta participation, pas de qui arrive en premier.",
        "demo": "Mode démo : le scan du QR est simulé par un bouton.",
        "logGym": "Gymnase", "logDance": "Zone de danse", "logStudy": "Salles d’étude",
        "logBall": "Ball pit", "logReserve": "Casier",
    },
    "en": {
        "tag": "Sport for happiness, a locker for comfort.",
        "hi": "Hi", "pts": "points", "goal": "A locker costs {cost} points ({hours} hours)",
        "tabH": "Home", "tabL": "Lockers", "tabM": "My booking",
        "earn": "Earn points", "scan": "Scan code", "hours": "hours",
        "gym": "Gym", "gymS": "+{gym} per session (min. {min} min)",
        "dance": "Dance zone", "danceS": "+{dance} per session (min. {min} min)",
        "study": "Study rooms", "studyS": "+{study} per hour",
        "ball": "Ball pit (courtyard)", "ballS": "+{ball} per hour",
        "hist": "Recent activity", "none": "No activity yet. Scan the code of a space.",
        "regT": "Create your account",
        "regP": "Earn points by using the university's spaces and book your locker.",
        "regN": "Your name", "regB": "Start",
        "free": "Free", "res": "Booked", "mnt": "Under maintenance", "mine": "Yours",
        "zG": "Block A – Gym", "zD": "Dance zone", "zS": "Study rooms",
        "tip": "Tap a free locker to book it ({cost} points, {hours} hours).",
        "noRes": "You have no active booking.", "book": "Book a locker",
        "myL": "Your locker", "until": "Valid until", "cancel": "Cancel booking (no refund)",
        "okEarn": "You earned", "okRes": "Locker booked: ", "noPts": "Not enough points. You need {cost}.",
        "hasRes": "You already have an active booking.", "taken": "That locker is no longer available.",
        "cancelled": "Booking cancelled.", "badName": "Please enter your name.",
        "rules": "Rules",
        "rulesT": "One locker = {cost} points for {hours} hours. Priority depends on your participation, not on who arrives first.",
        "demo": "Demo mode: the QR scan is simulated with a button.",
        "logGym": "Gym", "logDance": "Dance zone", "logStudy": "Study rooms",
        "logBall": "Ball pit", "logReserve": "Locker",
    },
}
IDIOMAS = tuple(TEXTOS)        # ("es", "fr", "en")


# ---------------------------------------------------------- base de datos
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def cerrar_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            puntos INTEGER NOT NULL DEFAULT 0 CHECK (puntos >= 0)
        );
        CREATE TABLE IF NOT EXISTS lockers (
            id TEXT PRIMARY KEY,                          -- identificador del locker
            zona TEXT NOT NULL,                           -- ubicación (zG, zD, zS)
            estado TEXT NOT NULL DEFAULT 'libre',         -- libre | reservado | mantenimiento
            usuario_id INTEGER REFERENCES usuarios(id),   -- quién lo tiene ahora
            reservado_en INTEGER,                         -- momento de la reserva
            expira_en INTEGER                             -- momento de expiración
        );
        CREATE TABLE IF NOT EXISTS actividad (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
            tipo TEXT NOT NULL,                           -- gym, dance, study, ball, reserve
            detalle TEXT,
            puntos INTEGER NOT NULL,
            fecha INTEGER NOT NULL
        );
        -- Una persona no puede tener dos lockers reservados a la vez,
        -- ni siquiera si manda dos peticiones al mismo tiempo.
        CREATE UNIQUE INDEX IF NOT EXISTS una_reserva_por_usuario
            ON lockers(usuario_id) WHERE estado = 'reservado';
    """)
    if db.execute("SELECT COUNT(*) FROM lockers").fetchone()[0] == 0:
        n = 0
        for zona, pref in ZONAS.items():
            for i in range(1, 5):
                n += 1
                estado = "libre"
                if n in (2, 6, 7, 11):      # demo: ocupados por otros
                    estado = "reservado"
                if n in (4, 9):             # demo: en mantenimiento
                    estado = "mantenimiento"
                exp = int(time.time()) + 3600 if estado == "reservado" else None
                db.execute(
                    "INSERT INTO lockers (id, zona, estado, expira_en) VALUES (?,?,?,?)",
                    (f"{pref}-0{i}", zona, estado, exp))
    db.commit()
    db.close()


def liberar_expirados():
    db = get_db()
    db.execute("""UPDATE lockers SET estado='libre', usuario_id=NULL,
                  reservado_en=NULL, expira_en=NULL
                  WHERE estado='reservado' AND expira_en IS NOT NULL AND expira_en <= ?""",
               (int(time.time()),))
    db.commit()


# ------------------------------------------------------------- utilidades
def idioma():
    lang = session.get("lang", "es")
    return lang if lang in TEXTOS else "es"


def traducir(clave):
    """Texto en el idioma actual (con respaldo en español) y reglas ya insertadas."""
    texto = TEXTOS[idioma()].get(clave) or TEXTOS["es"].get(clave, clave)
    return texto.format(**PARAMS)


def usuario_actual():
    """Usuario de la sesión; se consulta una sola vez por petición."""
    if "usuario" not in g:
        uid = session.get("uid")
        g.usuario = None if not uid else get_db().execute(
            "SELECT * FROM usuarios WHERE id=?", (uid,)).fetchone()
    return g.usuario


def reserva_de(uid):
    return get_db().execute(
        "SELECT * FROM lockers WHERE usuario_id=? AND estado='reservado'", (uid,)).fetchone()


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


@app.before_request
def proteger_csrf():
    """Todos los POST deben traer el token CSRF de la sesión."""
    if request.method == "POST":
        enviado = request.form.get("csrf_token", "").encode()
        esperado = session.get("csrf_token", "").encode()
        if not esperado or not secrets.compare_digest(enviado, esperado):
            abort(400)


@app.context_processor
def inyectar():
    return {"t": traducir, "lang": idioma(), "idiomas": IDIOMAS,
            "usuario": usuario_actual(), "csrf_token": csrf_token,
            "hora": lambda ts: datetime.fromtimestamp(ts).strftime("%H:%M")}


def requiere_login(vista):
    @wraps(vista)
    def envoltura(*a, **kw):
        if not usuario_actual():
            return redirect(url_for("registro"))
        liberar_expirados()
        return vista(*a, **kw)
    return envoltura


def msg(clave):
    flash(traducir(clave))


def volver_atras():
    """Vuelve a la página anterior solo si es de este mismo sitio."""
    ref = request.referrer
    if ref and urlparse(ref).netloc == request.host:
        return redirect(ref)
    return redirect(url_for("inicio"))


# ------------------------------------------------------------------ rutas
@app.route("/idioma/<code>")
def cambiar_idioma(code):
    if code in TEXTOS:
        session["lang"] = code
    return volver_atras()


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()[:30]
        if not nombre:
            msg("badName")
            return redirect(url_for("registro"))
        db = get_db()
        cur = db.execute("INSERT INTO usuarios (nombre) VALUES (?)", (nombre,))
        db.commit()
        session["uid"] = cur.lastrowid
        session.permanent = True
        return redirect(url_for("inicio"))
    if usuario_actual():
        return redirect(url_for("inicio"))
    return render_template("registro.html")


@app.route("/")
@requiere_login
def inicio():
    u = usuario_actual()
    log = get_db().execute(
        "SELECT * FROM actividad WHERE usuario_id=? ORDER BY id DESC LIMIT 6",
        (u["id"],)).fetchall()
    return render_template("inicio.html", tab="inicio", log=log,
                           pct=min(100, round(u["puntos"] / COSTO_LOCKER * 100)),
                           actividades=list(ACTIVIDADES),
                           por_hora={k: v[1] for k, v in ACTIVIDADES.items()},
                           max_horas=MAX_HORAS)


@app.route("/ganar", methods=["POST"])
@requiere_login
def ganar():
    tipo = request.form.get("tipo")
    if tipo not in ACTIVIDADES:
        return redirect(url_for("inicio"))
    base, por_hora = ACTIVIDADES[tipo]
    horas = 1
    if por_hora:
        try:
            horas = max(1, min(MAX_HORAS, int(request.form.get("horas", 1))))
        except ValueError:
            horas = 1
    pts = base * horas
    db = get_db()
    db.execute("UPDATE usuarios SET puntos = puntos + ? WHERE id=?", (pts, session["uid"]))
    db.execute("INSERT INTO actividad (usuario_id,tipo,puntos,fecha) VALUES (?,?,?,?)",
               (session["uid"], tipo, pts, int(time.time())))
    db.commit()
    flash(f"{traducir('okEarn')} +{pts} {traducir('pts')}")
    return redirect(url_for("inicio"))


@app.route("/lockers")
@requiere_login
def lockers():
    filas = get_db().execute("SELECT * FROM lockers ORDER BY id").fetchall()
    zonas = {z: [l for l in filas if l["zona"] == z] for z in ZONAS}
    return render_template("lockers.html", tab="lockers", zonas=zonas, uid=session["uid"])


@app.route("/reservar/<locker_id>", methods=["POST"])
@requiere_login
def reservar(locker_id):
    db = get_db()
    u = usuario_actual()
    if reserva_de(u["id"]):
        msg("hasRes")
        return redirect(url_for("lockers"))
    if u["puntos"] < COSTO_LOCKER:
        msg("noPts")
        return redirect(url_for("lockers"))
    ahora = int(time.time())
    try:
        # UPDATE condicional: evita que dos personas reserven el mismo locker
        cur = db.execute("""UPDATE lockers SET estado='reservado', usuario_id=?,
                            reservado_en=?, expira_en=? WHERE id=? AND estado='libre'""",
                         (u["id"], ahora, ahora + DURACION, locker_id))
        if cur.rowcount == 0:
            db.rollback()
            msg("taken")
            return redirect(url_for("lockers"))
        # El cobro solo ocurre si todavía hay puntos suficientes (todo o nada)
        cobro = db.execute(
            "UPDATE usuarios SET puntos = puntos - ? WHERE id=? AND puntos >= ?",
            (COSTO_LOCKER, u["id"], COSTO_LOCKER))
        if cobro.rowcount == 0:
            db.rollback()
            msg("noPts")
            return redirect(url_for("lockers"))
        db.execute("INSERT INTO actividad (usuario_id,tipo,detalle,puntos,fecha) VALUES (?,?,?,?,?)",
                   (u["id"], "reserve", locker_id, -COSTO_LOCKER, ahora))
        db.commit()
    except sqlite3.IntegrityError:      # ya tenía otra reserva (doble clic / dos pestañas)
        db.rollback()
        msg("hasRes")
        return redirect(url_for("lockers"))
    flash(traducir("okRes") + locker_id)
    return redirect(url_for("mi_reserva"))


@app.route("/mi-reserva")
@requiere_login
def mi_reserva():
    return render_template("mi_reserva.html", tab="mia", reserva=reserva_de(session["uid"]))


@app.route("/cancelar", methods=["POST"])
@requiere_login
def cancelar():
    db = get_db()
    db.execute("""UPDATE lockers SET estado='libre', usuario_id=NULL, reservado_en=NULL,
                  expira_en=NULL WHERE usuario_id=? AND estado='reservado'""", (session["uid"],))
    db.commit()
    msg("cancelled")
    return redirect(url_for("mi_reserva"))


init_db()   # también al correr con `flask run` o gunicorn, no solo con `python app.py`

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
