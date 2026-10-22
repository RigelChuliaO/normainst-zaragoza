"""Pruebas del contrato de respuesta (tarea 1.4)."""
import copy
import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

# 01_diseno empieza por un número y no se puede importar como paquete:
# se añade la carpeta al path y se importa el módulo directamente.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "01_diseno"))

from contrato import (  # noqa: E402
    EJEMPLO_ABSTENCION,
    EJEMPLO_COMPLETO,
    CitaInventadaError,
    Respuesta,
    exportar_esquema,
    validar_respuesta,
)


def completo():
    return copy.deepcopy(EJEMPLO_COMPLETO)


def abstencion():
    return copy.deepcopy(EJEMPLO_ABSTENCION)


# --- Casos válidos -----------------------------------------------------------

def test_ejemplo_completo_valida():
    r = Respuesta.model_validate(completo())
    assert len(r.citas) == 2
    assert r.abstencion.aplica is False


def test_ejemplo_abstencion_valida():
    r = Respuesta.model_validate(abstencion())
    assert r.abstencion.aplica is True
    assert r.citas == []


# --- Casos inválidos ---------------------------------------------------------

def test_abstencion_sin_motivo_falla():
    d = abstencion()
    d["abstencion"]["motivo"] = None
    with pytest.raises(ValidationError, match="motivo"):
        Respuesta.model_validate(d)


def test_abstencion_con_citas_falla():
    d = abstencion()
    d["citas"] = completo()["citas"]
    with pytest.raises(ValidationError, match="abstención no puede llevar"):
        Respuesta.model_validate(d)


def test_respuesta_sin_citas_falla():
    d = completo()
    d["citas"] = []
    d["texto_literal"] = []
    with pytest.raises(ValidationError, match="al menos una cita"):
        Respuesta.model_validate(d)


def test_texto_literal_con_fuente_inexistente_falla():
    d = completo()
    d["texto_literal"][0]["fuente"] = 5
    with pytest.raises(ValidationError, match="fuente = 5"):
        Respuesta.model_validate(d)


def test_nivel_citado_no_consultado_falla():
    d = completo()
    d["niveles_consultados"] = ["Estado"]
    with pytest.raises(ValidationError, match="Aragón"):
        Respuesta.model_validate(d)


def test_nivel_fuera_de_ambito_falla():
    d = completo()
    d["citas"][0]["nivel"] = "Huesca"
    with pytest.raises(ValidationError):
        Respuesta.model_validate(d)


def test_campo_extra_falla():
    d = completo()
    d["opinion"] = "Yo creo que..."
    with pytest.raises(ValidationError, match="opinion"):
        Respuesta.model_validate(d)


def test_url_invalida_falla():
    d = completo()
    d["citas"][0]["url"] = "boe rite"
    with pytest.raises(ValidationError):
        Respuesta.model_validate(d)


# --- Validación contra los chunks recuperados --------------------------------

def test_validar_respuesta_con_chunks_recuperados():
    ids = {"boe-rite-art24-001", "aragon-e0002a-001", "otro-chunk"}
    r = validar_respuesta(json.dumps(completo()), ids)
    assert r.niveles_consultados[0].value == "Estado"


def test_cita_inventada_falla():
    ids = {"boe-rite-art24-001"}  # falta el chunk de Aragón
    with pytest.raises(CitaInventadaError, match="aragon-e0002a-001"):
        validar_respuesta(json.dumps(completo()), ids)


def test_json_mal_formado_falla():
    with pytest.raises(ValidationError):
        validar_respuesta('{"respuesta": "sin cerrar"', set())


# --- Esquema -------------------------------------------------------------------

def test_exportar_esquema(tmp_path):
    ruta = tmp_path / "esquema.json"
    exportar_esquema(ruta)
    esquema = json.loads(ruta.read_text(encoding="utf-8"))
    assert "citas" in esquema["properties"]
    assert "abstencion" in esquema["required"]