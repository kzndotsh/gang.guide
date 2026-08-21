# User guide

Map of US criminal organizations: alliances, rivalries, history, and sources.

## Map

Works on desktop and mobile.

- Pan / zoom: wheel, trackpad pinch, or two-finger drag
- Year axis: stays pinned at the top of the map so the current years stay visible while you pan
- Select: click or tap a node for the inspector (Overview has type, status, years, lane, nation, membership, military when those fields exist; Identity has colors/symbols; Network and Sources are separate tabs)
- Brand title: resets the map (deselect, all lanes, default years, hover edges, fit zoom)
- Year slider: founding-year range (top bar); reset control returns to 1930 → latest year in the data
- GitHub: header icon, far right
- Lane filter: show or hide groups (Chicago, Bloods, Crips, and so on)
- Edges: On hover (hovered or selected org) or All links (every edge); desktop control is bottom-center

## URLs

- `?org=org:crips`: select that org
- `?year=1960-1990`: year range
- `?lane=chicago-folk,chicago-people`: only those lanes

## Edge colors

Same as the on-map legend:

| Color | Types |
|-------|--------|
| Green | alliance |
| Red | rivalry |
| Purple | nation, member_of |
| Amber | spin_off, parent |

Directed types have arrowheads.

## Lanes

Vertical bands by geography and affiliation. Band tint and node fill share a **group** color (not each org’s `colors[]` list): Bloods red, Crips blue, Hoover orange, Chicago green, Latino gold, Asian purple, New York terracotta, Detroit rust, plus muted hues for prison, motorcycle, white supremacist, organized crime, regional, and cybercrime. Unplaced has no band fill.

Groups include Chicago (Folk, People, Folk/People, Independent), California Bloods and Crips (plus nation rows), California Latino, Asian gangs, New York, Midwest, Detroit, South/Southwest, Historical East, Prison, White supremacist, Motorcycle clubs, Organized crime, Cybercrime, Other, Unplaced.

## Sources

Every org should have at least one cited source. Typical domains: Wikipedia, StreetGangs, UnitedGangs, Chicago Gang History, Detroit Street Gangs, NGCRC, NYC Gangs, StoneGreasers, DOJ/FBI, CourtListener, BlackPast, StopHoustonGangs, ADL, InSight Crime, SPLC.
