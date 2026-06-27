# Terminology

## Data Terms

| Term | Definition |
|------|-----------|
| **Org** | A criminal organization (gang, MC, crime family, prison gang, etc.) |
| **Edge** | A relationship between two orgs (alliance, rivalry, etc.) |
| **Lane** | A vertical grouping on the map (e.g. "Chicago Folk", "California Crips") |
| **Nation** | An umbrella alliance (Crips, Bloods, Folk Nation, People Nation) |
| **Set** | A local chapter of a larger gang (e.g. "Rollin 60s" is a Crip set) |
| **Metro** | The city/area where an org primarily operates |

## Edge Types

| Type | Meaning |
|------|---------|
| `alliance` | Two orgs that cooperate/support each other |
| `rivalry` | Two orgs in active conflict |
| `member_of` | Org belongs to a larger coalition (not a nation) |
| `nation` | Org is affiliated with a nation (auto-generated from field) |
| `spin_off` | Org was formed from another org |
| `parent` | Org is the parent/umbrella of another |

## Org Types

| Type | Examples |
|------|---------|
| `street_gang` | Crips, Bloods, Latin Kings, MS-13 |
| `prison_gang` | Aryan Brotherhood, Mexican Mafia, BGF |
| `motorcycle_club` | Hells Angels, Bandidos, Pagans |
| `organized_crime` | Gambino family, Sinaloa Cartel |
| `white_supremacist` | Volksfront, WAR, Aryan Nations |
| `alliance` | Folk Nation, People Nation |
| `nation` | Crips, Bloods (umbrella identities) |

## Precision Values

| Value | Meaning |
|-------|---------|
| `exact` | Year is confirmed by primary source |
| `circa` | Approximately that year (±2-3 years) |
| `decade` | Known to be in that decade (e.g. "1970s") |
| `estimate` | Best guess, needs research |

## Pipeline Terms

| Term | Definition |
|------|-----------|
| **Extract** | Send source text to LLM, get structured JSON back |
| **Adjudicate** | Smarter LLM validates evidence quotes from extraction |
| **Merge** | Combine multiple runs into consensus (2/3 agreement) |
| **Apply** | Write consensus data to org files + edges |
| **Consensus** | Data point that appeared in 2+ extraction runs |
| **Evidence** | Verbatim quote from source proving a relationship |
| **Temperature** | LLM randomness parameter (0.1 = conservative, 0.7 = creative) |
