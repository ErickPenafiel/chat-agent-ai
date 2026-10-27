# Cómo contribuir

1. Haz un fork y crea una rama desde `main`.
2. Backend (`agent-ai-backend/`): `uv sync && uv run ruff check . && uv run pytest`.
3. Frontend (`agent-ai-frontend/`): `pnpm install && pnpm lint && pnpm build`.
4. Abre un pull request describiendo el cambio; el CI debe pasar.

Convenciones: nombres de archivos, claves de config e ids en inglés; prompts,
mensajes al cliente, KB de ejemplo, comentarios y docs en español.
Los pendientes conocidos están en los issues con la etiqueta `good first issue`.
