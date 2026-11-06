# Evaluación con casos dorados

Negocio ficticio «Lumbre Café» (`examples/coffee-shop/golden.yaml`, 39 casos), modelo `openai/gpt-oss-120b` en Groq. Se repite con `uv run python -m scripts.run_golden`. Cada cambio de prompt, modelo o KB debería compararse contra esta base.

## Historial

| Corrida | Resueltos | Qué pasó |
|---|---|---|
| 1. Primera medición | 36/39 | 3 fallos reales: pierde el contexto en una pregunta de seguimiento y responde preguntas ajenas al negocio (capital de Francia, una receta) |
| 2. Tras las correcciones | 39/39 | Los 3 fallos corregidos |

## Qué se corrigió

- **Pregunta de seguimiento** («¿Y la de 250 g?» tras preguntar por la de 1 kg). Tenía tres causas encadenadas:
  1. El agente pide el nombre al cliente, y el siguiente mensaje se guardaba como si fuera ese dato aunque fuera una pregunta. Ahora un mensaje con `?` o de más de 8 palabras es una consulta nueva (`answering_capture` en `src/nodes/capture.py`).
  2. Con eso arreglado, el verificador anti-alucinación rechazaba la respuesta porque repetía datos de un turno anterior que ya no se recuperaban de la KB. Ahora también ve las respuestas previas del asistente (ya verificadas).
  3. Cambio de prompt del verificador para usarlas.
- **Preguntas ajenas al negocio.** Los prompts `agent_chat` y de RAG ahora llevan una regla de alcance: solo atiende temas del negocio y ofrece ayuda con eso.

Para despliegues que ya tienen los prompts guardados en la base, el cambio de los prompts por defecto **no se aplica solo**: hay que actualizarlos desde la API o la pantalla de prompts.

## Cómo leer el 100 %

- **Los casos se afinaron mientras se corregía el agente.** Tres expresiones del conjunto eran demasiado estrictas (el agente respondía bien con otras palabras) y se relajaron; los casos que fallaban de verdad no se tocaron. Por eso este 39/39 es un conjunto de desarrollo, no una prueba ciega.
- Con 39 casos, el intervalo de confianza del 95 % va de 91 % a 100 %.
- Para una cifra más confiable: casos nuevos que no se hayan visto al corregir (idealmente de conversaciones reales anonimizadas) y repetir cada corrida varias veces, porque un LLM no responde igual siempre.
