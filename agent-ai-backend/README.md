# Agente IA genérico de soporte/ventas por mensajería

Template reutilizable (un negocio = un despliegue). Diseño en `../ARCHITECTURE-PLAN.md`; puesta en marcha en
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
