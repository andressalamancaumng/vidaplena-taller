"""Controles reutilizables de las capas Aplicación y Datos (sesiones 3, 5 y 7–8)."""

import base64
import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Annotated, Literal

import bcrypt
import jwt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import database

MINUTOS_SESION = 30
EMISOR = "vidaplena"
AUDIENCIA = "vidaplena-api"
bearer = HTTPBearer(auto_error=False)


@lru_cache
def llaves():
    """Falla al iniciar si faltan llaves; nunca inventa reemplazos ni usa valores públicos."""
    valores = {}
    for nombre in ("DATA_KEY", "INDEX_KEY", "JWT_KEY"):
        try:
            llave = base64.b64decode(os.environ[nombre], altchars=b"-_", validate=True)
        except (KeyError, ValueError) as error:
            raise RuntimeError(f"Configura {nombre} con scripts/configurar.py") from error
        if len(llave) != 32:
            raise RuntimeError(f"{nombre} debe representar exactamente 32 bytes")
        valores[nombre] = llave
    if len(set(valores.values())) != 3:
        raise RuntimeError("El cifrado, el índice y la firma necesitan llaves distintas")
    return valores


def hash_contrasena(contrasena: str) -> str:
    # bcrypt incorpora una sal aleatoria por contraseña y un costo de trabajo de 12.
    entrada = contrasena.encode("utf-8")
    if not 1 <= len(entrada) <= 72:
        raise ValueError("La contraseña debe ocupar entre 1 y 72 bytes UTF-8")
    return bcrypt.hashpw(entrada, bcrypt.gensalt(rounds=12)).decode("ascii")


@lru_cache
def hash_ficticio():
    """Iguala el trabajo de bcrypt cuando el identificador no existe."""
    return hash_contrasena(secrets.token_urlsafe(32))


def verificar_contrasena(contrasena: str, almacenada: str) -> bool:
    entrada = contrasena.encode("utf-8")
    if not 1 <= len(entrada) <= 72:
        return False
    try:
        return bcrypt.checkpw(entrada, almacenada.encode("ascii"))
    except (ValueError, UnicodeError):
        return False  # Una cadena en texto plano nunca se acepta como hash.


def cifrar(valor: str | None, contexto: str) -> str | None:
    if valor is None:
        return None
    # Un nonce nuevo evita reutilizar el mismo cifrado. GCM también detecta alteraciones.
    nonce = secrets.token_bytes(12)
    cifrado = AESGCM(llaves()["DATA_KEY"]).encrypt(
        nonce, valor.encode("utf-8"), contexto.encode("utf-8")
    )
    return "v1:" + base64.urlsafe_b64encode(nonce + cifrado).decode("ascii")


def descifrar(valor: str | None, contexto: str) -> str | None:
    if valor is None:
        return None
    if not valor.startswith("v1:"):
        raise ValueError("Dato sin migrar: no se admite texto plano como cifrado")
    contenido = base64.b64decode(valor[3:], altchars=b"-_", validate=True)
    if len(contenido) < 28:
        raise ValueError("Cifrado incompleto")
    return AESGCM(llaves()["DATA_KEY"]).decrypt(
        contenido[:12], contenido[12:], contexto.encode("utf-8")
    ).decode("utf-8")


def indice_cedula(cedula: str) -> str:
    """Índice de igualdad: permite buscar sin descifrar toda la tabla ni guardar la cédula."""
    return hmac.new(llaves()["INDEX_KEY"], cedula.encode("utf-8"), hashlib.sha256).hexdigest()


def emitir_sesion(usuario_id: int, tipo: Literal["paciente", "admin"]) -> dict:
    ahora = datetime.now(timezone.utc)
    expira = ahora + timedelta(minutes=MINUTOS_SESION)
    identificador = secrets.token_hex(32)
    claims = {
        "sub": str(usuario_id), "tipo": tipo, "jti": identificador,
        "iat": ahora, "exp": expira, "iss": EMISOR, "aud": AUDIENCIA,
    }
    token = jwt.encode(claims, llaves()["JWT_KEY"], algorithm="HS256")
    with database.transaccion() as cursor:
        cursor.execute("DELETE FROM sesiones WHERE expira <= UTC_TIMESTAMP()")
        cursor.execute(
            "INSERT INTO sesiones (id, usuario_id, tipo, expira) VALUES (%s, %s, %s, %s)",
            (identificador, usuario_id, tipo, expira.replace(tzinfo=None)),
        )
    return {"access_token": token, "token_type": "bearer", "expires_in": MINUTOS_SESION * 60}


@dataclass(frozen=True)
class Usuario:
    id: int
    tipo: str
    sesion_id: str
    rol: str = ""


def no_autenticado():
    return HTTPException(401, "Sesión inválida o vencida", headers={"WWW-Authenticate": "Bearer"})


def usuario_actual(
    credencial: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Usuario:
    if credencial is None:
        raise no_autenticado()
    try:
        # El algoritmo permitido lo decide el servidor, no el encabezado enviado por el cliente.
        claims = jwt.decode(
            credencial.credentials, llaves()["JWT_KEY"], algorithms=["HS256"],
            issuer=EMISOR, audience=AUDIENCIA,
            options={"require": ["sub", "tipo", "jti", "iat", "exp", "iss", "aud"]},
        )
        usuario_id = int(claims["sub"])
        tipo = claims["tipo"]
        if tipo not in ("paciente", "admin") or usuario_id < 1:
            raise ValueError("Identidad inválida")
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise no_autenticado() from None

    sesion = database.consultar(
        "SELECT id FROM sesiones WHERE id = %s AND usuario_id = %s "
        "AND tipo = %s AND expira > UTC_TIMESTAMP()",
        (claims["jti"], usuario_id, tipo), uno=True,
    )
    if sesion is None:
        raise no_autenticado()
    if tipo == "admin":
        cuenta = database.consultar(
            "SELECT rol FROM usuarios_admin WHERE id = %s", (usuario_id,), uno=True
        )
    else:
        cuenta = database.consultar("SELECT id FROM pacientes WHERE id = %s", (usuario_id,), uno=True)
    if cuenta is None:
        raise no_autenticado()
    # Los privilegios se consultan en la base, no en localStorage ni en un ID enviado por el navegador.
    return Usuario(usuario_id, tipo, claims["jti"], cuenta.get("rol", ""))


SesionActual = Annotated[Usuario, Depends(usuario_actual)]


def exigir_admin(usuario: SesionActual) -> Usuario:
    if usuario.tipo != "admin" or usuario.rol != "administrador":
        raise HTTPException(403, "Se requiere una cuenta administradora")
    return usuario


SoloAdmin = Annotated[Usuario, Depends(exigir_admin)]


def verificar_propiedad(usuario: Usuario, paciente_id: int):
    """Una sola regla protege detalles, listados, facturas y creación de citas."""
    if usuario.tipo == "admin" and usuario.rol == "administrador":
        return
    if usuario.tipo != "paciente" or usuario.id != paciente_id:
        raise HTTPException(403, "No tienes permiso para acceder a los datos de otro paciente")
