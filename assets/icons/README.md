# Schattenfront — Icon & UI Art Folder

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

| Folder    | Contents | Canvas |
|-----------|----------|--------|
| `units/`  | Top-down map sprites, one per piece of equipment | 384×384 RGBA, transparent background |
| `ui/`     | Menu/bar pictograms, cursors, structure marks | 384×384 RGBA, transparent background |
| `keys/`   | Console-key face textures (ready/press/hover, per aspect) | height 160 px × aspect, RGBA |
| `sheets/` | Painted surfaces: console bar, fax paper, newsprint, tooltip plate | as found |

## Color rules

- **`units/` sprites are tinted by nation color at runtime.**
  Draw them in WHITE fill with BLACK detail lines on transparency
  (grayscale is safe; hue is not — a red detail would tint oddly).
  Shading baked into the sprite multiplies with the nation color,
  so keep highlights ≤ white.
- **`ui/` icons come in two inks:** `<name>_dark.png` is near-black
  ink for the light console keys; `<name>_light.png` is cream ink
  for dark plates. Both variants of a name must exist.
- The current art carries a graded-ink finish, a letterpress rim and
  a soft drop shadow. Hand-made art may bake in whatever finish it
  likes — the game does no post-processing on files it reads.

## `units/` naming

Nation-specific equipment carries its historical name; every nation
not listed for a type shares the generic file named for the type.

| File | Is |
|------|----|
| `tiger.png` | German tank |
| `t34.png` | Soviet tank |
| `churchill.png` | British tank |
| `chi_ha.png` | Japanese tank |
| `tank.png` | everyone else's tank |
| `halftrack.png` | German & American personnel carrier |
| `bren_carrier.png` | British personnel carrier |
| `zis_5.png` | Soviet personnel truck |
| `transport_truck.png` | generic personnel truck |
| `studebaker_us6.png` | American & Soviet supply truck |
| `supply_truck.png` | generic supply truck |
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
