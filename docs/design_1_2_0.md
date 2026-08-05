# GLOBAL OPERATIONS (1939 EDITION) — 1.2.0 Design Research

**Subject:** Deeper diplomacy, resources, city management and research.
**Positioning:** halfway between *Supreme Commander* and *Sid Meier's
Civilization*.

---

## 1. Where the game sits today

*Supreme Commander* is a **flow game**: income rates, physical
logistics, factories on the map, everything real-time and spatial.
*Civilization* is a **decision game**: discrete strategic choices —
what a city builds, which tech next, what a treaty says — resolved on
a cadence, with consequences that compound over decades.

The game is already three-quarters SupCom: real-time, physical
supply as the core law, factories-as-cities, interdictable roads,
rails and sea lanes. Its Civ half is thin:

| System     | Today | Civ-side depth missing |
|------------|-------|------------------------|
| Diplomacy  | binary war/ally/peace, scored yes/no answers | causes, currencies, terms, minors, endings |
| Resources  | one abstract treasury ($) | strategic materials, scarcity, embargo |
| Cities     | tax rate + draft pool + production queue | specialization, morale, growth, directives |
| Research   | 3 branches (land/air/sea), % tithe of revenue | choices, boosts, marquee unlocks |

The good news: the **fortnight** already gives the game a Civ-style
"turn" living inside real time. Every 1.2.0 mechanic below resolves
on the fortnight and is *expressed physically on the map* — that is
the halfway point in one sentence.

Standing laws respected throughout: supply burn per unit never
increases; manpower is never bought; everything travels physically.

---

## 2. Diplomacy — five ideas

*Civ sources: casus belli & grievances (V/VI), influence currency
(VII), alliances that level with shared wars (VI), city-states &
envoys (V/VI), the World Congress (V/VI).*

### D1. The Grievance Ledger (casus belli)
Wars want **reasons**. Border incidents, embargoes, broken pacts,
sunk neutral shipping and mobilizations generate *grievance points*
between nations, printed as incident faxes ("SHOTS EXCHANGED AT THE
FRONTIER"). Declaring war with cause is cheap; declaring without it
brands you the aggressor: volunteer prices rise, neutral nations'
`alliance_answer` hardens against you, minors embargo your resource
purchases for N fortnights. AI war councils already stagger their
declarations — grievances give them *dates and pretexts* (Gleiwitz,
Mukden) and give the player warning signs to read.

### D2. Influence, a second treasury (from Civ VII)
A third top-bar column: **INFLUENCE**, accrued per fortnight from
the capital, embassies and won battles. Every diplomatic act is
*priced* in it: proposing an alliance, requesting volunteers,
offering peace, swaying a minor, demanding transit rights. Replaces
"courier + scored yes/no" with a budget the player husbands. Big
asks stack the cost; refused asks refund half. The fax aesthetic
holds: influence is "diplomatic capital", spent by the Foreign
Office.

### D3. Lend-Lease and trade treaties — physically shipped
Standing deals, renewed each fortnight: *X oil / steel / $ per
fortnight in exchange for volunteers, basing rights, or resources.*
The goods **travel** — supply ships on real sea lanes, trains on
real rails — and can be raided, blockaded, or bombed. This is the
Atlantic convoy war for free, straight from the game's existing
interdiction systems, and it is the most WW2 mechanic on this list
(Lend-Lease, Murmansk runs, Swedish iron ore).

### D4. Minor-power patronage (city-states, WW2-dressed)
The 21 NPC nations track **favor** per major (envoys become
"military missions"). Rungs unlock in order: resource discounts →
**transit rights** (march through without war) → **basing rights**
(use their fields and quays) → co-belligerence at the top. Rivals
can outbid you; a coup fax flips a wavering minor. This turns the
neutral map into a contested board *between* the wars, exactly the
1938–41 scramble for Romania, Finland, Yugoslavia and Iraq.

### D5. Armistice conferences (the World Congress, but for endings)
Long wars end at a **table**, not a status-quo fax. When warscore
or exhaustion crosses a line, a conference paper convenes: the
belligerents (and interested neutrals) put terms on the sheet —
city transfers, demilitarized zones, reparations in resources,
released minors. The player drags demands onto the agenda priced in
warscore and influence; the AI counters. Munich, Vienna Awards,
armistices of Compiègne — wars acquire *negotiated shapes*, and
peace becomes a strategic act instead of a stop button.

---

## 3. Resources — exactly three: OIL, STEEL, RUBBER

*Civ sources: strategic resources on the map (all), stockpile
accumulation & per-turn consumption (VI), resource-gated units (VI).*

The classic WW2 triad. Three is enough: oil is *operations*, steel
is *production*, rubber is *motorization*. No food, no aluminum —
fold them narratively into the three.

### R1. Deposits live on the map at their historical sites
Oil at Ploiești, Baku, Texas, Persia, the East Indies; steel from
the Ruhr, Lorraine, the Urals, Pittsburgh, Sheffield; rubber from
Malaya, Indochina, Brazil, the Congo. A deposit is a **structure
beside its city** (like harbors today): own the city, work the
deposit. Output flows into a national stockpile each fortnight
(Civ VI's accumulate-and-spend model). Immediately, the map grows
strategic geography that matches the real war: Japan *needs* the
Indies, Germany *needs* Ploiești and Baku.

### R2. Production spends steel + rubber; the supply net pumps oil
Unit costs split: money **+ steel** (ships heaviest), motorized
kit **+ rubber**. Oil is consumed not by units (supply law is
untouched) but **at the pumps**: when cities and depots replenish
supply bound for *machines* — trucks, tanks, ships, sorties — the
national oil stockpile pays for the tonnage. Infantry and rail
burn none. Run dry and the supply network keeps feeding men but
stops feeding engines: the 1944 Wehrmacht, emergent, with zero new
per-unit bookkeeping.

### R3. Synthetic plants and strategic stockpiles
Engineer-buildable **synthetic fuel / buna rubber works** (costly,
city-adjacent, very bombable) convert money into a trickle of oil
or rubber — Germany's historical answer, and the strategic-bombing
target the game currently lacks. National stockpiles have caps;
forward depots can hold small local reserves; captured stocks are
looted. Scarcity becomes a *place* you can bomb, blockade or seize.

### R4. Resources travel — so they can be cut
A deposit's output rides real infrastructure to the industry that
spends it: rail to the works, convoy across the sea. Cut rails,
blockade straits, or sink the tankers and the flow stops — no new
systems, just new cargo on the existing interdiction board.
Embargo joins the diplomacy deck as a formal act (D1 grievance,
D3 treaty leverage): the US oil embargo on Japan is the tutorial
example that starts the Pacific war.

### R5. Shortage bottlenecks, reported like everything else
Marquee equipment carries a resource *requirement* (Civ VI-style):
jets and heavy bombers want oil headroom, heavy tanks a steel
quota. Shortage never deletes fielded units — it **halts the
production line** and slows repairs, announced on the War
Industries fax as a BOTTLENECK report naming the missing tonnage.
The player reads scarcity the same way they read everything: on
paper, then fixes it on the map.

---

## 4. City management — five ideas

*Civ sources: districts (VI), amenities & war weariness (V/VI),
housing/growth (VI), governors & production focus (VI), towns vs
cities (VII).*

### C1. Development slots — districts, rationed
Each city holds **1–3 works slots** by population. The player
decrees what fills them: Steel Works, Refinery, Shipway, Aircraft
Plant, Rail Yard, Research Institute, Flak Belt, Barracks District.
Slots build over fortnights, appear on the map beside the town
(bombable, capturable), and bias what the city can produce and how
fast. This is Civ VI's district layer at WW2 scale — and it gives
strategic bombing a *target list* (ball bearings at Schweinfurt).

### C2. The war-footing dial
A per-city (or national, with per-city override) decree: **CIVILIAN
/ MIXED / TOTAL WAR**. Total war raises production output and
draft rates but bleeds industry health and morale each fortnight;
civilian footing heals both and fills the treasury. It is Civ's
amenity trade-off shaped like Speer's 1943 speech, and it finally
makes the industry-health drift a *lever* instead of a side effect
of the tax slider.

### C3. Morale, unrest and partisans
Cities track **morale**: taxes, rationing, bombing, occupation,
war length and lost sons all press it down; victories, garrisons
and civilian footing lift it. Low morale shrinks draft pools and
revenue. In *occupied* cities it becomes **unrest**: rail
sabotage, supply pilferage, and at the bottom, partisan bands
spawning in the countryside — the Resistance, priced honestly:
garrisons suppress, which pins your Enlisted exactly like the real
rear-area war. (Civ's war weariness, given a rifle.)

### C4. City directives — governors without the middlemen
A standing order per city, one line on its fax: **PRIORITIZE
ARMOR / AIRCRAFT / HULLS**, **REPAIR FIRST**, **STOCKPILE**,
**EXPORT SURPLUS**. Default = auto-manage (today's behavior), so
the layer is opt-in and the 200-city world stays playable. This is
the useful half of Civ VI's governors with none of the personas —
the player writes a decree once and the city follows it until
countermanded.

### C5. Population as a living number
Population grows in peace and shrinks under drafts, bombing and
occupation — and **moves**: frontline civilians flee along the
road net to rear cities as refugees, carrying draft pool and
revenue with them (and pressing the host city's morale). Deep
strategic choices appear at no interface cost: bomb the workers or
the works? garrison the border town or let its people run? Manpower
still cannot be bought — now it must also be *husbanded*.

---

## 5. Research — from tithe to tree

Today: three branches (land/air/sea), tiers bought by a flat %
tithe of revenue. The Civ upgrade, kept lean:

- **Four branches** — ARMOR, AIR, SEA, INDUSTRY — each 4–5 tiers
  with a visible tree on the Research fax; INDUSTRY carries the
  resource/city techs (synthetic fuel, radar nets, welded hulls,
  assembly lines).
- **Research points** replace the pure tithe: the tithe still buys
  points, but **Research Institutes** (a C1 slot) add flat points —
  science becomes a thing you *build*, and bomb.
- **Combat boosts (eurekas)**: losing 5 tanks boosts the armor
  tier; a city firebombed boosts flak; first contact with enemy
  jets boosts your own jet tier. Civ VI's eureka, sourced from the
  battlefield ledger the game already keeps.
- **Marquee unlocks stay rare**: jets, heavy tanks, snorkel
  submarines, strategic bombers, radar (already gated) — each tied
  to a resource requirement (R5) so tech and resources interlock.
- **Espionage-lite**: capturing an enemy capital or research city
  grants a one-time boost toward their best tier — the Allied
  intelligence coups, without building a whole spy system.

---

## 6. How it composes (and what to build first)

Each pillar feeds the others: deposits (R1) make minors worth
courting (D4); lend-lease (D3) needs stockpiles (R3); city slots
(C1) build the refineries that R2 spends and the institutes that
research needs; morale (C3) is the cost side of the war-footing
dial (C2); conferences (D5) trade the cities that C1 made valuable.

Suggested build order — each stage shippable alone:

1. **Resources core** (R1, R2, R5): deposits, stockpiles, costs.
   Top bar grows three columns. Biggest bang, mostly systems the
   game already has (structures, fortnight, fax).
2. **City slots + dial** (C1, C2): the build-order layer; makes
   resources actionable.
3. **Influence + grievances** (D2, D1): re-plumb existing diplomacy
   scoring into currencies.
4. **Lend-lease + patronage** (D3, D4): physical trade on the
   existing logistics net.
5. **Morale/population** (C3, C5), **conferences** (D5), research
   tree — the long tail.

Save format: each stage bumps SAVE_VERSION; stockpiles, slots,
favor, morale and treaties all serialize as plain dicts under the
existing snapshot pattern.

**Complexity guardrail:** every new number must appear on at most
one paper the player already reads (top bar, city fax, ledger, war
industries, research fax). If a mechanic needs a new screen to be
understood, it is too big for this game.
