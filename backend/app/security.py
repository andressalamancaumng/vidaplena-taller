"""
security.py

Módulo de utilidades de seguridad para VidaPlena.

Este módulo agrupa las funciones criptográficas y de autenticación que
corrigen las fallas originales de la aplicación:

  - Falla 4 (Autenticación insegura): hashing de contraseñas con bcrypt
    en lugar de almacenarlas/compararlas en texto plano.
  - Falla 2 y 3 (Control de acceso roto / IDOR): emisión y verificación
    de JWT para identificar al usuario autenticado en cada solicitud, y
    dependencias de FastAPI para exigir sesión (y rol de administrador
    cuando corresponda) en los endpoints sensibles.
  - Falla 5 (Datos sensibles sin cifrar): cifrado simétrico (Fernet) de
    campos en reposo como `cedula` y `diagnostico`, más un hash
    determinístico (HMAC-SHA256) de la cédula para permitir búsquedas y
    la restricción de unicidad sin exponer el valor en claro ni perder
    la capacidad de consulta (Fernet es no determinístico por diseño).

Las claves se leen de variables de entorno con valores por defecto
"de demostración" para que el entorno docker-compose funcione de
inmediato en un salón de clase. En un entorno productivo real estas
claves NUNCA deben quedar hardcodeadas ni compartirse en el repositorio.
"""

import os
import hmac
import hashlib
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# ---------------------------------------------------------------------------
# Configuración / claves (todas sobreescribibles por variable de entorno)
# ---------------------------------------------------------------------------

# Clave para firmar los JWT (HMAC-SHA256 / HS256).
APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "vidaplena-jwt-secret-demo-cambiar-en-produccion")

# Clave Fernet (32 bytes, base64 urlsafe) para cifrar datos sensibles en reposo.
# Debe ser una clave Fernet válida generada con Fernet.generate_key(), o bien
# se deriva de forma determinística a partir de un valor plano de 32 bytes
# para que el equipo docente pueda fijar un valor legible en docker-compose.yml.
_RAW_ENCRYPTION_KEY = os.getenv("APP_ENCRYPTION_KEY", "vidaplena-taller-clave-demo-32b!")


def _derive_fernet_key(raw: str) -> bytes:
    """Convierte un string arbitrario en una clave Fernet válida (32 bytes, base64-urlsafe)."""
    digest = hashlib.sha256(raw.encode("utf-8")).digest()  # 32 bytes
    return base64.urlsafe_b64encode(digest)


_fernet = Fernet(_derive_fernet_key(_RAW_ENCRYPTION_KEY))

# Clave para el HMAC determinístico usado como índice de búsqueda de la cédula.
APP_HMAC_KEY = os.getenv("APP_HMAC_KEY", "vidaplena-hmac-key-demo-cambiar")

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 120


# ---------------------------------------------------------------------------
# Falla 4: hashing de contraseñas (bcrypt)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Genera un hash bcrypt de la contraseña en texto plano."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica una contraseña en texto plano contra su hash bcrypt almacenado."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        # Hash corrupto o con formato inesperado: nunca autenticar.
        return False


# ---------------------------------------------------------------------------
# Falla 5: cifrado en reposo (Fernet) + hash determinístico para búsqueda
# ---------------------------------------------------------------------------

def encrypt_value(value: str) -> str:
    """Cifra un valor sensible (p. ej. cédula, diagnóstico) para guardarlo en la BD."""
    return _fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(token: str) -> str:
    """Descifra un valor previamente cifrado con encrypt_value()."""
    return _fernet.decrypt(token.encode("utf-8")).decode("utf-8")


def hash_lookup(value: str) -> str:
    """
    Hash determinístico (HMAC-SHA256) usado SOLO como índice de búsqueda /
    restricción de unicidad (por ejemplo, para la cédula). No reemplaza el
    cifrado: el valor en claro nunca se guarda, pero al ser determinístico
    permite localizar el registro sin descifrar toda la tabla.
    """
    return hmac.new(APP_HMAC_KEY.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# Falla 2 y 3: autenticación con JWT y dependencias de autorización
# ---------------------------------------------------------------------------

def crear_token(datos: dict) -> str:
    """Crea un JWT firmado con los datos indicados (sub, rol, etc.) y expiración."""
    a_codificar = datos.copy()
    expiracion = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    a_codificar.update({"exp": expiracion})
    return jwt.encode(a_codificar, APP_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decodificar_token(token: str) -> dict:
    """Decodifica y valida un JWT. Lanza HTTPException 401 si no es válido o expiró."""
    try:
        return jwt.decode(token, APP_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesión expiró, por favor inicie sesión nuevamente.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación inválido.",
        )


_bearer_scheme = HTTPBearer(auto_error=False)


class UsuarioActual:
    """Representa al usuario autenticado extraído del JWT."""

    def __init__(self, id: int, rol: str):
        self.id = id
        self.rol = rol


def obtener_usuario_actual(
    credenciales: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> UsuarioActual:
    """
    Dependencia de FastAPI que exige un JWT válido en el header
    `Authorization: Bearer <token>` y devuelve el usuario autenticado.
    Úsese en cualquier endpoint que requiera sesión iniciada.
    """
    if credenciales is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó un token de autenticación.",
        )
    payload = decodificar_token(credenciales.credentials)
    try:
        return UsuarioActual(id=int(payload["sub"]), rol=payload["rol"])
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación con formato inválido.",
        )


def requerir_admin(usuario: UsuarioActual = Depends(obtener_usuario_actual)) -> UsuarioActual:
    """
    Dependencia de FastAPI que, además de exigir sesión iniciada, exige que el
    usuario autenticado tenga rol de administrador. Corrige la Falla 2
    (endpoint /api/admin/pacientes sin protección alguna).
    """
    if usuario.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta acción requiere privilegios de administrador.",
        )
    return usuario
