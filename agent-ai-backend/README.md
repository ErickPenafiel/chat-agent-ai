# Agente IA genérico de soporte/ventas por mensajería

Template reutilizable (un negocio = un despliegue). Puesta en marcha en
`docs/new-tenant-guide.md`; ejemplo completo con un negocio ficticio en `examples/coffee-shop/`.

```bash
uv sync
uv run pytest
# El ejemplo trae auth.mode: disabled, que exige este opt-in explícito (solo desarrollo local):
export ALLOW_INSECURE_AUTH=1 TENANT_CONFIG=examples/coffee-shop/tenant.yaml DATABASE_URL=sqlite:///./demo.db
uv run alembic upgrade head
uv run python -m scripts.seed_tenant examples/coffee-shop/kb.yaml
uv run uvicorn src.main:app
```

Para producción: `auth.mode: firebase` y `cors.allowed_origins` (ver la guía, sección 7b).

Para respuestas reales hay que configurar el bloque `llm` del tenant (ver la guía).

## Evaluación

`examples/coffee-shop/golden.yaml` tiene casos dorados (pregunta, datos que debe traer la respuesta, qué no puede afirmar, si debe pasar a una persona). Se corren contra el agente real con:

```bash
uv run python -m scripts.run_golden            # usa el LLM del tenant y las claves de .env
uv run python -m scripts.run_golden --only seguridad
```

Reporta resolución con intervalo de confianza, escalamiento correcto, recuperación de la KB y afirmaciones prohibidas, y guarda el informe en `eval_reports/`. Los casos que fallan por un error del LLM se reintentan y, si persiste, se descartan del porcentaje. La línea base está en [docs/eval-baseline.md](docs/eval-baseline.md).
