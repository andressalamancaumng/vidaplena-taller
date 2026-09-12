"""
VidaPlena — API de la Red de Clínicas (aplicación del taller)
----------------------------------------------------------------
Seguridad Informática — Ingeniería Multimedia, UMNG — Sesión 7

Versión CORREGIDA: los 5 hallazgos de seguridad ya están solucionados.
"""

from typing import Optional
from datetime import date, time as time_type
import secrets

from fastapi import Header, FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import bcrypt
from cryptography.fernet import Fernet

from app import database

app = FastAPI(
    title="VidaPlena API",
    description="Red de Clínicas VidaPlena — aplicación del taller de Seguridad de Datos (UMNG).",
    version="1.0.0",
)

# CORS abierto a propósito para simplificar el taller.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Tokens de sesión (Hallazgos 2 y 3)
# ---------------------------------------------------------------------------
tokens_pacientes = {}
tokens_admin = {}

# ---------------------------------------------------------------------------
# Cifrado Fernet (Hallazgo 5)
# ---------------------------------------------------------------------------
CLAVE_CIFRADO = b'4kL9pXz2Vb8sQ1rT6yU3wA7cE0mN5hJ8oI2dF4gK9qY='
cifrador = Fernet(CLAVE_CIFRADO)


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
# Pacientes
# ---------------------------------------------------------------------------

@app.post("/api/pacientes/registro")
def registrar_paciente(datos: PacienteRegistro):
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()
    try:
        contrasena_hash = bcrypt.hashpw(datos.contrasena.encode('utf-8'), bcrypt.gensalt())
        cedula_cifrada = cifrador.encrypt(datos.cedula.encode()).decode()
        cursor.execute(
            "INSERT INTO pacientes (nombre, cedula, telefono, correo, contrasena) "
            "VALUES (%s, %s, %s, %s, %s)",
            (datos.nombre, cedula_cifrada, datos.telefono, datos.correo, contrasena_hash),
        )
        conexion.commit()
        return {"id": cursor.lastrowid, "mensaje": "Paciente registrado"}
    finally:
        cursor.close()
        conexion.close()


@app.post("/api/login/paciente")
def login_paciente(datos: LoginRequest):
    """
    Ya no se puede buscar con WHERE cedula = %s porque la cédula está
    cifrada (Fernet genera un resultado distinto cada vez, aunque el
    texto original sea el mismo). Por eso se trae todo y se compara
    la cédula ya descifrada en Python.
    """
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT id, nombre, cedula, contrasena FROM pacientes")
        paciente_encontrado = None
        for fila in cursor.fetchall():
            cedula_descifrada = cifrador.decrypt(fila[2].encode()).decode()
            if cedula_descifrada == datos.identificador:
                paciente_encontrado = fila
                break

        if not paciente_encontrado:
            raise HTTPException(status_code=401, detail="Credenciales inválidas")

        if not bcrypt.checkpw(datos.contrasena.encode('utf-8'), paciente_encontrado[3].encode('utf-8')):
            raise HTTPException(status_code=401, detail="Credenciales inválidas")

        Token_Paciente = secrets.token_hex(16)
        tokens_pacientes[Token_Paciente] = paciente_encontrado[0]
        return {
            "id": paciente_encontrado[0],
            "nombre": paciente_encontrado[1],
            "cedula": datos.identificador,
            "token": Token_Paciente,
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
            "SELECT id, usuario, rol FROM usuarios_admin WHERE usuario = %s AND contrasena = %s",
            (datos.identificador, datos.contrasena),
        )
        fila = cursor.fetchone()
        if not fila:
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        Gen_Token = secrets.token_hex(16)
        tokens_admin[Gen_Token] = fila[0]
        return {"id": fila[0], "usuario": fila[1], "rol": fila[2], "token": Gen_Token}
    finally:
        cursor.close()
        conexion.close()


@app.get("/api/pacientes/buscar")
def buscar_paciente(cedula: str):
    """Búsqueda de un paciente por número de cédula (usada en recepción)."""
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT id, nombre, cedula, telefono, correo FROM pacientes")
        resultado = []
        for fila in cursor.fetchall():
            cedula_descifrada = cifrador.decrypt(fila[2].encode()).decode()
            if cedula_descifrada == cedula:
                dic = fila_a_dict(cursor, fila)
                dic["cedula"] = cedula_descifrada
                resultado.append(dic)
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
        diagnostico_cifrado = (
            cifrador.encrypt(datos.diagnostico.encode()).decode()
            if datos.diagnostico else None
        )
        cursor.execute(
            "INSERT INTO citas (paciente_id, fecha, hora, medico, motivo_consulta, diagnostico) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (datos.paciente_id, datos.fecha, datos.hora, datos.medico,
             datos.motivo_consulta, diagnostico_cifrado),
        )
        conexion.commit()
        return {"id": cursor.lastrowid, "mensaje": "Cita creada"}
    finally:
        cursor.close()
        conexion.close()


@app.get("/api/citas/{cita_id}")
def obtener_cita(cita_id: int, authorization: str = Header(None)):
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

        if authorization not in tokens_pacientes or tokens_pacientes[authorization] != fila[1]:
            raise HTTPException(status_code=401, detail="Acceso denegado")

        resultado = fila_a_dict(cursor, fila)
        if resultado.get("diagnostico"):
            resultado["diagnostico"] = cifrador.decrypt(resultado["diagnostico"].encode()).decode()
        return resultado
    finally:
        cursor.close()
        conexion.close()


@app.get("/api/citas/paciente/{paciente_id}")
def citas_de_paciente(paciente_id: int):
    """No trae diagnostico, así que no necesita descifrado."""
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

def verificar_admin(authorization: str = Header(None)):
    if authorization not in tokens_admin:
        raise HTTPException(status_code=401, detail="Acceso denegado")


@app.get("/api/admin/pacientes")
def listar_todos_los_pacientes(dependencies=Depends(verificar_admin)):
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
        resultado = []
        for f in cursor.fetchall():
            dic = fila_a_dict(cursor, f)
            dic["cedula"] = cifrador.decrypt(dic["cedula"].encode()).decode()
            if dic.get("diagnostico"):
                dic["diagnostico"] = cifrador.decrypt(dic["diagnostico"].encode()).decode()
            resultado.append(dic)
        return resultado
    finally:
        cursor.close()
        conexion.close()


@app.get("/api/salud")
def salud():
    return {"estado": "ok", "servicio": "VidaPlena API"}