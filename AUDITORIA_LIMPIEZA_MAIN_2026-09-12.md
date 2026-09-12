# Auditoría de limpieza de la rama `main` — 2026-09-12

## Motivo

Según el `README.md` del taller, la rama `main` debe contener **únicamente el código base**
publicado por el profesor (Andrés Mauricio Salamanca, `amsalamancaa@gmail.com`). Los estudiantes
deben trabajar en sus propias ramas (`taller/apellidos-...`) y **no hacer push a `main`**.

Al revisar `origin/main` se encontraron 4 commits ajenos, hechos directamente sobre `main` por un
estudiante, que no deberían estar ahí. Este documento deja constancia de su contenido antes de
eliminarlos (reset de `main` al commit base + force-push).

Commit base que se conserva:

```
f3c96665a3923bb774fa7d8a1b94d8427d13226d
Andrés Mauricio Salamanca <amsalamancaa@gmail.com>
Sat Sep 5 02:47:38 2026 +0000
"Código base del taller VidaPlena (app con fallas de seguridad de datos para auditoría)"
```

## Commits eliminados de `main`

Todos por el mismo autor:

- Autor: `Felipe-Acevedo-UMNG1 <est.felipe.acevedo@unimilitar.edu.co>`

| # | Hash | Fecha | Mensaje |
|---|------|-------|---------|
| 1 | `d716ecd28af154b30c211e306e446ead8a240394` | 2026-09-11 19:53:45 -0500 | Add files via upload |
| 2 | `96467f280c051a0e406f034c66df661cf2b1f40c` | 2026-09-11 19:54:26 -0500 | Add files via upload |
| 3 | `919cccae2cb21a69fee6474d4312d85ca922e4dd` | 2026-09-11 19:56:45 -0500 | Delete backend/requirements-test.txt |
| 4 | `e17ece76b7136cc247788b07461e6a2a65ea2497` | 2026-09-11 19:57:09 -0500 | Delete backend/Dockerfile |

## Efecto neto (diff acumulado `f3c9666` → `e17ece76`)

```diff
 backend/Dockerfile       | 12 ------------
 backend/download         |  5 +++++
 backend/requirements.txt |  3 +++
 3 files changed, 8 insertions(+), 12 deletions(-)
```

- **`backend/Dockerfile` quedó eliminado por completo.** El estudiante primero lo modificó
  (agregando un multi-stage build con etapas `base`/`pruebas`/`runtime`, un usuario no-root, y
  copiando `requirements-test.txt`/`tests`), y luego lo borró en un commit posterior. El resultado
  final en `origin/main` es que **el archivo no existe**, lo cual rompe
  `docker compose up --build` (el servicio `backend` referencia `build: ./backend` y necesita un
  `Dockerfile`).
- **`backend/requirements-test.txt` fue creado y luego eliminado** (contenía `pytest` y `httpx`
  para pruebas). Neto: no queda en el árbol.
- **`backend/download` (archivo nuevo, sin extensión).** Nombre atípico — por el contenido, todo
  indica que el estudiante quiso crear/editar un `.gitignore` y lo subió con el nombre equivocado
  ("download"). Contenido:
  ```
  __pycache__/
  .pytest_cache/
  .venv/
  *.pyc
  .env*
  ```
- **`backend/requirements.txt` quedó con 3 dependencias agregadas** que sobreviven en el neto:
  `bcrypt==5.0.0`, `cryptography==50.0.1`, `PyJWT==2.13.0`.

## Commits del profesor que si permanecen (en otras ramas, no en `main`)

Estos ya existen en el historial pero en ramas de trabajo del profesor, no fueron tocados por esta
limpieza:

- `17f3b57` Agrega módulo de seguridad (bcrypt, JWT, Fernet, HMAC) y sembrado de datos
- `b6bbbf8` Actualiza esquema, dependencias y variables de entorno para la solución de referencia
- `78ffd97` Corrige las 5 fallas de seguridad sembradas en la API (solución de referencia)
- `4c9d323` Adjunta el JWT a cada solicitud del frontend (contraparte de la Falla 2/3)

## Acción tomada

1. `main` local se reseteó al commit base `f3c9666...` (descartando los 4 commits ajenos).
2. Se hizo force-push de `main` a `origin/main` para que el remoto quede igual al código base.
3. Los commits originales de Felipe-Acevedo-UMNG1 no se pierden de forma irreversible: siguen
   accesibles por hash (`d716ecd`, `96467f2`, `919cccae`, `e17ece76`) mientras no se ejecute un
   `git gc` agresivo en el remoto, y GitHub conserva el historial de commits "huérfanos" por un
   tiempo. Si el estudiante necesita su trabajo, debe volver a subirlo a su propia rama
   (`taller/apellidos-...`), no a `main`.
