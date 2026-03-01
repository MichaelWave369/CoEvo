# Changelog

All notable changes to CoEvo are documented in this file.

## [0.8.0] - 2026-03-01

### Added
- Release metadata and publication docs for first GitHub release.
- `RELEASE_NOTES.md` with release highlights, deployment notes, and caveats.
- `scripts/create_release_archive.sh` for generating a clean source archive suitable for GitHub release assets.

### Changed
- Normalized visible project version references to `0.8.0` across root docs, server/web README files, frontend package metadata, and in-app UI badges.
- Polished deployment guidance with realistic environment variable templates for Render, Railway, and Vercel.

### Verified
- Backend dependency installation, startup, and `/api/health` endpoint.
- Frontend dependency installation and production build flow.

### Known limitations
- Agent features require external model provider credentials or self-hosted Ollama; they are best kept disabled (`COEVO_AGENT_ENABLED=0`) for simple public demos.
- SQLite is acceptable for local use and short demos; managed Postgres is recommended for persistent cloud deployments.
