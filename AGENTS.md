# AGENTS.md — gold24-7

GOLD24-7 research and **paper-trading only** platform (XM MT5, Hermes 3:8B via Ollama, OpenTraderWorld journal sync).

## Where it lives
- `~/dev/gold24-7` — a peer git repo **outside** the m-2nd-brain vault. It used to be `code/gold24-7`; do not recreate that.
- Registered in the vault's `BUILDS.md` → "Repositories outside the vault". Policy: vault `shared-infra/playbooks/docker-first-project-sop.md`.

## Run it (Docker-first)
- Dashboard: `docker compose up -d dashboard` → `http://localhost:8585`.
- Paper-trading daemon: `docker compose --profile daemon up -d`.
- Tests: `docker compose run --rm dashboard pytest`.
- The MT5 bridge (`scripts/mt5_bridge_server.py`) runs on Windows; the container reaches it at `host.docker.internal`.
- The host `.venv` exists only for editor tooling; its launcher scripts may carry stale paths, so use `python -m ...` or Docker.

## Hard rules
- Live trading is disabled: keep `ENVIRONMENT=paper`, `ALLOW_LIVE_EXECUTION=false`, `IS_SIMULATION_ONLY=true`.
- Never commit `.env`, broker credentials or account numbers.
- No resolved home-directory paths in docs or code; use `~/dev/gold24-7`, repo-relative paths or env vars.

## Session protocol
Read `HANDOFF.md` → `STATE.md` → `SESSION.md`. Before ending: rewrite the current-state sections of `HANDOFF.md`/`STATE.md`, update `SESSION.md`, commit scoped paths, and note the session in the vault's `HANDOFF.md` if it changed cross-repo state.
