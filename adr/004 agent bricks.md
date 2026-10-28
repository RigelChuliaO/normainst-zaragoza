# ADR-004 · Cuándo usar Agent Bricks en NormaInst Zaragoza

- **Estado:** aceptada
- **Fecha:** 2026-10-28
- **Objetivo del examen:** 1.6 (decidir cómo y cuándo usar Agent Bricks)

## Contexto

Agent Bricks es la familia de agentes «prefabricados» de Databricks: se configuran desde la
interfaz (sin código o con poco código) a partir de datos de Unity Catalog, y se mejoran con
ejemplos etiquetados y feedback de expertos. Los tres que importan para este proyecto son:

| Brick | Qué hace | Equivale en NormaInst a… |
|---|---|---|
| **Knowledge Assistant** | Chatbot de preguntas y respuestas con citas sobre documentos (volúmenes de UC, tablas o índices de AI Search) | Todo el RAG: retriever + prompt + LLM |
| **Supervisor Agent** (antes Multi-Agent Supervisor) | Coordina varios agentes y herramientas (Genie, Knowledge Assistant, funciones de UC, MCP…) y combina sus resultados en un solo endpoint | El agente con el catálogo de la 1.6 |
| **Information Extraction** | Convierte documentos o texto en campos estructurados con un esquema JSON; por debajo usa `ai_extract` | La extracción de trámites de la ingesta (T-10) |

Hechos que condicionan la decisión (documentación de Databricks consultada el 2026-10-28):

1. **Free Edition no incluye Knowledge Assistant ni Supervisor Agent.** Solo da serverless, un endpoint
   de AI Search y sin Direct Vector Access.
2. **Knowledge Assistant y Supervisor Agent figuran ahora como *legacy*.** Databricks recomienda
   Genie Agents para agentes sin código y el Agent Bricks CLI para agentes con código.
3. **Information Extraction tiene una versión nueva** basada en `ai_extract`, con evaluación contra
   una tabla etiquetada (precisión, exhaustividad y F1 por campo). Falta comprobar si `ai_extract`
   funciona en nuestra Free Edition (tarea 0.3).
4. **La guía del examen (marzo de 2026) sigue preguntando por Agent Bricks** con estos nombres, así que
   hay que conocerlos aunque no se usen en el proyecto.
5. El proyecto tiene requisitos que un brick no controla del todo: el contrato de respuesta propio
   (1.4), la separación entre texto literal, resumen e inferencias, los filtros por nivel, la
   abstención con motivo y los avisos de cobertura.

## Opciones y decisión por necesidad

### 1. Línea base de preguntas y respuestas

| Opción | A favor | En contra |
|---|---|---|
| A. Knowledge Assistant | Rápido de montar; citas incluidas; mejora con feedback de expertos | No está en Free Edition; *legacy*; no respeta nuestro contrato JSON ni los filtros por nivel; caja negra para el portfolio |
| B. RAG propio (AI Search + cadena + MLflow) | Control total del contrato, los filtros, la abstención y las trazas; demuestra conocimiento para el portfolio | Más trabajo |

**Decisión: B, RAG propio.** Knowledge Assistant no se implementa. Se estudia con la documentación
como la «línea base» con la que se compararía el sistema en un workspace de pago: si un Knowledge
Assistant igualara nuestras métricas con menos esfuerzo, sería la opción correcta en un proyecto real.

### 2. Enrutado y orquestación entre normativa y trámites

| Opción | A favor | En contra |
|---|---|---|
| A. Supervisor Agent | Coordinación sin código; control de acceso por subagente | No está en Free Edition; *legacy*; excesivo para dos fuentes |
| B. Agente propio con el catálogo de la 1.6 | Reglas de orden y límites explícitos; trazable con MLflow | Hay que programarlo y evaluarlo |
| C. Genie Agent | Recomendado por Databricks para nuevos agentes sin código; útil sobre tablas | Pensado para datos estructurados; dependencia de disponibilidad en Free Edition |

**Decisión: B, agente propio.** El agente solo consulta dos *tipos* de fuente (texto de normativa y
trámites estructurados). Añadir documentos, municipios o instalaciones no crea fuentes nuevas: son
más filas en las mismas tablas, con otros valores de los metadatos `nivel` y `tipo_instalacion`
(sección 3 del documento de definición). Para eso un supervisor añade complejidad sin beneficio.

**Cuándo revisar esta decisión.** Si aparecen fuentes de *otro tipo*, con acceso, formato o dueño
distintos; por ejemplo:
- datos tabulares consultables en lenguaje natural (registro de instaladores, estadísticas de
  expedientes) → un Genie Agent como subagente (objetivo 3.13);
- servicios externos vía API o MCP (catastro, sede electrónica);
- herramientas de cálculo o agentes especializados (por ejemplo, uno de eficiencia energética);
- fuentes con permisos distintos por usuario.

Con cuatro o más subagentes heterogéneos, compensa un orquestador (Genie Agents o multiagente con el
Agent Bricks CLI) en lugar de seguir ampliando el catálogo de la 1.6.

### 3. Extracción estructurada de trámites (T-10)

| Opción | A favor | En contra |
|---|---|---|
| A. Information Extraction / `ai_extract` | Esquema JSON, evaluación por campo integrada, se ejecuta en lote con SQL | Disponibilidad en Free Edition por confirmar |
| B. LLM con prompt y validación Pydantic (`ai_query`) | Funciona con cualquier modelo disponible | Hay que construir la evaluación a mano |

**Decisión: A si `ai_extract` está disponible en Free Edition; si no, B.** Es el caso de uso típico de
Information Extraction: muchos documentos, un esquema fijo (modelo, órgano, pasos, documentación) y
se ejecuta una vez por documento en la ingesta, no en cada consulta.

## Regla general: cuándo usar un Agent Brick

**Úsalo cuando:**
- el caso es estándar (preguntas sobre documentos, extracción de campos, coordinar agentes existentes);
- importa más el tiempo hasta tener algo funcionando que el control fino;
- hay expertos que pueden etiquetar ejemplos y dar feedback desde la interfaz;
- el formato de salida del brick es aceptable para el usuario final.

**Constrúyelo tú cuando:**
- necesitas un contrato de salida propio, guardrails específicos o una lógica de abstención concreta;
- la recuperación necesita filtros o búsqueda híbrida que el brick no expone;
- quieres versionar prompts y componentes y evaluarlos por separado;
- la plataforma no ofrece el brick (como aquí, en Free Edition) o su coste no encaja.

## Consecuencias

- **Positivas:** control total del contrato, la abstención y las trazas; el proyecto demuestra cada
  pieza del RAG; no se depende de productos marcados como *legacy*.
- **Negativas:** más código que mantener; no hay comparación real con un Knowledge Assistant, que
  queda como mejora futura si se dispone de un workspace de pago.
- **Para el examen hay que repasar:** fuentes que admite Knowledge Assistant (volúmenes, tablas con
  Change Data Feed, índices de AI Search; hasta 10 fuentes) y cómo mejora (pestaña Examples,
  guidelines de expertos, instrucciones); qué subagentes coordina un Supervisor (Genie, Knowledge
  Assistant, funciones de UC, MCP, otros endpoints); y cómo se evalúa Information Extraction
  (tabla etiquetada, precisión, exhaustividad y F1 por campo).

## Pendiente

- Tarea 0.3: comprobar si `ai_extract` y Genie están disponibles en nuestra Free Edition y actualizar
  la decisión 3 si hace falta.

## Fuentes

- Free Edition limitations: https://docs.databricks.com/aws/en/getting-started/free-edition-limitations
- Knowledge Assistant: https://docs.databricks.com/aws/en/generative-ai/agent-bricks/knowledge-assistant
- Supervisor Agent: https://docs.databricks.com/aws/en/generative-ai/agent-bricks/multi-agent-supervisor
- Information Extraction: https://docs.databricks.com/aws/en/generative-ai/agent-bricks/info-extraction