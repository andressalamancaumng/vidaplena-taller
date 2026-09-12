"""Conexiones y transacciones compartidas; las entradas siempre viajan como parámetros."""

import os
from contextlib import contextmanager

import mysql.connector


def obtener_conexion():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "db"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "vidaplena_app"),
        password=os.environ["DB_PASSWORD"],
        database=os.getenv("DB_NAME", "vidaplena"),
        connection_timeout=5,
        charset="utf8mb4",
        time_zone="+00:00",
    )


@contextmanager
def transaccion():
    """Confirma solo si todo sale bien y libera recursos incluso ante un error."""
    conexion = obtener_conexion()
    cursor = None
    try:
        cursor = conexion.cursor(dictionary=True, buffered=True)
        yield cursor
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        conexion.close()


def consultar(sql, parametros=(), *, uno=False):
    with transaccion() as cursor:
        cursor.execute(sql, parametros)
        return cursor.fetchone() if uno else cursor.fetchall()


def ejecutar(sql, parametros=()):
    with transaccion() as cursor:
        cursor.execute(sql, parametros)
        return cursor.lastrowid
