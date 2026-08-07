# Global Operations (1939 Edition) — Asset Catalogue

This file explains WHAT every image in the game is, where it
appears, and what the thing it depicts actually was — so an artist
can draw any file here with confidence. For the technical rules of
replacing art (canvases, the `.generated.json` protection manifest,
key/sheet naming), see [icons/README.md](icons/README.md).

The tree:

```
assets/
  audio/            interface sounds (fax chatter, key clicks)
  icons/
    units/          top-down map sprites -- the unit counters
    pictograms/     unit-type icons for bars, manifests and charts
    buildings/      structure marks laid flat on the map
    buttons/        button icons and console-key chrome
    cursors/        mouse cursors
    badges/         field badges (out of supply, war marker)
    flags/          nation standards
    keys/           painted console-key faces (generated)
    sheets/         painted surfaces: bar, fax paper, newsprint
    _gen/           the artist's own working files (never read)
  models/           (empty -- everything is drawn, not modelled)
```

General drawing rules for `units/`: top-down diagram, nose/muzzle
pointing NORTH (up), transparent background, no border or ground
pad, slight muted colour (olive drab, greys). The game rotates the
sprite to the unit's heading and tints nothing — ownership is shown
by a small flag beside foreign units. Every sprite must read at
about 40 px on screen, so silhouettes matter more than detail.

---

## units/ — the counters on the map

One file per piece of equipment. A nation listed for a file fields
that exact machine; every nation without its own file shares the
generic one named for the unit type.

### Land — the armies

| File | What it is | Drawing cues |
|------|------------|--------------|
| `infantry.png` | A rifle section ("Enlisted", every power). The only troops that can capture cities, man bunkers, and ride lorries and transports. | A handful of men from above: helmets, packs, slung rifles, loose wedge. |
| `tank.png` | The generic medium tank. Serves the German **Panzer IV**, British **Matilda II** and American **M4 Sherman**. | Boxy hull, centred turret, medium gun; tracks visible both sides. |
| `t34.png` | Soviet **T-34** medium tank. Cheap, sloped, everywhere. | Sloped glacis nose, rounded turret set forward. |
| `chi_ha.png` | Japanese **Type 97 Chi-Ha** medium tank. Light and quick, thin armour. | Small hull, narrow tracks, small offset turret, thin gun. |
| `tiger.png` | German **Tiger I** — the HEAVY tank slot. | Wide slab hull, overlapping road wheels, drum-like turret, long 88 with muzzle brake. |
| `churchill.png` | British **Churchill VII** — the heavy tank slot. | Very long hull, tracks running right round the hull, small turret amidships. |
| `heavy_tank.png` | The generic heavy/breakthrough tank: Soviet **IS-2**, American **M26 Pershing**, Japanese **Type 3 Chi-Nu**. | Broader than the medium, long heavy gun. |
| `supply_truck.png` | The generic 4x2 cargo lorry: German **Opel Blitz**, British **Bedford QL**, Japanese **Type 94**, American **GMC deuce-and-a-half**. Hauls stores (supply lbs) to columns and depots. | Cab forward, open or flat cargo bed, two axles. |
| `zis_5.png` | Soviet **ZIS-5** supply lorry. | 4x2, plain wooden cargo bed. |
| `transport_truck.png` | The generic troop lorry (carries infantry only). | Canvas-tilt bed with hoops, two axles. |
| `studebaker_us6.png` | Soviet troop carrier — the lend-lease **Studebaker US6**. | 6x6: three axles, canvas tilt. |
| `halftrack.png` | The German **Sd.Kfz. 251** and American **M3 half-track** — armoured infantry carriers. | Front wheels, tracks aft, open crew bay with benches. |
| `bren_carrier.png` | British **Universal (Bren) carrier** troop carrier. | Low, open-topped tracked box, crew heads visible. |
| `engineer.png` | Engineer company (Pioniere, Royal Engineers, Seabees, sappers). Builds ports, airfields, depots, bunkers, radar, roads, rails and bridges. | Men with tools among bridging gear / pontoon sections. |
| `artillery.png` | Towed field artillery (10.5cm leFH, 25-pounder, 105mm M2, ML-20, Type 91). | Split trails spread, gun shield, long tube north. |
| `aa_artillery.png` | The generic heavy AA battery (QF 3.7-in, M1 90mm, 85mm 52-K, Type 88). Shoots at aircraft only. | Gun in a ring emplacement (sandbags), barrels skyward. |
| `flak_88.png` | The German **88mm Flak** battery. | Cruciform outrigger mount, ONE long barrel. |
| `army_command.png` | Army field headquarters (OKH, GHQ, Stavka...). Projects the comm circle that keeps land units in contact. | Signals lorry: box body, radio masts and aerials, pennant. |
| `blimp.png` | The blimp STATION on the ground (winch truck, envelope stowed/low). | Lorry with a small tethered envelope above it. |
| `blimp_up.png` | The observation blimp ALOFT (wide vision, slow). *Still procedural — awaiting artist art.* | Fat envelope from above, tail fins, gondola line. |

### Air — every counter is a squadron/wing

| File | What it is | Drawing cues |
|------|------------|--------------|
| `fighter.png` | The generic fighter squadron — serves the American **P-51 Mustang**. | Single engine, laminar tapered wings. |
| `spitfire.png` | British **Supermarine Spitfire**. | The elliptical wing. |
| `bf_109.png` | German **Bf 109**. | Slim body, square-cut clipped wings. |
| `zero.png` | Japanese **A6M Zero**. | Broad rounded wingtips, long span. |
| `yak_3.png` | Soviet **Yak-3**. | Short, stubby, small tail. |
| `bomber.png` | The generic medium bomber — serves the German **Ju 88**. | Twin engines, glazed nose. |
| `b_17.png` | American **B-17 Flying Fortress** (the bomber slot). | Four engines, broad wing, big single fin. |
| `halifax.png` | British **Handley Page Halifax** (the bomber slot). | Four engines, TWIN tail fins. |
| `il_2.png` | Soviet **Il-2 Sturmovik** armoured attacker. | Single engine, long greenhouse canopy, rear gunner. |
| `g4m_betty.png` | Japanese **G4M** ("Betty") long-range bomber. | Cigar fuselage, round glazed nose, twin engines. |
| `heavy_bomber.png` | The generic heavy bomber: American **B-29 Superfortress**, German **He 177**, Soviet **Pe-8**, Japanese **Ki-67 Hiryu**. | Four engines, long straight wing, bomb-bay doors. |
| `lancaster.png` | British **Avro Lancaster** heavy bomber. | Four engines, twin fins, long greenhouse. |
| `jet_fighter.png` | The jet squadron (Me 262, Meteor, P-80, MiG-9, Kikka). | Swept-ish wings with underslung jet pods, no propeller. |
| `transport_air.png` | Air transport (C-47/Dakota/Ju 52/Li-2/Ki-57). Carries and paradrops infantry. | Wide twin-engine airliner body, cabin windows, cargo door. |
| `airforce_command.png` | Generic air command wing — the comm circle of the air force. | The generic bomber wearing a command flash. |
| `b_17_command.png` | American air command (B-17 with the flash). | As `b_17` plus a bright wing/fuselage flash. |
| `halifax_command.png` | British air command. | As `halifax` plus the flash. |
| `il_2_command.png` | Soviet air command. | As `il_2` plus the flash. |
| `g4m_command.png` | Japanese air command. | As `g4m_betty` plus the flash. |

### Sea — the fleets

| File | What it is | Drawing cues |
|------|------------|--------------|
| `naval_command.png` | The fleet flagship — the navy's comm circle. | Big warship, admiral's flag clear of the funnels. |
| `yamato.png` | Japan's flagship, the **Yamato**. | Massive beam, pagoda-less modern tower, three huge triple turrets. |
| `battleship.png` | The generic battleship: German **Bismarck**, British **King George V**, American **North Carolina**, Soviet **Gangut (mod.)**. | Two funnels, big twin/quad turrets fore and aft. |
| `nagato.png` | Japanese **Nagato-class** battleship. | Tall stepped pagoda mast, single funnel. |
| `fast_battleship.png` | The fast battleship (research): **Iowa**, **Scharnhorst**, **Renown**, **Kongo refit**, **Sovetsky Soyuz**. *Still procedural — awaiting artist art.* | Longer, finer hull; raked funnel. |
| `heavy_cruiser.png` | The heavy cruiser (research): **Admiral Hipper**, **County**, **Baltimore**, **Takao**, **Kirov**. *Still procedural — awaiting artist art.* | Slimmer than a battleship, more turrets than a destroyer, floatplane catapult. |
| `destroyer_sea_sea.png` | The generic gun/torpedo destroyer (Fletcher, Z-boat, Gnevny). | Narrow fast hull, small turrets, two funnels. |
| `fubuki.png` | Japanese **Fubuki-class** destroyer (Long Lance torpedoes). | Torpedo tube mounts amidships, one funnel pair. |
| `tribal_class.png` | British **Tribal-class** gun destroyer. | Two forward turrets. |
| `destroyer_aa.png` | The AA picket (Atlanta, Dido, Akizuki, Tashkent...). Screens fleets from aircraft. | Destroyer hull bristling with sky-pointing gun tubs. |
| `destroyer_sea_land.png` | The shore-bombardment ship (monitor HMS Roberts, Panzerschiff, Cleveland, Mogami, Marat). | Few but VERY large turrets for the hull size. |
| `submarine.png` | The submarine flotilla (Type VII, Gato, T-class, I-class, Shchuka). Can submerge/surface. | Slim cigar hull, conning tower, deck gun. |
| `aircraft_carrier.png` | The generic fleet carrier (Essex, Graf Zeppelin, Project 71). Its deck is an airfield: squadrons base, launch and land. | Full-length flight deck, starboard island, deck park. |
| `illustrious.png` | British **Illustrious-class** armoured carrier. | Rounded armoured deck outline, starboard island. |
| `akagi.png` | Japanese **Akagi**, the Kido Butai flagship. | Flush deck, small island on the PORT side (her oddity). |
| `supply_ship.png` | The naval supply vessel (Liberty ship, Dithmarschen, marus...). Feeds ships and shore columns. | Freighter: hatched holds, kingposts, derricks. |
| `personnel_transport.png` | The troop transport (APA, Landing Ship Infantry, Daihatsu convoy, MFP). Carries land units across water. | Liner-like hull, lifeboat rows, two funnels. |

---

## pictograms/ — unit-type icons

One monochrome icon per unit TYPE (27 files named exactly for the
type: `infantry.png`, `tank.png`, `heavy_tank.png`, ...). These are
NOT the map counters — they are the small ink pictograms printed on:

- the bottom-bar selection roster and transport/carrier menus,
- the BUDGET MANIFEST rows,
- the WAR INDUSTRIES production report,
- the RESEARCH CHART unlock lists,
- the idle-unit roster keys.

They must read at ~20 px: strong silhouette, SF-Symbols-like
monochrome with dimensional shading, no colour.

---

## buildings/ — marks laid flat on the map

Structure marks are drawn FLAT into the terrain like surveyed
features. Transparent ground — no grass/water/asphalt fill.

| File | What it marks |
|------|---------------|
| `airfield.png` | Airforce Bases (city-built, produce aircraft) and Airfields (engineer-built). Runways, hangars, dispersal. |
| `harbor.png` | Naval Bases (city-built, produce ships) and Ports (engineer-built). Quays, piers, crane, warehouses. |
| `army_post.png` | Army Bases (city-built; produce land units). Ramparts, tent lines, parade square. |
| `depot.png` | Supply depots (engineer-built), exchange stores with lorries. Crate stacks, camo net. |
| `bunker.png` | Bunkers (engineer-built): infantry-only ground, quarters damage. Casemate and trench works. |
| `radar.png` | Radar stations (research-gated works): wide vision. Lattice mast, aerial array. |
| `derrick.png` | An OIL deposit worked for the stockpile. Drilling derrick, pump house, tank farm. |
| `foundry.png` | A STEEL deposit. Sheds, stacks with smoke, ore heaps, rail spur. |
| `granary.png` | A FOOD deposit. Field rows, silo battery, barn. |
| `plantation.png` | Reserved alternate food-works mark (not currently placed in play). |
| `bridge_map.png` | A bridge where a road crosses a river — destroyable, repairable. Deck, piers, banks. |
| `city.png` / `capital.png` | Reserved city/capital marks (towns are sketched into the map itself; these are kept for menus and future use). |

---

## buttons/ — one icon per key

Monochrome icons on console keys, plus the key chrome itself.

| File | Where it sits |
|------|---------------|
| `factory_button.png` | Top bar: WAR INDUSTRIES production report. |
| `resource_button.png` | Top bar: STRATEGIC RESOURCES ledger. |
| `research_button.png` | Top bar: THE RESEARCH CHART. |
| `diplomacy_button.png` | Top bar: THE DIPLOMATIC LEDGER. |
| `tax_button.png` | City selection: the TAX DECREE fax. |
| `enlist_button.png` | City selection: the CIVILIAN DRAFT fax. |
| `info_button.png` | Bottom bar: the unit's service briefing. |
| `demolish_button.png` | Selected own works: pull it down. |
| `repair_button.png` | Engineer: repair the bridge. |
| `road_build.png` / `rail_build.png` | Engineer: survey a road / a railway. |
| `scramble_button.png` | Airfield/carrier: launch the sortie. |
| `paradrop_button.png` | Air transport: arm the drop. |
| `unload_button.png` | Transports: set the landing/drop-off. |
| `submerge_button.png` / `surface_button.png` | Submarines. |
| `blimp_raise_button.png` / `blimp_lower_button.png` | The blimp station: send the envelope up / winch it down. |
| `panel_button*.png`, `panel_key*.png`, `red_button*.png` | Static key chrome (ready/press/hover). The live keys are painted to `keys/` at exact aspect; these are the reference faces. |

---

## cursors/, badges/, flags/

| File | Purpose |
|------|---------|
| `cursors/cursor_default.png` | The map pointer. |
| `cursors/cursor_attack.png` | Over an attackable enemy: the gunsight. |
| `cursors/cursor_embark.png` | Ordering troops aboard a transport. |
| `cursors/cursor_disembark.png` | Setting the put-ashore point. |
| `badges/nosupply.png`, `nosupply_red.png` | The jerrican badge over a unit out of stores (red = flashing alert). |
| `badges/crossed_swords.png` | The war marker between two standards on the ledger's WARS RAGING board. |
| `flags/*.png` | Nation standards (180×120): flown beside foreign units/works, on city name-plates, the diplomacy ledger, the menu. `brit_med`, `raj`, `fareast` are British Empire commands (Mediterranean, India, Far East); `neutral` is the grey standard of no one. Keep them bold — they render ~20 px wide. |

## keys/ and sheets/ (generated chrome)

`keys/` holds the painted console-key faces the UI generates per
size — artists normally leave these alone and restyle via
`buttons/panel_*`/`red_button*` reference faces instead.
`sheets/bar.png` is the console panel behind the top/bottom bars,
`paper.png` every fax sheet and menu page, `newsprint.png` the
newspaper, `plate.png` the tooltip slip.

## audio/

`fax_v1/v2.wav` — the facsimile chatter when a sheet arrives;
`click_v1/v2.wav` — key clicks. WAV, short, mono.
