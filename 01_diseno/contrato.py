"""Contrato de respuesta de NormaInst Zaragoza.

Sigue la sección 6 del documento de definición del proyecto. Lo usan:
- el validador de la cadena (paso 8 de 01_diseno/cadena.md),
- el prompt de formato (tarea 1.5), que incluye el esquema JSON exportado,
- la evaluación, que comprueba que cada respuesta cumple el contrato.
"""
from __future__ import annotations

import json
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class Nivel(str, Enum):
    """Nivel normativo de una fuente."""

    ESTADO = "Estado"
    ARAGON = "Aragón"
    ZARAGOZA = "Zaragoza"


class _Base(BaseModel):
    # extra="forbid": un campo que no está en el contrato es un error, no se ignora.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Cita(_Base):
    """Fuente que respalda la respuesta. Sale de los metadatos del chunk, no del LLM."""

    chunk_id: str = Field(min_length=1, description="Identificador del chunk recuperado")
    norma: str = Field(min_length=1, description="Nombre o código de la norma o trámite")
    articulo_o_paso: str = Field(min_length=1, description="Artículo, apartado o paso del trámite")
    nivel: Nivel
    organo: str = Field(min_length=1, description="Órgano que publica la norma o gestiona el trámite")
    url: HttpUrl
    fecha_captura: date = Field(description="Fecha en que se descargó el documento")


class TextoLiteral(_Base):
    """Cita textual de la norma, copiada del chunk sin cambios."""

    texto: str = Field(min_length=1)
    fuente: int = Field(ge=0, description="Índice de la cita en la lista 'citas'")


class Abstencion(_Base):
    aplica: bool
    motivo: Optional[str] = None
    contexto_solicitado: Optional[str] = None

    @model_validator(mode="after")
    def _motivo_si_se_abstiene(self) -> "Abstencion":
        if self.aplica and not self.motivo:
            raise ValueError("Si abstencion.aplica es true, 'motivo' es obligatorio")
        if not self.aplica and (self.motivo or self.contexto_solicitado):
            raise ValueError("Si abstencion.aplica es false, 'motivo' y 'contexto_solicitado' van vacíos")
        return self


class Respuesta(_Base):
    """Respuesta completa del asistente."""

    respuesta: str = Field(min_length=1, description="Respuesta breve en lenguaje claro")
    texto_literal: list[TextoLiteral] = Field(default_factory=list)
    resumen: str = Field(default="", description="Explicación del modelo, marcada como resumen")
    inferencias: list[str] = Field(
        default_factory=list, description="Conclusiones que no están escritas literalmente en la fuente"
    )
    citas: list[Cita] = Field(default_factory=list)
    niveles_consultados: list[Nivel] = Field(default_factory=list)
    abstencion: Abstencion
    avisos: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _coherencia(self) -> "Respuesta":
        if self.abstencion.aplica:
            # Abstenerse significa no aportar evidencia: nada de citas ni textos inventados.
            if self.citas or self.texto_literal or self.inferencias:
                raise ValueError("Una abstención no puede llevar citas, texto_literal ni inferencias")
            return self

        if not self.citas:
            raise ValueError("Una respuesta que no se abstiene necesita al menos una cita")

        for i, t in enumerate(self.texto_literal):
            if t.fuente >= len(self.citas):
                raise ValueError(
                    f"texto_literal[{i}].fuente = {t.fuente}, pero solo hay {len(self.citas)} citas"
                )

        niveles_citados = {c.nivel for c in self.citas}
        faltan = niveles_citados - set(self.niveles_consultados)
        if faltan:
            nombres = ", ".join(sorted(n.value for n in faltan))
            raise ValueError(f"Niveles citados que no están en niveles_consultados: {nombres}")
        return self


class CitaInventadaError(ValueError):
    """Una cita apunta a un chunk que no se recuperó en esta consulta."""


def validar_respuesta(json_llm: str, chunk_ids_recuperados: set[str]) -> Respuesta:
    """Valida el JSON del LLM contra el contrato y contra los chunks recuperados.

    Lanza pydantic.ValidationError si el JSON no cumple el contrato
    y CitaInventadaError si cita un chunk que no estaba en el contexto.
    """
    r = Respuesta.model_validate_json(json_llm)
    inventadas = [c.chunk_id for c in r.citas if c.chunk_id not in chunk_ids_recuperados]
    if inventadas:
        raise CitaInventadaError(f"Citas a chunks no recuperados: {inventadas}")
    return r


def exportar_esquema(ruta: str | Path) -> None:
    """Guarda el JSON Schema del contrato (lo usa el prompt de la tarea 1.5)."""
    esquema = Respuesta.model_json_schema()
    Path(ruta).write_text(json.dumps(esquema, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Ejemplos. Sirven de fixtures en las pruebas y de few-shot en el prompt (1.5).
# Los textos literales y las URL son ilustrativos: se sustituyen por los
# reales cuando el corpus esté cargado (fase 2).
# ---------------------------------------------------------------------------

EJEMPLO_COMPLETO: dict = {
    "respuesta": (
        "Al terminar la instalación térmica, la empresa instaladora debe comunicar su puesta "
        "en servicio al Servicio Provincial de industria o a una entidad colaboradora, con el "
        "modelo E0002a y la documentación que exige el RITE."
    ),
    "texto_literal": [
        {"texto": "[Texto literal del artículo sobre puesta en servicio, copiado del chunk]", "fuente": 0},
        {"texto": "[Texto literal del paso de comunicación, copiado del chunk]", "fuente": 1},
    ],
    "resumen": (
        "Resumen: el RITE fija qué documentación acompaña a la puesta en servicio y el "
        "procedimiento de Aragón indica ante quién y con qué modelo se comunica."
    ),
    "inferencias": [
        "La documentación concreta depende de si la instalación necesita proyecto o memoria técnica."
    ],
    "citas": [
        {
            "chunk_id": "boe-rite-art24-001",
            "norma": "RITE (RD 1027/2007)",
            "articulo_o_paso": "Artículo 24",
            "nivel": "Estado",
            "organo": "Ministerio competente en industria",
            "url": "https://www.boe.es/buscar/act.php?id=BOE-A-2007-15820",
            "fecha_captura": "2026-10-13",
        },
        {
            "chunk_id": "aragon-e0002a-001",
            "norma": "Puesta en servicio de instalaciones térmicas (modelo E0002a)",
            "articulo_o_paso": "Paso 1: comunicación",
            "nivel": "Aragón",
            "organo": "Servicio Provincial de industria",
            "url": "https://www.aragon.es/",  # TODO: URL real del trámite
            "fecha_captura": "2026-10-13",
        },
    ],
    "niveles_consultados": ["Estado", "Aragón"],
    "abstencion": {"aplica": False},
    "avisos": [
        "Herramienta informativa: no es asesoramiento jurídico.",
        "Textos capturados el 13/10/2026; no se afirma su vigencia.",
    ],
}

EJEMPLO_ABSTENCION: dict = {
    "respuesta": "No puedo responder con las fuentes disponibles.",
    "texto_literal": [],
    "resumen": "",
    "inferencias": [],
    "citas": [],
    "niveles_consultados": [],
    "abstencion": {
        "aplica": True,
        "motivo": "La norma UNE consultada no forma parte del corpus porque es de pago.",
        "contexto_solicitado": None,
    },
    "avisos": ["Herramienta informativa: no es asesoramiento jurídico."],
}