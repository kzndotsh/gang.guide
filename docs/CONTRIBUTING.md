# Contributing

Full field reference: [SCHEMA.md](SCHEMA.md). Lint and writing rules: [STANDARDS.md](STANDARDS.md). Pipeline: [PIPELINE.md](PIPELINE.md). Docs map: [INDEX.md](INDEX.md).

## Setup

```bash
git clone https://github.com/kzndotsh/gang.guide.git
cd gang.guide
just setup
```

Needs Node 22+ and Python 3.12+. `nix develop` matches CI. Copy `.env.example` for pipeline keys; `apps/web/.env.example` for deploy.

```bash
just dev
just test-all
just fmt
just ci
```

## Commits

[Conventional commits](https://www.conventionalcommits.org/), lefthook + commitlint.

```
feat(web): add timeline scrubber
fix(data): correct disbanded_year for BMF
docs: update README
chore(infra): update CI workflow
```

Scopes: `web`, `data`, `pipeline`, `infra`, `deps`, `ci`, `release`.

## Adding an org

Slug from the name: lowercase, hyphens, no special characters, no `--`. File `data/orgs/{slug}.json`, `"id": "org:{slug}"`.

1. Create the org file (required: `id`, `name`, `description`, `sources`). Symbols title case. Description starts with the canonical name.
2. Add rows to `data/edges.json` if relationships are known (`alliance` / `rivalry` undirected; `member_of` / `spin_off` / `parent` directed: [SCHEMA.md](SCHEMA.md#edge-types)).
3. `just lint` then `just build-data`.

Do not invent organizations. Every source needs `url` and `title`. `founded_year_precision` is `exact` | `circa` | `decade` | `estimate`.

## Tests

```bash
pytest                     # unit (CI)
pytest -m slow             # e2e, needs API key
cd apps/web && npx vitest run
just test-all
```

## Pipeline

Needs `nix develop` (or equivalent) and keys from `.env.example`.

```bash
just pipeline chicago_history    # extract → adjudicate → merge → apply dry-run
just apply chicago_history       # after you review the dry-run
just verify chicago_history      # optional web-search pass (not in just pipeline)
just enrich
just clean
```

## Code style

- Python: Ruff, 4-space, 120-char, types on functions (`apps/pipeline/pyproject.toml`)
- TypeScript/Svelte: 2-space, Svelte 5 runes, no `any`; `svelte-check` on pre-push
- LF endings (`.editorconfig`)
