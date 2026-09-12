import os
from cryptography.fernet import Fernet

_key = os.getenv("FERNET_KEY")
if not _key:
    raise RuntimeError("Falta la variable de entorno FERNET_KEY")

_fernet = Fernet(_key.encode())


def cifrar(texto: str | None) -> str | None:
    """Cifra un string. Devuelve None si el valor de entrada es None."""
    if texto is None:
        return None
    return _fernet.encrypt(texto.encode()).decode()


def descifrar(texto_cifrado: str | None) -> str | None:
    """Descifra un string. Devuelve None si el valor de entrada es None."""
    if texto_cifrado is None:
        return None
    return _fernet.decrypt(texto_cifrado.encode()).decode()