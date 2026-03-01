# CoEvo 0.8.0 Release Notes

## Release status

**Recommended status:** Stable release (`v0.8.0`).

## Highlights

- CoEvo is now release-hardened for first GitHub publication.
- Version metadata is consistent across user-facing docs and frontend package metadata.
- Deployment instructions are publication-ready for:
  - Backend: Render or Railway
  - Frontend: Vercel or Railway
- Build/start smoke checks were run for backend and frontend paths.
- Release archive script outputs to `dist/coevo-<version>-release.zip` and excludes common local artifacts.

## Deployment notes

- Keep `COEVO_AGENT_ENABLED=0` unless model provider access is configured.
- Set a strong `COEVO_JWT_SECRET` and a non-default admin password.
- Use managed Postgres in cloud environments for persistence.
- Restrict `COEVO_CORS_ORIGINS` to exact frontend origins.

## Known limitations

- Agent functionality depends on external model runtimes/keys.
- Free-tier hosting can have cold starts and ephemeral disks.

## Suggested GitHub release title

`CoEvo v0.8.0 — First Public Release`
