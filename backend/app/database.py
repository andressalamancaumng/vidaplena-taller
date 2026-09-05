"""
Conexión a la base de datos MySQL de VidaPlena.

⚠️ Nota pedagógica: este módulo usa mysql.connector directamente (sin ORM)
a propósito, para que sea evidente en el código dónde se arma cada consulta
SQL y sea fácil identificar cuáles están mal construidas (vulnerables a
inyección) y cuáles ya usan parámetros.
"""

import os
import time

import mysql.connector
from mysql.connector import Error as MySQLError

DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "vidaplena_app")
DB_PASSWORD = os.getenv("DB_PASSWORD", "vidaplena_app_pw")
DB_NAME = os.getenv("DB_NAME", "vidaplena")

MAX_REINTENTOS = 20
ESPERA_SEGUNDOS = 3


def obtener_conexion():
    """
    Devuelve una nueva conexión a MySQL, reintentando varias veces.

    Se reintenta porque, con docker-compose, el contenedor de MySQL puede
    tardar unos segundos más en aceptar conexiones que en arrancar el
    proceso del backend.
    """
    ultimo_error = None
    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            conexion = mysql.connector.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
            )
            return conexion
        except MySQLError as error:
            ultimo_error = error
            print(f"[VidaPlena] Intento {intento}/{MAX_REINTENTOS}: "
                  f"MySQL no disponible todavía ({error}). Reintentando...")
            time.sleep(ESPERA_SEGUNDOS)

    raise RuntimeError(
        f"No fue posible conectar a MySQL tras {MAX_REINTENTOS} intentos: {ultimo_error}"
    )
