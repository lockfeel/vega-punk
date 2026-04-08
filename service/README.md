# Service Layer

The web service layer of Vega-punk, providing OpenClaw gateway integration, session management, and security audit capabilities. Decoupled from the SKILL state machine — the service layer handles **runtime infrastructure**, while the SKILL system handles **workflow orchestration**.

## Architecture

```
service/
├── vega.py                  # FastAPI entry point, route definitions, lifecycle management
├── data.db                  # SQLite database (sessions/audit records)
├── gateway/
│   ├── client.py            # OpenClaw gateway WebSocket client
│   ├── session_manager.py   # Session lifecycle management (idle timeout 1800s)
│   ├── config_loader.py     # Load OpenClaw connection config from env/config file
│   ├── security_audit.py    # Security audit engine (RiskLevel-based)
│   └── output_filter.py     # Output filtering (sensitive data redaction)
├── utils/
│   ├── db_util.py           # SQLite ORM / database operations
│   ├── token_util.py        # JWT token verification
│   └── common_util.py       # Common utility functions
└── templates/
    ├── login.html           # Login page
    └── chats.html           # Chat page
```

## Relationship with the SKILL System

| Layer | Responsibility | Communication |
|-------|---------------|---------------|
| **SKILL System** (SKILL.md + references/) | Workflow orchestration, state machine, design→plan→execute→review | `.vega-punk-state.json` + `roadmap.json` |
| **Service Layer** (service/) | Runtime infrastructure, gateway proxy, session management, security audit | HTTP/WebSocket API |

**The SKILL system does not depend on the Service layer.** vega-punk can run fully without service/. The Service layer provides for multi-user scenarios:
- WebSocket proxy and session reuse for the OpenClaw gateway
- Database-backed session persistence
- Security audit and output filtering
- Web UI management interface

## Getting Started

```bash
cd service
pip install -r requirements.txt  # if available
python vega.py
# Default: http://localhost:8000
```

Environment variables:
- `OPENCLAW_URL` — OpenClaw gateway address
- `OPENCLAW_TOKEN` — Authentication token (OpenClaw features unavailable if not configured; SKILL system unaffected)

## Security

- `security_audit.py` — RiskLevel-based tiered audit
- `output_filter.py` — Automatic redaction of sensitive information (tokens, keys, IPs)
- `token_util.py` — JWT authentication verification
