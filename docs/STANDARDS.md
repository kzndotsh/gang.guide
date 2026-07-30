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
| Invalid `status` value | Error | Must be `active`, `inactive`, or `unknown` |
| Symbol not title case | Error | e.g. `"pitchfork"` → `"Pitchfork"` (abbreviations ≤6 chars exempt) |
| Description contains navigation junk | Error | "Search for:", "Recent Posts", "Other gangs nearby" |
| Crip/Blood/Piru set before 1969 | Error | Impossible founding date (movement didn't exist yet) |
| `decade` precision with non-round year | Warning | `decade` implies only the decade is known — year should be round (1940, 1950) |
| `exact` precision on round year pre-2000 | Warning | Round years like 1960, 1970 are rarely exact — likely `circa` or `decade` |
| `exact` precision on round-5 year pre-1960 | Warning | e.g. 1955 exact — likely `circa` |
| `circa` on round decade year pre-1990 | Warning | Ambiguous — probably `decade` precision |
| Missing `lane` or `founded_year` | Warning | Expected but not blocking for stubs |
| Description < 50 chars | Warning | Too thin to be useful |
| HTML entities in description | Warning | Scrape junk (`&amp;`, `&#39;`) |
| Alias > 50 chars | Warning | Likely scrape junk |
| Invalid color value | Warning | Must be recognizable color names |
| Type/lane mismatch | Warning | `street_gang` in `prison` lane, `motorcycle_club` in wrong lane, etc. |
| `white_supremacist` org in non-WS/prison/MC lane | Warning | Check lane assignment |
| Bare domain as source title | Warning | Use proper name (e.g. "ADL" not "adl.org") |
| Name ends with `, NUMBER` | Warning | Move number to front |
| Name has double spaces | Warning | Formatting artifact |
| Name has junk side abbreviation | Warning | `(w/s)`, `(e/s)` in name |
| Name has `'v.'` prefix in parens | Warning | Usually a source artifact |
| Name contains colon or pipe | Warning | Likely page title fragment |
| Description starts with lowercase | Warning | Formatting artifact |
| Description starts with infobox pattern | Warning | Scrape junk (starts with "Full Name:", "Founded:", etc.) |
| Duplicate org name | Warning | Merge candidate |
| Single source only | Info | Under-sourced |
| Imprecise year precision | Info | `estimate` or `decade` — could be researched |

## Edge Rules (`check_edges`)

| Rule | Level | Description |
|------|-------|-------------|
| Source/target not in orgs | Error | Broken reference |
| Self-referencing edge | Error | Org related to itself |
| Duplicate edge (same src+tgt+type) | Error | Already exists |
| `end_year` < `start_year` | Error | Temporal impossibility |
| Alliance AND rivalry between same pair | Warning | Contradictory without temporal data |
| `start_year` well before org founded | Info | Suspicious temporal mismatch |

## Cross-Reference Rules

| Check | Level | Description |
|-------|-------|-------------|
| `check_nation_consistency` | Error | `member_of` Folk→People or People→Folk contradicts nation_affiliation |
| `check_nation_consistency` | Warning | `nation`/`alliance` type org has `nation_affiliation` set (nations don't belong to nations) |
| `check_member_of_usage` | Warning | Gang nation org (Crips, Bloods, etc.) is SOURCE of `member_of` — likely reversed |
| `check_member_of_usage` | Warning | `member_of` to gang nation when org already has `nation_affiliation` = same nation (redundant) |
| `check_member_of_usage` | Warning | Blood/Crip-lane org missing `nation_affiliation` |
| `check_page_title_orgs` | Error | Org name looks like a page title ("History of X", "Groups in Y") |
| `check_id_consistency` | Error | `id` field doesn't match filename |
| `check_spinoff_direction` | Warning | Target org is older than source by 5+ years (likely reversed) |
| `check_cross_metro` | Info | Rivalry between orgs in different cities |
| `check_stub_quality` | Info | Generic placeholder description for any org type, needs enrichment |
| `check_isolated` | Info | Org has zero edges and no nation affiliation |
| `check_fuzzy_dupes` | Warning | Two orgs with >90% name similarity |
| `check_fuzzy_dupes` | Error | Cross-lane spelling variant duplicates (e.g. Gangster/Gangsta) |
| `check_temporal_logic` | Warning | Org founded before its affiliated nation existed |

## Description Quality (`check_descriptions`)

| Rule | Level | Description |
|------|-------|-------------|
| Contains `class=`, `<div`, `href=` | Warning | HTML/code artifacts |
| Ends without period (>100 chars) | Info | Likely truncated |
| Boilerplate placeholder description | Info | e.g. "X is a street gang based in Y." or "X is a white supremacist organization." |
| Unbalanced quotes | Info | Odd number of `"` characters |

## Source Quality (`check_sources`)

| Rule | Level | Description |
|------|-------|-------------|
| Duplicate URL within same org | Warning | Same source listed twice |
| Same URL cited in 15+ orgs | Warning | Over-cited (likely wrong) |
| HTTP instead of HTTPS | Info | Should upgrade |
| Low-quality domain (fandom, yahoo answers) | Info | Weak source |

## `nation_affiliation` vs `member_of`

See [SCHEMA.md](SCHEMA.md#nation_affiliation-vs-member_of) for the full distinction. Summary:

- **`nation_affiliation`** — use for direct gang-nation membership (Crip sets → `org:crips`, Blood sets → `org:bloods`). Generates a `nation` edge at build time.
- **`member_of`** — use for structural hierarchies that aren't pure gang-nation affiliation (e.g. Latin Kings `member_of` People Nation, Florencia 13 `member_of` Mexican Mafia).
- **Never**: gang nation orgs (Crips, Bloods, Folk Nation, etc.) as the SOURCE of `member_of`.

## Pipeline Quality Gates

### Extraction (v2 prompt)
- Requires verbatim evidence quotes for every edge
- Infers `org_type` and `org_lane` from source text (38-lane taxonomy)
- Only emits edges with explicit relationship verbs
- Prefers local set names over generic national org names
- Returns null rather than guessing

### Adjudication
- Rejects co-mentions (same list/location ≠ relationship)
- Rejects opportunism as rivalry
- Validates both org names appear in evidence quote

### Application (`apply.py`)
- Contradiction gate: won't add alliance where rivalry exists without temporal data
- Nation consistency: won't add `member_of` contradicting `nation_affiliation`
- Type/lane upgrade: uses LLM-extracted `org_type`/`org_lane` when creating stubs via `--create-orgs`
- Page title filter: rejects org names matching "history of", "groups in", etc.
- LA identifier detection: won't inherit local metro for Piru/Inglewood/etc.
- Slug collision: won't create duplicate if file already exists
- Final lint gate: rejects all changes if lint fails

## Running

```bash
just lint                    # run all checks
python3 apps/pipeline/lint.py   # same thing directly
```
