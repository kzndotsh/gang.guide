# IDEA.md — future directions and research sources

Ideas, data sources, and long-term goals that aren't actionable yet. Moved here from TODO.md to keep the roadmap focused.

---

### Scale (Phase 4)
- [ ] Gangland (History Channel) episode transcripts
- [ ] SPLC Intelligence Reports (white supremacist orgs)
- [ ] FBI Vault declassified files
- [ ] ATF/NDIC National Gang Threat Assessments
- [ ] LA Times gang archive series
- [ ] Texas (Tango Blast, Texas Syndicate, Barrio Azteca)
- [ ] East Coast (NYC Latin Kings, Trinitarios, DDP, more UBN sets)
- [ ] Southeast (Atlanta sets, Memphis, New Orleans)
- [ ] Pacific NW (Sureños/Norteños expansion)
- [ ] GangsterReport.com timelines

### New Sources (researched)
- [ ] **InSight Crime** (insightcrime.org) — MS-13, Tren de Aragua, cartel profiles. Structured pages, good for pipeline extraction. Fills our transnational/Latino gap.
- [ ] **SPLC/ADL profiles** — Prison gang + white supremacist detailed profiles (AB, Nazi Lowriders, PEN1). Clean HTML, low effort.
- [ ] **FBI National Gang Threat Assessment (2015)** — Single PDF, confirms memberships/territories/threat levels for top orgs. Validation source.
- [ ] **State AG press releases** (CA, IL, NY) — RICO cases explicitly name sets + relationships in legal filings. Gold for edges.
- [ ] **PACER/CourtListener RICO filings** — Legal factual basis for edges (already in plan but worth prioritizing)
- [ ] **National Gang Center (NGC/OJJDP)** — Gang surveys, risk factors, legislation database. More stats than entities but useful for validation.
- [ ] **Chronicling America (LOC)** — Historic newspapers for pre-1960 org founding dates
- [ ] **NYPL Digital Collections** — NYC gang history archives for East Coast expansion
- [ ] **DEA Cartels page** — If we expand scope to cartel-street gang connections
- [ ] **DetroitStreetGangs.com** — Detroit-specific sets
- [ ] **ADL white supremacist prison gang inventory** (2022 assessment) — State-by-state AB variants, Aryan Circle, etc.
- [ ] **START.umd Tracking Cartels** — Infographics + data on cartel operational zones (territorial edges)
- [ ] **OCVED** (ocved.mx) — Organized crime violence event data, Mexico 2000-2019+. Territorial presence dataset.
- [ ] **ACLED Mexico data** — Criminal group violence, downloadable CSV datasets
- [ ] **GI-TOC Global Organized Crime Index** (ocindex.net) — Country-level metrics, regional observatories
- [ ] **UNODC SHERLOC** — Transnational organized crime case law + legislation
- [ ] **Journal of Gang Research (NGCRC)** — Peer-reviewed, special reports on prison gangs, federal legislation
- [ ] **Europol criminal network reports** — 821+ groups analyzed, good for international expansion if scope widens

### Geographic Expansion Sources
- [ ] **OJJDP "History of Street Gangs in the United States"** — Regional breakdowns (Northeast, South, Midwest). Scrape-friendly historical overview.
- [ ] **TDCJ Security Threat Groups reports** — Texas Syndicate, Mexikanemi, Tango Blast (Houstone, D-Town), Barrio Azteca. Structures, histories, tattoos.
- [ ] **FBI East Coast gang cases** — Trinitarios, UBN (Rikers origin), Bronx sets, Boston initiatives. RICO filings with named sets.
- [ ] **DetroitStreetGangs.com** — Detroit-specific sets and profiles
- [ ] **Purple Gang (Detroit)** — Prohibition-era, well-documented on Wikipedia + academic sources
- [ ] **Oxford Research Encyclopedia** — "Street Gangs in the 20th-Century American City" (Northeast/Mid-Atlantic emphasis)

### Schema improvements
- [ ] Add `tier` field to sources: 1=legal/court, 2=academic, 3=news/wiki, 4=community. Lets adjudicate.py weigh conflicts.
- [ ] Add `membership_estimate` + `membership_year` fields to org schema
- [ ] Add `structure_type` field (traditional/compressed/specialty/hybrid per Klein-Maxson typology)
- [ ] Add `territory` GeoJSON field (optional, for orgs with known boundaries)
- [ ] Add edge `weight` field (1-4 scale: 1=seen together, 2=co-offending, 3=co-membership, 4=co-leadership)

### Datasets & Structured Sources (high pipeline value)
- [ ] **Chicago PD Gang Boundaries GIS** (gis.chicagopolice.org) — Polygonal shapefiles with GANG_NAME attribute. Direct geo-join for territory data.
- [ ] **ICPSR 2792** (Klein/Maxson) — Prevalence of 5 gang structures in 201 cities. Structured CSV with ethnic distributions, sizes.
- [ ] **ICPSR 36787** (NYGS 2002-2012) — 2,388 cases, 606 variables. Gang presence, demographics, homicides, migration.
- [ ] **TxDPS Gang Threat Assessment** — Tier 1/2/3 orgs with membership counts (Tango Blast 22-25K, Texas Mexican Mafia 4-6K, Barrio Azteca 1-2.5K).
- [ ] **NJ State Police Gang Survey** (2007/2010) — Gang density across 21 counties, top orgs by prevalence.
- [ ] **BOP National Gang Unit** — 82 active prison gangs, 17,029 validated inmates (2022). STG classifications.
- [ ] **Stanford Mapping Militants Project** — Organizational lineage, splits, alliances for non-state armed groups. Cartel network evolution.
- [ ] **UNODC SHERLOC** — Case law database, 192 countries, transnational organized crime filings.
- [ ] **ACLED Mexico** — Downloadable CSV of criminal group violence events with geo coordinates.
- [ ] **Borderland Beat** — Cartel maps, profiles, translated intel docs. Contributor-led.
- [ ] **Densley/Grund co-offending network dataset** (GitHub) — Weighted tie-strength matrix. Reference model for edge weights.

### Pipeline methodology improvements
- [ ] Implement Eurogang durability filter (org must persist >= 3 months to be a valid node)
- [ ] Klein-Maxson structural typology assignment in extract.py (traditional/compressed/specialty/collective/neotraditional)
- [ ] Source reliability weighting in adjudicate.py (Tier 1 court > Tier 2 academic > Tier 3 news > Tier 4 community)
- [ ] Edge weight computation from co-offending/co-membership evidence strength
- [ ] Spatial validation: cross-reference org metro with Chicago GIS boundaries where available

### Unchecked Sources (need manual review → keep or discard)
- [ ] CalGang database (CA DOJ) — restricted access, privacy concerns, but public annual reports have stats
- [ ] CRDCN Canada — Criminal Organization and Street Gang Offences files (2016-2021 cohort)
- [ ] Data.gov "gangs" search — federal datasets, "Five Gang Structures in 201 Cities" (1992)
- [ ] Reddit r/gangs, r/Chiraqology — community intel on aliases, beefs (Tier 4 reliability)
- [ ] Kaggle/UCI crime datasets — quantitative crime stats, gang affiliation by arrest
- [ ] OpenStreetMap territory/neighborhood tags — spatial anchors for metro/lane
- [ ] RISSGang (Regional Info Sharing Systems) — LE-only, check for public summaries
- [ ] INTERPOL Project Millennium — major criminal groups/networks intel
- [ ] Europol "Decoding EU Criminal Networks" (821+ groups) — non-US but methodology reference
- [ ] OCCRP (Organized Crime and Corruption Reporting Project) — global investigations, sanctions databases
- [ ] Public Intelligence leaked LE manuals — gang intel docs, legal gray area
- [ ] Digital/social media gang studies — research on online presence (YouTube, IG beefs)
- [ ] Stratfor cartel territory maps — paywalled, possibly archived
- [ ] GIJN crime/organized crime resource links — meta-resource of datasets
- [ ] CGI (Civil Gang Injunction) safety zone shapefiles — LA geocoded injunction boundaries
- [ ] Bakersfield PD gang map server (Esri REST API) — single city, split by demographic
- [ ] Oregon DOC SMarT tattoo database — automated tattoo classification for affiliations
- [ ] NYPD Street Gang Manual — leaked, detailed coalition symbols/rules (Folk/People Nation)
- [ ] Eurogang Program methodology — operational definitions, durability thresholds
- [ ] USC Center for Research on Crime — gang affiliation factors (social identity studies)
- [ ] John Jay College research centers — Extremist Crime Consortium, Data Collaborative
- [ ] NIJ/OJP "Organized Crime in the US" publications — history 1950-1980, Mafia era
- [ ] Prison Policy Initiative reports (Tracked and Trapped, Guilt by Association) — database critiques + data
- [ ] NCJRS Virtual Library — 225,000+ records on criminology, gang intervention (since 1972)
- [ ] Sudhir Venkatesh ethnographies — granular Chicago gang internal politics
- [ ] Frederic Thrasher "The Gang" (1920s Chicago) — historical academic foundation
- [ ] James C. Howell "History of Street Gangs in US" — origins to transformations
- [ ] NYPL Digital Collections — digitized historical NYC gang accounts (20th century)
- [ ] Chronicling America (LOC) — historic newspapers, "first mentioned" dates for old orgs
- [ ] Local Historical Societies — newspaper archives 1940s-80s for regional gang emergence
- [ ] WA DOC STG validation criteria (form DOC 21-881) — suspect/affiliate/member scale
- [ ] AZ DOC DO 806 — STG validation evidence requirements (tattoos, mail, hit lists)
- [ ] Everett PD Gang Recognition Guide — symbols, colors, identifiers reference
- [ ] OCVED (ocved.mx) — organized crime violence event data, Mexico 2000-2019+
- [ ] GI-TOC Global Organized Crime Index (ocindex.net) — country metrics, resilience scores
- [ ] Borderland Beat — cartel maps, profiles, translated docs (contributor-led)
- [ ] UNODC SHERLOC case law database — 192 countries, TOC court filings

