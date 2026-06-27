# Data Standards

This document describes how gang.guide maintains data quality. All checks are enforced by `apps/pipeline/lint.py`, which runs in CI and as a gate after `apply.py`.

## Severity Levels

| Level | Meaning | CI |
|-------|---------|-----|
| **Error** | Data is broken or contradictory | ❌ Fails |
| **Warning** | Incomplete or suspicious | ✓ Passes |
| **Info** | Could be improved | ✓ Passes |

## Org Rules (`check_orgs`)

| Rule | Level | Description |
|------|-------|-------------|
| Missing `id`, `name`, `description`, `sources` | Error | Required fields must be non-empty |
| Invalid lane | Error | Must match an ID in `lanes.json` |
| Source missing url/title | Error | Every source needs both fields |
| `disbanded_year` < `founded_year` | Error | Temporal impossibility |
| Missing `lane` or `founded_year` | Warning | Expected but not blocking for stubs |
| Description < 50 chars | Warning | Too thin to be useful |
| HTML entities in description | Warning | Scrape junk (`&amp;`, `&#39;`) |
| Alias > 50 chars | Warning | Likely scrape junk |
| Invalid color value | Warning | Must be recognizable color names |
| Crip before 1969, Piru before 1972 | Warning | Impossible founding date |
| Type/lane mismatch | Warning | e.g. `street_gang` in `prison` lane |
| Name has whitespace/punctuation issues | Warning | Double spaces, colon, trailing space |
| Description starts with non-alpha | Warning | Likely scrape junk |
| Duplicate org name | Warning | Merge candidate |

## Edge Rules (`check_edges`)

| Rule | Level | Description |
|------|-------|-------------|
| Source/target not in orgs | Error | Broken reference |
| Self-referencing edge | Error | Org related to itself |
| Duplicate edge (same src+tgt+type) | Error | Already exists |
| `end_year` < `start_year` | Error | Temporal impossibility |
| Alliance AND rivalry between same pair | Warning | Contradictory without temporal data |

## Cross-Reference Rules

| Check | Level | Description |
|-------|-------|-------------|
| `check_nation_consistency` | Error | `member_of` contradicts `nation_affiliation` field |
| `check_page_title_orgs` | Error | Org name looks like a page title ("History of X") |
| `check_id_consistency` | Error | `id` field doesn't match filename |
| `check_spinoff_direction` | Warning | Target org is older than source (likely reversed) |
| `check_cross_metro` | Info | Rivalry between orgs in different cities |
| `check_stub_quality` | Info | Generic placeholder description, needs enrichment |
| `check_isolated` | Info | Org has zero edges and no nation affiliation |
| `check_fuzzy_dupes` | Warning | Two orgs with >90% name similarity |
| `check_temporal_logic` | Warning | Org older than its affiliated nation |

## Description Quality (`check_descriptions`)

| Rule | Level | Description |
|------|-------|-------------|
| Contains `class=`, `<div`, `href=` | Warning | HTML/code artifacts |
| Ends without period (>100 chars) | Info | Likely truncated |
| Boilerplate "X is a street gang based in Y." | Info | Needs enrichment |
| Unbalanced quotes | Info | Odd number of `"` characters |

## Source Quality (`check_sources`)

| Rule | Level | Description |
|------|-------|-------------|
| Duplicate URL within same org | Warning | Same source listed twice |
| HTTP instead of HTTPS | Info | Should upgrade |
| Low-quality domain (fandom, yahoo answers) | Info | Weak source |

## Pipeline Quality Gates

### Extraction (v2 prompt)
- Requires verbatim evidence quotes for every edge
- Only emits edges with explicit relationship verbs
- Prefers local set names over generic national org names
- Returns null rather than guessing

### Adjudication (v2 prompt)
- Rejects co-mentions (same list/location ≠ relationship)
- Rejects opportunism as rivalry
- Validates both org names appear in evidence quote
- Confidence: high (direct quote) vs medium (implied)

### Application (`apply.py`)
- Contradiction gate: won't add alliance where rivalry exists without temporal data
- Nation consistency: won't add `member_of` contradicting `nation_affiliation`
- Page title filter: rejects org names matching "history of", "groups in", etc.
- LA identifier detection: won't inherit local metro for Piru/Inglewood/etc.
- Slug collision: won't create duplicate if file already exists
- Final lint gate: rejects all changes if lint fails

## Running

```bash
just lint                    # run all checks
python3 apps/pipeline/lint.py   # same thing directly
```
