"""Pruebas de las primitivas criptográficas, configuración y migración idempotente."""

import base64

import pytest
from cryptography.exceptions import InvalidTag

from app.preparar_db import proteger_campo, proteger_contrasena
from app.seguridad import cifrar, descifrar, hash_contrasena, indice_cedula, llaves, verificar_contrasena


def test_bcrypt_usa_salt_unico():
    clave = "ClaveSegura2026!"
    primero, segundo = hash_contrasena(clave), hash_contrasena(clave)
    assert primero != segundo
    assert primero.startswith("$2b$12$")
    assert verificar_contrasena(clave, primero)
    assert not verificar_contrasena("distinta", primero)
    assert not verificar_contrasena(clave, clave)
    assert proteger_contrasena(primero) == primero


@pytest.mark.parametrize("texto", ["1010023456", "Diagnóstico: niño sano.", "", None])
def test_cifrado_y_reinicio_no_duplican_proteccion(texto):
    resultado = cifrar(texto, "citas.diagnostico")
    assert descifrar(resultado, "citas.diagnostico") == texto
    assert proteger_campo(resultado, "citas.diagnostico") == resultado
    if texto is not None:
        assert cifrar(texto, "citas.diagnostico") != resultado


def test_gcm_detecta_alteracion():
    cifrado = cifrar("Diagnóstico ficticio", "citas.diagnostico")
    datos = bytearray(base64.urlsafe_b64decode(cifrado[3:]))
    datos[-1] ^= 1
    alterado = "v1:" + base64.urlsafe_b64encode(datos).decode()
    with pytest.raises(InvalidTag):
        descifrar(alterado, "citas.diagnostico")
    with pytest.raises(ValueError):
        descifrar("texto plano", "citas.diagnostico")


def test_indice_hmac_busca_sin_revelar_cedula():
    indice = indice_cedula("1010023456")
    assert indice == indice_cedula("1010023456")
    assert indice != indice_cedula("1015098765")
    assert len(indice) == 64
    assert "1010023456" not in indice


@pytest.mark.parametrize("valor", [None, "invalido!", "YQ=="])
def test_no_arranca_sin_llave_valida(monkeypatch, valor):
    llaves.cache_clear()
    with monkeypatch.context() as cambios:
        if valor is None:
            cambios.delenv("DATA_KEY")
        else:
            cambios.setenv("DATA_KEY", valor)
        with pytest.raises(RuntimeError):
            llaves()
    llaves.cache_clear()


def test_no_reutiliza_llaves(monkeypatch):
    import os
    llaves.cache_clear()
    with monkeypatch.context() as cambios:
        cambios.setenv("INDEX_KEY", os.environ["DATA_KEY"])
        with pytest.raises(RuntimeError):
            llaves()
    llaves.cache_clear()
