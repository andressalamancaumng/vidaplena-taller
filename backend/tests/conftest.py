"""Pruebas offline con SQL real en SQLite; MySQL se verifica por separado en Docker."""

import base64
import re
import secrets
import shutil
import sqlite3
from datetime import date, datetime, time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from mysql.connector import IntegrityError

from app import database
from app.datos_demo import cargar_demo
from app.main import app
from app.seguridad import llaves

ESQUEMA = Path(__file__).resolve().parents[1] / "init-db" / "01_schema.sql"


@pytest.fixture(scope="session", autouse=True)
def configuracion():
    with pytest.MonkeyPatch.context() as cambios:
        for nombre in ("DATA_KEY", "INDEX_KEY", "JWT_KEY"):
            cambios.setenv(nombre, base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
        llaves.cache_clear()
        yield
        llaves.cache_clear()


class CursorSQLite:
    """Adapta solo el protocolo del conector; no simula resultados de las consultas."""

    def __init__(self, cursor, sentencias):
        self.cursor = cursor
        self.sentencias = sentencias

    def execute(self, sql, parametros=()):
        self.sentencias.append((sql, parametros))
        sql = sql.replace("%s", "?").replace("UTC_TIMESTAMP()", "CURRENT_TIMESTAMP")
        valores = tuple(str(v) if isinstance(v, (date, datetime, time)) else v for v in parametros)
        try:
            self.cursor.execute(sql, valores)
        except sqlite3.IntegrityError as error:
            raise IntegrityError(msg="Restricción de integridad", errno=1062) from error

    def executemany(self, sql, filas):
        for fila in filas:
            self.execute(sql, fila)

    @property
    def lastrowid(self):
        return self.cursor.lastrowid

    def fetchone(self):
        fila = self.cursor.fetchone()
        return dict(fila) if fila is not None else None

    def fetchall(self):
        return [dict(fila) for fila in self.cursor.fetchall()]

    def close(self):
        self.cursor.close()


class ConexionSQLite:
    def __init__(self, ruta, sentencias):
        self.conexion = sqlite3.connect(ruta, check_same_thread=False)
        self.conexion.row_factory = sqlite3.Row
        self.conexion.execute("PRAGMA foreign_keys = ON")
        self.sentencias = sentencias

    def cursor(self, **opciones):
        return CursorSQLite(self.conexion.cursor(), self.sentencias)

    def commit(self):
        self.conexion.commit()

    def rollback(self):
        self.conexion.rollback()

    def close(self):
        self.conexion.close()


@pytest.fixture(scope="session")
def base_modelo(tmp_path_factory, configuracion):
    ruta = tmp_path_factory.mktemp("modelo") / "demo.sqlite3"
    esquema = ESQUEMA.read_text(encoding="utf-8")
    esquema = esquema.replace("INT AUTO_INCREMENT PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
    esquema = re.sub(r",\s*INDEX idx_sesion_expira \(expira\)", "", esquema)
    with sqlite3.connect(ruta) as conexion:
        conexion.executescript(esquema)
    conexion = ConexionSQLite(ruta, [])
    cursor = conexion.cursor()
    cargar_demo(cursor)
    conexion.commit()
    cursor.close()
    conexion.close()
    return ruta


@pytest.fixture
def base_sqlite(tmp_path, monkeypatch, base_modelo):
    ruta = tmp_path / "prueba.sqlite3"
    shutil.copyfile(base_modelo, ruta)
    sentencias = []
    monkeypatch.setattr(database, "obtener_conexion", lambda: ConexionSQLite(ruta, sentencias))
    # El DDL/migración específico de MySQL se prueba en test_mysql.py, no con esta adaptación.
    monkeypatch.setattr("app.main.preparar_base", lambda: None)
    return sentencias


@pytest.fixture
def cliente(base_sqlite):
    with TestClient(app) as cliente:
        yield cliente


@pytest.fixture
def tokens(cliente):
    resultado = {}
    for nombre, tipo, identificador, contrasena in [
        ("ana", "paciente", "1010023456", "Cl4veSegura123"),
        ("carlos", "paciente", "1015098765", "MiPerro2019"),
        ("admin", "admin", "admin", "Admin123!"),
    ]:
        respuesta = cliente.post(f"/api/login/{tipo}", json={
            "identificador": identificador, "contrasena": contrasena,
        })
        assert respuesta.status_code == 200
        resultado[nombre] = {"Authorization": "Bearer " + respuesta.json()["access_token"]}
    return resultado
