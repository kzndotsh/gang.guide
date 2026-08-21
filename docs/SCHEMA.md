# Schema

Machine-readable org schema: [`apps/pipeline/schema.json`](../apps/pipeline/schema.json). Quality rules and lint severities: [STANDARDS.md](STANDARDS.md).

## Org (`data/orgs/*.json`)

```json
{
  "id": "org:slug-name",
  "name": "Display Name",
  "aliases": ["Alt Name 1", "Alt Name 2"],
  "type": "street_gang | prison_gang | motorcycle_club | organized_crime | white_supremacist | cybercrime_group | alliance | nation",
  "lane": "lane-id",
  "metro": "City Name",
  "description": "Factual 2-4 sentence summary starting with the canonical name.",
  "founded_year": 1958,
  "founded_year_precision": "exact | circa | decade | estimate",
  "disbanded_year": null,
  "colors": ["black", "blue"],
  "symbols": ["Pitchfork", "Six-Point Star"],
  "membership_estimate": 5000,
  "military_service": "Army, Marines",
  "nation_affiliation": "org:nation-id | null",
  "status": "active | inactive | unknown",
  "sources": [
    {"url": "https://...", "title": "Source Title"}
  ]
}
```

`military_service` is optional (mostly motorcycle clubs).

### Required vs recommended

Lint (`apps/pipeline/lint.py`) is the gate, not JSON Schema:

| | Fields |
|--|--------|
| **Required** (error if empty) | `id`, `name`, `description`, `sources` |
| **Recommended** (warning if empty) | `lane`, `founded_year` |

`apps/pipeline/schema.json` matches those required fields. `type`, `lane`, and `founded_year` are expected on real profiles but stubs may omit them.

### Field notes

- **Description**: Start with the canonical `name` (or "The X"). 2-4 factual sentences, 50-800 characters. No HTML entities, slurs, or scrape junk. Full rules: [STANDARDS.md](STANDARDS.md#common-data-quality-issues).
- **Status**: `active` (operating), `inactive` (disbanded/defunct/absorbed; set `disbanded_year` if known), `unknown`.
- **Metro**: Specific city, not county/region. Chicago neighborhoods → `"Chicago"`; LA neighborhoods → `"Los Angeles"`; national umbrellas → `"United States"`. Must fit the `lane`.
- **`founded_year_precision`**: `exact`, `circa`, `decade`, `estimate`. There is no `range` value.

### ID format

`org:` + kebab-case slug from the org name. Filename must be `data/orgs/{slug}.json`.

Lint **errors** if the slug is not `a-z`, `0-9`, hyphens, no doubles, no leading/trailing hyphen. Filename/ID mismatch is **info**, not an error.

**Slug derivation:** strip accents, lowercase, replace non-alphanumeric runs with `-`, trim hyphens.

- `Rollin 30s Original Harlem Crips` → `org:rollin-30s-original-harlem-crips`
- `Sureños` → `org:surenos`
- `C-Notes` → `org:c-notes`

### Constraints

- `lane` must exist in `data/lanes.json`
- `sources[].url` should be `https`
- `disbanded_year` must be ≥ `founded_year` (lint errors if it is before)
- `nation_affiliation` must reference an existing org ID

## Edge (`data/edges.json`)

```json
{
  "id": "a1b2c3d4e5f6",
  "source": "org:source-id",
  "target": "org:target-id",
  "type": "alliance | rivalry | member_of | spin_off | parent",
  "citations": [
    {
      "url": "https://en.wikipedia.org/wiki/Bloods",
      "title": "Wikipedia",
      "evidence": "Verbatim quote from the source proving this relationship."
    }
  ],
  "start_year": 1977,
  "end_year": 1992
}
```

`citations[]` is the canonical multi-source field. Each citation has:
- `url` — source page URL (should be `https`)
- `title` — human-readable source name (e.g. "Wikipedia", "UnitedGangs")
- `evidence` — verbatim quote from the source proving the relationship

Multiple citations allow the same edge to be supported by several independent sources. `build.py` falls back to legacy `evidence`/`source_url` fields if `citations` is absent.

**Deprecated fields** (do not use in new edges, will be removed):
- `evidence` — use `citations[0].evidence`
- `source_url` — use `citations[0].url`

`nation` is **not** stored here. `build.py` generates nation edges from `nation_affiliation`.

### Edge types

| Type | Direction | Meaning |
|------|-----------|---------|
| `alliance` | Undirected | Cooperation / support |
| `rivalry` | Undirected | Conflict |
| `member_of` | Directed | Source belongs to target (coalition, prison control, umbrella that is **not** a gang nation) |
| `spin_off` | Directed | Source is the origin; target formed from source (A → spin_off → B means B came from A) |
| `parent` | Directed | Source is the parent/umbrella of target |
| `nation` | Auto-generated | From `nation_affiliation` at build time |

### `nation_affiliation` vs `member_of`

**`nation_affiliation`** (org field): the set claims a gang nation. Examples: Rollin 60s Crips → `org:crips`, Mob Piru → `org:bloods`. Use this for Blood / Crip / Sureño / Folk / People (and similar) nation membership.

**`member_of`** (edge): structural hierarchy that is **not** that nation field. Examples: Latin Kings `member_of` People Nation; Florencia 13 `member_of` Mexican Mafia.

If the target is `org:crips`, `org:bloods`, `org:folk-nation`, `org:people-nation`, `org:surenos`, etc., use `nation_affiliation`, not `member_of`.

### Edge ID and storage

- ID is a 12-character SHA-256 of `source:target:type` (stable).
- `alliance` / `rivalry`: stored with the alphabetically smaller org ID as `source`.
- No self-references, no duplicate `source`+`target`+`type`. Alliance + rivalry on the same pair only with `start_year` / `end_year`.

## Lane (`data/lanes.json`)

```json
{
  "lanes": [
    {
      "id": "chicago-folk",
      "label": "Chicago Folk Nation",
      "group": "Chicago",
      "order": 22
    }
  ]
}
```

`group` drives the lane filter. `order` is canvas Y position.

Current IDs include: `prison`, `white-supremacist`, `motorcycle-clubs`, `organized-crime`, Chicago (`chicago-folk-people`, `chicago-folk`, `chicago-people`, `chicago-independent`), Bloods (`blood-nation`, `california-bloods-*`), Crips (`crip-nation`, `california-crips-*`), Latino (`california-latino-*`), `asian-gangs`, `new-york`, `midwest`, `detroit`, `southeast-southwest`, `historical-east`, `other-national`, `unplaced`.

Canonical list: `data/lanes.json`.

## graph.json

Slim payload for the canvas (`apps/web/static/graph.json`). Includes auto-generated nation edges, so the edge count is higher than `edges.json`.

Node `data` includes `standard_name`, `aliases`, `type`, `metro`, years, `colors`, `symbols`, `nation_affiliation`, `status`, and `layout` (`lane`, `y`, `display_year`, ...). `meta` has lanes and counts.

## details.json

Lazy-loaded on node click: `description` + `sources` keyed by org ID.

Lint check inventory and severities: [STANDARDS.md](STANDARDS.md).
