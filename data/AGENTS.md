# data/ — Source of Truth

All gang data lives here as flat JSON files. No database.

## Structure

```
├── orgs/               ← 980 JSON files, one per organization
├── edges.json  ← Edge list (1,561 edges)
├── lanes.json          ← Lane definitions + sort order
└── raw/                ← Scraped source material (gitignored, 682MB)
    ├── streetgangs/    ← 1,436 pages from StreetGangs.com
    └── chicago_history/ ← 97 pages from Chicago Gang History
```

## Org File Schema

```json
{
  "id": "org:slug-name",
  "name": "Display Name",
  "aliases": ["Alt", "ABBR"],
  "type": "set|alliance|network|organization",
  "lane": "california-crips-gangster",
  "metro": "Los Angeles",
  "description": "Factual 1-3 sentences...",
  "founded_year": 1972,
  "founded_year_precision": "exact|circa|decade|estimate",
  "colors": ["blue", "gray"],
  "nation_affiliation": "org:crips",
  "status": "active|inactive",
  "sources": [{"url": "...", "title": "..."}]
}
```

## Rules

- Every org must be a real, documented organization
- Descriptions must be factual — no scraped comments, no slurs, no HTML entities
- Sources must have both `url` and `title`
- `lane` must match an ID in `lanes.json`
- `nation_affiliation` creates an automatic edge in build.py
- After editing, run `python3 build.py` from repo root

## Relationships

Edge types in `edges.json`:
- `alliance` — documented cooperation/partnership
- `rivalry` — documented conflict/war
- `nation` — umbrella org membership (Crips, Bloods, Folk, People)
- `nation_affiliation` — auto-generated from org field
- `spin_off` — one org formed from another
