"""Evidencias reproducibles de las cinco fallas y de los flujos permitidos."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app import database
from app.seguridad import descifrar, llaves, verificar_contrasena

CITA = {
    "paciente_id": 1, "fecha": "2026-10-01", "hora": "11:30:00",
    "medico": "Dra. Ejemplo", "motivo_consulta": "Control",
    "diagnostico": "Texto clínico ficticio de prueba.",
}


@pytest.mark.parametrize("ruta", [
    "/api/admin/pacientes", "/api/citas/1", "/api/citas/paciente/1",
    "/api/facturas/paciente/1", "/api/pacientes/buscar?cedula=1010023456",
])
def test_sin_sesion_no_hay_datos(cliente, ruta):
    respuesta = cliente.get(ruta)
    assert respuesta.status_code == 401
    assert respuesta.headers["www-authenticate"] == "Bearer"


def test_no_crear_cita_sin_sesion(cliente):
    assert cliente.post("/api/citas", json=CITA).status_code == 401


def test_admin_autorizado_y_paciente_rechazado(cliente, tokens):
    assert cliente.get("/api/admin/pacientes", headers=tokens["ana"]).status_code == 403
    respuesta = cliente.get("/api/admin/pacientes", headers=tokens["admin"])
    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 3
    assert respuesta.json()[0]["cedula"] == "1010023456"
    assert "Paciente sana" in respuesta.json()[0]["diagnostico"]
    assert "contrasena" not in respuesta.text


@pytest.mark.parametrize("ataque", ["' OR '1'='1", "' OR 1=1 -- ", "'; DROP TABLE pacientes; --"])
def test_f1_inyeccion_no_cambia_la_consulta(cliente, tokens, base_sqlite, ataque):
    respuesta = cliente.get("/api/pacientes/buscar", params={"cedula": ataque}, headers=tokens["admin"])
    assert respuesta.status_code == 200
    assert respuesta.json() == []
    sql, parametros = base_sqlite[-1]
    assert "cedula_indice = %s" in sql
    assert ataque not in sql
    assert len(parametros[0]) == 64
    legitima = cliente.get("/api/pacientes/buscar", params={"cedula": "1010023456"}, headers=tokens["admin"])
    assert len(legitima.json()) == 1


@pytest.mark.parametrize("ruta", ["/api/citas/2", "/api/citas/paciente/2", "/api/facturas/paciente/2"])
def test_f3_bloquea_recursos_ajenos(cliente, tokens, ruta):
    assert cliente.get(ruta, headers=tokens["ana"]).status_code == 403
    assert cliente.get(ruta, headers=tokens["carlos"]).status_code == 200
    assert cliente.get(ruta, headers=tokens["admin"]).status_code == 200


def test_crear_cita_respeta_propietario_y_cifra(cliente, tokens):
    ajena = cliente.post("/api/citas", json={**CITA, "paciente_id": 2}, headers=tokens["ana"])
    assert ajena.status_code == 403
    creada = cliente.post("/api/citas", json=CITA, headers=tokens["ana"])
    assert creada.status_code == 201
    cita_id = creada.json()["id"]
    detalle = cliente.get(f"/api/citas/{cita_id}", headers=tokens["ana"])
    assert detalle.status_code == 200
    assert detalle.json()["diagnostico"] == CITA["diagnostico"]
    assert detalle.json()["hora"] == CITA["hora"]
    fila = database.consultar("SELECT diagnostico FROM citas WHERE id = %s", (cita_id,), uno=True)
    assert fila["diagnostico"].startswith("v1:")
    assert CITA["diagnostico"] not in fila["diagnostico"]
    panel = cliente.get("/api/admin/pacientes", headers=tokens["admin"]).json()
    assert len(panel) == 3  # La última consulta no duplica al paciente en el panel.
    assert panel[0]["diagnostico"] == CITA["diagnostico"]


def test_f4_f5_registro_login_y_duplicados(cliente):
    datos = {"nombre": "Paciente de prueba", "cedula": "9999900000", "contrasena": "ClaveNueva2026!"}
    creada = cliente.post("/api/pacientes/registro", json=datos)
    assert creada.status_code == 201
    fila = database.consultar("SELECT * FROM pacientes WHERE id = %s", (creada.json()["id"],), uno=True)
    assert verificar_contrasena(datos["contrasena"], fila["contrasena"])
    assert fila["contrasena"] != datos["contrasena"]
    assert fila["cedula"] != datos["cedula"]
    assert descifrar(fila["cedula"], "pacientes.cedula") == datos["cedula"]
    assert cliente.post("/api/pacientes/registro", json=datos).status_code == 409
    respuesta = cliente.post("/api/login/paciente", json={
        "identificador": datos["cedula"], "contrasena": datos["contrasena"],
    })
    assert respuesta.status_code == 200
    assert "access_token" in respuesta.json()
    assert "contrasena" not in respuesta.json()


@pytest.mark.parametrize("tipo,identificador", [("paciente", "1010023456"), ("admin", "admin")])
def test_contrasena_incorrecta(cliente, tipo, identificador):
    respuesta = cliente.post(f"/api/login/{tipo}", json={"identificador": identificador, "contrasena": "incorrecta"})
    assert respuesta.status_code == 401


def test_token_inventado(cliente):
    assert cliente.get("/api/admin/pacientes", headers={"Authorization": "Bearer inventado"}).status_code == 401


@pytest.mark.parametrize("cambio", ["expirado", "firma_falsa", "sin_exp", "algoritmo_distinto", "sin_firma"])
def test_jwt_invalido(cliente, tokens, cambio):
    token = tokens["ana"]["Authorization"].split()[1]
    claims = jwt.decode(token, options={"verify_signature": False})
    llave = llaves()["JWT_KEY"]
    algoritmo = "HS256"
    if cambio == "expirado":
        claims["exp"] = datetime.now(timezone.utc) - timedelta(seconds=1)
    elif cambio == "firma_falsa":
        claims["tipo"] = "admin"
        llave = b"llave_ajena_suficientemente_larga_123456"
    elif cambio == "sin_exp":
        del claims["exp"]
    elif cambio == "algoritmo_distinto":
        algoritmo = "HS384"
        llave = llave + b"solo_para_prueba_HS384"
    else:
        algoritmo, llave = "none", ""
    alterado = jwt.encode(claims, llave, algorithm=algoritmo)
    assert cliente.get("/api/admin/pacientes", headers={"Authorization": "Bearer " + alterado}).status_code == 401


def test_logout_revoca_token(cliente, tokens):
    assert cliente.post("/api/logout", headers=tokens["ana"]).status_code == 200
    assert cliente.get("/api/citas/1", headers=tokens["ana"]).status_code == 401
    assert cliente.get("/api/citas/2", headers=tokens["carlos"]).status_code == 200


def test_cambio_de_rol_se_respeta_sin_renovar_jwt(cliente, tokens):
    database.ejecutar("UPDATE usuarios_admin SET rol = %s WHERE id = %s", ("sin_privilegios", 1))
    assert cliente.get("/api/admin/pacientes", headers=tokens["admin"]).status_code == 403
    assert cliente.get("/api/citas/1", headers=tokens["admin"]).status_code == 403


@pytest.mark.parametrize("clave", ["corta", "á" * 40, "a" * 73])
def test_valida_password_sin_devolverlo(cliente, clave):
    respuesta = cliente.post("/api/pacientes/registro", json={
        "nombre": "Prueba", "cedula": "9999900000", "contrasena": clave,
    })
    assert respuesta.status_code == 422
    assert clave not in respuesta.text


def test_dato_alterado_no_se_devuelve(cliente, tokens):
    from app.seguridad import cifrar
    # Es un cifrado válido, pero pertenece a otro campo: el contexto autenticado lo rechaza.
    database.ejecutar("UPDATE citas SET diagnostico = %s WHERE id = 1", (cifrar("prueba", "pacientes.cedula"),))
    respuesta = cliente.get("/api/citas/1", headers=tokens["ana"])
    assert respuesta.status_code == 500
    assert "integridad" in respuesta.json()["detail"]


def test_respuestas_no_se_cachean(cliente, tokens):
    respuesta = cliente.get("/api/citas/1", headers=tokens["ana"])
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.headers["x-content-type-options"] == "nosniff"
    assert "access-control-allow-origin" not in respuesta.headers
