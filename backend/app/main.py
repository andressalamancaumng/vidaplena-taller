"""
VidaPlena — API de la Red de Clínicas (SOLUCIÓN DE REFERENCIA)
----------------------------------------------------------------
Seguridad Informática — Ingeniería Multimedia, UMNG
Sesión 7 (fallas de seguridad de datos) / Sesión 8 (aplicaciones seguras)

Esta es la versión corregida de la API del taller, usada como material
del docente (NO se comparte con los estudiantes como enunciado). Corrige
las 5 fallas sembradas originalmente:

  Falla 1 (Inyección SQL)              -> buscar_paciente() usa consulta parametrizada.
  Falla 2 (Control de acceso roto)     -> /api/admin/pacientes exige rol admin (requerir_admin).
  Falla 3 (IDOR)                       -> citas y facturas verifican propiedad del recurso.
  Falla 4 (Autenticación insegura)     -> contraseñas con bcrypt + sesión con JWT.
  Falla 5 (Datos sensibles en claro)   -> cédula y diagnóstico cifrados (Fernet) en reposo.

Ver app/security.py para el detalle de cada mecanismo y app/seed.py para
el sembrado de datos de demostración (ahora en la aplicación, no en SQL
plano, porque requiere hashing/cifrado).
"""

from typing import Optional
from datetime import date, time as time_type

import mysql.connector
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app import database, security
from app.seed import sembrar_datos_demo

app = FastAPI(
    title="VidaPlena API",
    description="Red de Clínicas VidaPlena — solución de referencia (UMNG, Seguridad Informática).",
    version="2.0.0",
)

# CORS abierto a propósito para simplificar el taller (el frontend Angular
# corre en un puerto distinto al backend). No es una de las 5 fallas del
# ejercicio, pero en un sistema real tampoco se dejaría así.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def evento_arranque():
    """Siembra los datos de demostración la primera vez que arranca el contenedor."""
    sembrar_datos_demo()


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


def _verificar_propiedad_o_admin(usuario: security.UsuarioActual, paciente_id: int):
    """
    Corrige la Falla 3 (IDOR): un paciente solo puede acceder a SUS PROPIOS
    recursos (citas, facturas). Un administrador puede acceder a los de
    cualquier paciente.
    """
    if usuario.rol != "admin" and usuario.id != paciente_id:
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para acceder a la información de otro paciente.",
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
            "INSERT INTO pacientes (nombre, cedula, cedula_hash, telefono, correo, contrasena_hash) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                datos.nombre,
                security.encrypt_value(datos.cedula),
                security.hash_lookup(datos.cedula),
                datos.telefono,
                datos.correo,
                security.hash_password(datos.contrasena),
            ),
        )
        conexion.commit()
        return {"id": cursor.lastrowid, "mensaje": "Paciente registrado"}
    except mysql.connector.errors.IntegrityError:
        conexion.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un paciente registrado con esa cédula.")
    finally:
        cursor.close()
        conexion.close()


@app.post("/api/login/paciente")
def login_paciente(datos: LoginRequest):
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute(
            "SELECT id, nombre, cedula, contrasena_hash FROM pacientes WHERE cedula_hash = %s",
            (security.hash_lookup(datos.identificador),),
        )
        fila = cursor.fetchone()
        if not fila or not security.verify_password(datos.contrasena, fila[3]):
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        token = security.crear_token({"sub": str(fila[0]), "rol": "paciente"})
        return {
            "access_token": token,
            "token_type": "bearer",
            "id": fila[0],
            "nombre": fila[1],
            "cedula": security.decrypt_value(fila[2]),
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
            "SELECT id, usuario, rol, contrasena_hash FROM usuarios_admin WHERE usuario = %s",
            (datos.identificador,),
        )
        fila = cursor.fetchone()
        if not fila or not security.verify_password(datos.contrasena, fila[3]):
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        token = security.crear_token({"sub": str(fila[0]), "rol": "admin"})
        return {
            "access_token": token,
            "token_type": "bearer",
            "id": fila[0],
            "usuario": fila[1],
            "rol": fila[2],
        }
    finally:
        cursor.close()
        conexion.close()


@app.get("/api/pacientes/buscar")
def buscar_paciente(cedula: str):
    """
    Búsqueda de un paciente por número de cédula (usada en recepción, sin
    necesidad de que el personal de recepción inicie sesión como admin —
    así se comporta la aplicación original, ver el frontend /buscar).

    Corrige la Falla 1 (inyección SQL): la consulta ahora es parametrizada
    y busca por `cedula_hash` (hash determinístico), ya que la cédula se
    guarda cifrada (Fernet, Falla 5) y no es directamente comparable con
    un `=` en SQL.

    Nota de diseño para el docente: a diferencia de /api/admin/pacientes
    (Falla 2, corregida exigiendo rol admin) este endpoint intencionalmente
    NO exige autenticación, para no romper el flujo de recepción existente
    en el frontend. Si se quisiera reforzar esto (p. ej. exigir una sesión
    de "personal" separada de paciente/admin), sería una extensión más allá
    del alcance de las 5 fallas originales del taller.
    """
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute(
            "SELECT id, nombre, cedula, telefono, correo FROM pacientes WHERE cedula_hash = %s",
            (security.hash_lookup(cedula),),
        )
        filas = cursor.fetchall()
        resultados = []
        for f in filas:
            fila_dict = fila_a_dict(cursor, f)
            fila_dict["cedula"] = security.decrypt_value(fila_dict["cedula"])
            resultados.append(fila_dict)
        return resultados
    finally:
        cursor.close()
        conexion.close()


# ---------------------------------------------------------------------------
# Citas
# ---------------------------------------------------------------------------

@app.post("/api/citas")
def crear_cita(datos: CitaCreate, usuario: security.UsuarioActual = Depends(security.obtener_usuario_actual)):
    _verificar_propiedad_o_admin(usuario, datos.paciente_id)
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()
    try:
        diagnostico_cifrado = security.encrypt_value(datos.diagnostico) if datos.diagnostico else None
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
def obtener_cita(cita_id: int, usuario: security.UsuarioActual = Depends(security.obtener_usuario_actual)):
    """Detalle completo de una cita, incluido el diagnóstico. Corrige la Falla 3 (IDOR)."""
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
        resultado = fila_a_dict(cursor, fila)
        _verificar_propiedad_o_admin(usuario, resultado["paciente_id"])
        if resultado.get("diagnostico"):
            resultado["diagnostico"] = security.decrypt_value(resultado["diagnostico"])
        return resultado
    finally:
        cursor.close()
        conexion.close()


@app.get("/api/citas/paciente/{paciente_id}")
def citas_de_paciente(paciente_id: int, usuario: security.UsuarioActual = Depends(security.obtener_usuario_actual)):
    _verificar_propiedad_o_admin(usuario, paciente_id)
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
def facturas_de_paciente(paciente_id: int, usuario: security.UsuarioActual = Depends(security.obtener_usuario_actual)):
    """
    Corrige el mismo patrón de IDOR (Falla 3) presente en el endpoint de
    citas: en la versión original, este endpoint tampoco validaba
    propiedad del recurso.
    """
    _verificar_propiedad_o_admin(usuario, paciente_id)
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
def listar_todos_los_pacientes(usuario: security.UsuarioActual = Depends(security.requerir_admin)):
    """
    Vista administrativa: todos los pacientes con su última consulta y
    diagnóstico. Corrige la Falla 2 (antes, sin ninguna protección).
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
        resultados = []
        for f in filas:
            fila_dict = fila_a_dict(cursor, f)
            fila_dict["cedula"] = security.decrypt_value(fila_dict["cedula"])
            if fila_dict.get("diagnostico"):
                fila_dict["diagnostico"] = security.decrypt_value(fila_dict["diagnostico"])
            resultados.append(fila_dict)
        return resultados
    finally:
        cursor.close()
        conexion.close()


@app.get("/api/salud")
def salud():
    return {"estado": "ok", "servicio": "VidaPlena API"}
