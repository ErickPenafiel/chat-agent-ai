# Agente IA genérico de soporte/ventas por mensajería

[![CI](https://github.com/ErickPenafiel/chat-agent-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/ErickPenafiel/chat-agent-ai/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Template reutilizable (un negocio = un despliegue).

## Quickstart

```bash
cp agent-ai-backend/.env.example agent-ai-backend/.env   # completa tus claves
docker compose up --build
```

Backend en `:8000`, frontend en `:5173` (ver `docker-compose.yml`). Para correr
sin Docker: `./scripts/start-demo.sh`.

## Contenido

- `ARCHITECTURE-PLAN.md` — plan de arquitectura.
- `agent-ai-backend/` — API y agente (Python, FastAPI, LangGraph). Ver `agent-ai-backend/README.md`.
- `agent-ai-frontend/` — consola web (React 19, Vite, Tailwind). `pnpm install && pnpm dev` desde esa carpeta.

## Contribuir y seguridad

Ver [CONTRIBUTING.md](CONTRIBUTING.md) y [SECURITY.md](SECURITY.md). Licencia: [MIT](LICENSE).
