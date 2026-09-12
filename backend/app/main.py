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

from fastapi import FastAPI, HTTPException

from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

import bcrypt

from app import database


app = FastAPI(
    title="VidaPlena API",
    description="Red de Clínicas VidaPlena — aplicación del taller de Seguridad de Datos (UMNG).",
    version="1.0.0",
)

# CORS abierto a propósito para simplificar el taller (el frontend Angular
# corre en un puerto distinto al backend). Esto no es una de las fallas
# que se pide corregir, pero en un sistema real tampoco se dejaría así.

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

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


def generar_hash(contrasena):
    return bcrypt.hashpw(
        contrasena.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


def verificar_contrasena(contrasena, hash_guardado):
    return bcrypt.checkpw(
        contrasena.encode("utf-8"),
        hash_guardado.encode("utf-8")
    )


# ---------------------------------------------------------------------------
# Pacientes
# ---------------------------------------------------------------------------

@app.post("/api/pacientes/registro")
def registrar_paciente(datos: PacienteRegistro):
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()

    try:
        # La contraseña nunca se guarda directamente.
        hash_contrasena = generar_hash(datos.contrasena)

        cursor.execute(
            "INSERT INTO pacientes "
            "(nombre, cedula, telefono, correo, contrasena) "
            "VALUES (%s, %s, %s, %s, %s)",
            (
                datos.nombre,
                datos.cedula,
                datos.telefono,
                datos.correo,
                hash_contrasena,
            ),
        )

        conexion.commit()

        return {
            "id": cursor.lastrowid,
            "mensaje": "Paciente registrado"
        }

    finally:
        cursor.close()
        conexion.close()


# ---------------------------------------------------------------------------
# Login de pacientes
# ---------------------------------------------------------------------------

@app.post("/api/login/paciente")
def login_paciente(datos: LoginRequest):
    global paciente_actual

    conexion = database.obtener_conexion()
    cursor = conexion.cursor()

    try:
        # Primero buscamos solamente por cédula.
        # No comparamos la contraseña directamente en MySQL.
        cursor.execute(
            "SELECT id, nombre, cedula, contrasena "
            "FROM pacientes WHERE cedula = %s",
            (datos.identificador,),
        )

        fila = cursor.fetchone()

        # La contraseña se verifica utilizando bcrypt.
        if not fila or not verificar_contrasena(
            datos.contrasena,
            fila[3]
        ):
            raise HTTPException(
                status_code=401,
                detail="Credenciales inválidas"
            )

        paciente_actual = {
            "id": fila[0],
            "nombre": fila[1],
            "cedula": fila[2]
        }

        return paciente_actual

    finally:
        cursor.close()
        conexion.close()


# ---------------------------------------------------------------------------
# Login de administradores
# ---------------------------------------------------------------------------

@app.post("/api/login/admin")
def login_admin(datos: LoginRequest):
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()

    try:
        # Primero buscamos al administrador por usuario.
        cursor.execute(
            "SELECT id, usuario, rol, contrasena "
            "FROM usuarios_admin WHERE usuario = %s",
            (datos.identificador,),
        )

        fila = cursor.fetchone()

        # Verificamos la contraseña utilizando bcrypt.
        if not fila or not verificar_contrasena(
            datos.contrasena,
            fila[3]
        ):
            raise HTTPException(
                status_code=401,
                detail="Credenciales inválidas"
            )

        # Verificamos que realmente tenga rol de administrador.
        if fila[2] != "administrador":
            raise HTTPException(
                status_code=403,
                detail="No eres administrador"
            )

        administrador_actual = {
            "id": fila[0],
            "usuario": fila[1],
            "rol": fila[2]
        }

        return administrador_actual

    finally:
        cursor.close()
        conexion.close()


# ---------------------------------------------------------------------------
# Buscar paciente
# ---------------------------------------------------------------------------

@app.get("/api/pacientes/buscar")
def buscar_paciente(cedula: str):
    """Búsqueda de un paciente por número de cédula (usada en recepción)."""

    conexion = database.obtener_conexion()
    cursor = conexion.cursor()

    try:
        consulta = (
            "SELECT id, nombre, cedula, telefono, correo "
            "FROM pacientes WHERE cedula = %s"
        )

        cursor.execute(consulta, (cedula,))

        filas = cursor.fetchall()

        return [
            fila_a_dict(cursor, fila)
            for fila in filas
        ]

    finally:
        cursor.close()
        conexion.close()


# ---------------------------------------------------------------------------
# MIGRACIÓN TEMPORAL
@app.post("/api/migrar-contrasenas")
def migrar_contrasenas():
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()

    try:
        cursor.execute(
            "SELECT id, contrasena FROM pacientes"
        )

        pacientes = cursor.fetchall()

        for paciente in pacientes:
            nuevo_hash = generar_hash(paciente[1])

            cursor.execute(
                "UPDATE pacientes SET contrasena = %s WHERE id = %s",
                (nuevo_hash, paciente[0])
            )

        cursor.execute(
            "SELECT id, contrasena FROM usuarios_admin"
        )

        administradores = cursor.fetchall()

        for administrador in administradores:
            nuevo_hash = generar_hash(administrador[1])

            cursor.execute(
                "UPDATE usuarios_admin SET contrasena = %s WHERE id = %s",
                (nuevo_hash, administrador[0])
            )

        conexion.commit()

        return {"mensaje": "Contraseñas migradas correctamente"}

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
             datos.motivo_consulta, datos.diagnostico),
        )
        conexion.commit()
        return {"id": cursor.lastrowid, "mensaje": "Cita creada"}
    finally:
        cursor.close()
        conexion.close()


@app.get("/api/citas/{cita_id}")
def obtener_cita(cita_id: int):
    """Detalle completo de una cita, incluido el diagnóstico."""

    if paciente_actual is None:
        raise HTTPException(
            status_code=401,
            detail="Debes iniciar sesión"
        )

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
            raise HTTPException(
                status_code=404,
                detail="Cita no encontrada"
            )

        if fila[1] != paciente_actual["id"]:
            raise HTTPException(
                status_code=403,
                detail="No tienes permiso para consultar esta cita"
            )

        return fila_a_dict(cursor, fila)

    finally:
        cursor.close()
        conexion.close()


@app.get("/api/citas/paciente/{paciente_id}")
def citas_de_paciente(paciente_id: int):

    if paciente_actual is None:
        raise HTTPException(
            status_code=401,
            detail="Debes iniciar sesión"
        )

    if paciente_id != paciente_actual["id"]:
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para consultar estas citas"
        )

    conexion = database.obtener_conexion()
    cursor = conexion.cursor()

    try:
        cursor.execute(
            "SELECT id, fecha, hora, medico, motivo_consulta "
            "FROM citas WHERE paciente_id = %s",
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
def listar_todos_los_pacientes():
    """
    Vista administrativa: todos los pacientes con su última consulta y
    diagnóstico, pensada para el personal de la clínica.
    """
    if administrador_actual is None:
        raise HTTPException(
            status_code=401,
            detail="Debes iniciar sesión como administrador"
    )
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
        return [fila_a_dict(cursor, f) for f in filas]
    finally:
        cursor.close()
        conexion.close()


@app.get("/api/salud")
def salud():
    return {"estado": "ok", "servicio": "VidaPlena API"}
