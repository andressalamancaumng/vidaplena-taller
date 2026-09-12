"""Genera configuración local una sola vez; no imprime ni sobrescribe secretos."""

import base64
import os
import secrets
from pathlib import Path


def crear_configuracion(destino: Path):
    valores = {
        "DB_PASSWORD": secrets.token_urlsafe(32),
        "DB_ROOT_PASSWORD": secrets.token_urlsafe(32),
        **{nombre: base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")
           for nombre in ("DATA_KEY", "INDEX_KEY", "JWT_KEY")},
        "CARGAR_DEMO": "true",
    }
    # O_EXCL impide reemplazar accidentalmente las llaves que protegen una base existente.
    descriptor = os.open(destino, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
        archivo.write("# Solo laboratorio local. No publicar ni perder este archivo.\n")
        archivo.writelines(f"{nombre}={valor}\n" for nombre, valor in valores.items())


if __name__ == "__main__":
    destino = Path(__file__).resolve().parents[1] / ".env"
    try:
        crear_configuracion(destino)
    except FileExistsError:
        print("El .env ya existe: se conservan sus llaves y contraseñas.")
    else:
        print("Configuración creada. Conserva una copia privada del .env; no lo subas a GitHub.")
