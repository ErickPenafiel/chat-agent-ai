# Generic AI support/sales agent for messaging channels

[Español](README.md) · English

Reusable template (one business = one deployment): a support/sales agent that answers over WhatsApp Cloud API or a web chat, backed by a per-tenant knowledge base, editable prompts, human handoff and an evaluation harness.

- `agent-ai-backend/` — API and agent (Python, FastAPI, LangGraph). See `agent-ai-backend/README.md`.
- `agent-ai-frontend/` — web console (React 19, Vite, Tailwind).

## Quickstart

```bash
cp agent-ai-backend/.env.example agent-ai-backend/.env   # fill in your keys
docker compose up --build
```

Backend on `:8000`, frontend on `:5173`. Without Docker: `./scripts/start-demo.sh`.

Tests: `cd agent-ai-backend && uv run pytest`. Configuration lives in `tenant.yaml` (see `agent-ai-backend/examples/coffee-shop/` and `agent-ai-backend/docs/new-tenant-guide.md`, in Spanish). Authentication uses Firebase Auth.

## Contributing & security

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md). License: [MIT](LICENSE).
