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

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from passlib.context import CryptContext

from app import database

from app.crypto_utils import cifrar, descifrar



app = FastAPI(
    title="VidaPlena API",
    description="Red de Clínicas VidaPlena — aplicación del taller de Seguridad de Datos (UMNG).",
    version="1.0.0",
)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ADMIN_API_KEY = "vidaplenaAD-2026"  # clave simple para el taller

def verificar_admin(x_admin_key: str = Header(...)):
    if x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="No autorizado")

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
# Pacientes
# ---------------------------------------------------------------------------

@app.post("/api/pacientes/registro")
def registrar_paciente(datos: PacienteRegistro):
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute(
        "INSERT INTO pacientes (nombre, cedula, telefono, correo, contrasena) "
        "VALUES (%s, %s, %s, %s, %s)",
        (datos.nombre, cifrar(datos.cedula), datos.telefono, datos.correo, pwd_context.hash(datos.contrasena)),
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
        cursor.execute("SELECT id, nombre, cedula, contrasena FROM pacientes")
        filas = cursor.fetchall()
        fila = next((f for f in filas if descifrar(f[2]) == datos.identificador), None)
        if not fila or not pwd_context.verify(datos.contrasena, fila[3]):
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
            "SELECT id, usuario, rol, contrasena FROM usuarios_admin WHERE usuario = %s",
            (datos.identificador,),
        )
        fila = cursor.fetchone()
        if not fila or not pwd_context.verify(datos.contrasena, fila[3]):
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        return {"id": fila[0], "usuario": fila[1], "rol": fila[2]}
    finally:
        cursor.close()
        conexion.close()


@app.get("/api/pacientes/buscar")
def buscar_paciente(cedula: str):
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT id, nombre, cedula, telefono, correo FROM pacientes")
        filas = cursor.fetchall()
        resultado = []
        for f in filas:
            fila_dict = fila_a_dict(cursor, f)
            fila_dict["cedula"] = descifrar(fila_dict["cedula"])
            if fila_dict["cedula"] == cedula:
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
        (datos.paciente_id, datos.fecha, datos.hora, datos.medico,
        datos.motivo_consulta, cifrar(datos.diagnostico)),
        )
        conexion.commit()
        return {"id": cursor.lastrowid, "mensaje": "Cita creada"}
    finally:
        cursor.close()
        conexion.close()


@app.get("/api/citas/{cita_id}")
def obtener_cita(cita_id: int, cedula_solicitante: str):
    """Detalle completo de una cita, incluido el diagnóstico."""
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute(
            "SELECT c.id, c.paciente_id, p.nombre, p.cedula, c.fecha, c.hora, c.medico, "
            "c.motivo_consulta, c.diagnostico "
            "FROM citas c JOIN pacientes p ON p.id = c.paciente_id "
            "WHERE c.id = %s",
            (cita_id,),
        )
        fila = cursor.fetchone()
        if not fila:
            raise HTTPException(status_code=404, detail="Cita no encontrada")

        datos = fila_a_dict(cursor, fila)
        datos["cedula"] = descifrar(datos["cedula"])
        datos["diagnostico"] = descifrar(datos["diagnostico"])
        if datos["cedula"] != cedula_solicitante:
            raise HTTPException(status_code=403, detail="No autorizado para ver esta cita")

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
def listar_todos_los_pacientes(admin: None = Depends(verificar_admin)):
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
        resultados = [fila_a_dict(cursor, f) for f in filas]
        for r in resultados:
            r["cedula"] = descifrar(r["cedula"])
            r["diagnostico"] = descifrar(r["diagnostico"])
        return resultados
    finally:
        cursor.close()
        conexion.close()


@app.get("/api/salud")
def salud():
    return {"estado": "ok", "servicio": "VidaPlena API"}
