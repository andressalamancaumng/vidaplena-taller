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

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
# Esquema de seguridad OAuth2
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from app import database

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import base64

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
# Seguridad y Autenticación 
# ---------------------------------------------------------------------------
# Define que el token se obtiene en el endpoint de login de admin
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login/admin")

def verificar_admin(token: str = Depends(oauth2_scheme)):
    """
    Valida el token enviado en el encabezado Authorization.
    En esta fase, se usa un token estático simulado.
    """
    if token != "admin_secreto_123":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acceso denegado: Token inválido o ausente",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token

# Configuración de cifrado AES (Modo ECB para búsquedas exactas)
CLAVE_AES = b'12345678901234567890123456789012'

def cifrar(texto: str) -> str:
    if not texto: return texto
    pad_len = 16 - (len(texto) % 16)
    texto_pad = texto + (chr(pad_len) * pad_len)
    cipher = Cipher(algorithms.AES(CLAVE_AES), modes.ECB(), backend=default_backend())
    encryptor = cipher.encryptor()
    cifrado = encryptor.update(texto_pad.encode()) + encryptor.finalize()
    return base64.b64encode(cifrado).decode()

def descifrar(texto_cifrado: str) -> str:
    if not texto_cifrado: return texto_cifrado
    try:
        cipher = Cipher(algorithms.AES(CLAVE_AES), modes.ECB(), backend=default_backend())
        decryptor = cipher.decryptor()
        texto_pad = decryptor.update(base64.b64decode(texto_cifrado)) + decryptor.finalize()
        pad_len = texto_pad[-1]
        return texto_pad[:-pad_len].decode()
    except:
        return texto_cifrado

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
        cedula_cifrada = cifrar(datos.cedula)
        cursor.execute(
            "INSERT INTO pacientes (nombre, cedula, telefono, correo, contrasena) "
            "VALUES (%s, %s, %s, %s, %s)",
            (datos.nombre, cedula_cifrada, datos.telefono, datos.correo, datos.contrasena),
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
        identificador_cifrado = cifrar(datos.identificador)
        cursor.execute(
            "SELECT id, nombre, cedula FROM pacientes WHERE cedula = %s AND contrasena = %s",
            (identificador_cifrado, datos.contrasena),
        )
        fila = cursor.fetchone()
        if not fila:
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        return {"id": fila[0], "nombre": fila[1], "cedula": descifrar(fila[2])}
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
        return {
            "id": fila[0],
            "usuario": fila[1], 
            "rol": fila[2],
            "access_token": "admin_secreto_123",
            "token_type": "bearer"
            }
    finally:
        cursor.close()
        conexion.close()


@app.get("/api/pacientes/buscar")
def buscar_paciente(cedula: str):
    """Búsqueda de un paciente por número de cédula (usada en recepción)."""
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()
    try:
        # Modificación %s para parametrizar la busqueda
        cedula_cifrada = cifrar(cedula)
        consulta = "SELECT id, nombre, cedula, telefono, correo FROM pacientes WHERE cedula = %s"
        cursor.execute(consulta, (cedula_cifrada,))
        filas = cursor.fetchall()
        resultados = []
        for f in filas:
            dic = fila_a_dict(cursor, f)
            dic["cedula"] = descifrar(dic["cedula"])
            resultados.append(dic)
        return resultados
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
        diagnostico_cifrado = cifrar(datos.diagnostico)
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
def obtener_cita(cita_id: int):
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

        dic = fila_a_dict(cursor, fila)
        if dic.get("diagnostico"):
            dic["diagnostico"] = descifrar(dic["diagnostico"])
        return dic
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

@app.get("/api/admin/pacientes", dependencies=[Depends(verificar_admin)])
def listar_todos_los_pacientes():
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
        # Iterar sobre todas las filas y descifrar los campos confidenciales
        resultados = []
        for f in filas:
            dic = fila_a_dict(cursor, f)
            if dic.get("cedula"):
                dic["cedula"] = descifrar(dic["cedula"])
            if dic.get("diagnostico"):
                dic["diagnostico"] = descifrar(dic["diagnostico"])
            resultados.append(dic)
        return resultados
    finally:
        cursor.close()
        conexion.close()


@app.get("/api/salud")
def salud():
    return {"estado": "ok", "servicio": "VidaPlena API"}
