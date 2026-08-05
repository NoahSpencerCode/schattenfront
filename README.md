# ZERO HOUR: 1939

A real-time strategy game set in the Second World War, played on a full 3D
globe built from real geographic data. Command the armies, navies, and air
forces of Britain, Germany, the Soviet Union, the United States, or Japan
in a world of 26 nations — every town of 1939 belongs to its historic
owner, from France and Italy to China and Siam, and the war only exists
where someone has declared it. Built entirely in code with Python +
Panda3D — no game-engine editor involved.

Everything on the map is drawn **flat on the planet surface** like symbols
inked onto a 1940s situation map — unit counters, city rings, bridges,
even the combat flashes. No 3D models, no billboards. Every prompt
arrives as an incoming FAX from the War Office, and the clock starts at
0500 hours, 1 September 1939.

## Quick Start — click and play

- **macOS**: double-click **`Play Zero Hour 1939.command`**
  (If macOS blocks it the first time: right-click → Open. If it opens in a
  text editor instead, run `chmod +x "Play Zero Hour 1939.command"` once in
  Terminal.)
- **Windows**: double-click **`Play Zero Hour 1939.bat`**

The first launch installs dependencies into a local `venv/` and paints the
globe map from real geographic data (about a minute). Every later launch
is fast.

Manual start, if you prefer:

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/python main.py
```

Requires Python 3.8+.

## Menu Background Video (MP4)

To show a video behind the main menu, place an MP4 file here:

```
ww2-rts-game/
├── main.py
├── ...
└── media/
    └── menu_background.mp4     <-- preferred name
```

- Any `.mp4` dropped into `media/` works: the game looks for
  `menu_background.mp4` first, otherwise it plays the first MP4 it finds
  there (alphabetically).
- Format: MP4, H.264 codec (the pip build of Panda3D ships with FFmpeg
  support, so no extra install is needed)
- Recommended: 1920x1080, 30 fps, under ~100 MB
- The game loops it automatically; if the file is missing or unreadable
  the menu falls back to a plain backdrop.

## How to Play

1. **NEW GAME** from the main menu (multiplayer is greyed out until it
   exists).
2. Pick your power: Britain, Germany, the Soviet Union, the USA, or
   Japan. Each starts with an army, an air wing, a small fleet, and its
   historical home cities (the first is your capital).
3. **The world begins at peace.** Nothing fires on anything until a
   state of war exists — and TOTAL VICTORY is holding the capitals of
   all five great powers with your own flag or an ally's.

### Diplomacy — the Foreign Office Ledger

The crossed-flags key on the right edge opens the **DIPLOMATIC
LEDGER**: every living nation with its stance (AT WAR / ALLIED / AT
PEACE) and the keys that move the bags. Declarations of war, offers of
alliance and terms of peace travel by courier for some game-hours and
are answered by return fax. A declaration binds **blocs** — every ally
of each side is dragged into the war. The 21 NPC nations (France,
Italy, China, the Balkans, the British dominions...) field standing
home-defense garrisons and answer diplomacy, but never expand. The AI
great powers run their own war councils: they declare opportunistic
wars, court co-belligerents, and will drag their alliances in against
you.

Every declaration, pact, peace, capitulation — anywhere on the globe —
prints an edition of **THE WORLD CHRONICLE**; the war's end prints the
final edition with the full statistical record.

### Enlistment — the Human Element (0.1.1)

Manpower is never bought. Each city's **draft pool** grows by one
citizen per 400,000 souls a fortnight (holding at most three
fortnights' worth); the **ENLIST** key beside the tax decree musters
them onto the streets as **Enlisted** — free. Enlisted fight as
riflemen, capture cities, and CREW every other unit: vehicles are
empty shells until a crew signs aboard. Production delivers hulls to
a **harbor**, airframes to an **airfield**, vehicles to an **army
post** (the army's harbor); march Enlisted onto a station to crew it
and click a shell to dispatch. Each great power opens with exactly
two of each station at its biggest cities.

### Railroads (0.1.1)

Each power's three biggest cities are bound by a **railroad** — two
silver rails with brown ties. Rails route like roads at road speed,
but a column on rail legs **burns no supply**. Engineers lay new
line at four times a road's build time.

Allies matter more: request **volunteer Enlisted** from the ledger
(price falls with every war fought on the same side), and supply
trucks refill at **allied cities** as readily as at home.

### Saving and Loading

**ESC → SAVE CAMPAIGN** files the whole situation map — every unit
with its orders and cargo, every war, pact and courier bag in flight,
every engineer work down to the road cuts — as one timestamped case
in `saves/` (or under `~/Documents/Zero Hour 1939/saves` when the
install directory is read-only). **LOAD GAME** at the main menu lists
the filed campaigns, newest first; one click resumes the war exactly
where it stood.

### The Fortnight Budget

Units are raised **only** through the budget. Press **[B]** (or the
BUDGET button in the top bar) and a large Budget Manifest FAX arrives
from the Exchequer. Allocate the available appropriation across unit
types with the + / − marks, then:

- **++ TRANSMIT ++** — the budget goes into effect. Works orders are
  distributed to your cities (ships to harbor cities, aircraft to the
  capital, army units round-robin). **The budget then stands for two
  weeks of campaign time and cannot be altered.** Budgets must be
  committed to.
- **-- DISCARD --** — the sheet goes in the bin and nothing is spent.

Unspent funds carry forward and keep accruing from your cities.

### Supply — Logistics Wins Wars

Everything on land and sea burns **supply (lbs)** to move and fight; a
unit at zero supply is flagged with a red jerrycan and can neither move
nor shoot until resupplied. Friendly cities are bottomless sources for
anything nearby. **Supply trucks** haul it forward: right-click a truck
to a front-line station and it automatically loops — hauling from the
nearest city or depot, delivering to any friendly unit inside its
vision, and going back for more. Naval units carry far more and the
**Naval Supply Vessel** replenishes ships at sea, tops up carriers'
aviation stock, and can even fill trucks along the shoreline. Aircraft
are exempt (they fly sorties), but every takeoff costs the airfield or
carrier **600 lbs of aviation stock** — city airfields refill from
their city; forward fields and carriers need the supply chain.

### Engineering Works

Select an engineer for the works menu: **bridges** (anywhere on a
river), **roads** (fast custom routes from the engineer's position to a
site), **supply depots** (caches that trucks deliver to and draw from),
**bunkers** (infantry nearby take a third of the damage from bombs and
naval shellfire), and **airfields**. Click a work, right-click the
site; the engineers march there and build it.

### Air Operations

Every city has an **airfield beside it** (ATC-tower icon), and aircraft
always park at an airfield or carrier — hidden in the hangars, with a
count badge under the tower. Select the airfield to see its aviation
stock and parked squadrons; click a squadron, then right-click an
objective to launch its sortie.

Aircraft fly **complete sorties** — no hovering, no mid-air re-tasking.
When you order a based aircraft anywhere, a full flight plan is drawn
first: airfield → objective → the nearest friendly airfield, and the
whole plan must fit within the aircraft's fuel endurance or the Air
Ministry refuses the sortie by FAX. Every friendly city is an airfield,
and **carriers** serve as airfields at sea — stage through them to
extend your reach. Bombers strike what they pass over (send several for
a stubborn bridge); fighters engage targets en route. Aircraft caught
on the ground when their airfield falls — or on a carrier when she is
sunk — are lost.

Aircraft that land on a **carrier** are struck below deck: they vanish
from the map and travel with the ship. A small plane badge under the
carrier's counter shows how many are aboard. Select the carrier and the
bottom bar lists the embarked squadrons — click one, then right-click
an objective to launch its sortie from the deck.

### Communications — W/T Contact

Friendly **vision fields** are sharp-edged circles inside which the map
keeps its full colour; beyond them it falls 20% darker and half
desaturated, and enemy units are invisible. Observation is short-ranged
and honest to the era: **aircraft see 3x further** than land or sea
units, **night halves everyone's vision**, and in darkness **air and
surface forces cannot spot each other at all** — night bombers slip past
AA, and AA sits silent under them. The wireless net (comm circles) is
radio, not eyes, and is unaffected. You can only see and
command units that are **inside a friendly communication circle**:

- Command units (Army Command Post, Fleet Command Ship, Air Command
  Wing) carry the wireless net — the large **white circle**, 100x the
  area of their vision field.
- Friendly cities carry the land-line network in a smaller radius.

A unit beyond every circle goes **W/T SILENT** (out of wireless-telegraphy
contact): it vanishes from your map, cannot be selected or given fresh
orders, and its sighting reports stop. It keeps executing its last
orders and defends itself. The top bar shows how many of your units are
currently out of contact. Move a command unit toward them — or wait for
them to march back into the net — to regain control.

### Controls (Supreme Commander conventions)

| Input | Action |
|---|---|
| Left-click | Select unit (own city/airfield → its panel; visible enemy → intelligence view) |
| Double-click | Select all on-screen units of that type |
| Left-drag | Box-select multiple units |
| Shift + left-click | Add/remove unit from selection |
| Right-click | Context order: move / attack / board / repair (red gunsight shows valid targets; multiple movers spread into formation) |
| Shift + right-click | Queue linked waypoints (neon path with join rings) |
| B | Budget manifest |
| H | Halt selected units |
| Ctrl + 1–9 / 1–9 | Assign / recall control group |
| W A S D or arrows | Rotate camera around the globe |
| Middle-mouse drag | Rotate camera |
| Mouse wheel | Zoom in glides toward the cursor (Google-maps style); zoom out is a plain zoom |
| Space | Pause |
| + / − | Game speed (0.5x–4x) |
| Esc | Discard budget → deselect → field-orders menu |

### The Map

- The globe is textured from **Natural Earth 10m** country data and 50m
  rivers — dull navy oceans, old-paper land, etched borders, WW2-globe
  style. Country names appear zoomed out; city names when you close in.
- **Deep zoom**: below a certain altitude the game repaints the visible
  region of the map in realtime from the raw vector data (on a
  background thread, Google-maps style), so coastlines, rivers, roads,
  and borders stay sharp down to the lowest camera altitude — 10x closer
  than the previous build.
- The **day/night terminator** sweeps the planet; the night side falls
  dark.
- **Roads** connect each nation's cities. Land units move **10x faster
  on roads** and the route planner uses them automatically.
- **Rivers** block land movement except at **bridges** — drawn to true
  river scale, laid along the road they carry (zoom in to see them).
  Tanks, bombers, and shore-gun destroyers can demolish bridges;
  **engineers** rebuild them. If a column has no practicable route,
  Movement Control refuses the order by FAX — use a **troop transport**
  or **air transport** (paradrop) instead. Roads never cross open
  water; island cities are supplied by sea and air.
- Unit counters carry **drawn pictogram icons** (generated into
  `assets/icons/` on first run — replace any PNG with your own art).
- When a unit comes under fire, quick **red flashes** burst around it on
  the map.

### Unit Roster

**Army** — Infantry, Medium Tank, Supply Truck, Personnel Truck, AA
Battery, Army Command Post, Engineers
**Navy** — Fleet Command Ship, Troop Transport, Destroyer (Surface / AA
Picket / Shore Gun), Fleet Carrier
**Air Force** — Fighter Squadron, Bomber Wing, Air Command Wing, Air
Transport (paradrop)

## Project Layout

| File | Purpose |
|---|---|
| `main.py` | Entry point and window setup |
| `game.py` | Game loop, states, orders, combat, comms, budget, AI |
| `menu.py` | Main menu + nation selection (MP4 background) |
| `globe.py` | Sphere mesh, day/night shader, realtime detail overlay |
| `geodata.py` | Natural Earth data → vectors, map rendering, roads, bridges |
| `pathfinding.py` | Road-graph A* (land), ocean-grid A* (sea) |
| `units.py` | Unit stats and behaviour |
| `models.py` | Flat map-marker builders (counters, rings, flashes) |
| `ui.py` | Top/bottom bars, FAX reports, Budget Manifest form |
| `config.py` | All tunable constants |
| `data/` | Natural Earth GeoJSON + generated cache |

`python main.py --offscreen` runs headless (used by the smoke tests).
Set `SHOW_FPS_METER = True` in `config.py` to display the frame-rate
meter.

## Troubleshooting

- **Game won't start** — ensure Python 3.8+, then delete `venv/` and
  relaunch to reinstall dependencies.
- **First start is slow** — vector data, the land mask, and the map
  texture are generated once and cached in `data/cache/`.
- **Video doesn't play** — the file must be `media/menu_background.mp4`,
  H.264-encoded.
- **Performance** — lower `DETAIL_TEX_SIZE`, `GLOBE_SEGMENTS`, or the
  texture size in `geodata.py` (`TEX_W`, `TEX_H`) on older machines.

## Release Builds

`python setup.py bdist_apps` (from the venv) assembles installable
builds for **macOS (Apple Silicon)** and **Windows (x64)** into
`dist/` as zips, icons included — Panda3D's deploy tools gather the
per-platform wheels, nothing is compiled locally. The bundle ships
every cache the game reads at runtime, so first launch pays no bake;
the deep-zoom tile cache rebuilds itself lazily in play.

## Known Limitations / Roadmap

- Multiplayer is not implemented; the menu key sits dark.
- macOS builds are ad-hoc signed, not notarized: right-click → Open on
  first launch. If macOS still refuses (or the app misbehaves after a
  download), clear the quarantine flag once:

  ```bash
  xattr -rd com.apple.quarantine "Zero Hour 1939.app"
  ```
