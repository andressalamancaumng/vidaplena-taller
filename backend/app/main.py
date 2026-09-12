"""VidaPlena: API del taller, con autenticación, autorización y datos protegidos."""

import logging
from contextlib import asynccontextmanager
from datetime import date, time, timedelta
from typing import Annotated

from cryptography.exceptions import InvalidTag
from fastapi import FastAPI, HTTPException, Request, Path
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from mysql.connector import Error as MySQLError, IntegrityError
from pydantic import BaseModel, Field, field_validator

from app import database
from app.preparar_db import preparar_base
from app.seguridad import (
    SesionActual, SoloAdmin, cifrar, descifrar, emitir_sesion, hash_contrasena,
    hash_ficticio, indice_cedula, verificar_contrasena, verificar_propiedad,
)

logger = logging.getLogger("vidaplena")


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    preparar_base()  # La API no acepta peticiones antes de terminar la migración.
    hash_ficticio()  # Precalienta el hash usado para identificadores inexistentes.
    yield


app = FastAPI(title="VidaPlena API", version="2.0.0", lifespan=ciclo_de_vida)
# Angular y la API comparten origen mediante nginx; no se necesita CORS abierto.
IdPositivo = Annotated[int, Path(gt=0)]


@app.exception_handler(MySQLError)
async def error_base(request: Request, error: MySQLError):
    logger.error("Error de base de datos: codigo=%s", error.errno)
    if isinstance(error, IntegrityError):
        return JSONResponse(status_code=409, content={"detail": "Registro duplicado o referencia inválida"})
    return JSONResponse(status_code=503, content={"detail": "Base de datos temporalmente no disponible"})


@app.exception_handler(InvalidTag)
async def error_integridad(request: Request, error: InvalidTag):
    logger.error("Se detectó un dato cifrado alterado o una llave incorrecta")
    return JSONResponse(status_code=500, content={"detail": "No se pudo verificar la integridad del dato"})


@app.exception_handler(RequestValidationError)
async def entrada_invalida(request: Request, error: RequestValidationError):
    # No devolver el cuerpo original: puede contener una contraseña o información médica.
    campos = sorted({str(item["loc"][-1]) for item in error.errors()})
    return JSONResponse(status_code=422, content={"detail": "Revisa los campos: " + ", ".join(campos)})


@app.middleware("http")
async def proteger_respuesta(request: Request, siguiente):
    respuesta = await siguiente(request)
    respuesta.headers["Cache-Control"] = "no-store"
    respuesta.headers["X-Content-Type-Options"] = "nosniff"
    if respuesta.status_code in (401, 403):
        # Registrar el rechazo, pero nunca contraseñas, JWT, cédulas ni diagnósticos.
        logger.warning("Acceso rechazado: metodo=%s estado=%s", request.method, respuesta.status_code)
    return respuesta


class EntradaContrasena(BaseModel):
    contrasena: str = Field(min_length=1, max_length=72)

    @field_validator("contrasena")
    @classmethod
    def limite_bcrypt(cls, valor):
        if len(valor.encode("utf-8")) > 72:
            raise ValueError("bcrypt admite como máximo 72 bytes UTF-8")
        return valor


class LoginRequest(EntradaContrasena):
    identificador: str = Field(min_length=1, max_length=100)


class PacienteRegistro(EntradaContrasena):
    nombre: str = Field(min_length=1, max_length=150)
    cedula: str = Field(pattern=r"^[0-9]{5,20}$")
    telefono: str | None = Field(default=None, max_length=20)
    correo: str | None = Field(default=None, max_length=150)
    contrasena: str = Field(min_length=12, max_length=72)


class CitaCreate(BaseModel):
    paciente_id: int = Field(gt=0)
    fecha: date
    hora: time
    medico: str = Field(min_length=1, max_length=150)
    motivo_consulta: str | None = Field(default=None, max_length=255)
    diagnostico: str | None = Field(default=None, max_length=5000)


def presentar(fila):
    """Descifra únicamente después del control de acceso; normaliza TIME de MySQL."""
    resultado = dict(fila)
    if "cedula" in resultado:
        resultado["cedula"] = descifrar(resultado["cedula"], "pacientes.cedula")
    if "diagnostico" in resultado:
        resultado["diagnostico"] = descifrar(resultado["diagnostico"], "citas.diagnostico")
    if isinstance(resultado.get("hora"), timedelta):
        segundos = int(resultado["hora"].total_seconds())
        resultado["hora"] = f"{segundos // 3600:02d}:{segundos % 3600 // 60:02d}:{segundos % 60:02d}"
    return resultado


def autenticar(fila, contrasena, tipo):
    almacenada = fila["contrasena"] if fila else hash_ficticio()
    if not verificar_contrasena(contrasena, almacenada) or fila is None:
        raise HTTPException(401, "Credenciales inválidas", headers={"WWW-Authenticate": "Bearer"})
    resultado = presentar({k: v for k, v in fila.items() if k != "contrasena"})
    return {**resultado, **emitir_sesion(fila["id"], tipo)}


@app.post("/api/pacientes/registro", status_code=201)
def registrar_paciente(datos: PacienteRegistro):
    paciente_id = database.ejecutar(
        "INSERT INTO pacientes (nombre, cedula, cedula_indice, telefono, correo, contrasena) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (datos.nombre, cifrar(datos.cedula, "pacientes.cedula"), indice_cedula(datos.cedula),
         datos.telefono, datos.correo, hash_contrasena(datos.contrasena)),
    )
    return {"id": paciente_id, "mensaje": "Paciente registrado"}


@app.post("/api/login/paciente")
def login_paciente(datos: LoginRequest):
    fila = database.consultar(
        "SELECT id, nombre, cedula, contrasena FROM pacientes WHERE cedula_indice = %s",
        (indice_cedula(datos.identificador),), uno=True,
    )
    return autenticar(fila, datos.contrasena, "paciente")


@app.post("/api/login/admin")
def login_admin(datos: LoginRequest):
    fila = database.consultar(
        "SELECT id, usuario, rol, contrasena FROM usuarios_admin WHERE usuario = %s",
        (datos.identificador,), uno=True,
    )
    return autenticar(fila, datos.contrasena, "admin")


@app.post("/api/logout")
def cerrar_sesion(usuario: SesionActual):
    database.ejecutar("DELETE FROM sesiones WHERE id = %s", (usuario.sesion_id,))
    return {"mensaje": "Sesión cerrada"}


@app.get("/api/pacientes/buscar")
def buscar_paciente(cedula: str, usuario: SoloAdmin):
    # F1: %s separa la instrucción SQL de los datos. F2: recepción requiere administrador.
    filas = database.consultar(
        "SELECT id, nombre, cedula, telefono, correo FROM pacientes WHERE cedula_indice = %s",
        (indice_cedula(cedula),),
    )
    return [presentar(fila) for fila in filas]


@app.post("/api/citas", status_code=201)
def crear_cita(datos: CitaCreate, usuario: SesionActual):
    verificar_propiedad(usuario, datos.paciente_id)
    cita_id = database.ejecutar(
        "INSERT INTO citas (paciente_id, fecha, hora, medico, motivo_consulta, diagnostico) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (datos.paciente_id, datos.fecha, datos.hora, datos.medico,
         datos.motivo_consulta, cifrar(datos.diagnostico, "citas.diagnostico")),
    )
    return {"id": cita_id, "mensaje": "Cita creada"}


@app.get("/api/citas/{cita_id}")
def obtener_cita(cita_id: IdPositivo, usuario: SesionActual):
    fila = database.consultar(
        "SELECT c.id, c.paciente_id, p.nombre, c.fecha, c.hora, c.medico, "
        "c.motivo_consulta, c.diagnostico FROM citas c JOIN pacientes p ON p.id = c.paciente_id "
        "WHERE c.id = %s", (cita_id,), uno=True,
    )
    if fila is None:
        raise HTTPException(404, "Cita no encontrada")
    verificar_propiedad(usuario, fila["paciente_id"])  # F3: validar ANTES de descifrar o devolver.
    return presentar(fila)


@app.get("/api/citas/paciente/{paciente_id}")
def citas_de_paciente(paciente_id: IdPositivo, usuario: SesionActual):
    verificar_propiedad(usuario, paciente_id)
    filas = database.consultar(
        "SELECT id, fecha, hora, medico, motivo_consulta FROM citas WHERE paciente_id = %s",
        (paciente_id,),
    )
    return [presentar(fila) for fila in filas]


@app.get("/api/facturas/paciente/{paciente_id}")
def facturas_de_paciente(paciente_id: IdPositivo, usuario: SesionActual):
    verificar_propiedad(usuario, paciente_id)
    return database.consultar(
        "SELECT id, servicio, valor, estado_pago, dias_mora FROM facturas WHERE paciente_id = %s",
        (paciente_id,),
    )


@app.get("/api/admin/pacientes")
def listar_todos_los_pacientes(usuario: SoloAdmin):
    filas = database.consultar(
        "SELECT p.id, p.nombre, p.cedula, p.telefono, p.correo, "
        "c.fecha, c.motivo_consulta, c.diagnostico "
        "FROM pacientes p LEFT JOIN citas c ON c.id = ("
        "SELECT ultima.id FROM citas ultima WHERE ultima.paciente_id = p.id "
        "ORDER BY ultima.fecha DESC, ultima.hora DESC, ultima.id DESC LIMIT 1) ORDER BY p.id"
    )
    return [presentar(fila) for fila in filas]


@app.get("/api/salud")
def salud():
    return {"estado": "ok", "servicio": "VidaPlena API"}
