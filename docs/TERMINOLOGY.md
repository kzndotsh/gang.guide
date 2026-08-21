# Terminology

## Data

| Term | Meaning |
|------|---------|
| **Org** | A criminal organization (gang, MC, crime family, prison gang, ...) |
| **Edge** | A relationship between two orgs |
| **Lane** | A vertical band on the map (e.g. Chicago Folk) |
| **Nation** | Umbrella identity (Crips, Bloods, Folk Nation, People Nation) |
| **Set** | Local chapter of a larger gang |
| **Metro** | Primary city/area |
| **Stub** | Minimal org file from `apply.py --create-orgs`; needs enrichment |

## Edge types

Canonical direction: [SCHEMA.md](SCHEMA.md#edge-types).

| Type | Meaning |
|------|---------|
| `alliance` | Cooperation (undirected) |
| `rivalry` | Conflict (undirected) |
| `member_of` | Source belongs to target (not a gang-nation field) |
| `nation` | From `nation_affiliation` at build time: not stored in `edges.json` |
| `spin_off` | Source spawned target |
| `parent` | Source is parent/umbrella of target |

## Org types

| Type | Examples |
|------|----------|
| `street_gang` | Crips sets, Latin Kings, MS-13 |
| `prison_gang` | Aryan Brotherhood, Mexican Mafia, BGF |
| `motorcycle_club` | Hells Angels, Bandidos, Pagans |
| `organized_crime` | Gambino family, Sinaloa Cartel |
| `white_supremacist` | Volksfront, Aryan Nations |
| `alliance` | Folk Nation, People Nation |
| `nation` | Crips, Bloods as umbrella identities |

## Precision

| Value | Meaning |
|-------|---------|
| `exact` | Year confirmed by a strong source |
| `circa` | About that year (±2-3) |
| `decade` | That decade; year should be the decade start (1970 = 1970s) |
| `estimate` | Best guess |

## Pipeline

| Term | Meaning |
|------|---------|
| **Extract** | LLM → structured JSON from source text (3 temperatures) |
| **Adjudicate** | LLM checks evidence quotes from the three runs |
| **Verify** | Optional web-search check of suspicious edges |
| **Merge** | `adjudicated.json` if present, else 2/3 consensus |
| **Apply** | Write consensus into org files and `edges.json` |
| **Enrich** | Fill weak profiles (standalone) |
| **Clean** | Spot-check existing fields (standalone) |
| **Evidence** | Verbatim quote supporting an edge |
| **Slug** | Kebab-case id/filename from the org name |
| **Display year** | Canvas X; lane fallback if `founded_year` is null |
| **Ignore file** | `.gangguideignore`: skip/suppress rules |

Source keys and scrapers: [PIPELINE.md](PIPELINE.md#sources).
