# gang.guide — task runner (https://just.systems/)

set dotenv-load := true

# ── Default ────────────────────────────────────────────────────────────────────

default:
    @just --list

# ── Development ────────────────────────────────────────────────────────────────

# Start the dev server
dev:
    cd apps/web && npm run dev

# Build graph.json + details.json from data/orgs/
build-data:
    python3 build.py

# Lint all org files and edges
lint:
    python3 apps/pipeline/lint.py

# Run web tests
test:
    cd apps/web && npm run test

# Run all tests (pipeline + web)
test-all:
    python -m pytest
    cd apps/web && npm run test

# Format Python code
fmt:
    ruff format apps/pipeline/ build.py
    ruff check --fix apps/pipeline/ build.py

# Run CI checks locally
ci: lint fmt test-all build-data check build

# Type-check the frontend
check:
    cd apps/web && npx svelte-kit sync && npm run check

# ── Build & Deploy ─────────────────────────────────────────────────────────────

# Production build (vite)
build:
    cd apps/web && npm run build

# Deploy to production (Cloudflare Workers)
deploy:
    cd apps/web && npm run deploy

# Deploy preview (personal stage)
deploy-preview:
    cd apps/web && npm run deploy:preview

# Tear down production
destroy:
    cd apps/web && npm run destroy

# ── Setup ──────────────────────────────────────────────────────────────────────

# Bootstrap after cloning
setup:
    npm install
    cd apps/web && npm install
    python3 build.py
    npx ruler apply
    @echo "Done. Run 'just dev' to start."

# Generate AI agent config files from .ruler/
ruler:
    npx ruler apply

# Install git hooks
hooks:
    npx lefthook install

# ── Pipeline ───────────────────────────────────────────────────────────────────

# Run LLM extraction on a source (requires nix develop + API key)
extract source:
    python3 -m apps.pipeline.extract --source {{source}}

# Run consensus merge on extracted data
merge source:
    python3 -m apps.pipeline.merge --source {{source}}

# Preview what apply would change (dry run)
apply-preview source:
    python3 -m apps.pipeline.apply --source {{source}} --dry-run

# Apply extracted data to orgs + edges
apply source:
    python3 -m apps.pipeline.apply --source {{source}}

# Full pipeline: extract → adjudicate → merge → apply (with preview)
pipeline source:
    python3 -m apps.pipeline.extract --source {{source}}
    python3 -m apps.pipeline.adjudicate --source {{source}}
    python3 -m apps.pipeline.merge --source {{source}}
    python3 -m apps.pipeline.apply --source {{source}} --dry-run
    @echo "\nReview above. Run 'just apply {{source}}' to commit changes."

# Adjudicate conflicting extractions (sonnet, only where needed)
adjudicate source:
    python3 -m apps.pipeline.adjudicate --source {{source}}

# Enrich weak org profiles (scores, gathers context from raw data, calls LLM)
enrich *args:
    python3 -m apps.pipeline.enrich {{args}}

# Enrich dry-run: show priority ranking without calling LLM
enrich-rank:
    python3 -m apps.pipeline.enrich --dry-run --limit 50

# Verify suspicious edges via web search (post-adjudication)
verify source *args:
    python3 -m apps.pipeline.verify --source {{source}} {{args}}

# Build the page→org index from raw data
index:
    python3 -m apps.pipeline.parse.parse_index
