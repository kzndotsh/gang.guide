# data/

Flat JSON. No database. **Schema:** [`docs/SCHEMA.md`](../docs/SCHEMA.md). **Lint:** [`docs/STANDARDS.md`](../docs/STANDARDS.md). After edits: `just lint` && `just build-data`.

```
orgs/          # one file per org; filename = slug
edges.json     # alliance, rivalry, member_of, spin_off, parent
lanes.json     # canvas bands
raw/           # gitignored scrapes
```

Do not store `nation` edges in `edges.json`. They are generated from `nation_affiliation`. Do not invent organizations.
