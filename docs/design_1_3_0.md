# ZERO HOUR: 1939 — 1.3.0 Design

Five reforms, one theme: **less ceremony between the player's
intention and the map**. Crews are gone, orders chain, the draft is
a decree, bases are a city's choice, and every city has a fortnight
focus.

---

## 1. The crew system is abolished

**Old law:** a finished vehicle arrived as an empty *shell* at a
station and waited for an Enlisted crew to be marched in, stationed,
and married to it. Army posts and harbors were warehouses.

**New law:** a finished vehicle **rolls off the line onto the map**,
scattered within a short radius of the works that built it. Fueled
and ready.

- Land vehicles spawn on open ground around the **army base**.
- Hulls take the water off the **naval base** (existing scatter).
- Aircraft spawn **parked at the airforce base** (operational
  basing — the sortie game — is untouched; only *warehousing* dies).
- `shells`, `crews`, the `station` order, the crew rosters, the
  NO CREW greying, `_ai_crews` — all deleted.
- A power with no works of the right kind gets the standing refund
  (nothing is ever delivered onto open ground it can't reach).

**Why:** the crew loop was three trips of ceremony per vehicle
(enlist → march → station → roll out) that taught nothing and
punished the player who forgot it. Manpower still matters — the
draft feeds the *infantry* game and the ration gates it.

## 2. Command chaining

**The rule that makes it work:** a unit that is aboard a transport,
or has an embark order pending, takes further orders **queued** —
never replacing. (You cannot mean "march now" for a man at sea.)

The flow, exactly as played:

1. Select land units, right-click a transport → **EMBARK** (as
   today).
2. The selection stays on the land units. The next right-click on
   ground is read as the **LANDING**: the transport receives a
   queued *sail-and-unload* order at that coast.
3. Every further right-click queues on the **passengers**: moves,
   attacks, builds (engineers with an armed works ghost), further
   embarks — executed in order after they step ashore.

So: engineer — move → embark → disembark → move → build → move →
build. Tank — move → embark → disembark → move → attack. No
modifier key, no re-selection, no arming UNLOAD from the panel
(the panel key remains for manual unloads).

Guidance faxes at each stage: "EMBARKATION ORDERED — RIGHT-CLICK
GROUND TO SET THE LANDING", then "LANDING SET AT THE COAST —
FURTHER ORDERS QUEUE FOR THE SHORE PARTY."

Shift-queueing continues to work everywhere for plain chains.

## 3. The civilian draft (a decree, not a button)

The ENLIST button now opens the **CIVILIAN DRAFT** fax:

- **THE VOLUNTEER LINE** — `population // 400,000` sections come
  forward each fortnight free (unchanged).
- **THE QUOTA** — a stepper sets the city's standing draft per
  fortnight, from 0 up to **3× the volunteer line**. Each fortnight
  the city musters the quota (still gated by rations).
- **MUSTER NOW** — a second stepper calls up any of the standing
  pool immediately.
- **The price of conscription:** every section per fortnight
  *above* the volunteer line grinds **−0.8 industry points per
  fortnight** while the quota stands. (Scale check: 1 tax point ≈
  0.5 points of drift, so a quota 2 over the line ≈ +3.2 tax points
  of industrial pain — real, visible on the same city sheet, not
  ruinous.)

The fax prints all three numbers and the drift consequence before
the decree is signed.

## 4. Bases and fields

Two families, cleanly split — **cities build bases; engineers build
infrastructure**:

| structure | built by | produces | supply role | resupply |
|---|---|---|---|---|
| **ARMY BASE** | city focus only | land vehicles | stores + issues | **automatic from its city** |
| **AIRFORCE BASE** | city focus only | aircraft | stores + sorties | **automatic from its city** |
| **NAVAL BASE** | city focus (coastal) | ships | stores + issues to fleet | **automatic from its city** |
| **AIRFIELD** | engineer | — | stores + sorties | supply trucks |
| **NAVAL PORT** | engineer | — | stores + issues to fleet | supply trucks |

- A base is tied to its city; capture the city, take the base. If
  the city falls the base changes flag with it (existing law).
- Auto-supply: a base's stock refills toward cap each tick while
  its city is friendly — the city IS its depot. Fields and ports
  live at the end of a truck line, which is what makes forward
  infrastructure a logistics decision.
- Each city can hold **one base of each type** at most; the base is
  sited on open ground (or water for naval) scattered next to the
  town.
- Engineers lose the ability to build production sites entirely.
  (`harbor` in the works menu becomes `NAVAL PORT`; airfields stay
  but never produce.)

## 5. City management — the fortnight focus

Every city works at **one directive per fortnight**, chosen on the
city sheet (default: FINANCE). Applied at the fortnight rollover.

| directive | yield | the unique advantage |
|---|---|---|
| **INVEST IN FINANCE** | +5.0 industry health (cap 100) | compounds: industry multiplies gross product, so this is the *money* engine and the *war-damage repair* |
| **INVEST IN AGRICULTURE** | +1 agriculture level (max 5): **+2 food/ftn each, permanent** | the only permanent food faucet a player controls — feeds the draft and the ration |
| **INVEST IN THE STEEL WORKS** | *(only in a city with a steel deposit)* +1 works level (max 5): **+2 steel/ftn each, permanent** | the only way to grow mining beyond conquest |
| **FUND THE LABORATORIES** | **+pop-scaled research points** (pop/1M × 4 RP, min 2) | the tech tree without tithing the treasury |
| **RAISE AN ARMY BASE** | one fortnight + **$400 + 10 steel** | once per city |
| **RAISE AN AIRFORCE BASE** | one fortnight + **$500 + 12 steel** | once per city |
| **RAISE A NAVAL BASE** | one fortnight + **$600 + 16 steel** | once per city, **coastal only** |

**Balance sheet** (why no directive dominates):

- FINANCE: +5 industry on a 5,000-gross city at 30% tax ≈ **+$75
  per fortnight thereafter** (and rising revenue is also the famine/
  bombing repair path). Pays off in ~4 fortnights against one
  agriculture level's food bought at market ($7/ton).
- AGRICULTURE: +2 food/ftn ≈ **$14/ftn at market prices** — but food
  cannot always be *bought* (war, seller capacity), and it feeds
  the draft directly. Its value is strategic, not fiscal.
- STEEL WORKS: +2 steel/ftn ≈ half a tank per fortnight, forever —
  but only deposit cities may choose it (13 on the map).
- LABORATORIES: a 1M-souls city yields 4 RP ≈ **$1,200 of tithe**
  (at $300/RP) — much cheaper than taxing for research, but it
  costs the city's whole fortnight and pays nothing to the
  treasury.
- BASES: pure capability, no income — a fortnight and a bill, and
  they define *where* your war machine stands.

The directive fax shows each option's yield **in numbers for this
specific city**, so the choice is informed, Civ-style.

Future directives (designed, not built): fortifications (city
walls/AA), propaganda (annexation speed), the transport levy
(free trucks).

## 6. The opening of the war

- Pre-placed airfields, harbors and army posts are **gone from the
  map**. The world starts with cities, deposits, roads and rails.
- Each playable power starts with **one base, in its most populated
  city**, by national character:
  - **Britain, Japan** — a NAVAL BASE (island empires);
  - **Germany, Soviet Union** — an ARMY BASE (continental armies);
  - **USA** — an AIRFORCE BASE (the arsenal builds bombers).
- Each playable power starts with **5 supply trucks, 5 transport
  trucks and 3 engineers**, spawned around the same city — a
  logistics seed, not an army.
- No starting shells, crews, fleets or air wings. NPC garrison law
  unchanged.
- The AI plays the same game: a focus policy (build its missing
  base types first from its biggest cities, then weigh finance /
  agriculture by its food balance, tithe research occasionally).

**Why this opening:** the first hour becomes the *build-up* — chose
focuses, raise bases, wire supply — instead of inheriting a fully
formed war machine. It also makes each power's opening problem its
historical one: Britain must decide where her army will even come
from; Germany must build a fleet from nothing.

## 7. Save compatibility

SAVE_VERSION 4. New per-city fields (`focus`, `agri_level`,
`works_level`, `draft_quota`), base/port flags on structures,
starting-forces changes. Old saves load tolerantly: shells and
crews on file are written off (refunded at cost), missing fields
default.
