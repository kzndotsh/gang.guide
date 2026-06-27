# Data Standards

This document describes how gang.guide maintains data quality across its org files and edge list. All checks are enforced by `apps/pipeline/lint.py`, which runs in CI and as a gate after `apply.py`.

## Severity Levels

| Level | Meaning | CI behavior |
|-------|---------|-------------|
| **Error** | Data is broken or contradictory — must be fixed | Fails CI |
| **Warning** | Data is incomplete or suspicious — should be investigated | Passes CI |
| **Info** | Data could be improved — low priority | Passes CI |

## Org Validation (`check_orgs`)

### Errors
- **Missing required fields**: `id`, `name`, `description`, `sources` must be non-empty.
- **Invalid lane**: `lane` must match an ID in `data/lanes.json`.
- **Sources missing url/title**: Every source object needs both fields.
- **Temporal impossibility**: `disbanded_year` before `founded_year`.

### Warnings
- **Missing recommended fields**: `lane`, `founded_year` — expected but not blocking (stub orgs from pipeline).
- **Thin description**: Under 50 characters.
- **HTML entities in description**: Leftover scrape junk (`&amp;`, `&#39;`).
- **Alias too long**: Over 50 characters (likely scrape junk, not a real alias).
- **Invalid colors**: Must be recognizable color names.
- **Impossible founding dates**: Crip set before 1969, Piru before 1972.
- **Type/lane mismatch**: `street_gang` in `prison` lane, non-MC in `motorcycle-clubs`.
- **Name issues**: trailing whitespace, double spaces, redundant prefixes, colon/pipe characters.
- **Description issues**: starts with lowercase, starts with non-alphanumeric, infobox pattern.
- **Duplicate names**: Two orgs with the same name (likely merge candidates).

## Edge Validation (`check_edges`)

### Errors
- **Broken references**: `source` or `target` not in orgs.
- **Self-referencing**: Org allied/rivaling itself.
- **Duplicates**: Same source+target+type appears twice.
- **Temporal impossibility**: `end_year` before `start_year`.

### Warnings
- **Contradictory edges**: Same pair has both `alliance` AND `rivalry` without temporal data to explain the change.

## Cross-Reference Checks

### `check_nation_consistency` (Error)
A `member_of` edge must not contradict the org's `nation_affiliation` field. If an org's field says Folk Nation, it cannot have `member_of → People Nation`.

### `check_cross_metro` (Info)
Flags rivalry edges between orgs in different cities. Cross-city rivalries are sometimes valid (national orgs) but often indicate a name resolution error where a local set was matched to a same-named org in another city.

### `check_spinoff_direction` (Warning)
Flags `spin_off` edges where the target org is older than the source. Since `A → spin_off → B` means "B came from A", the target should generally be younger.

### `check_page_title_orgs` (Error)
Flags orgs whose names look like page titles rather than real organizations ("History of X", "Groups in Y", "Defunct sets"). These are pipeline artifacts that should be deleted.

## Description Quality (`check_descriptions`)

### Info
- **Boilerplate**: Description matches the pattern "X is a street gang based in Y." with no additional detail.
- **Truncated**: Description ends without a period (likely cut off mid-sentence).
- **Unbalanced quotes**: Odd number of quotation marks.

### Warnings
- **Code/markup junk**: Contains `class=`, `<div`, `href=`, or other HTML artifacts.

## Source Quality (`check_sources`)

### Warnings
- **Duplicate URL within org**: Same source listed twice.

### Info
- **HTTP instead of HTTPS**: Should be upgraded.
- **Low-quality domains**: fandom.com, answers.yahoo, quora.com.

## Structural Checks

### `check_fuzzy_dupes` (Warning)
Detects potential duplicate orgs using Levenshtein distance and Dice coefficient at 90% threshold. Filters out numbered sets (e.g., "112th Street Crips" vs "113th Street Crips").

### `check_isolated` (Info)
Flags orgs with zero edges and no `nation_affiliation`. These exist in the data but aren't connected to anything on the map.

### `check_id_consistency` (Error)
Ensures the `id` field matches the filename (`org:latin-kings` must be in `latin-kings.json`).

### `check_temporal_logic` (Warning)
Flags orgs that are older than their affiliated nation (e.g., org founded 1950 but nation founded 1978).

### `check_stub_quality` (Info)
Identifies stub orgs that need enrichment — those with generic placeholder descriptions and no real content.

## Pipeline Quality Gates

### Extraction (`extract.py`)
- v2 prompt requires verbatim evidence quotes for every edge
- Only emits edges with explicit relationship verbs
- Prefers local set names over generic national org names
- Returns null rather than guessing fields

### Adjudication (`adjudicate.py`)
- Rejects co-mentions (orgs in same list/location without explicit relationship)
- Rejects opportunism as rivalry ("benefits from X's weakness" ≠ conflict)
- Validates evidence quotes contain both org names and relationship language
- Confidence scoring: high (direct quote) vs medium (implied)

### Application (`apply.py`)
- **Contradiction gate**: Won't add alliance where rivalry exists (or vice versa) without temporal data
- **Nation consistency**: Won't add `member_of` that contradicts `nation_affiliation`
- **Page title filter**: Won't create orgs from page titles
- **LA identifier detection**: Won't inherit local metro for known LA org names (Piru, Inglewood, etc.)
- **Slug collision check**: Won't create duplicate org if slug already exists
- Lint runs as final gate — rejects all changes if lint fails

## Running Lint

```bash
python3 apps/pipeline/lint.py          # full run
just lint                              # same thing via justfile
```

Lint output is grouped by severity (errors → warnings → info) with a summary line. CI fails only on errors.
