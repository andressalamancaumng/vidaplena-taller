"""Integración real y migración: requiere compose.pruebas.yml, nunca la base del usuario."""

import base64
import os
import re
import secrets
from pathlib import Path

import mysql.connector
import pytest
from cryptography.exceptions import InvalidTag
from fastapi.testclient import TestClient

from app import database
from app.main import app
from app.preparar_db import preparar_base
from app.seguridad import descifrar, llaves, verificar_contrasena

pytestmark = pytest.mark.skipif(
    os.getenv("VIDAPLENA_TEST_MYSQL") != "1",
    reason="Requiere MySQL aislado: ejecutar compose.pruebas.yml",
)


@pytest.fixture
def mysql_base(monkeypatch):
    # Cada prueba crea su propia base y solo elimina ese nombre al terminar.
    nombre = "vidaplena_test_" + secrets.token_hex(8)
    assert re.fullmatch(r"vidaplena_test_[a-f0-9]{16}", nombre)
    administrador = mysql.connector.connect(
        host=os.environ["DB_HOST"], port=int(os.getenv("DB_PORT", "3306")),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"], autocommit=True,
    )
    cursor = administrador.cursor()
    cursor.execute(f"CREATE DATABASE `{nombre}` CHARACTER SET utf8mb4")
    monkeypatch.setenv("DB_NAME", nombre)
    monkeypatch.setenv("CARGAR_DEMO", "true")
    try:
        yield nombre
    finally:
        # Identificador generado internamente y validado; nunca se acepta un nombre externo.
        cursor.execute(f"DROP DATABASE `{nombre}`")
        cursor.close()
        administrador.close()


def autenticar(cliente, tipo, identificador, contrasena):
    respuesta = cliente.post(f"/api/login/{tipo}", json={
        "identificador": identificador, "contrasena": contrasena,
    })
    assert respuesta.status_code == 200, respuesta.text
    return {"Authorization": "Bearer " + respuesta.json()["access_token"]}


def test_mysql_flujo_completo_y_cinco_controles(mysql_base):
    with TestClient(app) as cliente:
        admin = autenticar(cliente, "admin", "admin", "Admin123!")
        ana = autenticar(cliente, "paciente", "1010023456", "Cl4veSegura123")
        assert cliente.get("/api/admin/pacientes").status_code == 401
        assert cliente.get("/api/admin/pacientes", headers=ana).status_code == 403
        assert cliente.get("/api/admin/pacientes", headers=admin).status_code == 200
        assert cliente.get("/api/citas/2", headers=ana).status_code == 403
        propia = cliente.get("/api/citas/1", headers=ana)
        assert propia.status_code == 200
        assert propia.json()["hora"] == "09:00:00"
        for ruta in ("/api/citas/paciente/2", "/api/facturas/paciente/2"):
            assert cliente.get(ruta, headers=ana).status_code == 403
        ataque = cliente.get("/api/pacientes/buscar", headers=admin, params={"cedula": "' OR '1'='1"})
        assert ataque.json() == []
        legitima = cliente.get("/api/pacientes/buscar", headers=admin, params={"cedula": "1010023456"})
        assert len(legitima.json()) == 1
        cita = {"paciente_id": 1, "fecha": "2026-10-01", "hora": "11:00:00",
                "medico": "Dra. Prueba", "diagnostico": "Control ficticio"}
        assert cliente.post("/api/citas", json={**cita, "paciente_id": 2}, headers=ana).status_code == 403
        creada = cliente.post("/api/citas", json=cita, headers=ana)
        assert creada.status_code == 201
        detalle = cliente.get(f"/api/citas/{creada.json()['id']}", headers=ana).json()
        assert detalle["diagnostico"] == cita["diagnostico"]
        assert detalle["hora"] == "11:00:00"
        fila = database.consultar("SELECT cedula, contrasena FROM pacientes WHERE id = 1", uno=True)
        assert fila["cedula"].startswith("v1:")
        assert verificar_contrasena("Cl4veSegura123", fila["contrasena"])
        assert cliente.post("/api/logout", headers=ana).status_code == 200
        assert cliente.get("/api/citas/1", headers=ana).status_code == 401


def crear_esquema_heredado():
    esquema = (Path(__file__).resolve().parents[1] / "init-db" / "01_schema.sql").read_text(encoding="utf-8")
    esquema = esquema.replace("cedula VARCHAR(255) NOT NULL", "cedula VARCHAR(20) NOT NULL UNIQUE")
    esquema = esquema.replace("    cedula_indice CHAR(64) NOT NULL UNIQUE,\n", "")
    with database.transaccion() as cursor:
        for instruccion in esquema.split(";"):
            if re.sub(r"--[^\n]*", "", instruccion).strip():
                cursor.execute(instruccion)
        cursor.execute(
            "INSERT INTO pacientes (id, nombre, cedula, contrasena) VALUES (%s, %s, %s, %s)",
            (8, "Paciente heredado", "8888888888", "Migracion2026!"),
        )
        cursor.execute(
            "INSERT INTO usuarios_admin (usuario, contrasena) VALUES (%s, %s)", ("admin", "Admin123!")
        )
        cursor.execute(
            "INSERT INTO citas (id, paciente_id, fecha, hora, medico, diagnostico) VALUES (%s, %s, %s, %s, %s, %s)",
            (17, 8, "2026-09-10", "09:00:00", "Dra. Prueba", "Diagnóstico heredado ficticio"),
        )


def test_mysql_migracion_preserva_ids_y_no_cifra_dos_veces(mysql_base):
    crear_esquema_heredado()
    preparar_base()
    paciente = database.consultar("SELECT * FROM pacientes WHERE id = 8", uno=True)
    cita = database.consultar("SELECT * FROM citas WHERE id = 17", uno=True)
    assert descifrar(paciente["cedula"], "pacientes.cedula") == "8888888888"
    assert verificar_contrasena("Migracion2026!", paciente["contrasena"])
    assert descifrar(cita["diagnostico"], "citas.diagnostico") == "Diagnóstico heredado ficticio"
    preparar_base()
    assert database.consultar("SELECT * FROM pacientes WHERE id = 8", uno=True) == paciente
    assert database.consultar("SELECT * FROM citas WHERE id = 17", uno=True) == cita
    assert len(database.consultar("SELECT id FROM pacientes")) == 1
    with TestClient(app) as cliente:
        usuario = autenticar(cliente, "paciente", "8888888888", "Migracion2026!")
        assert cliente.get("/api/citas/17", headers=usuario).status_code == 200


@pytest.mark.parametrize("nombre", ["DATA_KEY", "INDEX_KEY"])
def test_mysql_no_admite_cambio_accidental_de_llave(mysql_base, monkeypatch, nombre):
    preparar_base()
    antes = database.consultar("SELECT * FROM pacientes")
    with monkeypatch.context() as cambios:
        cambios.setenv(nombre, base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
        llaves.cache_clear()
        with pytest.raises((InvalidTag, RuntimeError)):
            preparar_base()
    llaves.cache_clear()
    assert database.consultar("SELECT * FROM pacientes") == antes


def test_mysql_fallo_revierte_cambios_de_datos(mysql_base):
    crear_esquema_heredado()
    database.ejecutar(
        "INSERT INTO pacientes (nombre, cedula, contrasena) VALUES (%s, %s, %s)",
        ("Contraseña fuera del límite", "9999999999", "a" * 73),
    )
    with pytest.raises(ValueError):
        preparar_base()
    fila = database.consultar("SELECT cedula, contrasena FROM pacientes WHERE id = 8", uno=True)
    assert fila == {"cedula": "8888888888", "contrasena": "Migracion2026!"}
    assert database.consultar("SELECT * FROM seguridad_estado") == []
