"""
THE PAINT SHOP: the redrawn art, every piece of it.

icons.py keeps the machinery -- the registries, the supersampled
bench, the letterpress finish, the manifest -- and this module keeps
the ART: one painter per unit and per pictogram, drawn as detailed
TOP-DOWN FLAT DIAGRAMS in true colour. A tank is a tank seen from a
reconnaissance photograph: hull plates, track links, stowage on the
engine deck. A harbour is the quay itself, drawn on transparent
ground so it sits in the map like it grew there.

Every painter works in the familiar 96-space on the _ScaledDraw
proxy and is registered over the old drawer at the bottom of
icons.py. The conventions:

  * units face NORTH (the bow or nose at low y);
  * a dark ink outline holds every silhouette together at map size;
  * three tones to a surface -- lit, base, shaded -- so the diagram
    reads as a diagram and not a flat sticker;
  * buildings paint their own muted map-sepia colours and leave the
    ground transparent; the ink argument is theirs to ignore.
"""

import math

# ---------------------------------------------------------------- palette
INK = (38, 32, 24, 255)             # the outline everything wears

# land: olive drab and its neighbours
OD = (99, 104, 68, 255)
OD_D = (70, 74, 48, 255)
OD_L = (124, 130, 90, 255)
FELD = (108, 112, 100, 255)         # field grey (german vehicles)
FELD_D = (78, 82, 72, 255)
CANVAS = (146, 138, 104, 255)       # tilts and tarpaulins
CANVAS_D = (118, 111, 82, 255)
TRACK = (56, 54, 48, 255)
TRACK_L = (84, 82, 74, 255)
TIRE = (44, 42, 40, 255)
WOOD = (128, 100, 62, 255)
GUNMETAL = (66, 68, 70, 255)
UNIFORM = (92, 96, 72, 255)
SKIN = (196, 164, 128, 255)

# sea: warship greys
HULL = (108, 114, 118, 255)
HULL_D = (78, 84, 90, 255)
HULL_L = (132, 138, 141, 255)
DECK = (128, 132, 132, 255)
DECK_L = (150, 153, 151, 255)
WOODDECK = (150, 132, 100, 255)
WOODDECK_D = (124, 108, 80, 255)
STACK = (62, 66, 70, 255)
CIVIL = (96, 88, 84, 255)           # a freighter's rust-touched hull

# air
ALU = (150, 155, 158, 255)
ALU_D = (116, 121, 126, 255)
AIROLIVE = (92, 96, 66, 255)
AIROLIVE_D = (66, 70, 48, 255)
AIROLIVE_L = (116, 121, 84, 255)
GLASS = (152, 176, 182, 255)
GLASS_D = (108, 130, 138, 255)
PROP = (60, 58, 52, 160)            # a spinning disc, half there

# buildings: the map's own sepia
SKETCH = (74, 62, 46, 255)          # building linework
ROOF = (140, 116, 84, 255)
ROOF_D = (112, 92, 66, 255)
ROOF_L = (162, 138, 102, 255)
CONCRETE = (156, 150, 134, 255)
CONCRETE_D = (128, 122, 108, 255)
TARMAC = (110, 104, 96, 255)
TARMAC_D = (88, 84, 78, 255)
EARTH = (134, 118, 88, 140)         # a worked-ground wash, translucent
GRASSW = (104, 116, 76, 90)         # a grass wash, translucent
WATERW = (78, 96, 112, 110)         # a water wash, translucent
NET = (96, 92, 62, 200)             # camouflage netting


def _c(col, f, a=None):
    """A tone of a colour: f<1 shaded, f>1 lit."""
    r, g, b = col[0], col[1], col[2]
    out = (max(0, min(255, int(r * f))),
           max(0, min(255, int(g * f))),
           max(0, min(255, int(b * f))),
           col[3] if a is None else a)
    return out


# ---------------------------------------------------------------- strokes
def P(d, pts, fill, outline=INK, w=2):
    d.polygon(list(pts), fill=fill, outline=outline, width=w)


def R(d, box, fill, outline=INK, w=2):
    d.rectangle(list(box), fill=fill, outline=outline, width=w)


def E(d, box, fill, outline=INK, w=2):
    d.ellipse(list(box), fill=fill, outline=outline, width=w)


def L(d, pts, col=INK, w=2):
    d.line(list(pts), fill=col, width=w)


def _rot(pts, cx, cy, deg):
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    return [(cx + (x - cx) * ca - (y - cy) * sa,
             cy + (x - cx) * sa + (y - cy) * ca) for (x, y) in pts]


def barrel(d, x, y0, y1, w=3.4, col=GUNMETAL, muzzle=True):
    """A gun barrel running from y0 (breech) to y1 (muzzle)."""
    R(d, [x - w / 2, min(y0, y1), x + w / 2, max(y0, y1)], col, w=2)
    if muzzle:
        my = y1 if y1 < y0 else y1
        R(d, [x - w / 2 - 1.2, my - 1.0, x + w / 2 + 1.2, my + 2.2],
          _c(col, 0.8), w=2)


def track_band(d, x0, y0, x1, y1, links=9):
    """One track run with its links picked out."""
    R(d, [x0, y0, x1, y1], TRACK, w=2)
    step = (y1 - y0) / float(links)
    for i in range(1, links):
        yy = y0 + i * step
        L(d, [(x0 + 1.2, yy), (x1 - 1.2, yy)], TRACK_L, 1)


def road_wheels(d, x, y0, y1, n, r=2.2):
    step = (y1 - y0) / float(max(1, n - 1))
    for i in range(n):
        yy = y0 + i * step
        E(d, [x - r, yy - r, x + r, yy + r], _c(TRACK, 1.5),
          outline=None, w=1)


# ================================================================= LAND
def tu_infantry(d, ink, nat=None):
    """A rifle section on the march, seen from above: two files of
    men -- helmets, shoulders, packs, rifles slung -- the section
    leader a pace ahead of the wedge."""
    def man(cx, cy, lead=False):
        # rifle slung across the pack, muzzle up-right
        L(d, [(cx - 6, cy + 8), (cx + 6.6, cy - 8.6)],
          _c(WOOD, 0.95), 3)
        # pack and shoulders
        P(d, [(cx - 8, cy - 2), (cx + 8, cy - 2),
              (cx + 6.4, cy + 8.4), (cx - 6.4, cy + 8.4)],
          UNIFORM, w=2)
        R(d, [cx - 4, cy + 2, cx + 4, cy + 8], _c(UNIFORM, 0.8),
          w=1)                                   # the pack itself
        # the helmet, with its lit rim
        E(d, [cx - 5.4, cy - 8.4, cx + 5.4, cy + 2.6],
          _c(UNIFORM, 1.3) if not lead else _c(UNIFORM, 1.42), w=2)
        E(d, [cx - 2.6, cy - 6, cx + 1.2, cy - 2.6],
          _c(UNIFORM, 1.6), outline=None)
    man(48, 17, lead=True)
    for dx, dy in ((-19, 42), (19, 42), (-19, 68), (19, 68)):
        man(48 + dx, dy)


def _tank_body(d, hull, x0=26, x1=70, y0=12, y1=84, skirt=2):
    """Tracks, hull plate and engine deck common to the tank family.
    Returns the hull box for the caller's turret."""
    track_band(d, x0 - 8, y0, x0 - 8 + 7, y1, links=11)
    track_band(d, x1 + 1, y0, x1 + 8, y1, links=11)
    # glacis, hull roof, engine deck
    P(d, [(x0, y0 + 2), (x1, y0 + 2), (x1, y1 - 2), (x0, y1 - 2)],
      hull, w=2)
    P(d, [(x0, y0 + 2), (x1, y0 + 2), (x1 - 4, y0 + 10),
          (x0 + 4, y0 + 10)], _c(hull, 1.2), w=2)     # lit glacis
    R(d, [x0 + 4, y1 - 20, x1 - 4, y1 - 4], _c(hull, 0.82), w=2)
    for yy in (y1 - 16, y1 - 12, y1 - 8):             # engine louvres
        L(d, [(x0 + 7, yy), (x1 - 7, yy)], _c(hull, 0.6), 1)
    return x0, x1, y0, y1


def tu_tank(d, ink, nat=None):
    """The medium tank, per nation: Tiger I's slab hull, the T-34's
    sloped plates, the Churchill's long track guards, the Chi-Ha's
    small turret, and the Sherman for everyone else."""
    hull = FELD if nat == 'germany' else OD
    if nat == 'britain':
        x0, x1, y0, y1 = _tank_body(d, hull, 28, 68, 8, 88)
    elif nat == 'germany':
        x0, x1, y0, y1 = _tank_body(d, hull, 24, 72, 12, 84)
    else:
        x0, x1, y0, y1 = _tank_body(d, hull, 27, 69, 12, 84)
    cx = 48
    if nat == 'germany':                    # Tiger: drum turret, 88
        E(d, [cx - 14, 30, cx + 14, 58], _c(hull, 1.08), w=2)
        R(d, [cx - 5, 50, cx + 5, 56], _c(hull, 0.85), w=2)
        barrel(d, cx, 34, 2, w=3.8)
        E(d, [cx + 4, 40, cx + 10, 46], _c(hull, 1.3), w=2)  # hatch
    elif nat == 'soviet':                   # T-34: rounded, forward
        E(d, [cx - 12, 24, cx + 12, 50], _c(hull, 1.08), w=2)
        barrel(d, cx, 30, 4, w=3.2)
        E(d, [cx - 8, 32, cx - 2, 38], _c(hull, 1.3), w=2)
    elif nat == 'japan':                    # Chi-Ha: small, offset
        E(d, [cx - 9, 30, cx + 11, 50], _c(hull, 1.08), w=2)
        barrel(d, cx + 1, 34, 10, w=2.6)
        E(d, [cx - 5, 35, cx + 1, 41], _c(hull, 1.3), w=2)
    elif nat == 'britain':                  # Churchill: turret amidships
        P(d, [(cx - 11, 34), (cx + 11, 34), (cx + 9, 56),
              (cx - 9, 56)], _c(hull, 1.08), w=2)
        barrel(d, cx, 38, 8, w=3.0)
        E(d, [cx + 2, 42, cx + 8, 48], _c(hull, 1.3), w=2)
    else:                                   # Sherman
        E(d, [cx - 11, 28, cx + 11, 52], _c(hull, 1.08), w=2)
        barrel(d, cx, 32, 6, w=3.0)
        E(d, [cx - 8, 36, cx - 2, 42], _c(hull, 1.3), w=2)
    # stowage on the deck: a rolled tarp and jerricans
    R(d, [30, 74, 44, 79], CANVAS_D, w=1)
    R(d, [56, 73, 62, 80], _c(GUNMETAL, 1.2), w=1)


def tu_heavy_tank(d, ink, nat=None):
    """The heavy: wider tracks, a long gun with muzzle brake, spare
    links bolted to the glacis."""
    hull = FELD if nat == 'germany' else OD
    track_band(d, 12, 8, 23, 88, links=12)
    track_band(d, 73, 8, 84, 88, links=12)
    P(d, [(26, 10), (70, 10), (70, 86), (26, 86)], hull, w=2)
    P(d, [(26, 10), (70, 10), (66, 20), (30, 20)], _c(hull, 1.2), w=2)
    R(d, [30, 66, 66, 82], _c(hull, 0.82), w=2)
    for yy in (70, 74, 78):
        L(d, [(33, yy), (63, yy)], _c(hull, 0.6), 1)
    for xx in (32, 38, 44, 50, 56, 62):     # spare track on the bow
        R(d, [xx, 12, xx + 4, 17], TRACK, w=1)
    P(d, [(32, 28), (64, 28), (60, 60), (36, 60)], _c(hull, 1.08), w=2)
    barrel(d, 48, 30, 0, w=4.2)
    R(d, [45.4, 2, 50.6, 7], GUNMETAL, w=2)          # muzzle brake
    E(d, [52, 46, 60, 54], _c(hull, 1.3), w=2)
    E(d, [37, 46, 43, 52], _c(hull, 1.25), w=2)


def _truck_body(d, cab_col, bed_w=30, y_cab=18, tires=True):
    """Chassis, cab and front wings shared by the lorry family.
    Returns the bed box behind the cab."""
    cx = 48
    x0, x1 = cx - bed_w // 2, cx + bed_w // 2
    if tires:
        for yy in (14, 66, 78):
            E(d, [x0 - 6, yy, x0 - 1, yy + 9], TIRE, w=1)
            E(d, [x1 + 1, yy, x1 + 6, yy + 9], TIRE, w=1)
    # bonnet and wings
    P(d, [(x0 + 3, 8), (x1 - 3, 8), (x1, y_cab), (x0, y_cab)],
      _c(cab_col, 1.12), w=2)
    L(d, [(cx, 9), (cx, y_cab - 1)], _c(cab_col, 0.7), 1)
    # cab roof with its windscreen line
    R(d, [x0, y_cab, x1, y_cab + 12], cab_col, w=2)
    R(d, [x0 + 3, y_cab + 1, x1 - 3, y_cab + 5], GLASS_D, w=1)
    return x0, y_cab + 12, x1, 88


def tu_supply_truck(d, ink, nat=None):
    """The stores lorry: canvas tilt over hoops, crates lashed at
    the tailboard."""
    col = OD if nat not in ('germany',) else FELD
    x0, y0, x1, y1 = _truck_body(d, col)
    R(d, [x0, y0, x1, y1 - 8], CANVAS, w=2)
    for yy in range(y0 + 6, y1 - 10, 9):    # the tilt's hoops
        L(d, [(x0 + 1, yy), (x1 - 1, yy)], CANVAS_D, 2)
    L(d, [(x0 + 3, y0 + 2), (x0 + 3, y1 - 10)], _c(CANVAS, 1.15), 1)
    R(d, [x0 + 3, y1 - 8, x1 - 3, y1], WOOD, w=2)      # open tailgate
    R(d, [x0 + 5, y1 - 7, x0 + 14, y1 - 1], _c(WOOD, 0.8), w=1)
    R(d, [x1 - 14, y1 - 7, x1 - 5, y1 - 1], _c(WOOD, 0.85), w=1)


def tu_transport_truck(d, ink, nat=None):
    """The troop carrier, per nation: the American half-track, the
    British Bren carrier, the Soviet ZIS with benches, and an open
    lorry with its section aboard for the rest."""
    if nat == 'usa':                        # M3 half-track
        track_band(d, 26, 48, 34, 86, links=6)
        track_band(d, 62, 48, 70, 86, links=6)
        E(d, [27, 12, 33, 24], TIRE, w=1)
        E(d, [63, 12, 69, 24], TIRE, w=1)
        P(d, [(34, 8), (62, 8), (64, 20), (32, 20)], _c(OD, 1.12), w=2)
        R(d, [32, 20, 64, 30], OD, w=2)
        R(d, [35, 21, 61, 25], GLASS_D, w=1)
        R(d, [30, 30, 66, 84], OD, w=2)                 # open bay
        R(d, [33, 33, 63, 81], _c(OD, 0.8), w=1)
        for yy in (40, 52, 64, 76):                     # the benches
            L(d, [(34, yy), (62, yy)], _c(OD, 1.2), 2)
        for xx, yy in ((39, 36), (57, 36), (39, 48), (57, 48),
                       (39, 60), (57, 60)):             # helmets
            E(d, [xx - 3, yy - 3, xx + 3, yy + 3],
              _c(UNIFORM, 1.3), w=1)
        return
    if nat == 'britain':                    # Bren carrier: low, open
        track_band(d, 24, 16, 33, 82, links=9)
        track_band(d, 63, 16, 72, 82, links=9)
        P(d, [(34, 12), (62, 12), (64, 80), (32, 80)], OD, w=2)
        P(d, [(34, 12), (62, 12), (60, 22), (36, 22)], _c(OD, 1.2),
          w=2)
        R(d, [36, 26, 60, 76], _c(OD, 0.8), w=2)        # the open tub
        L(d, [(48, 26), (48, 76)], _c(OD, 0.65), 1)
        for xx, yy in ((42, 36), (54, 36), (42, 56), (54, 56)):
            E(d, [xx - 3, yy - 3, xx + 3, yy + 3],
              _c(UNIFORM, 1.3), w=1)
        L(d, [(40, 18), (46, 14)], GUNMETAL, 2)         # the Bren
        return
    col = FELD if nat == 'germany' else OD
    x0, y0, x1, y1 = _truck_body(d, col)
    R(d, [x0, y0, x1, y1], col, w=2)                    # open bed
    R(d, [x0 + 3, y0 + 3, x1 - 3, y1 - 3], _c(col, 0.78), w=1)
    for yy in (y0 + 10, y0 + 22, y0 + 34, y0 + 46):     # benches
        L(d, [(x0 + 3, yy), (x1 - 3, yy)], _c(col, 1.2), 2)
    for xx, yy in ((41, y0 + 6), (55, y0 + 6), (41, y0 + 17),
                   (55, y0 + 17), (41, y0 + 28), (55, y0 + 28),
                   (41, y0 + 40), (55, y0 + 40)):
        E(d, [xx - 3, yy - 3, xx + 3, yy + 3], _c(UNIFORM, 1.3), w=1)


def tu_engineer(d, ink, nat=None):
    """The engineer company: a lorry with the bridge sections on its
    bed and the tool lockers open."""
    col = OD if nat != 'germany' else FELD
    x0, y0, x1, y1 = _truck_body(d, col)
    R(d, [x0, y0, x1, y1], col, w=2)
    # two pontoon sections, carried nested
    R(d, [x0 + 3, y0 + 3, x1 - 3, y0 + 22], _c(WOOD, 1.05), w=2)
    R(d, [x0 + 6, y0 + 6, x1 - 6, y0 + 19], _c(WOOD, 0.8), w=1)
    R(d, [x0 + 3, y0 + 25, x1 - 3, y0 + 44], _c(WOOD, 0.95), w=2)
    R(d, [x0 + 6, y0 + 28, x1 - 6, y0 + 41], _c(WOOD, 0.72), w=1)
    # plank rails alongside, tools at the tail
    L(d, [(x0 + 1, y0 + 2), (x0 + 1, y1 - 2)], _c(WOOD, 1.2), 2)
    L(d, [(x1 - 1, y0 + 2), (x1 - 1, y1 - 2)], _c(WOOD, 1.2), 2)
    R(d, [x0 + 4, y1 - 12, x1 - 4, y1 - 2], _c(GUNMETAL, 1.1), w=2)
    L(d, [(x0 + 7, y1 - 10), (x0 + 13, y1 - 4)], INK, 2)   # pick
    L(d, [(x0 + 13, y1 - 10), (x0 + 7, y1 - 4)], INK, 2)
    E(d, [x1 - 15, y1 - 11, x1 - 7, y1 - 3], _c(GUNMETAL, 1.4), w=1)


def tu_artillery(d, ink, nat=None):
    """The field piece deployed for action: split trails staked out
    wide, gun shield across the carriage, the barrel long over it,
    ready ammunition boxed at the trail."""
    col = OD if nat != 'germany' else FELD
    # split trails, spades dug in
    P(d, [(44, 56), (52, 56), (72, 88), (62, 88)], _c(col, 0.85), w=2)
    P(d, [(44, 56), (52, 56), (34, 88), (24, 88)], _c(col, 0.85), w=2)
    R(d, [20, 84, 32, 92], _c(col, 0.68), w=2)
    R(d, [64, 84, 76, 92], _c(col, 0.68), w=2)
    # wheels either side of the axle
    E(d, [20, 38, 32, 62], TIRE, w=2)
    E(d, [23, 43, 29, 57], _c(TIRE, 1.7), w=1)
    E(d, [64, 38, 76, 62], TIRE, w=2)
    E(d, [67, 43, 73, 57], _c(TIRE, 1.7), w=1)
    # the shield, angled back like the real plate
    P(d, [(30, 36), (66, 36), (62, 54), (34, 54)], _c(col, 1.15), w=2)
    L(d, [(33, 40), (63, 40)], _c(col, 1.35), 2)
    # cradle and the piece
    R(d, [42, 40, 54, 62], _c(col, 0.9), w=2)
    barrel(d, 48, 44, 6, w=4.4)
    R(d, [44.4, 6, 51.6, 13], GUNMETAL, w=2)         # muzzle brake
    # ready ammunition at the right trail
    for i in range(3):
        R(d, [68, 62 + i * 8, 86, 68 + i * 8], _c(WOOD, 1.05), w=2)
        L(d, [(71, 65 + i * 8), (83, 65 + i * 8)], _c(WOOD, 0.7), 1)


def tu_aa(d, ink, nat=None):
    """The AA battery emplaced: a ring of sandbags round the pit,
    the cruciform mount staked out, the long barrel trained up and
    across the position."""
    col = FELD if nat == 'germany' else OD
    # the sandbag parapet: bags laid one against the next
    for i in range(18):
        a = 2 * math.pi * i / 18
        bx, by = 48 + 39 * math.cos(a), 52 + 38 * math.sin(a)
        pts = _rot([(bx - 6, by - 3.4), (bx + 6, by - 3.4),
                    (bx + 6, by + 3.4), (bx - 6, by + 3.4)],
                   bx, by, math.degrees(a) + 90)
        P(d, pts, _c(CANVAS, 0.92) if i % 2 else CANVAS_D, w=1)
    # cruciform outriggers
    for ang in (45, 135):
        pts = _rot([(43, 22), (53, 22), (53, 82), (43, 82)],
                   48, 52, ang)
        P(d, pts, _c(col, 0.88), w=2)
    E(d, [34, 38, 62, 66], _c(col, 1.12), w=2)      # the platform
    E(d, [41, 45, 55, 59], _c(col, 0.8), w=2)       # the pedestal
    # the piece, trained up-right, with its recuperator
    pts = _rot([(45, 52), (51, 52), (51, 4), (45, 4)], 48, 52, 28)
    P(d, pts, GUNMETAL, w=2)
    mz = _rot([(43.4, 8), (52.6, 8), (52.6, 14), (43.4, 14)],
              48, 52, 28)
    P(d, mz, _c(GUNMETAL, 0.72), w=2)
    br = _rot([(46, 40), (50, 40), (50, 52), (46, 52)], 48, 52, 28)
    P(d, br, _c(GUNMETAL, 1.3), w=1)
    # crew seats
    E(d, [30, 58, 38, 66], _c(col, 1.3), w=2)
    E(d, [58, 58, 66, 66], _c(col, 1.3), w=2)


def tu_army_command(d, ink, nat=None):
    """The headquarters on wheels: a box-bodied signals lorry, the
    frame aerial over the roof, and the command pennant flying at
    the wing."""
    col = FELD if nat == 'germany' else OD
    x0, y0, x1, y1 = _truck_body(d, col, bed_w=32)
    # the signals box body
    R(d, [x0 - 1, y0, x1 + 1, y1], col, w=2)
    R(d, [x0 + 3, y0 + 4, x1 - 3, y1 - 4], _c(col, 1.12), w=1)
    L(d, [(48, y0 + 4), (48, y1 - 4)], _c(col, 0.75), 1)
    # roof hatch and ventilator
    R(d, [x0 + 5, y1 - 16, x0 + 15, y1 - 7], _c(col, 1.3), w=1)
    E(d, [x1 - 13, y1 - 15, x1 - 6, y1 - 8], _c(col, 0.7), w=1)
    # the frame aerial: four masts and the wire rectangle slung
    # between them, riding clear above the roof
    for mx, my in ((x0 + 2, y0 + 6), (x1 - 2, y0 + 6),
                   (x0 + 2, y1 - 20), (x1 - 2, y1 - 20)):
        E(d, [mx - 1.6, my - 1.6, mx + 1.6, my + 1.6],
          _c(GUNMETAL, 1.6), w=1)
    R(d, [x0 + 2, y0 + 6, x1 - 2, y1 - 20], None,
      outline=_c(GUNMETAL, 1.55), w=2)
    L(d, [(x0 + 2, y0 + 6), (x1 - 2, y1 - 20)],
      _c(GUNMETAL, 1.55), 1)
    L(d, [(x1 - 2, y0 + 6), (x0 + 2, y1 - 20)],
      _c(GUNMETAL, 1.55), 1)
    # the pennant at the near wing
    L(d, [(x0 - 5, 10), (x0 - 5, 24)], INK, 2)
    P(d, [(x0 - 5, 10), (x0 - 16, 13.5), (x0 - 5, 17)],
      (172, 44, 36, 255), w=2)


def tu_blimp_truck(d, ink, nat=None):
    """The balloon station grounded: envelope folded on the bed,
    winch drum at the tail -- clearly NOT aloft."""
    col = OD if nat != 'germany' else FELD
    x0, y0, x1, y1 = _truck_body(d, col, bed_w=34)
    R(d, [x0, y0, x1, y1], col, w=2)
    # the folded envelope, humped in canvas
    E(d, [x0 + 2, y0 + 2, x1 - 2, y1 - 18], CANVAS, w=2)
    E(d, [x0 + 7, y0 + 7, x1 - 7, y1 - 26], _c(CANVAS, 1.15),
      outline=None)
    for yy in range(y0 + 8, y1 - 22, 8):
        L(d, [(x0 + 4, yy), (x1 - 4, yy)], CANVAS_D, 1)
    # the winch
    E(d, [42, y1 - 14, 54, y1 - 2], _c(GUNMETAL, 1.2), w=2)
    E(d, [46, y1 - 10, 50, y1 - 6], _c(GUNMETAL, 0.7), w=1)


def tu_blimp_up(d, ink, nat=None):
    """The balloon ALOFT: the envelope full and taut with its fins,
    the tether falling away to a tiny winch far below."""
    # the tether and the winch it rises from
    L(d, [(60, 88), (52, 58)], _c(GUNMETAL, 1.3), 1)
    R(d, [58, 86, 66, 92], _c(OD, 0.9), w=1)
    # envelope
    E(d, [22, 8, 74, 76], ALU, w=2)
    E(d, [30, 14, 58, 44], _c(ALU, 1.18), outline=None)
    L(d, [(48, 10), (48, 74)], _c(ALU, 0.8), 1)
    for t in (0.3, 0.5, 0.7):
        yy = 8 + 68 * t
        E(d, [24 + 6 * abs(t - 0.5) * 2, yy - 1,
              72 - 6 * abs(t - 0.5) * 2, yy + 1], None,
          outline=_c(ALU, 0.75), w=1)
    # tail fins
    P(d, [(48, 66), (30, 84), (40, 84), (48, 74)], _c(ALU, 0.85), w=2)
    P(d, [(48, 66), (66, 84), (56, 84), (48, 74)], _c(ALU, 0.85), w=2)
    # the observation car
    R(d, [43, 40, 53, 52], _c(GUNMETAL, 1.25), w=2)
    R(d, [45, 42, 51, 46], GLASS_D, w=1)


# ================================================================== AIR
def _prop(d, cx, cy, r=7):
    """The spinning disc, centred ON the spinner -- not floating
    ahead of it like a toy balloon."""
    E(d, [cx - r, cy - r, cx + r, cy + r], PROP, outline=None)
    E(d, [cx - 1.8, cy - 1.8, cx + 1.8, cy + 1.8],
      _c(GUNMETAL, 1.25), w=1)


def _wing_engine(d, cx, cy, col):
    R(d, [cx - 3.4, cy - 5, cx + 3.4, cy + 7], _c(col, 0.85), w=2)
    _prop(d, cx, cy - 4, r=5.5)


def tu_fighter(d, ink, nat=None):
    """The single-seat fighter, per nation: the Spitfire's ellipse,
    the 109's clipped wing, the Zero's long round tip, the Yak's
    taper -- canopy, prop disc and tailplane on all of them."""
    col = {'germany': FELD, 'japan': ALU,
           'soviet': OD}.get(nat, AIROLIVE)
    if nat == 'britain':
        wing = [(48, 30), (10, 40), (6, 48), (10, 54), (48, 58),
                (86, 54), (90, 48), (86, 40)]
    elif nat == 'germany':
        wing = [(48, 32), (12, 44), (12, 56), (48, 56), (84, 56),
                (84, 44)]
    elif nat == 'japan':
        wing = [(48, 30), (8, 42), (6, 50), (14, 56), (48, 56),
                (82, 56), (90, 50), (88, 42)]
    else:
        wing = [(48, 32), (14, 46), (16, 56), (48, 56), (80, 56),
                (82, 46)]
    P(d, wing, col, w=2)
    L(d, [(24, 46), (40, 42)], _c(col, 1.2), 1)       # aileron line
    L(d, [(56, 42), (72, 46)], _c(col, 1.2), 1)
    # tailplane
    P(d, [(48, 74), (30, 82), (32, 88), (48, 86), (64, 88),
          (66, 82)], _c(col, 0.95), w=2)
    # fuselage over the wing
    P(d, [(45, 12), (51, 12), (53, 30), (52, 78), (48, 90),
          (44, 78), (43, 30)], _c(col, 1.1), w=2)
    R(d, [44.6, 34, 51.4, 46], GLASS, w=2)            # the canopy
    L(d, [(48, 34), (48, 46)], GLASS_D, 1)
    _prop(d, 48, 13, r=9)
    E(d, [45.4, 9, 50.6, 16], _c(col, 0.85), w=2)     # the cowling
    return col


def _bomber_common(d, col, span, nose, tail, engines, body_w=5.5,
                   glass_nose=True, twin_tail=False):
    """Wing, fuselage, tail and engines for the bomber family."""
    x0, x1 = 48 - span // 2, 48 + span // 2
    # main plane, swept slightly back
    P(d, [(48, 34), (x0, 46), (x0 + 2, 56), (48, 50), (x1 - 2, 56),
          (x1, 46)], col, w=2)
    # tailplane
    if twin_tail:
        P(d, [(48, 74), (32, 80), (33, 86), (48, 83), (63, 86),
              (64, 80)], _c(col, 0.95), w=2)
        R(d, [30, 76, 34, 88], _c(col, 1.15), w=1)
        R(d, [62, 76, 66, 88], _c(col, 1.15), w=1)
    else:
        P(d, [(48, 74), (32, 82), (34, 88), (48, 85), (62, 88),
              (64, 82)], _c(col, 0.95), w=2)
    # fuselage
    P(d, [(48 - body_w, nose + 6), (48 + body_w, nose + 6),
          (48 + body_w - 1, 70), (48, tail), (48 - body_w + 1, 70)],
      _c(col, 1.1), w=2)
    E(d, [48 - body_w, nose, 48 + body_w, nose + 12],
      GLASS if glass_nose else _c(col, 1.1), w=2)
    R(d, [45, 40, 51, 50], GLASS_D, w=1)              # dorsal glass
    # engines on the wing
    k = span / 2.0
    for off in engines:
        _wing_engine(d, 48 + off * k, 44 - abs(off) * 4, col)
        _wing_engine(d, 48 - off * k, 44 - abs(off) * 4, col)


def tu_bomber(d, ink, nat=None):
    """The bomber, per nation: the B-17's four engines, the
    Halifax's long square wing, the Il-2 a single-engined attacker,
    the Betty's cigar body -- a twin-engined Ju 88 for the rest."""
    if nat == 'usa':
        _bomber_common(d, ALU, 84, 8, 90, (0.35, 0.72),
                       body_w=5.5, twin_tail=False)
        return
    if nat == 'britain':
        _bomber_common(d, AIROLIVE, 82, 10, 90, (0.36, 0.74),
                       twin_tail=True)
        return
    if nat == 'soviet':                     # the Sturmovik
        col = AIROLIVE
        P(d, [(48, 30), (12, 44), (14, 54), (48, 54), (82, 54),
              (84, 44)], col, w=2)
        P(d, [(48, 72), (34, 80), (36, 86), (48, 84), (60, 86),
              (62, 80)], _c(col, 0.95), w=2)
        P(d, [(43, 10), (53, 10), (54, 32), (52, 76), (48, 88),
              (44, 76), (42, 32)], _c(col, 1.1), w=2)
        R(d, [44.4, 30, 51.6, 44], GLASS, w=2)        # long greenhouse
        L(d, [(48, 30), (48, 44)], GLASS_D, 1)
        _prop(d, 48, 12, r=9)
        E(d, [45, 8, 51, 15], _c(col, 0.85), w=2)
        return
    if nat == 'japan':                      # the Betty
        col = ALU
        _bomber_common(d, col, 80, 10, 88, (0.42,), body_w=6.5)
        E(d, [42, 76, 54, 88], _c(col, 1.05), w=2)    # tail cone gun
        return
    _bomber_common(d, FELD if nat == 'germany' else AIROLIVE,
                   76, 10, 88, (0.4,))


def tu_heavy_bomber(d, ink, nat=None):
    """The heavy: four engines and a long bomb bay; the Lancaster
    wears its twin fins."""
    if nat == 'britain':
        _bomber_common(d, AIROLIVE_D, 88, 8, 92, (0.33, 0.68),
                       body_w=6, twin_tail=True)
    else:
        _bomber_common(d, AIROLIVE_D, 90, 8, 92, (0.32, 0.66),
                       body_w=6.5)
    R(d, [44, 52, 52, 68], _c(AIROLIVE_D, 0.75), w=1)  # the bay doors
    L(d, [(48, 52), (48, 68)], _c(AIROLIVE_D, 0.55), 1)


def tu_jet(d, ink, nat=None):
    """The jet: swept wings and two slung pods, no prop anywhere."""
    col = ALU
    P(d, [(48, 34), (14, 52), (16, 60), (48, 52), (80, 60),
          (82, 52)], col, w=2)
    R(d, [26, 46, 33, 60], _c(GUNMETAL, 1.15), w=2)   # the pods
    R(d, [63, 46, 70, 60], _c(GUNMETAL, 1.15), w=2)
    E(d, [27, 44, 32, 48], INK, w=1)                  # intakes
    E(d, [64, 44, 69, 48], INK, w=1)
    P(d, [(48, 76), (34, 84), (36, 89), (48, 86), (60, 89),
          (62, 84)], _c(col, 0.95), w=2)
    P(d, [(45, 8), (51, 8), (53, 34), (52, 78), (48, 92),
          (44, 78), (43, 34)], _c(col, 1.12), w=2)
    R(d, [44.8, 26, 51.2, 38], GLASS, w=2)
    P(d, [(45, 8), (51, 8), (48, 2)], _c(col, 0.9), w=2)  # the point


def tu_transport_air(d, ink, nat=None):
    """The transport: broad straight wing, two engines, the big
    cargo door aft on the port side."""
    col = OD if nat != 'germany' else FELD
    P(d, [(48, 36), (8, 44), (8, 54), (48, 52), (88, 54), (88, 44)],
      col, w=2)
    P(d, [(48, 74), (30, 82), (32, 88), (48, 85), (64, 88),
          (66, 82)], _c(col, 0.95), w=2)
    P(d, [(42, 12), (54, 12), (55, 36), (53, 74), (48, 90),
          (43, 74), (41, 36)], _c(col, 1.1), w=2)
    E(d, [42, 6, 54, 18], _c(col, 1.05), w=2)
    R(d, [44, 10, 52, 14], GLASS_D, w=1)              # cockpit glass
    _wing_engine(d, 30, 42, col)
    _wing_engine(d, 66, 42, col)
    R(d, [40, 60, 44, 70], _c(col, 0.7), w=1)         # the cargo door
    for yy in (20, 26, 32):                           # cabin windows
        E(d, [44.6, yy, 47, yy + 2.4], GLASS_D, outline=None)
        E(d, [49, yy, 51.4, yy + 2.4], GLASS_D, outline=None)


def tu_air_command(d, ink, nat=None):
    """The flying headquarters: the nation's own bomber wearing the
    command band across the wings and the long trailing aerial."""
    tu_bomber(d, ink, nat)
    # the command band, painted athwart both wings
    R(d, [10, 47, 34, 52], (206, 178, 90, 235), outline=INK, w=1)
    R(d, [62, 47, 86, 52], (206, 178, 90, 235), outline=INK, w=1)
    # the trailed wireless aerial
    L(d, [(48, 88), (58, 95)], _c(GUNMETAL, 1.6), 1)
    E(d, [57, 94, 60, 97], _c(GUNMETAL, 1.6), w=1)


# ================================================================== SEA
def _ship_hull(d, beam, bow, stern, col=HULL, deck=None):
    """The hull plan: a fine entry easing out to the full beam a
    third of the way aft, straight run, tucked stern -- the lines a
    draughtsman would fair, not a coffin wedge."""
    cx = 48
    x0, x1 = cx - beam / 2.0, cx + beam / 2.0
    sh = bow + (stern - bow) * 0.30         # full beam reached here
    fw = bow + (stern - bow) * 0.12         # the entry's waist
    P(d, [(cx, bow),
          (cx + beam * 0.28, fw), (x1 - 0.5, sh),
          (x1, stern - 8), (x1 - 3, stern), (x0 + 3, stern),
          (x0, stern - 8),
          (x0 + 0.5, sh), (cx - beam * 0.28, fw)], col, w=2)
    dk = deck or _c(col, 1.12)
    P(d, [(cx, bow + 3.5),
          (cx + beam * 0.24, fw + 1), (x1 - 3, sh),
          (x1 - 2.5, stern - 8.5), (x1 - 5, stern - 2.5),
          (x0 + 5, stern - 2.5), (x0 + 2.5, stern - 8.5),
          (x0 + 3, sh), (cx - beam * 0.24, fw + 1)], dk,
      outline=None)
    L(d, [(cx, bow + 4), (cx, stern - 4)], _c(dk, 0.88), 1)
    return x0, x1


def _turret_ship(d, cx, cy, r, n_guns=2, up=True, col=None):
    """A main turret with its barrels, trained fore or aft."""
    col = col or _c(HULL, 1.25)
    E(d, [cx - r, cy - r, cx + r, cy + r], col, w=2)
    step = (r * 1.1) if n_guns == 2 else 0
    xs = {1: (cx,), 2: (cx - step / 2, cx + step / 2),
          3: (cx - step, cx, cx + step)}[n_guns]
    ln = r * 2.4
    for x in xs:
        y1 = cy - r - ln if up else cy + r + ln
        L(d, [(x, cy - (r - 1) if up else cy + (r - 1)), (x, y1)],
          GUNMETAL, 2)


def tu_dd_sea(d, ink, nat=None):
    """The fleet destroyer: two turrets forward, one aft, torpedo
    tubes amidships, twin raked funnels."""
    _ship_hull(d, 17, 4, 92)
    _turret_ship(d, 48, 18, 3.4, 1)
    _turret_ship(d, 48, 27, 3.4, 1)
    R(d, [43, 34, 53, 46], _c(HULL, 1.2), w=2)        # the bridge
    R(d, [45, 35.5, 51, 39], GLASS_D, w=1)
    E(d, [45, 48, 51, 54], STACK, w=2)                # funnels
    E(d, [45, 57, 51, 63], STACK, w=2)
    # the tubes, trained fore-and-aft on the centreline
    R(d, [45.5, 65, 50.5, 75], _c(GUNMETAL, 1.25), w=1)
    for yy in (66.5, 69.5, 72.5):
        E(d, [46.2, yy, 49.8, yy + 2.2], GUNMETAL, outline=None)
    _turret_ship(d, 48, 82, 3.2, 1, up=False)
    if nat == 'japan':                  # Fubuki: enclosed twin aft
        _turret_ship(d, 48, 82, 3.8, 2, up=False)
    if nat == 'britain':                # Tribal: twin forward
        _turret_ship(d, 48, 18, 3.8, 2)


def tu_dd_aa(d, ink, nat=None):
    """The AA escort: one funnel, and the deck TUFTED with gun tubs
    -- rings of small mounts along both rails."""
    x0, x1 = _ship_hull(d, 17, 4, 92)
    _turret_ship(d, 48, 18, 3.2, 1)
    R(d, [43, 26, 53, 38], _c(HULL, 1.2), w=2)
    R(d, [45, 27.5, 51, 31], GLASS_D, w=1)
    E(d, [44.5, 41, 51.5, 48], STACK, w=2)
    for yy in (52, 62, 72):                           # the tubs
        for xx in (x0 + 3.4, x1 - 3.4):
            E(d, [xx - 3, yy - 3, xx + 3, yy + 3],
              _c(HULL, 1.3), w=1)
            L(d, [(xx, yy), (xx + (2.6 if xx > 48 else -2.6),
                             yy - 2.6)], GUNMETAL, 1)
    E(d, [44, 80, 52, 88], _c(HULL, 1.3), w=2)        # aft director
    L(d, [(48, 82), (48, 76)], GUNMETAL, 2)


def tu_dd_land(d, ink, nat=None):
    """The bombardment ship: heavy twin turrets forward and a bank
    of rocket rails laid over the afterdeck."""
    _ship_hull(d, 18, 4, 92)
    _turret_ship(d, 48, 17, 4.2, 2)
    _turret_ship(d, 48, 28, 4.2, 2)
    R(d, [43, 36, 53, 48], _c(HULL, 1.2), w=2)
    R(d, [45, 37.5, 51, 41], GLASS_D, w=1)
    E(d, [44.5, 51, 51.5, 58], STACK, w=2)
    # the rails, angled up the port quarter
    for i in range(5):
        x = 41.5 + i * 3.4
        L(d, [(x, 84), (x + 3.5, 62)], _c(GUNMETAL, 1.3), 2)
    R(d, [39, 82, 59, 88], _c(HULL, 0.9), w=2)


def tu_cruiser(d, ink, nat=None):
    """The heavy cruiser: 2+2 main turrets, the aircraft catapult
    and its floatplane amidships between the funnels."""
    _ship_hull(d, 22, 4, 93)
    _turret_ship(d, 48, 15, 4, 2)
    _turret_ship(d, 48, 25, 4, 2)
    R(d, [41, 32, 55, 44], _c(HULL, 1.2), w=2)
    R(d, [43.5, 33.5, 52.5, 37.5], GLASS_D, w=1)
    E(d, [44, 46, 52, 53], STACK, w=2)
    # the catapult laid athwartships, floatplane on it
    L(d, [(34, 60), (62, 56)], _c(GUNMETAL, 1.35), 2)
    P(d, [(52, 53), (58, 58), (52, 60), (47, 58)], ALU, w=1)
    E(d, [44, 63, 52, 70], STACK, w=2)
    _turret_ship(d, 48, 78, 4, 2, up=False)
    _turret_ship(d, 48, 88, 4, 2, up=False)


def tu_battleship(d, ink, nat=None):
    """The battle line: 2+2 heavy turrets, the citadel block, and
    Nagato's pagoda foremast when she wears the flag of Japan."""
    _ship_hull(d, 27, 3, 93, deck=WOODDECK)
    _turret_ship(d, 48, 16, 5.5, 2)
    _turret_ship(d, 48, 28, 5.5, 2)
    # the citadel
    R(d, [39, 36, 57, 62], _c(HULL, 1.18), w=2)
    R(d, [42, 38, 54, 44], _c(HULL, 1.32), w=2)       # bridge block
    R(d, [44.5, 39, 51.5, 42], GLASS_D, w=1)
    if nat == 'japan':                                # the pagoda
        R(d, [42, 38, 54, 48], _c(HULL, 1.28), w=2)
        R(d, [44, 40, 52, 46], _c(HULL, 1.42), w=1)
        R(d, [46, 41.5, 50, 44.5], _c(HULL, 1.6), w=1)
        E(d, [45, 50, 51, 56], STACK, w=2)            # one funnel
    else:
        E(d, [44.5, 46, 51.5, 53], STACK, w=2)
        E(d, [44.5, 55, 51.5, 61], STACK, w=2)
    # secondary casemates along the citadel
    for yy in (40, 46, 52, 58):
        L(d, [(39, yy), (36, yy - 2)], GUNMETAL, 1)
        L(d, [(57, yy), (60, yy - 2)], GUNMETAL, 1)
    _turret_ship(d, 48, 74, 5.5, 2, up=False)
    _turret_ship(d, 48, 86, 5.5, 2, up=False)


def tu_fast_battleship(d, ink, nat=None):
    """The fast battleship: a longer, cleaner hull, triple turrets
    two forward one aft, one raked funnel and a tower mast."""
    _ship_hull(d, 25, 2, 94, deck=WOODDECK)
    _turret_ship(d, 48, 14, 5.2, 3)
    _turret_ship(d, 48, 26, 5.2, 3)
    R(d, [40, 34, 56, 56], _c(HULL, 1.18), w=2)
    R(d, [43, 36, 53, 44], _c(HULL, 1.32), w=2)
    R(d, [45, 37.5, 51, 41], GLASS_D, w=1)
    E(d, [48 - 3.5, 44, 48 + 3.5, 51], None,
      outline=_c(HULL, 1.4), w=1)                     # tower ring
    E(d, [44, 58, 52, 66], STACK, w=2)                # the one funnel
    L(d, [(44.5, 59), (51.5, 65)], _c(STACK, 1.5), 1)
    # AA sponsons along the rails
    for yy in (38, 48, 58):
        E(d, [34, yy, 39, yy + 5], _c(HULL, 1.3), w=1)
        E(d, [57, yy, 62, yy + 5], _c(HULL, 1.3), w=1)
    _turret_ship(d, 48, 82, 5.2, 3, up=False)


def tu_naval_command(d, ink, nat=None):
    """The fleet flagship: the battle line with the admiral's boats
    at the davits and his flag at the mainmast -- Yamato herself
    under the Japanese flag."""
    if nat == 'japan':                                # Yamato
        _ship_hull(d, 30, 2, 94, deck=WOODDECK)
        _turret_ship(d, 48, 15, 6.5, 3)
        _turret_ship(d, 48, 29, 6.5, 3)
        R(d, [40, 38, 56, 60], _c(HULL, 1.18), w=2)
        R(d, [43, 40, 53, 47], _c(HULL, 1.32), w=2)
        R(d, [45, 41.5, 51, 45], GLASS_D, w=1)
        E(d, [44, 50, 52, 58], STACK, w=2)            # raked funnel
        L(d, [(45, 51), (51, 57)], _c(STACK, 1.5), 1)
        _turret_ship(d, 48, 80, 6.5, 3, up=False)
        # the seaplane deck aft
        L(d, [(38, 88), (58, 88)], _c(GUNMETAL, 1.3), 2)
        P(d, [(52, 84), (57, 88), (52, 90), (48, 88)], ALU, w=1)
    else:
        tu_battleship(d, ink, None)
    # the admiral's barge and launch at the davits
    R(d, [34, 63, 39, 71], _c(WOOD, 1.2), w=1)
    R(d, [57, 63, 62, 71], _c(WOOD, 1.2), w=1)
    # his flag at the mainmast, flown clear of the funnels
    L(d, [(56, 36), (62, 30)], INK, 1)
    P(d, [(62, 30), (72, 32.5), (62, 35)], (172, 44, 36, 255), w=2)


def tu_carrier(d, ink, nat=None):
    """The fleet carrier: the flight deck end to end, the island to
    starboard (AKAGI wears hers to PORT), elevators, arrester wires
    and a parked flight forward."""
    deck = _c(TARMAC, 1.05)
    # the deck, full length, tapering to the bow ramp
    P(d, [(48, 3), (62, 8), (68, 16), (68, 84), (64, 92),
          (32, 92), (28, 84), (28, 16), (34, 8)], deck, w=2)
    L(d, [(48, 8), (48, 90)], _c(deck, 1.18), 1)      # centre stripe
    L(d, [(34, 8), (34, 90)], _c(deck, 0.8), 1)       # deck edge lines
    L(d, [(62, 8), (62, 90)], _c(deck, 0.8), 1)
    for yy in (70, 75, 80):                           # arrester wires
        L(d, [(31, yy), (65, yy)], _c(deck, 0.7), 1)
    # elevators fore and aft
    R(d, [41, 14, 55, 24], _c(deck, 0.88), w=1)
    R(d, [41, 58, 55, 68], _c(deck, 0.88), w=1)
    # the island
    if nat == 'japan':
        R(d, [22, 34, 30, 52], _c(HULL, 1.2), w=2)    # port side
        R(d, [23.5, 36, 28.5, 41], GLASS_D, w=1)
        E(d, [66, 50, 72, 60], STACK, w=2)            # curved funnel
    else:
        R(d, [66, 30, 76, 56], _c(HULL, 1.2), w=2)
        R(d, [67.5, 32, 74.5, 37], GLASS_D, w=1)
        E(d, [68, 44, 74, 52], STACK, w=2)
    # the parked flight, wings folded, spotted forward
    for i, (px, py) in enumerate(((38, 28), (48, 32), (58, 28))):
        P(d, [(px, py - 5), (px - 4, py + 3), (px + 4, py + 3)],
          ALU, w=1)
        L(d, [(px, py - 5), (px, py + 5)], _c(ALU, 0.7), 1)
    if nat == 'britain':                              # armoured deck
        R(d, [30, 8, 66, 12], _c(deck, 0.82), w=1)


def tu_submarine(d, ink, nat=None):
    """The boat: slim casing, the conning tower with periscopes up,
    bow planes out and the deck gun before the tower."""
    P(d, [(48, 6), (54, 16), (55, 40), (55, 70), (52, 90),
          (44, 90), (41, 70), (41, 40), (42, 16)], HULL_D, w=2)
    P(d, [(48, 10), (52, 18), (52.5, 68), (50, 86), (46, 86),
          (43.5, 68), (44, 18)], _c(HULL_D, 1.18), outline=None)
    L(d, [(48, 10), (48, 86)], _c(HULL_D, 0.8), 1)
    # bow planes and stern planes
    R(d, [32, 20, 42, 24], _c(HULL_D, 1.1), w=2)
    R(d, [54, 20, 64, 24], _c(HULL_D, 1.1), w=2)
    R(d, [36, 80, 44, 84], _c(HULL_D, 1.05), w=2)
    R(d, [52, 80, 60, 84], _c(HULL_D, 1.05), w=2)
    # the deck gun
    E(d, [45, 30, 51, 36], _c(GUNMETAL, 1.2), w=1)
    L(d, [(48, 31), (48, 24)], GUNMETAL, 2)
    # the tower, periscope shears up
    R(d, [43, 44, 53, 62], _c(HULL_D, 1.3), w=2)
    R(d, [45, 46, 51, 52], _c(HULL_D, 0.85), w=1)
    E(d, [46, 54, 48, 56], INK, outline=None)
    E(d, [49, 55, 51, 57], INK, outline=None)


def tu_supply_ship(d, ink, nat=None):
    """The fleet auxiliary: a working freighter -- hatched holds,
    kingpost cranes fore and aft, deck cargo lashed amidships."""
    _ship_hull(d, 24, 5, 92, col=CIVIL, deck=_c(CIVIL, 1.15))
    # holds with their hatch boards
    for y0, y1 in ((16, 30), (34, 48), (64, 78)):
        R(d, [40, y0, 56, y1], _c(WOOD, 0.95), w=2)
        for yy in range(y0 + 3, y1 - 2, 4):
            L(d, [(41.5, yy), (54.5, yy)], _c(WOOD, 0.7), 1)
    # kingposts and their derricks
    for py in (32, 62):
        L(d, [(41, py), (55, py)], _c(GUNMETAL, 1.4), 2)
        L(d, [(48, py), (58, py - 10)], _c(GUNMETAL, 1.2), 1)
    # deck cargo: drums and crates lashed between the holds
    R(d, [41, 50, 47, 56], _c(WOOD, 1.15), w=1)
    E(d, [49, 50, 54, 55], _c(GUNMETAL, 1.3), w=1)
    E(d, [49, 56, 54, 61], _c(GUNMETAL, 1.15), w=1)
    # bridge and funnel right aft, as a tramp carries them
    R(d, [41, 80, 55, 88], _c(CIVIL, 1.3), w=2)
    R(d, [43.5, 81.5, 52.5, 84.5], GLASS_D, w=1)
    E(d, [45, 85, 51, 90], STACK, w=1)


def tu_personnel_transport(d, ink, nat=None):
    """The trooper: a liner taken up from trade -- boat deck lined
    with lifeboats along both rails, two buff funnels."""
    _ship_hull(d, 26, 4, 92, col=HULL, deck=DECK_L)
    R(d, [40, 24, 56, 78], _c(DECK_L, 1.05), w=2)     # superstructure
    L(d, [(48, 26), (48, 76)], _c(DECK_L, 0.85), 1)
    R(d, [42, 28, 54, 34], _c(DECK_L, 1.2), w=1)      # bridge
    R(d, [44, 29, 52, 32], GLASS_D, w=1)
    E(d, [44, 40, 52, 48], STACK, w=2)                # the funnels
    E(d, [44, 56, 52, 64], STACK, w=2)
    # the boats, swung at their davits down both sides
    for yy in (28, 38, 48, 58, 68):
        E(d, [34, yy, 39, yy + 6], _c(WOOD, 1.25), w=1)
        E(d, [57, yy, 62, yy + 6], _c(WOOD, 1.25), w=1)


# ============================================================ BUILDINGS
# Top-down works drawn on TRANSPARENT ground in the map's own sepia,
# so they sit in the terrain like they were surveyed onto it. These
# ignore the ink argument and paint their own colours.

def bd_airfield(d, ink, nat=None):
    """The aerodrome from the air: two grass-crossed runways, the
    dispersal loop, a pair of hangars and the windsock."""
    # the field itself: a translucent grass apron
    E(d, [4, 10, 92, 86], GRASSW, outline=None)
    # crossed runways
    pts = _rot([(14, 42), (82, 42), (82, 54), (14, 54)], 48, 48, 18)
    P(d, pts, TARMAC, outline=TARMAC_D, w=2)
    pts = _rot([(14, 42), (82, 42), (82, 54), (14, 54)], 48, 48, -52)
    P(d, pts, TARMAC, outline=TARMAC_D, w=2)
    for t in (0.25, 0.45, 0.65):        # centreline dashes
        x = 20 + 56 * t
        seg = _rot([(x, 47), (x + 7, 47), (x + 7, 49), (x, 49)],
                   48, 48, 18)
        P(d, seg, _c(CONCRETE, 1.1), outline=None)
    # the dispersal loop off the southern taxiway
    E(d, [56, 62, 84, 84], None, outline=TARMAC_D, w=3)
    E(d, [76, 68, 84, 76], TARMAC, outline=TARMAC_D, w=2)
    # two hangars, gable roofs
    for bx in (10, 30):
        R(d, [bx, 12, bx + 16, 26], ROOF, outline=SKETCH, w=2)
        L(d, [(bx + 8, 12), (bx + 8, 26)], ROOF_L, 2)
        L(d, [(bx, 14), (bx + 16, 14)], ROOF_D, 1)
    R(d, [52, 12, 62, 20], CONCRETE, outline=SKETCH, w=2)  # control hut
    # the windsock on its pole
    L(d, [(88, 20), (88, 30)], SKETCH, 2)
    P(d, [(88, 20), (95, 22), (88, 25)], (196, 120, 60, 255), w=1)


def bd_harbor(d, ink, nat=None):
    """The port from above: the quay wall along the water, two piers
    with a freighter alongside, the crane and its shadow, and the
    warehouses ranked behind."""
    # water wash on the seaward half, ground transparent
    P(d, [(0, 44), (96, 44), (96, 96), (0, 96)], WATERW,
      outline=None)
    # the quay wall and its facing
    R(d, [0, 38, 96, 48], CONCRETE, outline=SKETCH, w=2)
    for x in range(8, 96, 12):
        L(d, [(x, 40), (x, 46)], CONCRETE_D, 1)
    # two piers running out
    R(d, [16, 46, 26, 84], CONCRETE, outline=SKETCH, w=2)
    R(d, [56, 46, 66, 78], CONCRETE, outline=SKETCH, w=2)
    for yy in range(52, 82, 8):
        L(d, [(17.5, yy), (24.5, yy)], CONCRETE_D, 1)
    # the freighter working alongside the west pier
    P(d, [(34, 50), (40, 54), (40, 82), (34, 86), (30, 82),
          (30, 54)], CIVIL, w=2)
    R(d, [32, 58, 38, 66], _c(WOOD, 0.95), w=1)
    R(d, [32, 70, 38, 78], _c(WOOD, 0.95), w=1)
    # the crane on the east pier, jib over the water
    E(d, [58, 52, 64, 58], _c(GUNMETAL, 1.3), w=2)
    L(d, [(61, 55), (74, 64)], GUNMETAL, 2)
    L(d, [(74, 64), (74, 70)], _c(GUNMETAL, 1.4), 1)
    # warehouses ranked along the shore
    for bx in (6, 34, 62):
        R(d, [bx, 18, bx + 24, 34], ROOF, outline=SKETCH, w=2)
        L(d, [(bx + 12, 18), (bx + 12, 34)], ROOF_L, 2)
        L(d, [(bx + 2, 21), (bx + 22, 21)], ROOF_D, 1)
    # bollards along the quay
    for x in (12, 46, 80):
        E(d, [x - 1.5, 42.5, x + 1.5, 45.5], SKETCH, outline=None)


def bd_army_post(d, ink, nat=None):
    """The garrison camp: the earth rampart round it, tent lines,
    the vehicle park, and the colours at the gate."""
    # rampart and ditch, squared with cut corners
    P(d, [(14, 6), (82, 6), (92, 16), (92, 80), (82, 90),
          (14, 90), (4, 80), (4, 16)], None, outline=EARTH, w=6)
    P(d, [(16, 8), (80, 8), (90, 18), (90, 78), (80, 88),
          (16, 88), (6, 78), (6, 18)], None, outline=SKETCH, w=1)
    # tent lines, two companies
    for row, y0 in ((0, 16), (1, 34)):
        for i in range(4):
            bx = 14 + i * 17
            P(d, [(bx, y0 + 10), (bx + 12, y0 + 10), (bx + 6, y0)],
              CANVAS, outline=SKETCH, w=2)
            L(d, [(bx + 6, y0), (bx + 6, y0 + 10)], CANVAS_D, 1)
    # the parade square
    R(d, [16, 56, 46, 82], EARTH, outline=SKETCH, w=1)
    # vehicle park: three lorries nose to the wall
    for i in range(3):
        bx = 56 + i * 11
        R(d, [bx, 60, bx + 8, 74], OD, outline=SKETCH, w=1)
        R(d, [bx + 1, 61, bx + 7, 65], _c(OD, 1.2), w=1)
    # the colours at the gate
    L(d, [(48, 88), (48, 78)], SKETCH, 2)
    P(d, [(48, 78), (58, 80.5), (48, 83)], (172, 44, 36, 255), w=1)


def bd_depot(d, ink, nat=None):
    """The supply dump: crate stacks and drum rows under a thrown
    camouflage net, a lorry lane through the middle."""
    # the net, thrown at an angle over the north half
    pts = _rot([(8, 8), (88, 8), (88, 44), (8, 44)], 48, 26, -6)
    P(d, pts, (96, 92, 62, 90), outline=NET, w=2)
    for i in range(5):
        L(d, [(10 + i * 16, 6), (26 + i * 16, 46)], NET, 1)
        L(d, [(26 + i * 16, 6), (10 + i * 16, 46)], NET, 1)
    # crate stacks beneath and beside it
    for bx, by in ((14, 16), (34, 12), (54, 18), (16, 30), (60, 30)):
        R(d, [bx, by, bx + 14, by + 10], WOOD, outline=SKETCH, w=2)
        L(d, [(bx, by + 5), (bx + 14, by + 5)], _c(WOOD, 0.75), 1)
        L(d, [(bx + 7, by), (bx + 7, by + 10)], _c(WOOD, 0.75), 1)
    # the lane, worked earth
    R(d, [4, 50, 92, 62], EARTH, outline=None)
    # fuel drums ranked on the south side
    for i in range(7):
        bx = 10 + i * 11
        E(d, [bx, 68, bx + 8, 76], _c(GUNMETAL, 1.25),
          outline=SKETCH, w=2)
        E(d, [bx + 2, 70, bx + 6, 74], _c(GUNMETAL, 0.9), w=1)
    for i in range(6):
        bx = 16 + i * 11
        E(d, [bx, 80, bx + 8, 88], _c(GUNMETAL, 1.1),
          outline=SKETCH, w=2)


def bd_bunker(d, ink, nat=None):
    """The strongpoint: a concrete casemate sunk in its earthwork,
    firing notches on three faces and the zigzag trench behind."""
    # the earthwork
    E(d, [8, 12, 88, 84], EARTH, outline=None)
    # the casemate, hexagonal
    P(d, [(30, 22), (66, 22), (80, 48), (66, 74), (30, 74),
          (16, 48)], CONCRETE, outline=SKETCH, w=3)
    P(d, [(36, 30), (60, 30), (70, 48), (60, 66), (36, 66),
          (26, 48)], CONCRETE_D, outline=None)
    R(d, [42, 42, 54, 54], _c(CONCRETE, 0.8), outline=SKETCH, w=2)
    # firing notches on the north faces
    for pts in ([(38, 20), (44, 20), (42, 26), (40, 26)],
                [(52, 20), (58, 20), (56, 26), (54, 26)],
                [(20, 38), (24, 34), (28, 40), (24, 42)],
                [(72, 34), (76, 38), (72, 42), (68, 40)]):
        P(d, pts, INK, outline=None)
    # the trench zigzag to the rear
    L(d, [(48, 74), (42, 82), (54, 86), (48, 94)], SKETCH, 3)


def bd_radar(d, ink, nat=None):
    """The radar station: the mattress array on its gantry, the
    plotting hut, the guy wires, and the sweep drawn faint."""
    # the sweep, a faint arc across the ground
    for r in (30, 38):
        E(d, [48 - r, 48 - r, 48 + r, 48 + r], None,
          outline=(74, 62, 46, 60), w=1)
    L(d, [(48, 48), (86, 26)], (74, 62, 46, 90), 1)
    # guy wires to their anchors
    for ax, ay in ((14, 14), (82, 14), (14, 82), (82, 82)):
        L(d, [(48, 48), (ax, ay)], _c(GUNMETAL, 1.2), 1)
        E(d, [ax - 2, ay - 2, ax + 2, ay + 2], SKETCH, w=1)
    # the gantry and the mattress array, angled
    pts = _rot([(30, 44), (66, 44), (66, 52), (30, 52)], 48, 48, -20)
    P(d, pts, _c(GUNMETAL, 1.35), outline=SKETCH, w=2)
    for i in range(5):
        x = 34 + i * 7
        seg = _rot([(x, 44), (x, 52)], 48, 48, -20)
        L(d, seg, _c(GUNMETAL, 0.8), 1)
    E(d, [44, 44, 52, 52], _c(GUNMETAL, 1.1), outline=SKETCH, w=2)
    # the plotting hut with its cable run
    R(d, [62, 64, 82, 78], ROOF, outline=SKETCH, w=2)
    L(d, [(72, 64), (72, 78)], ROOF_L, 2)
    L(d, [(52, 52), (66, 66)], SKETCH, 1)


def bd_derrick(d, ink, nat=None):
    """The oilfield: the derrick's square lattice from above, the
    pump house, pipe runs and a pair of storage tanks."""
    E(d, [6, 8, 90, 88], EARTH, outline=None)
    # the derrick: nested squares with the X bracing
    R(d, [30, 22, 58, 50], _c(GUNMETAL, 1.15), outline=SKETCH, w=3)
    R(d, [36, 28, 52, 44], None, outline=SKETCH, w=2)
    L(d, [(30, 22), (58, 50)], SKETCH, 2)
    L(d, [(58, 22), (30, 50)], SKETCH, 2)
    E(d, [42, 34, 46, 38], INK, outline=None)          # the wellhead
    # the pump house
    R(d, [14, 58, 34, 74], ROOF, outline=SKETCH, w=2)
    L(d, [(24, 58), (24, 74)], ROOF_L, 2)
    # pipe runs to the tanks
    L(d, [(44, 50), (44, 62), (62, 62)], _c(GUNMETAL, 1.3), 2)
    # the tank farm
    E(d, [58, 54, 74, 70], _c(GUNMETAL, 1.2), outline=SKETCH, w=2)
    E(d, [62, 58, 70, 66], _c(GUNMETAL, 0.95), w=1)
    E(d, [70, 68, 84, 82], _c(GUNMETAL, 1.1), outline=SKETCH, w=2)
    E(d, [74, 72, 80, 78], _c(GUNMETAL, 0.85), w=1)


def bd_foundry(d, ink, nat=None):
    """The steel works: the long shed roofs, the twin stacks with
    their smoke, the ore heaps and the rail spur through the yard."""
    E(d, [4, 10, 92, 88], EARTH, outline=None)
    # two long production sheds, ridged
    for by in (16, 38):
        R(d, [10, by, 62, by + 16], ROOF_D, outline=SKETCH, w=2)
        L(d, [(10, by + 8), (62, by + 8)], ROOF, 2)
        for x in range(16, 60, 8):
            L(d, [(x, by + 1), (x, by + 15)], _c(ROOF_D, 0.8), 1)
    # the stacks, seen as circles, smoke drifting east
    for i, (sx, sy) in enumerate(((70, 22), (78, 30))):
        E(d, [sx - 5, sy - 5, sx + 5, sy + 5], _c(GUNMETAL, 1.1),
          outline=SKETCH, w=2)
        E(d, [sx - 2, sy - 2, sx + 2, sy + 2], INK, outline=None)
        E(d, [sx + 4, sy - 10, sx + 16, sy - 2],
          (120, 116, 110, 70), outline=None)
    # ore heaps
    for hx, hy in ((14, 66), (28, 72), (20, 80)):
        E(d, [hx, hy, hx + 14, hy + 10], (104, 96, 88, 255),
          outline=SKETCH, w=1)
    # the rail spur, curving through the yard
    L(d, [(92, 60), (60, 64), (40, 72), (34, 88)], SKETCH, 2)
    L(d, [(92, 64), (62, 68), (44, 76), (38, 90)], SKETCH, 2)
    for t in (0.15, 0.35, 0.55, 0.75, 0.95):
        x1, y1 = 92 - 58 * t, 60 + 26 * t
        L(d, [(x1, y1 - 2), (x1 - 2, y1 + 5)], SKETCH, 1)


def bd_granary(d, ink, nat=None):
    """The granary: the silo battery, the great barn, and the field
    rows running away from the yard."""
    # field rows, translucent, on two sides
    for i in range(6):
        L(d, [(4, 12 + i * 6), (40, 8 + i * 6)], GRASSW, 3)
    for i in range(6):
        L(d, [(60 + i * 6, 92), (56 + i * 6, 56)], GRASSW, 3)
    # the silo battery: four bins in line
    for i in range(4):
        cx = 18 + i * 15
        E(d, [cx - 6.5, 52, cx + 6.5, 65], CONCRETE,
          outline=SKETCH, w=2)
        E(d, [cx - 3, 55, cx + 3, 61], CONCRETE_D, w=1)
    R(d, [10, 62, 66, 68], CONCRETE_D, outline=SKETCH, w=1)
    # the barn, hipped roof
    R(d, [46, 14, 86, 42], ROOF, outline=SKETCH, w=2)
    L(d, [(50, 28), (82, 28)], ROOF_L, 3)
    L(d, [(46, 14), (50, 28)], ROOF_D, 1)
    L(d, [(86, 14), (82, 28)], ROOF_D, 1)
    L(d, [(46, 42), (50, 28)], ROOF_D, 1)
    L(d, [(86, 42), (82, 28)], ROOF_D, 1)
    # the yard and the cart track
    E(d, [16, 70, 60, 90], EARTH, outline=None)
    L(d, [(38, 90), (30, 70), (28, 52)], (74, 62, 46, 120), 2)


def bd_plantation(d, ink, nat=None):
    """The plantation: tree crowns in their planted grid, the
    estate house and the drying sheds at the corner."""
    for r in range(4):
        for c in range(5):
            cx, cy = 14 + c * 13 + (6 if r % 2 else 0), 16 + r * 14
            E(d, [cx - 5.5, cy - 5.5, cx + 5.5, cy + 5.5],
              (86, 108, 62, 235), outline=(56, 74, 40, 255), w=2)
            E(d, [cx - 2.5, cy - 3.5, cx + 1, cy - 0.5],
              (110, 132, 80, 255), outline=None)
    R(d, [64, 70, 88, 84], ROOF, outline=SKETCH, w=2)
    L(d, [(76, 70), (76, 84)], ROOF_L, 2)
    R(d, [40, 74, 58, 86], ROOF_D, outline=SKETCH, w=2)
    L(d, [(4, 88), (36, 80), (62, 79)], (74, 62, 46, 120), 2)


def bd_bridge_map(d, ink, nat=None):
    """The bridge: the deck slung between its banks, piers in the
    stream, the roadway carried across."""
    # the banks, transparent water between
    P(d, [(0, 0), (34, 0), (26, 96), (0, 96)], EARTH, outline=None)
    P(d, [(66, 0), (96, 0), (96, 96), (58, 96)], EARTH,
      outline=None)
    P(d, [(34, 0), (66, 0), (58, 96), (26, 96)], WATERW,
      outline=None)
    # the deck
    P(d, [(24, 40), (72, 40), (70, 56), (22, 56)], CONCRETE,
      outline=SKETCH, w=3)
    L(d, [(24, 48), (71, 48)], CONCRETE_D, 1)
    # piers showing either side of the deck
    for px in (38, 56):
        E(d, [px - 4, 34, px + 4, 40], CONCRETE_D, outline=SKETCH,
          w=1)
        E(d, [px - 4, 56, px + 4, 62], CONCRETE_D, outline=SKETCH,
          w=1)
    # the road running onto it
    P(d, [(6, 42), (24, 42), (22, 54), (2, 54)], TARMAC,
      outline=None)
    P(d, [(72, 42), (92, 40), (94, 52), (70, 54)], TARMAC,
      outline=None)


def bd_city(d, ink, nat=None):
    """A town from the survey: the block plan round its square."""
    R(d, [40, 40, 56, 56], EARTH, outline=SKETCH, w=1)
    for bx, by, bw, bh in ((12, 12, 20, 12), (38, 10, 22, 12),
                           (66, 14, 18, 12), (10, 30, 16, 14),
                           (64, 32, 22, 12), (12, 50, 18, 14),
                           (66, 50, 20, 14), (14, 70, 22, 12),
                           (42, 68, 18, 14), (66, 70, 18, 12)):
        R(d, [bx, by, bx + bw, by + bh], ROOF, outline=SKETCH, w=1)
        L(d, [(bx + bw / 2, by), (bx + bw / 2, by + bh)], ROOF_D, 1)
    L(d, [(4, 26), (92, 24)], SKETCH, 1)
    L(d, [(6, 64), (90, 66)], SKETCH, 1)
    L(d, [(34, 4), (36, 92)], SKETCH, 1)
    L(d, [(62, 6), (60, 90)], SKETCH, 1)


def bd_capital(d, ink, nat=None):
    """The capital: the same survey, with the citadel star at its
    heart."""
    bd_city(d, ink, nat)
    pts = []
    for i in range(8):
        a = math.pi * i / 4 - math.pi / 2
        r1, r2 = 12, 5.5
        pts.append((48 + r1 * math.cos(a), 48 + r1 * math.sin(a)))
        pts.append((48 + r2 * math.cos(a + math.pi / 8),
                    48 + r2 * math.sin(a + math.pi / 8)))
    P(d, pts, CONCRETE, outline=SKETCH, w=2)


# ============================================================== BUTTONS
# The console pictograms: printer's ink on the key face. These DO
# honour the ink argument, so the red alert variants come free.

def _tone(ink, a):
    return (ink[0], ink[1], ink[2], a)


def ub_tax(d, ink, nat=None):
    """The exchequer: coin columns on the ledger, the note under."""
    P(d, [(14, 62), (82, 62), (78, 84), (18, 84)], _tone(ink, 70),
      outline=ink, w=2)
    L(d, [(24, 70), (72, 70)], _tone(ink, 130), 2)
    L(d, [(24, 76), (64, 76)], _tone(ink, 130), 2)
    for cx, n in ((28, 4), (48, 6), (68, 3)):
        for i in range(n):
            E(d, [cx - 9, 52 - i * 7, cx + 9, 60 - i * 7],
              _tone(ink, 90), outline=ink, w=2)
    E(d, [39, 14, 57, 32], _tone(ink, 60), outline=ink, w=3)
    L(d, [(48, 17), (48, 29)], ink, 2)
    L(d, [(44, 20), (52, 20)], ink, 2)
    L(d, [(44, 26), (52, 26)], ink, 2)


def ub_enlist(d, ink, nat=None):
    """The recruiting office: the soldier marching off the poster,
    rifle at the slope."""
    E(d, [40, 6, 56, 22], _tone(ink, 110), outline=ink, w=3)
    L(d, [(38, 14), (58, 14)], ink, 3)              # the brim
    P(d, [(36, 26), (60, 26), (58, 56), (38, 56)], _tone(ink, 90),
      outline=ink, w=3)
    L(d, [(38, 56), (30, 86)], ink, 6)              # the stride
    L(d, [(58, 56), (66, 86)], ink, 6)
    L(d, [(28, 84), (36, 88)], ink, 3)              # the boots
    L(d, [(64, 84), (72, 88)], ink, 3)
    L(d, [(60, 30), (72, 44)], ink, 4)              # the near arm
    # the rifle at the slope over the far shoulder
    L(d, [(30, 48), (52, 4)], _tone(ink, 170), 4)
    R(d, [26, 44, 36, 52], _tone(ink, 110), outline=ink, w=2)


def ub_factory(d, ink, nat=None):
    """War industries: the sawtooth shed, the tall stack working."""
    P(d, [(10, 46), (10, 84), (86, 84), (86, 46), (66, 58),
          (66, 46), (46, 58), (46, 46), (26, 58), (26, 46)],
      _tone(ink, 90), outline=ink, w=3)
    R(d, [70, 16, 80, 48], _tone(ink, 110), outline=ink, w=3)
    for cy in (10, 4):
        E(d, [66 - (10 - cy), cy, 84, cy + 8], _tone(ink, 45),
          outline=None)
    for bx in (18, 38, 58):
        R(d, [bx, 66, bx + 12, 76], _tone(ink, 55), outline=ink, w=2)


def ub_resource(d, ink, nat=None):
    """The quartermaster's stores: drum, ingot and the wheat sheaf
    -- oil, steel, food on one shelf."""
    E(d, [10, 30, 38, 42], _tone(ink, 80), outline=ink, w=3)
    R(d, [10, 36, 38, 74], _tone(ink, 80), outline=ink, w=3)
    E(d, [10, 68, 38, 80], _tone(ink, 80), outline=ink, w=3)
    L(d, [(14, 40), (14, 70)], _tone(ink, 140), 2)
    P(d, [(44, 62), (70, 54), (86, 62), (60, 70)], _tone(ink, 110),
      outline=ink, w=3)                          # the ingot
    P(d, [(44, 70), (70, 62), (86, 70), (60, 78)], _tone(ink, 90),
      outline=ink, w=3)
    for i in range(3):                           # the sheaf
        L(d, [(56 + i * 8, 40), (62 + i * 8, 14)], ink, 3)
        E(d, [59 + i * 8, 10, 66 + i * 8, 20], _tone(ink, 90),
          outline=ink, w=2)
    L(d, [(58, 34), (80, 26)], ink, 2)           # the binding


def ub_research(d, ink, nat=None):
    """The laboratories: the flask at work over the branching
    chart."""
    L(d, [(40, 10), (40, 34)], ink, 4)
    L(d, [(56, 10), (56, 34)], ink, 4)
    L(d, [(34, 10), (62, 10)], ink, 4)
    P(d, [(40, 34), (56, 34), (72, 66), (24, 66)], _tone(ink, 70),
      outline=ink, w=3)
    L(d, [(31, 56), (65, 56)], ink, 2)
    E(d, [42, 44, 48, 50], _tone(ink, 140), outline=None)
    E(d, [50, 48, 54, 52], _tone(ink, 120), outline=None)
    L(d, [(48, 66), (48, 76)], ink, 3)           # the chart below
    L(d, [(28, 76), (68, 76)], ink, 3)
    L(d, [(28, 76), (28, 86)], ink, 3)
    L(d, [(68, 76), (68, 86)], ink, 3)
    E(d, [24, 84, 32, 92], _tone(ink, 90), outline=ink, w=2)
    E(d, [64, 84, 72, 92], _tone(ink, 90), outline=ink, w=2)


def ub_diplomacy(d, ink, nat=None):
    """The foreign office: two standards crossed over the treaty,
    its seal and ribbon at the foot."""
    for sgn in (1, -1):
        x0, x1 = 48 - sgn * 30, 48 + sgn * 24
        L(d, [(x0, 12), (x1, 62)], ink, 4)
        # the standard, flown square from the head of its staff
        P(d, [(x0, 12), (x0 + sgn * 24, 16), (x0 + sgn * 22, 30),
              (x0 - sgn * 2, 26)], _tone(ink, 110), outline=ink,
          w=2)
        L(d, [(x0 + sgn * 4, 15), (x0 + sgn * 5, 27)],
          _tone(ink, 170), 2)
    R(d, [30, 60, 66, 84], _tone(ink, 60), outline=ink, w=3)
    L(d, [(36, 67), (60, 67)], _tone(ink, 150), 2)
    L(d, [(36, 73), (54, 73)], _tone(ink, 150), 2)
    E(d, [58, 74, 68, 84], _tone(ink, 170), outline=ink, w=2)
    L(d, [(63, 84), (60, 92)], ink, 2)
    L(d, [(63, 84), (68, 92)], ink, 2)


def ub_repair(d, ink, nat=None):
    """Field workshops: the open-end spanner crossed with the
    engineer's hammer."""
    # the spanner, jaws open at the head
    L(d, [(26, 74), (66, 34)], ink, 7)
    P(d, [(60, 20), (72, 14), (80, 22), (74, 34), (78, 40),
          (66, 44), (58, 36), (64, 26)], _tone(ink, 110),
      outline=ink, w=3)
    P(d, [(70, 22), (76, 28), (70, 34), (64, 28)], (0, 0, 0, 0),
      outline=ink, w=2)
    P(d, [(18, 66), (30, 70), (28, 84), (14, 80)], _tone(ink, 90),
      outline=ink, w=3)
    # the hammer across it
    L(d, [(24, 26), (64, 70)], ink, 5)
    P(d, [(12, 12), (34, 16), (32, 30), (16, 30)], _tone(ink, 130),
      outline=ink, w=3)


def ub_info(d, ink, nat=None):
    """The briefing: a print 'i' in its ring."""
    E(d, [14, 14, 82, 82], None, outline=ink, w=5)
    E(d, [42, 24, 54, 36], ink, outline=None)
    R(d, [43, 42, 53, 68], ink, w=1)
    L(d, [(38, 42), (52, 42)], ink, 4)
    L(d, [(38, 68), (58, 68)], ink, 4)


def ub_demolish(d, ink, nat=None):
    """Demolitions: the plunger box, the cable, the charge going
    up."""
    R(d, [12, 52, 40, 80], _tone(ink, 90), outline=ink, w=3)
    L(d, [(26, 52), (26, 38)], ink, 4)
    L(d, [(16, 38), (36, 38)], ink, 5)
    L(d, [(40, 66), (58, 70), (66, 62)], ink, 2)     # the cable
    for a in range(8):                                # the burst
        ang = math.pi * a / 4
        L(d, [(72 + 8 * math.cos(ang), 34 + 8 * math.sin(ang)),
              (72 + 18 * math.cos(ang), 34 + 18 * math.sin(ang))],
          ink, 3)
    E(d, [66, 28, 78, 40], _tone(ink, 130), outline=ink, w=2)


def ub_scramble(d, ink, nat=None):
    """Scramble: the flight climbing away, echeloned."""
    for i, (ox, oy, s) in enumerate(((0, 0, 1.0), (-22, 18, 0.8),
                                     (20, 22, 0.7))):
        cx, cy = 54 + ox, 34 + oy
        P(d, [(cx, cy - 16 * s), (cx - 14 * s, cy + 6 * s),
              (cx - 4 * s, cy + 2 * s), (cx, cy + 12 * s),
              (cx + 4 * s, cy + 2 * s), (cx + 14 * s, cy + 6 * s)],
          _tone(ink, 110 if i == 0 else 70), outline=ink, w=2)
    L(d, [(20, 84), (36, 68)], ink, 4)
    P(d, [(36, 76), (36, 60), (44, 68)], ink, w=1)


def ub_paradrop(d, ink, nat=None):
    """The drop: canopy full, the crate swinging under."""
    P(d, [(16, 38), (24, 20), (48, 10), (72, 20), (80, 38)],
      _tone(ink, 80), outline=ink, w=3)
    for x in (28, 48, 68):
        L(d, [(x, 16 if x == 48 else 24), (x, 38)],
          _tone(ink, 120), 1)
    for x0, x1 in ((18, 40), (78, 56), (30, 44), (66, 52)):
        L(d, [(x0, 38), (x1, 62)], ink, 2)
    R(d, [38, 62, 58, 82], _tone(ink, 90), outline=ink, w=3)
    L(d, [(38, 72), (58, 72)], ink, 2)
    L(d, [(48, 62), (48, 82)], ink, 2)


def _sub_profile(d, ink):
    P(d, [(8, 52), (24, 44), (72, 44), (88, 50), (72, 60),
          (24, 60)], _tone(ink, 90), outline=ink, w=3)
    R(d, [40, 32, 56, 44], _tone(ink, 110), outline=ink, w=2)
    L(d, [(50, 32), (50, 24)], ink, 2)


def ub_submerge(d, ink, nat=None):
    """Dive: the boat and the chevrons taking her down."""
    _sub_profile(d, ink)
    for i in range(2):
        yy = 68 + i * 10
        P(d, [(38, yy), (48, yy + 8), (58, yy)], (0, 0, 0, 0),
          outline=ink, w=4)


def ub_surface(d, ink, nat=None):
    """Surface: the boat and the chevrons bringing her up."""
    _sub_profile(d, ink)
    for i in range(2):
        yy = 76 - i * 10 + 8
        P(d, [(38, yy), (48, yy - 8), (58, yy)], (0, 0, 0, 0),
          outline=ink, w=4)


def _blimp_profile(d, ink):
    E(d, [14, 30, 74, 58], _tone(ink, 90), outline=ink, w=3)
    P(d, [(70, 36), (86, 30), (86, 44)], _tone(ink, 70),
      outline=ink, w=2)
    P(d, [(70, 52), (86, 58), (86, 44)], _tone(ink, 70),
      outline=ink, w=2)
    R(d, [38, 58, 52, 66], _tone(ink, 110), outline=ink, w=2)


def ub_blimp_raise(d, ink, nat=None):
    _blimp_profile(d, ink)
    L(d, [(24, 88), (24, 70)], ink, 5)
    P(d, [(16, 76), (24, 66), (32, 76)], ink, w=1)


def ub_blimp_lower(d, ink, nat=None):
    _blimp_profile(d, ink)
    L(d, [(24, 68), (24, 86)], ink, 5)
    P(d, [(16, 80), (24, 90), (32, 80)], ink, w=1)


def ub_unload(d, ink, nat=None):
    """Disembark: the crate swung ashore over the ship's side."""
    P(d, [(8, 66), (56, 66), (52, 84), (12, 84)], _tone(ink, 90),
      outline=ink, w=3)
    L(d, [(14, 66), (18, 58)], ink, 2)
    L(d, [(50, 66), (46, 58)], ink, 2)
    L(d, [(30, 58), (30, 22)], ink, 3)               # the derrick
    L(d, [(30, 22), (68, 22)], ink, 3)
    L(d, [(68, 22), (68, 34)], _tone(ink, 130), 2)
    R(d, [58, 34, 78, 52], _tone(ink, 90), outline=ink, w=3)
    L(d, [(58, 43), (78, 43)], ink, 2)
    P(d, [(62, 58), (68, 64), (74, 58)], ink, w=1)


def ub_road(d, ink, nat=None):
    """Road works: the way running to the horizon, the shovel
    standing in the verge."""
    P(d, [(34, 88), (44, 12), (52, 12), (62, 88)], _tone(ink, 90),
      outline=ink, w=3)
    for t in (0.2, 0.45, 0.7):
        y = 84 - t * 64
        w2 = 2.4 - t * 1.2
        R(d, [47 - w2, y - 5, 49 + w2, y], _tone(ink, 160),
          outline=None)
    L(d, [(74, 40), (74, 74)], ink, 4)               # the shovel
    P(d, [(68, 74), (80, 74), (78, 88), (70, 88)], _tone(ink, 110),
      outline=ink, w=2)
    L(d, [(68, 40), (80, 40)], ink, 3)


def ub_rail(d, ink, nat=None):
    """Rail works: the permanent way, sleepered and spiked."""
    L(d, [(30, 8), (22, 88)], ink, 4)
    L(d, [(66, 8), (74, 88)], ink, 4)
    for i in range(7):
        t = i / 6.0
        y = 12 + t * 70
        x0, x1 = 30 - t * 8, 66 + t * 8
        L(d, [(x0 - 4, y), (x1 + 4, y)], _tone(ink, 150), 4)


def ub_nosupply(d, ink, nat=None):
    """Stores out: the jerrican upended and empty."""
    P(d, [(28, 20), (68, 20), (72, 30), (72, 82), (24, 82),
          (24, 30)], _tone(ink, 80), outline=ink, w=3)
    L(d, [(36, 20), (36, 12)], ink, 4)
    L(d, [(36, 12), (52, 12)], ink, 4)
    L(d, [(32, 34), (64, 72)], ink, 5)
    L(d, [(64, 34), (32, 72)], ink, 5)
    for i in range(3):
        E(d, [76, 62 + i * 9, 82, 68 + i * 9], _tone(ink, 90),
          outline=ink, w=2)


def ub_swords(d, ink, nat=None):
    """War: the sabres crossed."""
    for sgn in (1, -1):
        cx = 48
        x0, x1 = cx - sgn * 34, cx + sgn * 30
        L(d, [(x0, 14), (x1, 78)], ink, 5)
        L(d, [(x0 - sgn * 2, 16), (x0 + sgn * 8, 24)],
          _tone(ink, 150), 2)
        L(d, [(x1 - sgn * 12, 66), (x1 + sgn * 6, 84)], ink, 7)
        L(d, [(x1 - sgn * 16, 76), (x1 + sgn * 12, 70)], ink, 4)


def cu_default(d, ink, nat=None):
    """The pointer."""
    P(d, [(20, 8), (20, 74), (38, 58), (50, 86), (60, 80),
          (48, 54), (70, 54)], (240, 236, 224, 255), outline=INK,
      w=3)


def cu_attack(d, ink, nat=None):
    cu_default(d, ink, nat)
    for a in range(8):
        ang = math.pi * a / 4
        L(d, [(74 + 7 * math.cos(ang), 26 + 7 * math.sin(ang)),
              (74 + 15 * math.cos(ang), 26 + 15 * math.sin(ang))],
          (172, 44, 36, 255), 3)
    E(d, [69, 21, 79, 31], (172, 44, 36, 255), outline=INK, w=2)


def cu_embark(d, ink, nat=None):
    cu_default(d, ink, nat)
    P(d, [(58, 20), (90, 20), (84, 32), (64, 32)],
      (240, 236, 224, 255), outline=INK, w=2)
    L(d, [(74, 20), (74, 10)], INK, 2)
    P(d, [(66, 14), (74, 6), (82, 14)], INK, w=1)


def cu_disembark(d, ink, nat=None):
    cu_default(d, ink, nat)
    P(d, [(58, 10), (90, 10), (84, 22), (64, 22)],
      (240, 236, 224, 255), outline=INK, w=2)
    L(d, [(74, 24), (74, 34)], INK, 2)
    P(d, [(66, 30), (74, 38), (82, 30)], INK, w=1)
