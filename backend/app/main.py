"""
VidaPlena — API de la Red de Clínicas (aplicación del taller)
----------------------------------------------------------------
Seguridad Informática — Ingeniería Multimedia, UMNG — Sesión 7

Esta API gestiona pacientes, citas y facturas de una red de clínicas
FICTICIA. Es la aplicación "insegura" del taller: contiene fallas de
seguridad de datos sembradas a propósito para que ustedes las encuentren
y las corrijan (ver la Guía del Taller en docs/).

No es necesario (ni se espera) que memoricen este archivo antes de
empezar: la idea es que lo exploren, lo prueben desde el navegador o con
curl/Postman, y vayan identificando qué está mal a medida que avanza el
taller.
"""

import secrets
from typing import Optional
from datetime import date, time as time_type

import bcrypt
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app import database
from app import cifrado

app = FastAPI(
    title="VidaPlena API",
    description="Red de Clínicas VidaPlena — aplicación del taller de Seguridad de Datos (UMNG).",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Sesiones de administrador (Hallazgo 2 — control de acceso)
# ---------------------------------------------------------------------------
# Guardamos en memoria los tokens de administrador emitidos al hacer login.
# Es intencionalmente simple (se pierde si se reinicia el backend), pero ya
# es un control REAL del lado del servidor: sin un token válido en el
# encabezado Authorization, nadie puede llamar a los endpoints de admin,
# sin importar lo que haga o no haga el frontend.
TOKENS_ADMIN: dict[str, dict] = {}

# Mismo mecanismo, para pacientes (Hallazgo 3 — IDOR). Nos permite saber
# CON QUIÉN estamos hablando, para poder comparar contra el dueño real
# del recurso antes de devolver datos sensibles como un diagnóstico.
TOKENS_PACIENTE: dict[str, dict] = {}


def verificar_admin(authorization: Optional[str] = Header(None)) -> dict:
    """
    Dependencia de FastAPI: exige y valida un token de administrador antes
    de permitir que se ejecute el endpoint protegido. Se usa con
    `Depends(verificar_admin)` en cada ruta que deba quedar restringida al
    personal de VidaPlena.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Falta el token de administrador")
    token = authorization.removeprefix("Bearer ")
    admin = TOKENS_ADMIN.get(token)
    if not admin:
        raise HTTPException(status_code=401, detail="Token de administrador inválido o expirado")
    return admin


def verificar_paciente(authorization: Optional[str] = Header(None)) -> dict:
    """
    Igual que `verificar_admin`, pero para pacientes. Además de exigir un
    token válido, esto es lo que nos deja luego comparar el `id` del
    paciente autenticado contra el dueño real de la cita consultada.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Falta el token del paciente")
    token = authorization.removeprefix("Bearer ")
    paciente = TOKENS_PACIENTE.get(token)
    if not paciente:
        raise HTTPException(status_code=401, detail="Token de paciente inválido o expirado")
    return paciente

# CORS abierto a propósito para simplificar el taller (el frontend Angular
# corre en un puerto distinto al backend). Esto no es una de las fallas
# que se pide corregir, pero en un sistema real tampoco se dejaría así.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Modelos de entrada
# ---------------------------------------------------------------------------

class PacienteRegistro(BaseModel):
    nombre: str
    cedula: str
    telefono: Optional[str] = None
    correo: Optional[str] = None
    contrasena: str


class LoginRequest(BaseModel):
    identificador: str  # cédula para paciente, usuario para admin
    contrasena: str


class CitaCreate(BaseModel):
    paciente_id: int
    fecha: date
    hora: time_type
    medico: str
    motivo_consulta: Optional[str] = None
    diagnostico: Optional[str] = None


# ---------------------------------------------------------------------------
# Utilidad
# ---------------------------------------------------------------------------

def fila_a_dict(cursor, fila):
    columnas = [desc[0] for desc in cursor.description]
    return dict(zip(columnas, fila))


# ---------------------------------------------------------------------------
# Hallazgo 4 — Contraseñas mal gestionadas
# ---------------------------------------------------------------------------
# Migración simple al arrancar: cualquier contraseña que todavía esté en
# texto plano (los hashes de bcrypt siempre empiezan por "$2b$") se
# re-escribe como hash con salt. Así los usuarios de ejemplo del taller
# (Ana, Carlos, Laura, admin) siguen entrando con la misma contraseña de
# siempre, sin tener que borrar y recrear la base de datos.
def migrar_contrasenas_a_hash():
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()
    try:
        for tabla in ("pacientes", "usuarios_admin"):
            cursor.execute(f"SELECT id, contrasena FROM {tabla}")
            filas = cursor.fetchall()
            for fila_id, contrasena in filas:
                if not contrasena.startswith("$2b$"):
                    nuevo_hash = bcrypt.hashpw(contrasena.encode(), bcrypt.gensalt()).decode()
                    cursor.execute(
                        f"UPDATE {tabla} SET contrasena = %s WHERE id = %s",
                        (nuevo_hash, fila_id),
                    )
        conexion.commit()
    finally:
        cursor.close()
        conexion.close()


# ---------------------------------------------------------------------------
# Hallazgo 5 — Datos sensibles sin cifrar
# ---------------------------------------------------------------------------
# cedula y diagnostico son Confidencial/Secreta según la tabla de
# clasificación de la Sesión 5. Se cifran a nivel de aplicación con Fernet
# (ver app/cifrado.py) antes de guardarse, y se descifran solo al leerlas
# para mostrarlas. Como Fernet es cifrado NO determinístico (el mismo
# texto produce un resultado distinto cada vez que se cifra), ya no se
# puede filtrar por cedula con un WHERE en SQL — por eso los endpoints que
# buscan por cédula (login, búsqueda de recepción, registro) ahora traen
# los candidatos y comparan el valor ya descifrado en Python.
def migrar_campos_a_cifrado():
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()
    try:
        # La columna cedula media 20 caracteres; un valor cifrado con
        # Fernet ocupa bastante más, así que se amplía primero (operación
        # segura de repetir, no borra datos).
        cursor.execute("ALTER TABLE pacientes MODIFY COLUMN cedula VARCHAR(255) NOT NULL")

        cursor.execute("SELECT id, cedula FROM pacientes")
        for fila_id, cedula in cursor.fetchall():
            if cedula is not None and not cifrado.ya_esta_cifrado(cedula):
                cursor.execute(
                    "UPDATE pacientes SET cedula = %s WHERE id = %s",
                    (cifrado.cifrar(cedula), fila_id),
                )

        cursor.execute("SELECT id, diagnostico FROM citas")
        for fila_id, diagnostico in cursor.fetchall():
            if diagnostico is not None and not cifrado.ya_esta_cifrado(diagnostico):
                cursor.execute(
                    "UPDATE citas SET diagnostico = %s WHERE id = %s",
                    (cifrado.cifrar(diagnostico), fila_id),
                )
        conexion.commit()
    finally:
        cursor.close()
        conexion.close()


@app.on_event("startup")
def _al_arrancar():
    migrar_contrasenas_a_hash()
    migrar_campos_a_cifrado()


# ---------------------------------------------------------------------------
# Pacientes
# ---------------------------------------------------------------------------

@app.post("/api/pacientes/registro")
def registrar_paciente(datos: PacienteRegistro):
    # Nunca guardamos la contraseña tal cual la escribió el usuario: se
    # hashea con bcrypt (incluye salt automático) antes de tocar la BD.
    hash_contrasena = bcrypt.hashpw(datos.contrasena.encode(), bcrypt.gensalt()).decode()
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()
    try:
        # La cédula queda cifrada en la BD, así que ya no se puede validar
        # "cédula duplicada" con un simple UNIQUE de SQL: se compara en
        # Python contra las cédulas ya descifradas.
        cursor.execute("SELECT cedula FROM pacientes")
        for (cedula_cifrada,) in cursor.fetchall():
            if cifrado.descifrar(cedula_cifrada) == datos.cedula:
                raise HTTPException(status_code=400, detail="Ya existe un paciente con esa cédula")

        cursor.execute(
            "INSERT INTO pacientes (nombre, cedula, telefono, correo, contrasena) "
            "VALUES (%s, %s, %s, %s, %s)",
            (datos.nombre, cifrado.cifrar(datos.cedula), datos.telefono, datos.correo, hash_contrasena),
        )
        conexion.commit()
        return {"id": cursor.lastrowid, "mensaje": "Paciente registrado"}
    finally:
        cursor.close()
        conexion.close()


@app.post("/api/login/paciente")
def login_paciente(datos: LoginRequest):
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()
    try:
        # La cédula ahora está cifrada (Hallazgo 5), así que ya no se puede
        # filtrar con WHERE cedula = %s: se trae a los pacientes y se
        # compara la cédula ya descifrada en Python. La contraseña sigue
        # verificándose aparte con bcrypt (Hallazgo 4), nunca en el WHERE.
        cursor.execute("SELECT id, nombre, cedula, contrasena FROM pacientes")
        encontrado = None
        for fila in cursor.fetchall():
            if cifrado.descifrar(fila[2]) == datos.identificador:
                encontrado = fila
                break
        if not encontrado or not bcrypt.checkpw(datos.contrasena.encode(), encontrado[3].encode()):
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        paciente = {"id": encontrado[0], "nombre": encontrado[1], "cedula": datos.identificador}
        token = secrets.token_hex(32)
        TOKENS_PACIENTE[token] = paciente
        return {**paciente, "token": token}
    finally:
        cursor.close()
        conexion.close()


@app.post("/api/login/admin")
def login_admin(datos: LoginRequest):
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute(
            "SELECT id, usuario, rol, contrasena FROM usuarios_admin WHERE usuario = %s",
            (datos.identificador,),
        )
        fila = cursor.fetchone()
        if not fila or not bcrypt.checkpw(datos.contrasena.encode(), fila[3].encode()):
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        admin = {"id": fila[0], "usuario": fila[1], "rol": fila[2]}
        # Emitimos un token real de sesión y lo guardamos del lado del
        # servidor. A partir de ahora, el frontend debe enviarlo en el
        # encabezado Authorization para poder usar los endpoints de admin.
        token = secrets.token_hex(32)
        TOKENS_ADMIN[token] = admin
        return {**admin, "token": token}
    finally:
        cursor.close()
        conexion.close()


@app.get("/api/pacientes/buscar")
def buscar_paciente(cedula: str):
    """
    Búsqueda de un paciente por número de cédula (usada en recepción).

    Sigue sin pegar el texto del usuario dentro del SQL (Hallazgo 1 no se
    reintroduce): de hecho, ahora ni siquiera hay un WHERE con la cédula,
    porque al estar cifrada (Hallazgo 5) la comparación se hace en Python
    contra el valor ya descifrado.
    """
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT id, nombre, cedula, telefono, correo FROM pacientes")
        resultado = []
        for f in cursor.fetchall():
            datos = fila_a_dict(cursor, f)
            cedula_plana = cifrado.descifrar(datos["cedula"])
            if cedula_plana == cedula:
                datos["cedula"] = cedula_plana
                resultado.append(datos)
        return resultado
    finally:
        cursor.close()
        conexion.close()


# ---------------------------------------------------------------------------
# Citas
# ---------------------------------------------------------------------------

@app.post("/api/citas")
def crear_cita(datos: CitaCreate):
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute(
            "INSERT INTO citas (paciente_id, fecha, hora, medico, motivo_consulta, diagnostico) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (datos.paciente_id, datos.fecha, datos.hora, datos.medico,
             datos.motivo_consulta, cifrado.cifrar(datos.diagnostico)),
        )
        conexion.commit()
        return {"id": cursor.lastrowid, "mensaje": "Cita creada"}
    finally:
        cursor.close()
        conexion.close()


@app.get("/api/citas/{cita_id}")
def obtener_cita(cita_id: int, paciente: dict = Depends(verificar_paciente)):
    """
    Detalle completo de una cita, incluido el diagnóstico.

    Protegido en dos capas: `Depends(verificar_paciente)` exige que quien
    llama esté autenticado, y además comparamos el `paciente_id` dueño de
    la cita contra el `id` del paciente autenticado (verificación de
    propiedad del recurso) — esto es lo que corrige el IDOR: ya no basta
    con adivinar un número de cita ajeno, el servidor rechaza cualquier
    cita que no sea tuya.
    """
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute(
            "SELECT c.id, c.paciente_id, p.nombre, c.fecha, c.hora, c.medico, "
            "c.motivo_consulta, c.diagnostico "
            "FROM citas c JOIN pacientes p ON p.id = c.paciente_id "
            "WHERE c.id = %s",
            (cita_id,),
        )
        fila = cursor.fetchone()
        if not fila:
            raise HTTPException(status_code=404, detail="Cita no encontrada")
        datos = fila_a_dict(cursor, fila)
        if datos["paciente_id"] != paciente["id"]:
            raise HTTPException(status_code=403, detail="Esta cita no pertenece al paciente autenticado")
        datos["diagnostico"] = cifrado.descifrar(datos["diagnostico"])
        return datos
    finally:
        cursor.close()
        conexion.close()


@app.get("/api/citas/paciente/{paciente_id}")
def citas_de_paciente(paciente_id: int):
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute(
            "SELECT id, fecha, hora, medico, motivo_consulta FROM citas WHERE paciente_id = %s",
            (paciente_id,),
        )
        filas = cursor.fetchall()
        return [fila_a_dict(cursor, f) for f in filas]
    finally:
        cursor.close()
        conexion.close()


# ---------------------------------------------------------------------------
# Facturas
# ---------------------------------------------------------------------------

@app.get("/api/facturas/paciente/{paciente_id}")
def facturas_de_paciente(paciente_id: int):
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute(
            "SELECT id, servicio, valor, estado_pago, dias_mora FROM facturas WHERE paciente_id = %s",
            (paciente_id,),
        )
        filas = cursor.fetchall()
        return [fila_a_dict(cursor, f) for f in filas]
    finally:
        cursor.close()
        conexion.close()


# ---------------------------------------------------------------------------
# Panel administrativo
# ---------------------------------------------------------------------------

@app.get("/api/admin/pacientes")
def listar_todos_los_pacientes(admin: dict = Depends(verificar_admin)):
    """
    Vista administrativa: todos los pacientes con su última consulta y
    diagnóstico, pensada para el personal de la clínica.

    Protegida con `Depends(verificar_admin)`: FastAPI ejecuta esa
    dependencia ANTES del cuerpo de la función. Si no hay un token válido
    en el encabezado Authorization, lanza 401 y esta consulta ni siquiera
    llega a correr contra la base de datos.
    """
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute(
            "SELECT p.id, p.nombre, p.cedula, p.telefono, p.correo, "
            "c.fecha, c.motivo_consulta, c.diagnostico "
            "FROM pacientes p "
            "LEFT JOIN citas c ON c.paciente_id = p.id "
            "ORDER BY p.id"
        )
        filas = cursor.fetchall()
        resultado = []
        for f in filas:
            datos = fila_a_dict(cursor, f)
            datos["cedula"] = cifrado.descifrar(datos["cedula"])
            datos["diagnostico"] = cifrado.descifrar(datos["diagnostico"])
            resultado.append(datos)
        return resultado
    finally:
        cursor.close()
        conexion.close()


@app.get("/api/salud")
def salud():
    return {"estado": "ok", "servicio": "VidaPlena API"}
