# ZERO HOUR: 1939 — 1.2.0 Interaction & UI Plan

Companion to `design_1_2_0.md`. For every mechanic: **where it
lives**, **what the player does**, **what they read**, and **how it
warns them**. Nothing here invents a new interface grammar — the
game already speaks five languages and every mechanic below is
written in them:

| Surface | Used for | Interaction grammar |
|---|---|---|
| **Map** | everything physical | LMB select, RMB order, hover tooltips, ghosts for siting |
| **Top bar** | national numbers | read-only columns + one key each |
| **Bottom bar** | the selected thing | title / info line / one row of keys / hint |
| **Papers** (faxes, ledger, budget, war industries, research) | decisions on a cadence | full-page sheets with keys and +/- steppers |
| **Signals** (toasts, signal line, newspaper) | events finding the player | short faxes; newspapers for the world-historical |

**Two standing rules for 1.2.0 UI:**
1. *Glance → click → paper.* Every mechanic must be readable at a
   glance (map badge or bar column), actionable in one click (a key
   on an existing menu), and explorable in one paper (its page).
2. *Decrees, not sliders.* Multi-step states are 2–4 stamped
   choices (like tax rates and the war-footing dial), never analog
   sliders — this is a government that issues orders on paper.

---

## Part I — Resources (build first, so the UI foundation comes first)

### The Resource Strip (new, top bar)
Three new top-bar columns after TREASURY: **OIL · STEEL · RUBBER**.
Each shows `stockpile` with a small trend glyph (`▲ +120/ftn`,
`▼ -80/ftn`) colored ink-green/ink-red. Hover tooltip itemizes the
flow: `WELLS +200 · SYNTHETIC +40 · TREATY +80 · PUMPS -220 ·
PRODUCTION -180`. One glance answers "am I bleeding?"; the tooltip
answers "why".

### R1 — Deposits on the map
- **See:** a deposit is a structure beside its city (derrick, blast
  furnace, plantation icon — three new `ui/` marks for the artist)
  with the owner's flag if foreign. Its badge shows fortnight
  output (`+60`).
- **Do:** nothing to micromanage — you own it by owning the city.
  Clicking it selects it like a depot: title `PLOIESTI FIELDS --
  OIL`, info `OUTPUT 60/FTN -> BUCHAREST RAILHEAD`, and its
  delivery route flashes on the map (same highlight as unit paths).
- **Warned:** if its route is cut, the deposit flies the existing
  red no-supply flag and files a toast: `PLOIESTI OUTPUT STRANDED
  -- LINE CUT AT ARGES BRIDGE`.

### R2 — Costs in materials; oil at the pumps
- **See:** every price in the game grows a second line. Budget
  rows read `$430 · 12 STEEL · 2 RUBBER` under the existing cost;
  station/production tooltips likewise. Unaffordable-in-materials
  lines grey out exactly like NO CREW keys, tooltip naming the
  shortfall (`WANTS 12 STEEL -- 4 IN STOCK`).
- **Do:** nothing new — the budget +/- steppers simply refuse past
  the stockpile, same as they refuse past funds today.
- **Oil at the pumps** is deliberately ambient: cities/depots
  feeding *machines* print a small drop glyph on their stock
  tooltip. When the national oil trend goes red, the resource
  strip is the warning; when it runs DRY, every affected depot
  flies a small amber "NO FUEL" pennant (distinct from red
  no-supply) and motorized units queue a signal-line despatch:
  `PUMPS DRY AT MUNICH DEPOT -- ENGINES ON RESERVE`.

### R3 — Synthetic plants & stockpiles
- **Do:** two new engineer works keys (`SYNTHETIC FUEL WORKS`,
  `BUNA RUBBER WORKS`) on the existing works menu, ghost-sited
  beside a city like depots. Costly; the tooltip carries price and
  output as everywhere else.
- **See:** on the map they read as industrial marks with a smoke
  detail; their badge shows conversion (`$→+8 OIL`).
- **Warned:** bombed plants file the standard works-damage faxes;
  a destroyed plant makes the newspaper if it covered >20% of your
  synthetic flow.

### R4 — Resources travel
- **See:** no new object — resource traffic rides the existing
  convoy/train visual language. Selected deposits, works and
  capitals show their supply LINES (reuse path viz).
- **Do:** protect or cut lines with the tools you have (escorts,
  demolition, blockade). An enemy deposit's tooltip names where
  its output goes — that *is* the targeting UI.
- **Warned:** your interdicted flows appear in the resource strip
  tooltip as `STRANDED 140` in red, each stranded source listed on
  the War Industries page with its cause (`LINE CUT`, `BLOCKADE`).

### R5 — Bottleneck reports
- **See:** the War Industries fax (factory key, top bar) gains a
  BOTTLENECKS section: one line per halted production lane —
  `HEINKEL LINE HALTED -- WANTS 30 STEEL/FTN, HAS 12`.
- **Do:** each line carries two keys: `PRIORITIZE` (this lane
  draws materials first) and `SUSPEND` (free its claim). That's
  the whole management surface — two stamps per line.
- **Warned:** the factory key on the top bar wears a small red
  pip while any bottleneck stands (same idiom as OUT OF CONTACT).

---

## Part II — Cities

### The City Ledger (extended city selection)
Clicking a city today shows tax + enlist. In 1.2.0 the bottom bar
for a city becomes three sections on one row (paged if needed):
**decree keys** (tax, enlist, footing, directive), **works slots**
(C1), and the info line reads
`POP 2.1M ▲ · MORALE STEADY · FOOTING: MIXED · SLOTS 2/3`.
Everything deeper lives on the existing Tax-fax-style page, now
titled the **CITY LEDGER**, one page per city.

### C1 — Works slots
- **Do:** the city's bottom bar shows its slots as keys: filled
  slots show their works icon (click = that works' detail), empty
  slots show a hollow key that opens a build sheet — a fax listing
  the eight works with cost, build time, output and a `DECREE`
  key each. One click decrees; engineers are not involved (city
  labor builds it over fortnights, progress on the slot key as a
  countdown caption, same as station production keys today).
- **See:** built works appear on the map beside the city
  (bombable structures with the usual badges).
- **Warned:** completion and destruction file standard faxes;
  a works destroyed by bombing makes the signal line immediately.

### C2 — War-footing dial
- **Do:** one key on the city bar cycling three stamped states
  (`CIVILIAN / MIXED / TOTAL WAR`), styled like the tax decree; a
  national default lives on the Budget fax header (`FOOTING FOR
  THE FORTNIGHT: [ ]`), per-city decrees override it.
- **See:** the city info line prints the footing; TOTAL WAR cities
  show a small red banner chip on their map label.
- **Warned:** the fortnight appropriation fax reports the cost:
  `TOTAL WAR: +18% OUTPUT, INDUSTRY -2, MORALE -1 IN 6 CITIES`.

### C3 — Morale, unrest, partisans
- **See:** morale is ONE word on the city info line (`HIGH /
  STEADY / STRAINED / BITTER`), with the tooltip itemizing causes
  (`BOMBED -2 · TAXED HARD -1 · VICTORIES +1`). Occupied cities
  show unrest the same way; a city at BITTER prints a small unrest
  glyph beside its name on the map.
- **Do:** the levers are ones you already hold — taxes, footing,
  garrisons, liberation. No morale button; morale is a consequence.
- **Warned:** sabotage files toasts naming the damage; partisan
  bands appear as regular enemy units (with the occupied nation's
  flag) so every existing combat idiom applies. A general rising
  makes the newspaper.

### C4 — City directives
- **Do:** one key on the city bar opens a four-line fax:
  `PRIORITIZE ARMOR / AIRCRAFT / HULLS`, `REPAIR FIRST`,
  `STOCKPILE`, `EXPORT SURPLUS`, `AUTO (DEFAULT)`. One click
  stamps it; the decree line prints on the city info line.
- **See:** cities with a standing directive show a small decree
  chip on their City Ledger row; AUTO cities show nothing.
- This is the whole surface. No governor portraits, no lenses.

### C5 — Population & refugees
- **See:** population on the city info line grows a trend arrow;
  refugee columns on the road net reuse the civilian-column
  visual (a grey unflagged counter that cannot be ordered).
  Host cities' tooltips show `+140K REFUGEES`.
- **Do:** indirectly — evacuation decree (`EVACUATE`) appears on
  frontline city bars when enemy units are near, moving pop and a
  slice of draft pool rearward at a morale price.
- **Warned:** newspapers carry the human story at thresholds
  (`A CITY ON THE ROADS: 400,000 FLEE THE FRONTIER`).

---

## Part III — Diplomacy

### The Ledger grows tabs, not screens
The Diplomatic Ledger keeps its one-page form but gains a header
row of three stamps: **NATIONS** (today's page), **TREATIES**
(D3), **CONFERENCE** (D5, only lit while one sits). Influence and
grievances print on the NATIONS page itself.

### D1 — Grievance ledger
- **See:** each ledger row's relations line gains a grievance
  figure against you and for you (`GRIEVANCE 3 // THEIRS 1`),
  tooltip itemizing incidents with dates. Fresh incidents arrive
  as toasts; serious ones as newspapers.
- **Do:** the WAR key's tooltip prices the declaration in
  standing: `WITH CAUSE (3 GRIEVANCES): CLEAN` vs `WITHOUT CAUSE:
  AGGRESSOR -- VOLUNTEERS +50%, NEUTRALS HARDEN 6 FTN`. The player
  can also `PROTEST` an incident (one key on the incident fax) to
  convert it into influence or let it accrue as casus belli.
- **Warned:** when a rival accumulates 3+ grievances against you,
  the diplomacy key on the right edge wears the red pip — war is
  being justified against you, go read why.

### D2 — Influence
- **See:** a fourth top-bar column: **INFLUENCE 12 ▲**. Every
  diplomatic key on the ledger prints its price directly on the
  key (`ALLY 8`, `SWAY 3`, `MEN 4+$400`), greyed when
  unaffordable — the exact idiom of budget steppers and NO CREW
  keys.
- **Do:** click a priced key; the courier departs as today. Refusals
  refund half, reported on the reply fax.
- **Warned:** nothing to warn — influence only accrues. The tooltip
  on the column itemizes income (capital, embassies, victories).

### D3 — Lend-lease & treaties
- **See:** the TREATIES tab lists standing deals as ledger lines:
  `TO BRITAIN: 40 OIL/FTN ← BASING RIGHTS · CONVOY: HALIFAX–
  LIVERPOOL · LAST RUN: ARRIVED`. Each line's convoy is a real
  route; clicking the line flashes it on the map.
- **Do:** `PROPOSE TREATY` key on any nation's row opens a
  single-sheet builder: two columns (WE GIVE / WE ASK), each with
  4–5 stepper lines (oil, steel, rubber, money, volunteers,
  basing, transit); a wax-seal `DISPATCH` key prices it in
  influence. The AI's counter arrives as a fax with `ACCEPT /
  DECLINE / AMEND` keys.
- **Warned:** a raided convoy files a toast naming the loss and
  marks the treaty line `INTERRUPTED`; three failed runs in a row
  and the AI renegotiates — by fax, of course.

### D4 — Minor-power patronage
- **See:** each minor's ledger row gains a favor track: four small
  rung pips (`DISCOUNT · TRANSIT · BASING · BROTHERS`), filled as
  favor rises, with the leading rival's flag printed beside it if
  someone outbids you. The map shows nothing until rungs unlock —
  then their fields/quays gain your small courtesy pennant.
- **Do:** a `MISSION` key per minor spends influence to climb;
  rung benefits activate automatically (transit = your columns
  stop being refused passage; basing = their fields appear in
  your dispatch lists, marked with the courtesy pennant).
- **Warned:** losing a rung to a rival files a toast; a coup or
  flip makes the newspaper.

### D5 — Armistice conferences
- **See:** when warscore/exhaustion trips, a newspaper announces
  the conference and the ledger's CONFERENCE tab lights. The tab
  is one sheet: agenda lines down the middle (city transfers,
  reparations, DMZs, released minors), each with the demanding
  party's flag, priced in warscore chips printed on the line.
- **Do:** `ADD DEMAND` opens a picker fax (cities you occupy or
  claim, reparation steppers); each demand consumes your warscore
  budget shown at the sheet's foot. `TABLE THE TERMS` sends it;
  counters return as amended sheets with per-line `YIELD /
  HOLD` keys. Accepting stamps the treaty — and the newspaper
  prints the settlement map.
- **Warned:** walking away is legal but the exhaustion number on
  the sheet keeps climbing fortnightly, and YOUR cities' morale
  line knows it.

---

## Part IV — Research

- **See:** the Research fax becomes four columns (ARMOR / AIR /
  SEA / INDUSTRY), each a vertical tier ladder with the current
  tier lit, next tier showing cost in points and its unlocks as
  pictograms (the icon set already exists). A points line at the
  head: `RESEARCH 14/FTN (TITHE 9 · INSTITUTES 5)`.
- **Do:** click the next tier in exactly one branch to make it
  ACTIVE (stamped `PRIORITY`); the tithe stepper stays as today.
  Eureka boosts arrive as small faxes (`FIELD REPORTS: TIGER
  RECOVERED -- ARMOR TIER ADVANCED 20%`) — no interaction, just
  good news with a number.
- **Warned:** a completed tier files a fax with the new unlocks'
  pictograms and any resource requirement they carry (R5), so the
  player learns the jet needs oil headroom the moment they earn
  the jet.

---

## Part V — Rollout & load-bearing details

1. **Ship the resource strip with R-core** — it is the single most
   load-bearing new UI element; everything else prices against it.
2. **Grey-out is the universal "can't afford"** — money, steel,
   crews, influence, warscore all use the one idiom the player
   already knows from NO CREW keys and budget steppers.
3. **Red pips are the universal "go look"** — factory key
   (bottlenecks), diplomacy key (grievances), conference tab.
   Never more than three pips possible at once.
4. **Newspapers are reserved** for the world-historical: risings,
   coups, conferences, famine, the first jet. Toasts for events,
   signal line for unit-level chatter — the existing hierarchy.
5. **Every new tooltip itemizes its number** (`▼ -80/ftn` must
   always decompose on hover). If a number can't explain itself in
   one tooltip, the mechanic behind it is too complicated.
6. **Save/load**: every stamped decree serializes as a plain dict;
   papers rebuild from state (no UI state is ever saved).
