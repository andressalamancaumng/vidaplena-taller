# VidaPlena — correcciones del taller, rama Dustyn

Aplicación de clínicas ficticias de Seguridad Informática (UMNG). Esta rama corrige
los cinco hallazgos de la guía y conserva el frontend Angular, FastAPI y MySQL.
No incluye el video ni el artículo IEEE. `main` conserva el ejercicio original.

## Arranque local

Si es una instalación nueva:

```bash
git clone --branch Dustyn https://github.com/Felipe-Acevedo-UMNG1/Taller-Sesi-n-7-Seguridad-Inform-tica.git vidaplena
cd vidaplena
python scripts/configurar.py
docker compose up --build -d
```

Si no tienes Python instalado, sustituye el tercer comando por este (PowerShell o Bash,
desde la carpeta del repositorio):

```bash
docker run --rm -v "${PWD}:/work" -w /work python:3.11-slim python scripts/configurar.py
```

La configuración crea llaves aleatorias en `.env` y no sobrescribe un archivo existente.
Nunca subas ese archivo ni lo muestres en el video.

- Aplicación: [localhost:4200](http://localhost:4200).
- API interactiva: [localhost:8000/docs](http://localhost:8000/docs).
- Los puertos 4200, 8000 y 3306 se publican solo en el computador local.
- Apagar conservando datos: `docker compose down`. **No uses `down -v` para actualizar**.

Las cuentas de ejemplo del taller se mantienen para la demostración:

| Tipo | Identificador | Contraseña de demostración |
|---|---|---|
| Paciente Ana | `1010023456` | `Cl4veSegura123` |
| Paciente Carlos | `1015098765` | `MiPerro2019` |
| Paciente Laura | `1022334455` | `12345678` |
| Administrador | `admin` | `Admin123!` |

Son credenciales sintéticas y públicas, no cuentas aptas para un servicio real. Las
contraseñas nuevas exigen 12 caracteres como mínimo y no más de 72 bytes UTF-8.
Las cuentas antiguas conservan sus contraseñas, pero su almacenamiento pasa a bcrypt.

## Si ya tenías el taller funcionando

1. Conserva la misma carpeta/proyecto de Compose para reutilizar su volumen. Haz un
   respaldo privado antes de migrar y detén la versión anterior con `docker compose down`.
2. Actualiza a `Dustyn` y ejecuta `scripts/configurar.py`.
3. Si el volumen se creó con el código original, conserva en `.env` estas credenciales
   **del laboratorio anterior**: `DB_PASSWORD=vidaplena_app_pw` y
   `DB_ROOT_PASSWORD=root_pw_taller`. Si las habías cambiado, usa sus valores actuales.
   Cambiar una variable no cambia la contraseña de un usuario que ya existe en MySQL.
4. Ejecuta `docker compose up --build -d`. La migración amplía la columna de cédula,
   agrega su índice HMAC y protege pacientes, administradores y diagnósticos antes
   de aceptar peticiones. No elimina filas, citas ni facturas.
5. Consulta `docker compose logs backend` si no arranca. Una llave incorrecta provoca
   un fallo seguro: restaura el `.env` correcto; no regeneres las llaves.

La migración es repetible: no vuelve a cifrar ni a aplicar hash a los mismos datos.
Los cambios de datos usan una transacción; los cambios de estructura de MySQL
(`ALTER TABLE`) se confirman por separado. Mantén el respaldo previo hasta validar
el arranque. Un respaldo anterior puede contener texto plano: protégelo y no lo publiques.

## Qué cambió y dónde comprobarlo

| Falla | Control aplicado | Código principal |
|---|---|---|
| 1. Inyección SQL | Consultas con `%s`; búsqueda exacta mediante un índice HMAC | `backend/app/main.py`: `buscar_paciente` |
| 2. Acceso administrativo | JWT firmado, sesión vigente y rol verificado en el servidor | `backend/app/seguridad.py`: `usuario_actual`, `exigir_admin` |
| 3. IDOR | Comparar el paciente solicitado con la identidad autenticada, antes de devolver datos | `verificar_propiedad` y rutas de citas/facturas |
| 4. Contraseñas legibles | bcrypt, sal aleatoria y costo 12 para pacientes y administradores | `hash_contrasena`, `verificar_contrasena`, `preparar_db.py` |
| 5. Datos sin cifrar | AES-256-GCM para cédulas y diagnósticos, con nonce aleatorio | `cifrar`, `descifrar` y `preparar_db.py` |

La autenticación también protege listados, facturas y creación de citas. Un paciente
solo puede consultar o crear sus propias citas. El administrador autorizado puede
operar sobre los pacientes. La búsqueda de recepción requiere administrador.

Las transacciones se centralizan en `database.py`; los controles criptográficos y de
permisos en `seguridad.py`. Un interceptor de Angular adjunta la credencial a la API,
sin repetir encabezados en cada servicio. El panel muestra solo la última cita de
cada paciente, evitando filas duplicadas.

El JWT vence a los 30 minutos y se revoca en el servidor al cerrar sesión. Se guarda
solo en memoria del navegador: al recargar la página hay que iniciar sesión otra vez.
Si no hay conexión al cerrar sesión, se elimina el estado local, pero el token emitido
puede seguir válido hasta su vencimiento.

## Gestión de llaves

- `DATA_KEY`: cifra y descifra los campos.
- `INDEX_KEY`: calcula el HMAC-SHA256 usado para buscar cédulas sin almacenarlas legibles.
- `JWT_KEY`: firma y verifica los tokens de sesión.

Son tres llaves independientes de 32 bytes, generadas aleatoriamente. No se guardan
en la base de datos ni en Git. El índice HMAC no es el cifrado de la cédula y solo
permite búsquedas de igualdad; no permite búsquedas parciales. No se usa SHA-256
simple para evitar que una copia de la base facilite probar cédulas sin una llave.

Conserva un respaldo privado de las llaves, separado del respaldo de datos. Si pierdes
`DATA_KEY`, no podrás recuperar los campos cifrados. Cambiar `DATA_KEY` o `INDEX_KEY`
requiere una migración de rotación: no basta con editar `.env`. Para invalidar todas
las sesiones puede rotarse `JWT_KEY` y reiniciarse el backend.

## Comprobación práctica

En Swagger, ejecuta primero `POST /api/login/paciente` o `POST /api/login/admin`,
copia el `access_token` y pégalo en **Authorize**. No muestres el token en una grabación.

| Prueba | Resultado esperado |
|---|---|
| Buscar la cédula de Ana como administrador | Un solo paciente |
| Buscar `' OR '1'='1` como administrador | Lista vacía, nunca todos los pacientes |
| Llamar `GET /api/admin/pacientes` sin token | 401 |
| Llamar al mismo endpoint con token de Ana | 403 |
| Llamar con token de administrador | 200 con pacientes |
| Consultar cita 1 como Ana | 200 con su cita |
| Consultar cita 2 como Ana | 403 sin diagnóstico ajeno |
| Cambiar el paciente del listado, factura o nueva cita | 403 |
| Registrar paciente y luego iniciar sesión | Registro 201 e inicio 200 |
| Cerrar sesión y reutilizar el JWT | 401 |

Para observar el almacenamiento protegido, sin imprimir llaves:

```bash
docker compose exec backend python -c "from app.database import consultar; print(consultar('SELECT id, cedula, contrasena FROM pacientes')); print(consultar('SELECT id, diagnostico FROM citas')); print(consultar('SELECT usuario, contrasena FROM usuarios_admin'))"
```

Las contraseñas comienzan con `$2b$12$`; los campos cifrados con `v1:`. Un prefijo
por sí solo no demuestra seguridad: las pruebas también verifican el login, el
descifrado autorizado, la aleatoriedad y el rechazo de cifrados alterados.

## Pruebas automáticas

Pruebas locales de API, autorización y criptografía (Python 3.11 o superior):

```bash
cd backend
python -m pip install -r requirements-test.txt
python -m pytest -v tests
```

Sin MySQL, se ejecutan **41 pruebas offline** y se omiten **5 pruebas de integración**.
Las offline ejecutan las consultas sobre una base SQLite temporal con una adaptación
del conector: no sustituyen la comprobación específica de MySQL ni de sus migraciones.

Para ejecutar también la integración real, desde la raíz del repositorio:

```bash
docker compose -f compose.pruebas.yml up --build --abort-on-container-exit --exit-code-from pruebas
docker compose -f compose.pruebas.yml down
```

El entorno de pruebas tiene otro nombre de proyecto, MySQL sin puertos públicos y
datos efímeros. Cada prueba crea y elimina únicamente su propia base temporal; nunca
usa el volumen ni las llaves de la aplicación. Comprueba la migración, conservación
de IDs, reinicio, rechazo de llaves diferentes y reversión ante fallos.

Frontend:

```bash
cd frontend
npm ci
npm run build
npx tsc --noEmit -p tsconfig.spec.json
npm test -- --watch=false --browsers=ChromeHeadless
```

El último comando necesita Chrome/Chromium. Los tests de Angular comprueban el
interceptor, la expiración y el cierre de sesión. Para desarrollo sin nginx usa
`npm start`: su proxy local envía `/api` al backend.

## Relación con la materia

- **Sesiones 1–2:** confidencialidad, integridad y disponibilidad. Se restringe quién
  accede, se detectan alteraciones del cifrado y se verifican los flujos permitidos.
- **Sesión 3:** AES, hash y HMAC. La contraseña usa hash no reversible; la cédula y el
  diagnóstico usan cifrado reversible con llave. HMAC permite la búsqueda protegida.
- **Sesión 5:** Defensa en Profundidad, especialmente capas 6 (Aplicación) y 7 (Datos).
- **Sesiones 7–8:** autenticación, autorización por recurso, sesiones JWT, consultas
  parametrizadas y pruebas de seguridad durante el desarrollo.
- **Sesiones 9–10:** backend sin root, puertos limitados al equipo local y registros
  de accesos rechazados sin contraseñas, tokens ni diagnósticos.

La guía relaciona los accesos sin autorización con los casos DIAN y
Conalcréditos/BBVA/Nu. La relación es el patrón de exposición y la necesidad de
controles del servidor; no demuestra que todos esos casos tuvieran exactamente
la misma causa ni que involucraran las cinco fallas.

Referencias técnicas consultadas: [FastAPI: JWT y dependencias](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/),
[OWASP: almacenamiento de contraseñas](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
y [cryptography: AES-GCM](https://cryptography.io/en/latest/hazmat/primitives/aead/).

## Alcance y pendientes

- Esta es una corrección del laboratorio, **no una certificación para producción**.
- Se conservó Angular 18 del ejercicio. La auditoría `npm audit --omit=dev` detecta
  9 dependencias afectadas, de severidad alta. Su actualización requiere una
  migración mayor coordinada con PrimeNG; no se aplicó `npm audit fix --force`.
- No se implementaron MFA, límites de intentos, copias de seguridad automatizadas
  ni TLS de producción. El registro de diagnósticos conserva el flujo didáctico,
  no un sistema real de autorización clínica.
- No se desplegó en AWS. Antes de exponer el servicio se necesitan HTTPS, gestión
  segura de secretos, credenciales no públicas y revisión de dependencias y permisos.
  La guía fija un tope de 4.0 sin AWS y habilita 5.0 al completar también ese despliegue.
- En este entorno se verificaron las pruebas offline, la compilación de Angular y
  los tipos de sus tests. Docker/MySQL y el navegador de tests no se ejecutaron aquí.
