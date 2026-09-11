"""
Cifrado a nivel de aplicación para campos sensibles (Hallazgo 5).

Usa Fernet, de la librería `cryptography` — cifrado simétrico autenticado:
además de ocultar el contenido, detecta si el dato fue alterado (si alguien
edita el valor cifrado directamente en la base de datos, descifrar() falla
en vez de devolver datos corruptos silenciosamente).

Gestión de la llave: la llave NUNCA se escribe en este archivo ni en
ningún otro archivo de código. Se lee desde la variable de entorno
CIFRADO_KEY (definida en docker-compose.yml para este taller). En un
sistema real, esa llave viviría en un gestor de secretos (AWS Secrets
Manager, HashiCorp Vault, etc.) y se rotaría periódicamente — nunca en un
archivo de configuración versionado en git tal como está aquí; lo dejamos
así solo por simplicidad pedagógica del taller.
"""

import os

from cryptography.fernet import Fernet, InvalidToken

_CLAVE = os.getenv("CIFRADO_KEY")
if not _CLAVE:
    raise RuntimeError(
        "Falta la variable de entorno CIFRADO_KEY (ver docker-compose.yml)."
    )

_fernet = Fernet(_CLAVE.encode())


def cifrar(texto):
    """Cifra un texto plano. None pasa intacto (campos opcionales)."""
    if texto is None:
        return None
    return _fernet.encrypt(texto.encode()).decode()


def descifrar(texto):
    """Descifra un texto cifrado con cifrar(). None pasa intacto."""
    if texto is None:
        return None
    return _fernet.decrypt(texto.encode()).decode()


def ya_esta_cifrado(texto) -> bool:
    """
    Heurística usada solo por la migración al arrancar: intenta descifrar
    y, si funciona, asume que el valor ya estaba cifrado. Si falla, se
    trata como texto plano pendiente de migrar.
    """
    if texto is None:
        return False
    try:
        _fernet.decrypt(texto.encode())
        return True
    except (InvalidToken, ValueError):
        return False
