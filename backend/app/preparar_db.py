"""Migra el volumen original sin borrarlo y prepara instalaciones nuevas del taller."""

import hmac
import logging
import os
import re
from pathlib import Path

from app import database
from app.datos_demo import cargar_demo
from app.seguridad import cifrar, descifrar, hash_contrasena, indice_cedula, llaves

COMPROBANTE = "vidaplena:seguridad:v1"
PATRON_BCRYPT = re.compile(r"^\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}$")


def proteger_contrasena(valor):
    # Evita volver a aplicar hash al reiniciar o retomar una migración.
    return valor if PATRON_BCRYPT.fullmatch(valor) else hash_contrasena(valor)


def proteger_campo(valor, contexto):
    if valor is None:
        return None
    if valor.startswith("v1:"):
        descifrar(valor, contexto)  # Verifica la llave antes de conservar el cifrado existente.
        return valor
    return cifrar(valor, contexto)


def preparar_base():
    llaves()
    with database.transaccion() as cursor:
        # El bloqueo se libera al cerrar la conexión; evita migraciones simultáneas.
        cursor.execute("SELECT GET_LOCK('vidaplena_migracion', 30) AS obtenido")
        if cursor.fetchone()["obtenido"] != 1:
            raise RuntimeError("Otra instancia está preparando la base de datos")

        esquema = Path(__file__).resolve().parents[1] / "init-db" / "01_schema.sql"
        for instruccion in esquema.read_text(encoding="utf-8").split(";"):
            if re.sub(r"--[^\n]*", "", instruccion).strip():
                cursor.execute(instruccion)

        cursor.execute("SELECT comprobante, indice_comprobante FROM seguridad_estado WHERE id = 1")
        estado = cursor.fetchone()
        if estado:
            if (descifrar(estado["comprobante"], "seguridad_estado") != COMPROBANTE
                    or not hmac.compare_digest(estado["indice_comprobante"], indice_cedula(COMPROBANTE))):
                raise RuntimeError("Las llaves no corresponden a esta base; restaura el .env original")
            return

        cursor.execute(
            "SELECT COLUMN_NAME, CHARACTER_MAXIMUM_LENGTH FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'pacientes'"
        )
        columnas = {fila["COLUMN_NAME"]: fila["CHARACTER_MAXIMUM_LENGTH"] for fila in cursor.fetchall()}
        if columnas["cedula"] < 255:
            cursor.execute("ALTER TABLE pacientes MODIFY cedula VARCHAR(255) NOT NULL")
        if "cedula_indice" not in columnas:
            # Se permite NULL mientras se migran las filas antiguas, sin borrar su índice único.
            cursor.execute("ALTER TABLE pacientes ADD COLUMN cedula_indice CHAR(64) NULL UNIQUE")

        # Todo el DDL precede a los datos: MySQL confirma ALTER automáticamente.
        cursor.execute("SELECT id, cedula, cedula_indice, contrasena FROM pacientes")
        for fila in cursor.fetchall():
            cedula = fila["cedula"]
            if cedula.startswith("v1:"):
                cedula = descifrar(cedula, "pacientes.cedula")
            indice = indice_cedula(cedula)
            if fila["cedula_indice"] and not hmac.compare_digest(fila["cedula_indice"], indice):
                raise RuntimeError("El índice de cédula no corresponde a la llave configurada")
            cursor.execute(
                "UPDATE pacientes SET cedula = %s, cedula_indice = %s, contrasena = %s WHERE id = %s",
                (proteger_campo(fila["cedula"], "pacientes.cedula"), indice,
                 proteger_contrasena(fila["contrasena"]), fila["id"]),
            )
        cursor.execute("SELECT id, contrasena FROM usuarios_admin")
        for fila in cursor.fetchall():
            cursor.execute(
                "UPDATE usuarios_admin SET contrasena = %s WHERE id = %s",
                (proteger_contrasena(fila["contrasena"]), fila["id"]),
            )
        cursor.execute("SELECT id, diagnostico FROM citas")
        for fila in cursor.fetchall():
            cursor.execute(
                "UPDATE citas SET diagnostico = %s WHERE id = %s",
                (proteger_campo(fila["diagnostico"], "citas.diagnostico"), fila["id"]),
            )
        cursor.execute(
            "SELECT (SELECT COUNT(*) FROM pacientes) + (SELECT COUNT(*) FROM usuarios_admin) "
            "+ (SELECT COUNT(*) FROM citas) + (SELECT COUNT(*) FROM facturas) AS total"
        )
        if cursor.fetchone()["total"] == 0 and os.getenv("CARGAR_DEMO", "true").lower() == "true":
            cargar_demo(cursor)  # Nunca mezclar los ejemplos con registros existentes.
        cursor.execute(
            "INSERT INTO seguridad_estado (id, comprobante, indice_comprobante) VALUES (1, %s, %s)",
            (cifrar(COMPROBANTE, "seguridad_estado"), indice_cedula(COMPROBANTE)),
        )
    logging.getLogger("vidaplena").info("Migración completada: contraseñas y campos protegidos")


if __name__ == "__main__":
    preparar_base()
