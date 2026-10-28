"""Utilidades para probar a mano el prompt de respuesta (tarea 1.5).

Uso desde un notebook en la raíz del repositorio:

    import sys; sys.path.insert(0, "03_desarrollo/prompts")
    from probar_prompt import montar_prompt, comprobar
    print(montar_prompt("respuesta_v0"))   # copiar como system prompt en AI Playground
    comprobar(salida, documentos)          # validar lo que devuelve el modelo
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "01_diseno"))

ENDPOINT = "databricks-gpt-oss-120b"  # cámbialo si tu endpoint se llama distinto

from contrato import Respuesta, validar_respuesta  # noqa: E402


def montar_prompt(version: str = "respuesta_v1") -> str:
    """Devuelve el system prompt con el esquema JSON ya insertado."""
    plantilla = (RAIZ / "03_desarrollo" / "prompts" / f"{version}.txt").read_text(encoding="utf-8")
    esquema = (RAIZ / "01_diseno" / "respuesta_schema.json").read_text(encoding="utf-8")
    return plantilla.replace("<<ESQUEMA_JSON>>", esquema)


def _normalizar(texto: str) -> str:
    return " ".join(texto.split())

def preguntar(mensaje_usuario: str, version: str, endpoint: str = ENDPOINT) -> str:
    """Llama al modelo con el system prompt de la versión indicada y devuelve su texto."""
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
 
    w = WorkspaceClient()
    r = w.serving_endpoints.query(
        name=endpoint,
        messages=[
            ChatMessage(role=ChatMessageRole.SYSTEM, content=montar_prompt(version)),
            ChatMessage(role=ChatMessageRole.USER, content=mensaje_usuario),
        ],
        temperature=0,
        max_tokens=2000,
    )
    return r.choices[0].message.content
def comprobar(salida: str, documentos: dict[str, str]) -> Respuesta:
    """Valida la salida del modelo y revisa lo que Pydantic no puede comprobar.

    salida: el JSON que devolvió el modelo, tal cual.
    documentos: {chunk_id: texto que pegaste en el <doc>}.
    """
    salida = salida.strip()
    if salida.startswith("```"):
        print("✗ El modelo envolvió el JSON en un bloque de código (incumple el formato)")
        salida = salida.strip("`").removeprefix("json").strip()

    r = validar_respuesta(salida, set(documentos))  # lanza excepción si no cumple el contrato
    print("✓ Cumple el contrato y no cita chunks inventados")

    for t in r.texto_literal:
        cid = r.citas[t.fuente].chunk_id
        if _normalizar(t.texto) in _normalizar(documentos[cid]):
            print(f"✓ texto_literal literal de {cid}")
        else:
            print(f"✗ texto_literal NO es literal de {cid}: «{t.texto[:70]}…»")

    textos_modelo = " ".join([r.respuesta, r.resumen, *r.inferencias]).lower()
    if "vigente" in textos_modelo or "derogad" in textos_modelo:
        print("✗ Habla de vigencia o derogación en respuesta, resumen o inferencias: revísalo")

    print(f"  abstención: {r.abstencion.aplica} | motivo: {r.abstencion.motivo}")
    print(f"  citas: {[c.chunk_id for c in r.citas]} | niveles: {[n.value for n in r.niveles_consultados]}")
    print(f"  avisos: {r.avisos}")
    return r