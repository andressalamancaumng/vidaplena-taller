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

from typing import Optional
from datetime import date, time as time_type

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app import database

from fastapi.security import HTTPBasic, HTTPBasicCredentials
import bcrypt

import hashlib
from cryptography.fernet import Fernet
import os

FERNET_KEY = os.getenv("FERNET_KEY")
_cipher = Fernet(FERNET_KEY.encode("utf-8"))

security = HTTPBasic()

app = FastAPI(
    title="VidaPlena API",
    description="Red de Clínicas VidaPlena — aplicación del taller de Seguridad de Datos (UMNG).",
    version="1.0.0",
)

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
# Cifrado
# ---------------------------------------------------------------------------


def cifrar_dato(dato_plano: str) -> str:
    """Cifra un dato sensible (reversible) antes de guardarlo en la base de datos."""
    return _cipher.encrypt(dato_plano.encode("utf-8")).decode("utf-8")


def descifrar_dato(dato_cifrado: str) -> str:
    """Descifra un dato previamente cifrado con cifrar_dato, para mostrarlo a un usuario autorizado."""
    return _cipher.decrypt(dato_cifrado.encode("utf-8")).decode("utf-8")


def hash_busqueda(dato_plano: str) -> str:
    """Hash determinístico (SHA-256, no reversible) usado solo para poder buscar por
    igualdad, ya que el cifrado Fernet no es determinístico y no permite comparar
    directamente en una cláusula WHERE."""
    return hashlib.sha256(dato_plano.encode("utf-8")).hexdigest()


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


def hashear_contrasena(contrasena_plana: str) -> str:
    """Genera un hash bcrypt (con salt incorporado) a partir de una contraseña en texto plano."""
    return bcrypt.hashpw(contrasena_plana.encode("utf-8"), bcrypt.gensalt()).decode(
        "utf-8"
    )


def verificar_contrasena(contrasena_plana: str, hash_guardado: str) -> bool:
    """Compara una contraseña en texto plano contra su hash bcrypt almacenado."""
    return bcrypt.checkpw(
        contrasena_plana.encode("utf-8"), hash_guardado.encode("utf-8")
    )


# ---------------------------------------------------------------------------
# Pacientes
# ---------------------------------------------------------------------------


@app.post("/api/pacientes/registro")
def registrar_paciente(datos: PacienteRegistro):
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute(
            "INSERT INTO pacientes (nombre, cedula, cedula_hash, telefono, correo, contrasena) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                datos.nombre,
                cifrar_dato(datos.cedula),
                hash_busqueda(datos.cedula),
                datos.telefono,
                datos.correo,
                hashear_contrasena(datos.contrasena),
            ),
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
        cursor.execute(
            "SELECT id, nombre, cedula, contrasena FROM pacientes WHERE cedula_hash = %s",
            (hash_busqueda(datos.identificador),),
        )
        fila = cursor.fetchone()
        if not fila or not verificar_contrasena(datos.contrasena, fila[3]):
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        return {"id": fila[0], "nombre": fila[1], "cedula": descifrar_dato(fila[2])}
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
        if not fila or not verificar_contrasena(datos.contrasena, fila[3]):
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        return {"id": fila[0], "usuario": fila[1], "rol": fila[2]}
    finally:
        cursor.close()
        conexion.close()


@app.get("/api/pacientes/buscar")
def buscar_paciente(cedula: str):
    """Busqueda de un paciente por numero de cedula (usada en recepcion)."""
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute(
            "SELECT id, nombre, cedula, telefono, correo FROM pacientes WHERE cedula_hash = %s",
            (hash_busqueda(cedula),),
        )
        filas = cursor.fetchall()
        resultado = []
        for f in filas:
            fila_dict = fila_a_dict(cursor, f)
            fila_dict["cedula"] = descifrar_dato(fila_dict["cedula"])
            resultado.append(fila_dict)
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
            (
                datos.paciente_id,
                datos.fecha,
                datos.hora,
                datos.medico,
                datos.motivo_consulta,
                cifrar_dato(datos.diagnostico) if datos.diagnostico else None,
            ),
        )
        conexion.commit()
        return {"id": cursor.lastrowid, "mensaje": "Cita creada"}
    finally:
        cursor.close()
        conexion.close()


def verificar_paciente(credenciales: HTTPBasicCredentials = Depends(security)):
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute(
            "SELECT id, nombre, cedula, contrasena FROM pacientes WHERE cedula_hash = %s",
            (hash_busqueda(credenciales.username),),
        )
        fila = cursor.fetchone()
    finally:
        cursor.close()
        conexion.close()

    if not fila or not verificar_contrasena(credenciales.password, fila[3]):
        raise HTTPException(
            status_code=401,
            detail="Credenciales de paciente inválidas",
            headers={"WWW-Authenticate": "Basic"},
        )
    return {"id": fila[0], "nombre": fila[1], "cedula": descifrar_dato(fila[2])}


@app.get("/api/citas/{cita_id}")
def obtener_cita(cita_id: int, paciente: dict = Depends(verificar_paciente)):
    """Detalle completo de una cita, incluido el diagnóstico."""
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

        cita = fila_a_dict(cursor, fila)
        if cita.get("diagnostico"):
            cita["diagnostico"] = descifrar_dato(cita["diagnostico"])
        if cita["paciente_id"] != paciente["id"]:
            raise HTTPException(status_code=403, detail="No tiene permiso para consultar esta cita")
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


def verificar_admin(credenciales: HTTPBasicCredentials = Depends(security)):
    """Valida usuario/contraseña de administrador contra la base de datos antes de dejar
    pasar a un endpoint protegido."""
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute(
            "SELECT id, usuario, rol, contrasena FROM usuarios_admin WHERE usuario = %s",
            (credenciales.username,),
        )
        fila = cursor.fetchone()
    finally:
        cursor.close()
        conexion.close()

    if not fila or not verificar_contrasena(credenciales.password, fila[3]):
        raise HTTPException(
            status_code=401,
            detail="Credenciales de administrador inválidas",
            headers={"WWW-Authenticate": "Basic"},
        )
    return {"id": fila[0], "usuario": fila[1], "rol": fila[2]}


@app.get("/api/admin/pacientes")
def listar_todos_los_pacientes(admin: dict = Depends(verificar_admin)):
    """
    Vista administrativa: todos los pacientes con su última consulta y
    diagnóstico, pensada para el personal de la clínica.
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
            fila_dict = fila_a_dict(cursor, f)
            fila_dict["cedula"] = descifrar_dato(fila_dict["cedula"])
            if fila_dict.get("diagnostico"):
                fila_dict["diagnostico"] = descifrar_dato(fila_dict["diagnostico"])
            resultado.append(fila_dict)
        return resultado
    finally:
        cursor.close()
        conexion.close()


@app.get("/api/salud")
def salud():
    return {"estado": "ok", "servicio": "VidaPlena API"}
