# MériteCasier (Flask + SQLite)

> *Deporte por felicidad, locker por comodidad.* · *Sport for happiness, a locker for comfort.*

Web app (pensada para celular) donde los estudiantes **ganan puntos usando los espacios de la universidad** (gimnasio, zona de baile, salas de estudio, ball pit) y los **canjean por un locker**. Disponible en español, francés e inglés.

A mobile-first web app where students **earn points by using campus spaces** (gym, dance zone, study rooms, ball pit) and **spend them on a locker**. Available in Spanish, French and English.

## Ejecutar / Run

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abre / open http://127.0.0.1:5000 (mejor en vista de celular / best in mobile view).
La base de datos SQLite (`meritecasier.db`) se crea sola. / The SQLite database is created automatically.

Modo desarrollo con recarga automática / development mode with auto-reload:

```bash
FLASK_DEBUG=1 python app.py      # Windows (PowerShell): $env:FLASK_DEBUG=1; python app.py
```

## Reglas / Rules

Se cambian arriba en `app.py`; los textos de la app se actualizan solos.
They are set at the top of `app.py`; the on-screen texts update automatically.

| Actividad / Activity | Puntos / Points |
|---|---|
| Gym / Dance zone | +10 por sesión / per session (min. 45 min) |
| Study rooms / Ball pit | +5 por hora / per hour (máx. / max. 3 h) |
| Locker | 15 puntos / points for 2 hours |

## Estructura / Structure

```
app.py               rutas, reglas, textos (es/fr/en) y base de datos / routes, rules, texts, database
templates/           páginas HTML (Jinja2) / HTML pages
static/style.css     estilos azul y verde, modo claro/oscuro / styles, light/dark mode
tests/               pruebas automáticas con pytest / automated tests
```

## Pruebas / Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Configuración / Configuration

| Variable | Para qué sirve / Purpose |
|---|---|
| `SECRET_KEY` | Clave de sesión. Si no existe, se genera y se guarda en `.secret_key` (no se sube a GitHub). / Session key. If unset, one is generated and saved to `.secret_key`. |
| `MERITECASIER_DB` | Ruta de la base de datos (opcional). / Database path (optional). |
| `FLASK_DEBUG` | `1` activa el modo desarrollo. / `1` enables development mode. |

## Limitaciones conocidas / Known limitations

- **Modo demo:** el escaneo del QR se simula con un botón, así que cualquiera puede sumar puntos sin límite. En una versión real, cada QR debería ser único y validarse en el servidor. / The QR scan is simulated with a button, so points can be earned without limit. A real version needs unique, server-validated QR codes.
- No hay contraseñas: la cuenta vive en la cookie del navegador. / There are no passwords: the account lives in the browser cookie.
