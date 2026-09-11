"""
VidaPlena — API de la Red de Clínicas (aplicación del taller)
----------------------------------------------------------------
Seguridad Informática — Ingeniería Multimedia, UMNG — Sesión 7

Versión corregida hasta la Falla 5:
1. Inyección SQL: consultas parametrizadas.
2. Endpoint admin: token obligatorio.
3. IDOR: verificación de propiedad de la cita.
4. Contraseñas: bcrypt con salt.
5. Cédula y diagnóstico: cifrado Fernet a nivel de aplicación.
"""

from typing import Optional
from datetime import date, time as time_type
import base64
import hashlib
import hmac
import os
import secrets

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app import database


# ---------------------------------------------------------------------------
# Cifrado
# ---------------------------------------------------------------------------

FERNET_KEY = os.getenv("FERNET_KEY")

if not FERNET_KEY:
    raise RuntimeError(
        "Falta la variable de entorno FERNET_KEY. "
        "Configúrela mediante backend/.env antes de iniciar el backend."
    )

fernet = Fernet(FERNET_KEY.encode("utf-8"))
hmac_key = base64.urlsafe_b64decode(FERNET_KEY.encode("utf-8"))


def cifrar_texto(valor: Optional[str]) -> Optional[str]:
    if valor is None:
        return None
    return fernet.encrypt(valor.encode("utf-8")).decode("utf-8")


def descifrar_texto(valor: Optional[str]) -> Optional[str]:
    if valor is None:
        return None

    try:
        return fernet.decrypt(valor.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError(
            "Se encontró un dato que no está cifrado con la llave configurada. "
            "Ejecute primero la migración de la Falla 5."
        ) from exc


def hash_busqueda(valor: str) -> str:
    """
    HMAC-SHA256 determinístico para poder localizar una cédula sin guardar
    la cédula en texto plano. La cédula real sigue almacenada cifrada.
    """
    return hmac.new(
        hmac_key,
        valor.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


# ---------------------------------------------------------------------------
# Aplicación
# ---------------------------------------------------------------------------

app = FastAPI(
    title="VidaPlena API",
    description="Red de Clínicas VidaPlena — taller de Seguridad de Datos (UMNG).",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Autenticación
# ---------------------------------------------------------------------------

tokens_admin = set()
tokens_pacientes = {}


def validar_admin(authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Credencial administrativa requerida",
        )

    token = authorization.replace("Bearer ", "", 1).strip()

    if token not in tokens_admin:
        raise HTTPException(
            status_code=401,
            detail="Credencial administrativa invalida",
        )

    return token


def validar_paciente(authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Credencial de paciente requerida",
        )

    token = authorization.replace("Bearer ", "", 1).strip()

    if token not in tokens_pacientes:
        raise HTTPException(
            status_code=401,
            detail="Credencial de paciente invalida",
        )

    return tokens_pacientes[token]


# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------

class PacienteRegistro(BaseModel):
    nombre: str
    cedula: str
    telefono: Optional[str] = None
    correo: Optional[str] = None
    contrasena: str


class LoginRequest(BaseModel):
    identificador: str
    contrasena: str


class CitaCreate(BaseModel):
    paciente_id: int
    fecha: date
    hora: time_type
    medico: str
    motivo_consulta: Optional[str] = None
    diagnostico: Optional[str] = None


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def hashear_contrasena(contrasena: str) -> str:
    return bcrypt.hashpw(
        contrasena.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def verificar_contrasena(contrasena: str, hash_guardado: str) -> bool:
    return bcrypt.checkpw(
        contrasena.encode("utf-8"),
        hash_guardado.encode("utf-8"),
    )


def fila_a_dict(cursor, fila):
    columnas = [desc[0] for desc in cursor.description]
    return dict(zip(columnas, fila))


# ---------------------------------------------------------------------------
# Pacientes
# ---------------------------------------------------------------------------

@app.post("/api/pacientes/registro")
def registrar_paciente(datos: PacienteRegistro):
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()

    try:
        cedula_cifrada = cifrar_texto(datos.cedula)
        cedula_hash = hash_busqueda(datos.cedula)
        contrasena_hash = hashear_contrasena(datos.contrasena)

        cursor.execute(
            "INSERT INTO pacientes "
            "(nombre, cedula, cedula_hash, telefono, correo, contrasena) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                datos.nombre,
                cedula_cifrada,
                cedula_hash,
                datos.telefono,
                datos.correo,
                contrasena_hash,
            ),
        )
        conexion.commit()

        return {
            "id": cursor.lastrowid,
            "mensaje": "Paciente registrado",
        }

    finally:
        cursor.close()
        conexion.close()


@app.post("/api/login/paciente")
def login_paciente(datos: LoginRequest):
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()

    try:
        cursor.execute(
            "SELECT id, nombre, cedula, contrasena "
            "FROM pacientes "
            "WHERE cedula_hash = %s",
            (hash_busqueda(datos.identificador),),
        )

        fila = cursor.fetchone()

        if not fila:
            raise HTTPException(
                status_code=401,
                detail="Credenciales invalidas",
            )

        if not verificar_contrasena(datos.contrasena, fila[3]):
            raise HTTPException(
                status_code=401,
                detail="Credenciales invalidas",
            )

        token = secrets.token_urlsafe(32)
        tokens_pacientes[token] = fila[0]

        return {
            "id": fila[0],
            "nombre": fila[1],
            "cedula": descifrar_texto(fila[2]),
            "token": token,
        }

    finally:
        cursor.close()
        conexion.close()


@app.post("/api/login/admin")
def login_admin(datos: LoginRequest):
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()

    try:
        cursor.execute(
            "SELECT id, usuario, rol, contrasena "
            "FROM usuarios_admin "
            "WHERE usuario = %s",
            (datos.identificador,),
        )

        fila = cursor.fetchone()

        if not fila:
            raise HTTPException(
                status_code=401,
                detail="Credenciales invalidas",
            )

        if not verificar_contrasena(datos.contrasena, fila[3]):
            raise HTTPException(
                status_code=401,
                detail="Credenciales invalidas",
            )

        token = secrets.token_urlsafe(32)
        tokens_admin.add(token)

        return {
            "id": fila[0],
            "usuario": fila[1],
            "rol": fila[2],
            "token": token,
        }

    finally:
        cursor.close()
        conexion.close()


@app.get("/api/pacientes/buscar")
def buscar_paciente(cedula: str):
    """
    FALLA 1 + FALLA 5:
    consulta parametrizada y búsqueda mediante HMAC de la cédula.
    """
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()

    try:
        cursor.execute(
            "SELECT id, nombre, cedula, telefono, correo "
            "FROM pacientes "
            "WHERE cedula_hash = %s",
            (hash_busqueda(cedula),),
        )

        filas = cursor.fetchall()
        resultado = []

        for fila in filas:
            paciente = fila_a_dict(cursor, fila)
            paciente["cedula"] = descifrar_texto(paciente["cedula"])
            resultado.append(paciente)

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
        diagnostico_cifrado = cifrar_texto(datos.diagnostico)

        cursor.execute(
            "INSERT INTO citas "
            "(paciente_id, fecha, hora, medico, motivo_consulta, diagnostico) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                datos.paciente_id,
                datos.fecha,
                datos.hora,
                datos.medico,
                datos.motivo_consulta,
                diagnostico_cifrado,
            ),
        )
        conexion.commit()

        return {
            "id": cursor.lastrowid,
            "mensaje": "Cita creada",
        }

    finally:
        cursor.close()
        conexion.close()


@app.get("/api/citas/{cita_id}")
def obtener_cita(
    cita_id: int,
    paciente_id_autenticado: int = Depends(validar_paciente),
):
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()

    try:
        cursor.execute(
            "SELECT "
            "c.id, "
            "c.paciente_id, "
            "p.nombre, "
            "c.fecha, "
            "c.hora, "
            "c.medico, "
            "c.motivo_consulta, "
            "c.diagnostico "
            "FROM citas c "
            "JOIN pacientes p ON p.id = c.paciente_id "
            "WHERE c.id = %s",
            (cita_id,),
        )

        fila = cursor.fetchone()

        if not fila:
            raise HTTPException(
                status_code=404,
                detail="Cita no encontrada",
            )

        if fila[1] != paciente_id_autenticado:
            raise HTTPException(
                status_code=403,
                detail="No tiene permiso para consultar esta cita",
            )

        cita = fila_a_dict(cursor, fila)
        cita["diagnostico"] = descifrar_texto(cita["diagnostico"])
        return cita

    finally:
        cursor.close()
        conexion.close()


@app.get("/api/citas/paciente/{paciente_id}")
def citas_de_paciente(paciente_id: int):
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()

    try:
        cursor.execute(
            "SELECT id, fecha, hora, medico, motivo_consulta "
            "FROM citas "
            "WHERE paciente_id = %s",
            (paciente_id,),
        )

        filas = cursor.fetchall()
        return [fila_a_dict(cursor, fila) for fila in filas]

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
            "SELECT id, servicio, valor, estado_pago, dias_mora "
            "FROM facturas "
            "WHERE paciente_id = %s",
            (paciente_id,),
        )

        filas = cursor.fetchall()
        return [fila_a_dict(cursor, fila) for fila in filas]

    finally:
        cursor.close()
        conexion.close()


# ---------------------------------------------------------------------------
# Panel administrativo
# ---------------------------------------------------------------------------

@app.get("/api/admin/pacientes")
def listar_todos_los_pacientes(
    _: str = Depends(validar_admin),
):
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()

    try:
        cursor.execute(
            "SELECT "
            "p.id, "
            "p.nombre, "
            "p.cedula, "
            "p.telefono, "
            "p.correo, "
            "c.fecha, "
            "c.motivo_consulta, "
            "c.diagnostico "
            "FROM pacientes p "
            "LEFT JOIN citas c ON c.paciente_id = p.id "
            "ORDER BY p.id"
        )

        filas = cursor.fetchall()
        resultado = []

        for fila in filas:
            registro = fila_a_dict(cursor, fila)
            registro["cedula"] = descifrar_texto(registro["cedula"])
            registro["diagnostico"] = descifrar_texto(registro["diagnostico"])
            resultado.append(registro)

        return resultado

    finally:
        cursor.close()
        conexion.close()


@app.get("/api/salud")
def salud():
    return {
        "estado": "ok",
        "servicio": "VidaPlena API",
    }
