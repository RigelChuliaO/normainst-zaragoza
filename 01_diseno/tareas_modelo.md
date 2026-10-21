# 1.2 · Requisitos y tareas del modelo

| ID | Requisito | Traza | Tarea | Por qué |
|---|---|---|---|---|
| T-01 | Saber si la pregunta es técnica o de trámite | RF-01 | Clasificacion| |
| T-02 | Detectar instalación y nivel cuando el usuario no filtra | RF-02, RF-07 |Extraccion | |
| T-03 | Detectar si la pregunta está fuera de alcance (UNE, Huesca, cálculos) | RF-05 |Clasificacion | |
| T-04 | Detectar intentos de inyección en la pregunta | RNF-01 |Clasificacion | |
| T-05 | Encontrar los chunks relevantes | RF-09 |Embeddings + modelo| |
| T-06 | Quedarse con los mejores chunks | RF-14 |Re--ranking | |
| T-07 | Redactar la respuesta JSON con citas | RF-03, RF-04 |Generacion | |
| T-08 | Aplicar el filtro de nivel e instalación elegido por el usuario | RF-02 |Sin modelo | |
| T-09 | Enmascarar correos, teléfonos y DNI antes de registrar | RNF-03 |Sin modelo | |
| T-10 | Sacar los pasos, modelos y órganos de los documentos de trámite (ingesta) | RF-08 |Exraccion | |
| T-11 | Comprobar que cada cita respalda su frase (evaluación) | RF-03 |Juez | |
| T-12 | Comprobar que no se afirma vigencia (evaluación) | RNF-02 |Juez | |


# 1.2 · Requisitos y tareas del modelo

| ID | Requisito | Traza | Tarea | Por qué |
|---|---|---|---|---|
| T-01 | Saber si la pregunta es técnica o de trámite | RF-01 | Clasificación | Etiqueta de una lista cerrada (técnica/trámite); basta un modelo pequeño o el LLM con salida forzada, no hace falta generar texto. |
| T-02 | Detectar instalación y nivel cuando el usuario no filtra | RF-02, RF-07 | Extracción | Hay que sacar valores concretos de la pregunta (geotermia, Zaragoza) y convertirlos en filtros de metadatos para la búsqueda. |
| T-03 | Detectar si la pregunta está fuera de alcance (UNE, Huesca, cálculos) | RF-05 | Clasificación | Decisión cerrada (dentro/fuera y motivo) que se toma antes de buscar; ahorra una llamada cara al LLM y evita respuestas inventadas. |
| T-04 | Detectar intentos de inyección en la pregunta | RNF-01 | Clasificación | Guardrail de entrada con etiqueta sí/no antes de llegar al LLM; el juez evalúa salidas, no filtra entradas en tiempo real. |
| T-05 | Encontrar los chunks relevantes | RF-09 | Embeddings + sin modelo (BM25) | Búsqueda híbrida: los embeddings encuentran por significado y BM25 encuentra códigos exactos (E0002a, RD 1027/2007) que los embeddings pueden perder. |
| T-06 | Quedarse con los mejores chunks | RF-14 | Re-ranking | Un reranker compara pregunta y chunk juntos y ordena mejor que la similitud de vectores; se adopta solo si mejora la métrica de recuperación. |
| T-07 | Redactar la respuesta JSON con citas | RF-03, RF-04 | Generación | Es el único paso que redacta texto nuevo; el LLM sintetiza los chunks en el formato del contrato, validado después con Pydantic. |
| T-08 | Aplicar el filtro de nivel e instalación elegido por el usuario | RF-02 | Sin modelo | Es un filtro sobre metadatos en Vector Search; un modelo añadiría coste y errores a algo que una condición resuelve con exactitud. |
| T-09 | Enmascarar correos, teléfonos y DNI antes de registrar | RNF-03 | Sin modelo | Correos, teléfonos y DNI tienen formato fijo; una regex es más barata, determinista y fácil de probar que un modelo. |
| T-10 | Sacar los pasos, modelos y órganos de los documentos de trámite (ingesta) | RF-08 | Extracción | Convierte texto libre en campos estructurados (paso, modelo, órgano); se hace una vez por documento en la ingesta, no en cada consulta. |
| T-11 | Comprobar que cada cita respalda su frase (evaluación) | RF-03 | Juez | Parecerse no es respaldar: frases opuestas tienen embeddings casi iguales; hace falta un LLM que compruebe si la frase se sigue de la cita. |
| T-12 | Comprobar que no se afirma vigencia (evaluación) | RNF-02 | Juez | Es puntuar si la respuesta generada cumple una regla; evaluar la salida de otro modelo es la función del juez. |

## Resumen
- Usan LLM en tiempo de consulta: T-01, T-02, T-03, T-04 (pueden ir en una sola llamada al analizador) y T-07.
- Usan LLM solo en ingesta o evaluación: T-10, T-11 y T-12.
- No usan modelo: T-08, T-09 y la parte BM25 de T-05.