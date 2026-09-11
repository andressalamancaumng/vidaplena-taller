"""
Migración de la Falla 5 para VidaPlena.

- Amplía la columna cedula para almacenar tokens Fernet.
- Agrega cedula_hash para búsquedas sin guardar la cédula en texto plano.
- Cifra las cédulas existentes.
- Cifra los diagnósticos existentes.
- Puede ejecutarse más de una vez sin volver a cifrar los datos.
"""

import base64
import hashlib
import hmac
import os

from cryptography.fernet import Fernet, InvalidToken

from app import database


FERNET_KEY = os.getenv("FERNET_KEY")

if not FERNET_KEY:
    raise RuntimeError("Falta la variable de entorno FERNET_KEY.")

fernet = Fernet(FERNET_KEY.encode("utf-8"))
hmac_key = base64.urlsafe_b64decode(FERNET_KEY.encode("utf-8"))


def cifrar(valor: str) -> str:
    return fernet.encrypt(valor.encode("utf-8")).decode("utf-8")


def intentar_descifrar(valor: str):
    try:
        return fernet.decrypt(valor.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None


def hash_busqueda(valor: str) -> str:
    return hmac.new(
        hmac_key,
        valor.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def columna_existe(cursor, tabla: str, columna: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND column_name = %s
        """,
        (tabla, columna),
    )
    return cursor.fetchone()[0] > 0


def indice_existe(cursor, tabla: str, indice: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND index_name = %s
        """,
        (tabla, indice),
    )
    return cursor.fetchone()[0] > 0


def main():
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()

    try:
        # Fernet necesita bastante más espacio que VARCHAR(20).
        cursor.execute(
            "ALTER TABLE pacientes "
            "MODIFY COLUMN cedula VARCHAR(255) NOT NULL"
        )

        if not columna_existe(cursor, "pacientes", "cedula_hash"):
            cursor.execute(
                "ALTER TABLE pacientes "
                "ADD COLUMN cedula_hash VARCHAR(64) NULL AFTER cedula"
            )

        # Migrar cédulas.
        cursor.execute("SELECT id, cedula FROM pacientes")
        pacientes = cursor.fetchall()

        for paciente_id, cedula_guardada in pacientes:
            texto_plano = intentar_descifrar(cedula_guardada)

            if texto_plano is None:
                texto_plano = cedula_guardada
                cedula_cifrada = cifrar(texto_plano)
            else:
                cedula_cifrada = cedula_guardada

            cursor.execute(
                "UPDATE pacientes "
                "SET cedula = %s, cedula_hash = %s "
                "WHERE id = %s",
                (
                    cedula_cifrada,
                    hash_busqueda(texto_plano),
                    paciente_id,
                ),
            )

        cursor.execute(
            "ALTER TABLE pacientes "
            "MODIFY COLUMN cedula_hash VARCHAR(64) NOT NULL"
        )

        if not indice_existe(
            cursor,
            "pacientes",
            "ux_pacientes_cedula_hash",
        ):
            cursor.execute(
                "CREATE UNIQUE INDEX ux_pacientes_cedula_hash "
                "ON pacientes (cedula_hash)"
            )

        # Migrar diagnósticos.
        cursor.execute(
            "SELECT id, diagnostico "
            "FROM citas "
            "WHERE diagnostico IS NOT NULL"
        )
        citas = cursor.fetchall()

        for cita_id, diagnostico_guardado in citas:
            if diagnostico_guardado == "":
                continue

            texto_plano = intentar_descifrar(diagnostico_guardado)

            if texto_plano is None:
                cursor.execute(
                    "UPDATE citas SET diagnostico = %s WHERE id = %s",
                    (
                        cifrar(diagnostico_guardado),
                        cita_id,
                    ),
                )

        conexion.commit()
        print("Migracion de Falla 5 completada correctamente.")

    except Exception:
        conexion.rollback()
        raise

    finally:
        cursor.close()
        conexion.close()


if __name__ == "__main__":
    main()
