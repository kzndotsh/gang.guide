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
