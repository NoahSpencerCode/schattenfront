# Global Operations (1939 Edition) — Icon & UI Art Folder

> For WHAT each image depicts — the full catalogue with a
> description of every unit, building and button — see
> [../README.md](../README.md). This file covers the technical
> rules of replacing art.

This folder is the game's entire 2-D art inventory. Every file here
can be replaced with hand-made art: keep the **same filename** and
the **same canvas**, drop it in, and the game uses it forever.

A sidecar manifest (`.generated.json`) records what the game's
procedural painter generated. A file that is missing from the
manifest — or whose bytes no longer match its record — is treated as
an artist's file and is **never overwritten**, even when the
procedural art changes. You do not need to touch the manifest;
just replace PNGs.

## Layout

| Folder        | Contents | Canvas |
|---------------|----------|--------|
| `units/`      | Top-down map sprites (the unit counters), one per piece of equipment | 384×384 RGBA, transparent background |
| `pictograms/` | Menu/bar unit-type pictograms, one per unit type | 384×384 RGBA, transparent background |
| `buildings/`  | Structure marks: airfield, harbor, army_post, depot, bunker, radar, derrick, foundry, granary, plantation, bridge_map, city, capital | 384×384 RGBA, transparent background |
| `buttons/`    | Button icons and the console-key chrome (`panel_*`, `red_button*`) | 384×384 RGBA, transparent background |
| `cursors/`    | The mouse cursors (`cursor_*`) | 384×384 RGBA, transparent background |
| `badges/`     | Field badges: `nosupply`, `nosupply_red`, `crossed_swords` | 384×384 RGBA, transparent background |
| `flags/`  | Nation standards flown above foreign units and works | 180×120 RGBA (3:2) |
| `keys/`   | Console-key face textures (ready/press/hover, per aspect) | height 160 px × aspect, RGBA |
| `sheets/` | Painted surfaces: console bar, fax paper, newsprint, tooltip plate | as found |

## Color rules

- **One file per name** (no dark/light pairs, no nation tinting).
  Exception: `badges/nosupply_red.png` for the red out-of-supply
  alert.
- **Three art styles by folder/role:**
  - **`pictograms/`, `buttons/`, `cursors/`, `badges/`** —
    monochrome SF Symbols style with **dimensional shading** (dark
    greys + depth), refined proportions and internal detail so
    icons read clearly and stay distinct at small sizes.
  - **`units/` map sprites** — simple top-down vehicle diagrams
    with **slight** realistic colour (muted olive/grey), vehicle
    only (no outer border, pad, or floating symbols).
  - **`buildings/` structure marks** — lightly coloured, more
    detailed top-down cartographic diagrams. Draw
    buildings/runways/docks; do **not** fill grass, water, dirt, or
    asphalt slabs under them. Empty space stays transparent.
- **Ownership is shown by the flag,** not the paint: units and
  works of every nation but the player's fly a tiny standard from
  `flags/<country>.png`. Keep flags bold and simple — they render
  around 20 px wide.
- Hand-made art may bake in whatever finish it likes — the game
  does no post-processing on files it reads.

## `units/` naming

Nation-specific equipment carries its historical name; every nation
not listed for a type shares the generic file named for the type.

| File | Is |
|------|----|
| `tiger.png` | German heavy tank (Tiger I) |
| `churchill.png` | British heavy tank (Churchill VII) |
| `heavy_tank.png` | everyone else's heavy tank |
| `t34.png` | Soviet tank |
| `chi_ha.png` | Japanese tank |
| `tank.png` | everyone else's tank (Panzer IV, Matilda II, Sherman) |
| `halftrack.png` | German & American personnel carrier |
| `bren_carrier.png` | British personnel carrier |
| `studebaker_us6.png` | Soviet personnel truck (Studebaker US6) |
| `transport_truck.png` | generic personnel truck |
| `zis_5.png` | Soviet supply truck (ZIS-5) |
| `supply_truck.png` | generic supply truck (incl. the American GMC) |
| `flak_88.png` | German AA (the 88) |
| `aa_artillery.png` | generic AA battery |
| `spitfire.png` / `bf_109.png` / `zero.png` / `yak_3.png` | fighters |
| `fighter.png` | generic fighter |
| `b_17.png` / `halifax.png` / `il_2.png` / `g4m_betty.png` | bombers |
| `bomber.png` | generic bomber |
| `lancaster.png` | British heavy bomber |
| `heavy_bomber.png` | generic heavy bomber |
| `b_17_command.png` etc. | air command ships (the nation's bomber wearing the command flash) |
| `yamato.png` | Japanese fleet flagship |
| `nagato.png` | Japanese battleship |
| `fubuki.png` / `tribal_class.png` | destroyers (Japan / Britain) |
| `illustrious.png` / `akagi.png` | carriers (Britain / Japan) |
| everything else | named for its unit type |

**Adding new nation-specific art** (say, a Sherman for the American
tank) needs a one-line code entry in `icons.py`'s `UNIT_ART`
register in addition to the PNG — ask the dev team; the register is
five seconds to extend.

## `keys/` and `sheets/`

Key faces are named `<palette>_<state>_a<aspect>_r<corner>.png`
(palette `panel` or `red`; states `ready`, `press`, `hover`). All
keys of one aspect share a face — replace all three states for a
consistent feel. `sheets/bar.png` is the console panel behind both
bars, `paper.png` every fax sheet and menu page, `newsprint.png`
the newspaper, `plate.png` the tooltip slip.
