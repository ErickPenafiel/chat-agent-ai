# Guía: configurar un tenant nuevo

Un negocio = un despliegue (su propia base de datos y su propio `tenant.yaml`). Esta guía lleva de cero a un agente
respondiendo. El tenant ficticio `examples/coffee-shop/` es el ejemplo completo para copiar.

## 0. Requisitos

```bash
uv sync
```

## 1. Configuración de negocio

```bash
cp config/tenant.example.yaml config/tenant.yaml
```

Todo lo que no tiene default es obligatorio: el template no asume ningún negocio.

| Campo | Qué define |
|---|---|
| `business_name` | Nombre que usan los prompts. |
| `tone` | `formality`, `address_form` (usted, tú, vos…) e idioma. Se inyecta en todos los prompts. |
| `thresholds` | `sla_hours` y `session_timeout_minutes` (una conversación nueva empieza tras ese tiempo inactivo). |
| `intents` | Intenciones habilitadas. `chat` y `escalate` son obligatorias. Cada una puede declarar `capture_fields` y `capture_before_answer` (default `false`: responder primero, pedir datos después). |
| `categories` | Temas de la KB (opcionales). Distintos de las intenciones. |
| `llm` | `provider` (`google`, `anthropic` o `groq`), `model` y opcionales `temperature`, `max_tokens`, `timeout_seconds` (default 30). Ver paso 4. |
| `channels` | `web` y/o `whatsapp_cloud_api`. |
| `connectors` | Ids de conectores activos (paso 6). |
| `max_input_chars` | Tope de caracteres por mensaje del cliente (default 2000); protege la cuota del LLM. |
| `verify_responses` | Default `false`. Con `true`, un LLM verifica cada respuesta contra la KB y los datos antes de enviarla (ver paso 4b). |

Claves desconocidas o con typo hacen fallar el arranque; es intencional.

## 2. Base de datos

```bash
export DATABASE_URL=sqlite:///./agent.db      # o postgresql+psycopg://... (ver nota)
uv run alembic upgrade head
```

> El código usa SQLAlchemy y no depende de SQLite, pero **solo se probó con SQLite**. Para Postgres hay que instalar
> un driver y probar las migraciones. El checkpoint de conversación usa `MemorySaver` (se pierde al reiniciar);
> para producción hay que cambiarlo por `AsyncPostgresSaver` en `src/api/app.py`.

## 3. Base de conocimiento

La KB arranca **vacía**. Cada negocio carga la suya. Opción recomendada: un archivo YAML versionado en git
(formato en `examples/coffee-shop/kb.yaml`).

```bash
uv run python -m scripts.seed_tenant mi-kb.yaml            # primera carga (solo si la KB está vacía)
uv run python -m scripts.rebuild_knowledge_base mi-kb.yaml # sincronizar después (crea/actualiza con versión)
uv run python -m scripts.rebuild_knowledge_base mi-kb.yaml --prune   # además archiva los de origen seed ausentes
```

Reglas que valida cada bloque: `intents` y `category` deben existir en `tenant.yaml` (un typo da error, no un bloque
invisible); los pasos referencian adjuntos por `id`. Los bloques se identifican por título; cambiar el título crea
un bloque nuevo. Sincronizar **sobrescribe** ediciones manuales de los bloques del archivo (la versión anterior queda
para rollback).

También se puede gestionar por API: `POST/PATCH /knowledge-blocks`, con `status` (`draft` → `published`), historial
en `/knowledge-blocks/{id}/versions` y rollback. Solo los bloques `published` llegan al cliente.

## 4. LLM

```yaml
llm:
  provider: google          # o anthropic, groq
  model: <modelo vigente>   # explícito; verificar el nombre actual en la documentación del proveedor
  timeout_seconds: 15       # opcional (default 30)
```

```bash
export GOOGLE_API_KEY=...        # o ANTHROPIC_API_KEY / GROQ_API_KEY
```

Los tres proveedores reintentan solos hasta 2 veces (espera de 0,5 s y 1 s) ante 429, 5xx, errores de red y timeouts.
El peor caso de una llamada es entonces `3 × timeout_seconds` más la espera: con un demo en vivo conviene bajar el timeout.

**Sin bloque `llm` el agente no es útil**: el clasificador por defecto manda todo a `chat` y solo responde el mensaje de
respaldo. Existe para poder probar el grafo sin red.

Los prompts se siembran en la base al arrancar y se editan por API sin redeploy: `GET /prompts`,
`PUT /prompts/{slug}`, `POST /prompts/{slug}/rollback/{versión}`. Los slugs salen de tus intenciones y conectores
activos (`agent_<intención>`, `tone`, `intent_classifier`, `handoff`, uno por conector). Revisa y ajusta los textos por
defecto: son genéricos y no se probaron con un LLM real.

## 4b. Verificación anti-alucinación (opcional)

Con `verify_responses: true` el grafo agrega el nodo `verify` después de `response`. Un LLM recibe el borrador, la KB y los
datos de conectores que lo respaldan (prompt `verifier`) y devuelve `{"supported": bool, "unsupported_claims": [...]}`.
Si afirma algo sin respaldo, se reemplaza por una respuesta segura y se corrige el historial de la conversación.

- Cuesta **una llamada más al LLM por turno** (casi el doble de latencia en turnos con KB).
- Solo verifica respuestas generadas por el LLM que tengan hechos que contrastar; handoff, charla sin KB y respuestas en
  crudo se omiten sin llamada extra.
- Ante un fallo del verificador se envía el borrador (el guardrail no tumba la conversación).
- Es estricto: puede bloquear inferencias correctas que no están escritas en la KB (ej. «no aceptamos criptomonedas» si
  la KB solo lista las formas de pago aceptadas). El prompt `verifier` se ajusta por API; está en `PROTECTED_PROMPTS`, así
  que el corrector nocturno no lo modifica.
- El resultado de cada turno llega en el trace del webhook (`verification`: `supported`, `rejected`, `skipped` o `error`, y
  `unsupported_claims`) y se ve en el panel del simulador de chat.

Otras protecciones que ya existen sin esta opción: delimitadores XML y una instrucción anti-inyección en los prompts
(`_GUARD`), respuestas acotadas a `<kb_context>`/`<system_data>` y el tope `max_input_chars`.

## 5. Canales

- **`web`** (mock): `POST /channels/web/webhook` con `{"user_id": "...", "text": "..."}`; lo que respondió el agente
  está en `GET /channels/web/outbox/{user_id}`. Sirve para probar sin contratar nada.
- **`whatsapp_cloud_api`**: exige `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_APP_SECRET` y
  `WHATSAPP_VERIFY_TOKEN` en el entorno. Webhook en `/channels/whatsapp_cloud_api/webhook` (GET para la verificación
  de Meta, POST para mensajes, con firma). Sin esas variables, el arranque falla.
- Otro canal (Telegram, widget…): implementar `MessagingChannel` (`src/channels/base.py`) y registrarlo en
  `src/channels/registry.py`.

## 6. Conectores (datos en vivo)

Sin conectores el agente responde solo con la KB. Para agregar uno:

1. Subclase de `Connector` (`src/connectors/base.py`): `id`, `intents`/`issues` que lo disparan, `prompt_key`,
   `fetch(state)` y una `response_template`. Ver `src/connectors/example.py` (datos simulados).
2. Registrarlo en `AVAILABLE` (`src/connectors/registry.py`) y listarlo en `connectors:` de `tenant.yaml`.
3. Si necesita saber de qué entidad habla el cliente (pedido, cuenta…), pasar un `entity_resolver` a `create_app`
   (`src/main.py`): una función `estado -> {"id": ...} | None`. Sin resolver, `entity` es siempre `None`.

Un conector que lanza excepción no tumba la conversación: se registra el error y se responde con la KB.

## 7. Levantar

```bash
TENANT_CONFIG=config/tenant.yaml DATABASE_URL=... uv run uvicorn src.main:app
```

Documentación interactiva de la API en `/docs`.

## 7b. Autenticación (Firebase) y CORS

La API de administración (`/knowledge-blocks`, `/prompts`, `/connectors`, `/conversation-outcomes`,
`/improvement-proposals`, `/auth/me`, `/channels/web/*`) exige un **ID token de Firebase Auth** en
`Authorization: Bearer <token>`. El backend lo verifica con las claves públicas de Google (RS256, audiencia y emisor
de tu proyecto, expiración); no necesita credenciales de servicio ni secretos.

```yaml
auth:
  mode: firebase
  firebase_project_id: mi-proyecto
  admin_emails: [admin@mi-dominio.com]   # correo verificado en Firebase
  require_email_verified: true           # default
cors:
  allowed_origins: ["https://app.mi-dominio.com"]   # explícitos; "*" no se admite
```

**Autenticar no es autorizar.** Cualquiera que se registre en tu proyecto Firebase obtiene un token válido, así que
además se exige ser admin: correo en `admin_emails` (con email verificado) o el custom claim `admin: true`
(asignable con el SDK Admin de Firebase). Respuestas: `401` sin token o inválido, `403` token válido sin permisos.

El frontend puede llamar `GET /auth/me` para comprobar sesión y permisos. `GET /health` es público.
Los webhooks de canales reales (WhatsApp) no usan Firebase: verifican la firma del proveedor. El canal `web` mock
también exige admin, porque consume LLM.

`auth.mode: disabled` deja todo abierto y **el arranque falla** salvo que definas `ALLOW_INSECURE_AUTH=1`. Es solo
para desarrollo local; los ejemplos del repo lo traen así para poder probarlos sin Firebase.

Limitaciones actuales: no hay roles más finos que «admin»; CORS no aplica a webhooks (son servidor a servidor);
no hay límite de peticiones (rate limit) en ningún endpoint.

## 8. Evaluación y mejora continua

Requieren `llm` configurado.

| Capa | Qué hace | Cómo |
|---|---|---|
| 0 | Reglas por turno + juez LLM sobre conversaciones terminadas | Reglas automáticas; juez en `scripts.run_nightly` |
| 0.5 | Clientes simulados por LLM contra el agente real | `uv run python -m scripts.run_simulations mis-escenarios.yaml` |
| 1 | Calificación del cliente (1–5) | `POST /conversation-outcomes/feedback` (enviar la encuesta al cliente es responsabilidad de tu despliegue) |
| 2 | Propuestas de cambio a KB/prompts | `scripts.run_nightly` las genera; se revisan en `/improvement-proposals` y **nada se aplica sin `approve`** |

Programa `scripts.run_nightly` con cron (una vez por noche). Revisa las conversaciones en `/conversation-outcomes`
(filtros `source`, `flag`, `max_score`). Para probar un cambio de KB/prompt contra conversaciones pasadas:
`uv run python -m scripts.replay_conversations web <user_id>` (solo canales que exponen historial).

## 9. Checklist antes de producción

- [ ] `tenant.yaml` completo y revisado; `llm` configurado y prompts revisados.
- [ ] Decidido `verify_responses` (latencia y cuota vs. riesgo de alucinación) y probados a mano mensajes de inyección de prompt.
- [ ] KB cargada y `GET /knowledge-blocks/orphans` vacío.
- [ ] Escenarios propios corridos con `run_simulations` y sus resultados leídos.
- [ ] `auth.mode: firebase` con `admin_emails` y `cors.allowed_origins` definidos (sin `ALLOW_INSECURE_AUTH`).
- [ ] Checkpointer persistente y base de datos de producción probada con las migraciones.
- [ ] `run_nightly` programado.
- [ ] Mecanismo para enviar la encuesta de feedback, si se quiere la Capa 1.
