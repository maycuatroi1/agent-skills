---
name: dokploy-cli
description: Manage Dokploy services (apps, compose, databases, domains, env vars, deploys) via the official `@dokploy/cli`. Trigger on any of "dokploy cli", "install dokploy cli", "set up dokploy on this machine", "list dokploy services", "deploy dokploy app", "set dokploy env", "create dokploy domain", "dokploy postgres/mysql/mongo/redis", or mentions of managing services on a Dokploy panel that are NOT LMS-specific (LMS-specific workflows live in `./lms dokploy` — see "Boundary" below). Provides a one-shot idempotent installer (`scripts/install.sh`) that handles npm install + ~/.omelet.json verification + shell rc wiring + smoke test, so the same skill works on a fresh machine. Covers auth via `~/.omelet.json` + shell rc, the 32 command groups, common patterns (get JSON output, pipe with jq, find composeId/applicationId), and how it coexists with the LMS CLI.
version: 0.1.0
---

# dokploy-cli

Thin wrapper guidance for the official `@dokploy/cli`: a 449-command CLI auto-generated from the Dokploy OpenAPI spec covering every panel feature (projects, apps, compose, postgres/mysql/mariadb/mongo/redis, domains, certificates, backups, schedules, servers, SSO, settings, etc.).

## When to use

Use this skill when the user wants to **manage any Dokploy service** that is not part of the LMS-specific multi-service workflows. Examples:

- List/inspect projects, applications, compose services
- Update env vars on a single service
- Trigger a deploy / rollback / restart
- Create or delete a domain
- Create or stop a database (postgres, mysql, mongo, redis, mariadb)
- Manage backups, certificates, schedules, mounts, registries
- Anything else surfaced in the Dokploy panel

### Boundary with the LMS CLI

Two LMS-specific workflows stay in `./lms dokploy` (in `~/git/evo-lms-workspace/elearning/evo-lms-django`) because they wrap multi-step logic (gh API + env-file substitution + redeploy polling):

| Stays in `./lms dokploy`                  | Why                                                                  |
| ----------------------------------------- | -------------------------------------------------------------------- |
| `./lms dokploy sync-env-vars`             | Patches `envs/.{tenant}.env` via gh API + waits for webhook redeploy |
| `./lms dokploy clone-environment`         | Clones all compose services with rename rules across env + branch    |

Everything else — `projects all`, `application deploy`, `compose env-vars`, etc. — moved to the official `dokploy` CLI.

## Install (one command, idempotent)

```bash
bash ~/agent-skills/skills/dokploy-cli/scripts/install.sh
```

Does all four setup steps. Safe to re-run on the same machine or on a new one:

1. **npm package** — installs `@dokploy/cli` globally if `dokploy` not on PATH.
2. **Credentials** — verifies `~/.omelet.json` has `dokploy_url` + `dokploy_api_key`; prints exact `add_credential.py` invocations if either is missing.
3. **Shell rc** — appends `source .../export_dokploy_env.sh` to `~/.zshrc` and `~/.bashrc` (only those that exist; only if not already present — matches both `~/...` and absolute-path forms).
4. **Smoke test** — exports the env vars and runs `dokploy project all` to confirm the token works.

After install, open a new terminal (or `exec $SHELL`) so the shell rc picks up the source line.

### Cross-machine workflow

On a new machine:

```bash
git clone <agent-skills repo> ~/agent-skills
OMELET_SYNC_REPO=owner/repo bash ~/agent-skills/skills/credentials-utils/scripts/sync_pull.sh
bash ~/agent-skills/skills/dokploy-cli/scripts/install.sh
```

The `credentials-utils` `sync_pull.sh` brings the credentials folder from the user's private repo and compiles `~/.omelet.json` (with `dokploy_url` + `dokploy_api_key`, sourced from `infra/dokploy.json`); the install script does the rest. The flat `~/.omelet.json` is a generated artifact - to change the Dokploy creds, edit via `credentials-utils` `add_credential.py` (writes `infra/dokploy.json` then recompiles), not by hand.

### What the install script does NOT do

- Doesn't install Node.js itself — errors out with instructions if `node` is missing.
- Doesn't create `~/.omelet.json` — prints the `add_credential.py` commands but doesn't run them, so secrets are entered interactively (no echo).
- Doesn't run `dokploy auth -u ... -t ...` — that command stores the token inside the installed npm package (wiped on reinstall). Env vars from `~/.omelet.json` survive upgrades and roam across machines via credentials-utils sync.

### Manual reference (if install.sh is unavailable)

```bash
npm install -g @dokploy/cli
# Add to ~/.zshrc or ~/.bashrc:
#   source ~/agent-skills/skills/dokploy-cli/scripts/export_dokploy_env.sh
# Then in a new shell:
dokploy project all --json | jq '.[].name'
```

Credentials keys:
- `dokploy_url` — panel URL **without** `/api` suffix (e.g. `https://dokploy.omelet.tech`)
- `dokploy_api_key` — long-lived API token from Dokploy → Profile → API keys

## Quick reference

```bash
# Discovery
dokploy --help                              # 32 command groups
dokploy <group> --help                      # actions in a group
dokploy <group> <action> --help             # options for an action

# Projects / services
dokploy project all                         # list all projects
dokploy project one --projectId <id>        # full project (incl. environments)
dokploy environment one --environmentId <id># env contents (apps + compose)

# Application (Nixpacks / Dockerfile / static)
dokploy application one --applicationId <id>
dokploy application deploy --applicationId <id>
dokploy application stop  --applicationId <id>
dokploy application start --applicationId <id>
dokploy application reload --applicationId <id>

# Compose (docker-compose)
dokploy compose one --composeId <id>
dokploy compose deploy --composeId <id>
dokploy compose stop   --composeId <id>
dokploy compose start  --composeId <id>
dokploy compose redeploy --composeId <id>

# Databases — same pattern for postgres / mysql / mariadb / mongo / redis
dokploy postgres create --name my-db --environmentId <id> ...
dokploy postgres one    --postgresId <id>
dokploy postgres stop   --postgresId <id>
dokploy postgres start  --postgresId <id>
dokploy postgres deploy --postgresId <id>

# Domains
dokploy domain byApplicationId --applicationId <id>
dokploy domain byComposeId     --composeId <id>
dokploy domain create --host api.example.com --composeId <id> \
                      --serviceName web --port 8080 --https true \
                      --certificateType letsencrypt --domainType compose

# Deployments / rollback
dokploy deployment allByApplication --applicationId <id>
dokploy deployment allByCompose     --composeId <id>
dokploy rollback rollback --rollbackId <id>

# Servers
dokploy server all
dokploy server one --serverId <id>
```

All commands accept `--json` for raw JSON suitable for `jq` piping.

## Common patterns

### Find a composeId / applicationId without browsing the panel

```bash
# Across all projects/envs (jq filters)
dokploy project all --json | jq -r '
  .[] |
  .environments[] |
  (.compose[]?         | "compose      \(.composeId)      \(.name)"),
  (.applications[]?    | "application  \(.applicationId)  \(.name)")
'
```

For LMS specifically, there is also `./lms dokploy find-service` in the LMS CLI — but for any other Dokploy panel, the jq snippet above works.

### Update one env var on a compose service

There is no atomic "set one key" command — the API takes the entire env blob. Pattern: read, mutate, write.

```bash
ID=<composeId>

# Read current env as plain text (Dokploy stores it as one multi-line string)
ENV=$(dokploy compose one --composeId "$ID" --json | jq -r '.env')

# Mutate (e.g. set FOO=bar; append if absent, replace if present)
NEW_ENV=$(printf '%s\n' "$ENV" | awk -v k=FOO -v v=bar '
  BEGIN { done=0 }
  $0 ~ "^"k"=" { print k"="v; done=1; next }
  { print }
  END { if (!done) print k"="v }
')

# Write back
dokploy compose update --composeId "$ID" --env "$NEW_ENV"
```

For LMS deploy branches, `./lms dokploy sync-env-vars` is preferred — it commits the change to the git repo so the env file remains the source of truth.

### Trigger a deploy and tail status

```bash
ID=<composeId>
dokploy compose deploy --composeId "$ID"

# Poll status
while :; do
  S=$(dokploy compose one --composeId "$ID" --json | jq -r '.composeStatus')
  echo "$(date +%T) status=$S"
  [ "$S" = "done" ] && break
  [ "$S" = "error" ] && { echo "DEPLOY FAILED"; exit 1; }
  sleep 15
done
```

### Output JSON for scripting

```bash
dokploy project all --json | jq '.[] | {name, projectId, environments: [.environments[].name]}'
```

## Gotchas

- **URL without `/api`**: `DOKPLOY_URL` must be the panel root (e.g. `https://dokploy.omelet.tech`). The CLI appends `/api` itself. The LMS CLI's internal `get_dokploy_credentials()` adds `/api` automatically for backward compat.
- **API path is `/api/trpc/...` under the hood**: don't try to call endpoints with raw `curl` against `/api/<endpoint>` like the legacy LMS code does — that path still works (it's the older REST surface) but the official CLI uses the tRPC surface. Use the CLI; only fall back to curl for endpoints the CLI lacks.
- **`compose.update` silently ignores `serverId`**: must be set on `compose.create`. The LMS `clone-environment` workflow handles this.
- **No "set single env var" command**: see pattern above.
- **`dokploy auth` writes inside the npm package**: avoid — use env vars from `~/.omelet.json` instead so the auth survives `npm i -g @dokploy/cli` upgrades.
- **Token is org-scoped**: the same token works for every project the user has access to; no per-project auth.

## Command groups (449 total)

| Group              | Count | Group           | Count |
| ------------------ | ----: | --------------- | ----: |
| admin              |     1 | notification    |    38 |
| ai                 |     9 | organization    |    10 |
| application        |    29 | patch           |    12 |
| backup             |    11 | port            |     4 |
| bitbucket          |     7 | postgres        |    14 |
| certificates       |     4 | preview-deployment |  4 |
| cluster            |     4 | project         |     8 |
| compose            |    28 | redirects       |     4 |
| deployment         |     8 | redis           |    14 |
| destination        |     6 | registry        |     7 |
| docker             |     7 | rollback        |     2 |
| domain             |     9 | schedule        |     6 |
| environment        |     7 | security        |     4 |
| gitea              |     8 | server          |    16 |
| github             |     6 | settings        |    49 |
| gitlab             |     7 | ssh-key         |     6 |
| git-provider       |     2 | sso             |    10 |
| license-key        |     6 | stripe          |     7 |
| mariadb            |    14 | swarm           |     3 |
| mongo              |    14 | user            |    18 |
| mounts             |     6 | volume-backups  |     6 |
| mysql              |    14 |                 |       |

Drill down with `dokploy <group> --help` to discover specific actions.

## Files in this skill

```
scripts/
  install.sh               # one-shot idempotent setup: npm install + shell rc + smoke test
  export_dokploy_env.sh    # sourced from shell rc; exports DOKPLOY_URL/DOKPLOY_API_KEY from ~/.omelet.json
```

## See also

- Upstream: https://github.com/Dokploy/cli (MIT, TypeScript)
- LMS-specific workflows: `~/git/evo-lms-workspace/elearning/evo-lms-django` → `./lms dokploy --help`
- Credentials lifecycle: `credentials-utils` skill
- Cloning an entire environment (LMS HUST → NTU pattern): `~/git/evo-lms-workspace/elearning/evo-lms-django/.claude/skills/learned/dokploy-clone-environment/`
