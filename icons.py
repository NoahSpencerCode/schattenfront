"""
Procedurally drawn unit icons — small pictogram images, one per unit
type, generated with PIL on first run into assets/icons/.

Each icon is drawn in two variants: "dark" ink for light faction
counters, "light" ink for dark ones.  Replace any generated PNG with
your own art (same filename) and it will be used instead.
"""

import os

from PIL import Image, ImageDraw

ICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "assets", "icons")
SIZE = 96
INK_DARK = (32, 26, 20, 255)
INK_LIGHT = (235, 229, 205, 255)
INK_RED = (200, 30, 20, 255)

_INKS = {'dark': INK_DARK, 'light': INK_LIGHT, 'red': INK_RED}

_W = 5  # default stroke width


def _ship_hull(d, ink, y=60, bow=88, stern=8, depth=16):
    d.polygon([(stern, y), (bow, y), (bow - 14, y + depth),
               (stern + 8, y + depth)], fill=ink)


def _plane(d, ink, wing_span=76, wing_y=44, wing_chord=13, nose=14,
           tail=84, body_w=9, tail_span=30):
    cx = SIZE // 2
    d.rectangle([cx - body_w // 2, nose, cx + body_w // 2, tail], fill=ink)
    d.rectangle([cx - wing_span // 2, wing_y,
                 cx + wing_span // 2, wing_y + wing_chord], fill=ink)
    d.rectangle([cx - tail_span // 2, tail - 10, cx + tail_span // 2,
                 tail - 2], fill=ink)
    d.ellipse([cx - body_w // 2 - 1, nose - 8, cx + body_w // 2 + 1,
               nose + 6], fill=ink)


def _flag(d, ink, x=64, top=14, h=46):
    d.line([(x, top), (x, top + h)], fill=ink, width=4)
    d.polygon([(x, top), (x + 24, top + 8), (x, top + 16)], fill=ink)


def _wheels(d, ink, y=70, xs=(24, 44, 68), r=7):
    for x in xs:
        d.ellipse([x - r, y - r, x + r, y + r], fill=ink)


# ------------------------------------------------------------ unit icons

def _draw_infantry(d, ink):
    d.rectangle([14, 24, 82, 72], outline=ink, width=_W)
    d.line([(14, 24), (82, 72)], fill=ink, width=_W)
    d.line([(82, 24), (14, 72)], fill=ink, width=_W)


def _draw_tank(d, ink):
    d.ellipse([12, 48, 84, 78], fill=ink)                     # tracks
    d.rectangle([30, 34, 66, 52], fill=ink)                   # turret
    d.rectangle([62, 38, 92, 44], fill=ink)                   # barrel


def _draw_supply_truck(d, ink):
    d.rectangle([14, 38, 58, 64], outline=ink, width=_W)      # cargo box
    d.line([(36, 38), (36, 64)], fill=ink, width=3)
    d.polygon([(58, 44), (80, 44), (86, 56), (86, 64), (58, 64)], fill=ink)
    _wheels(d, ink)


def _draw_transport_truck(d, ink):
    d.pieslice([12, 30, 60, 78], 180, 360, fill=ink)          # canopy
    d.polygon([(58, 44), (80, 44), (86, 56), (86, 64), (58, 64)], fill=ink)
    _wheels(d, ink)


def _draw_aa_artillery(d, ink):
    d.rectangle([34, 62, 62, 74], fill=ink)                   # mount
    d.line([(48, 66), (24, 18)], fill=ink, width=6)           # twin guns
    d.line([(48, 66), (72, 18)], fill=ink, width=6)
    d.ellipse([40, 58, 56, 74], fill=ink)


def _draw_army_command(d, ink):
    _flag(d, ink, x=40)
    d.rectangle([24, 62, 74, 74], fill=ink)                   # HQ bar


def _draw_engineer(d, ink):
    # compact centred bridge-works glyph (fits the round counter)
    d.line([(24, 42), (72, 42)], fill=ink, width=6)           # beam
    d.line([(28, 42), (42, 60)], fill=ink, width=5)
    d.line([(42, 42), (28, 60)], fill=ink, width=5)           # truss X
    d.line([(54, 42), (68, 60)], fill=ink, width=5)
    d.line([(68, 42), (54, 60)], fill=ink, width=5)
    d.rectangle([24, 58, 72, 64], fill=ink)


def _draw_naval_command(d, ink):
    _ship_hull(d, ink)
    _flag(d, ink, x=48, top=18, h=42)


def _draw_personnel_transport(d, ink):
    _ship_hull(d, ink)
    for x in (30, 46, 62):
        d.ellipse([x - 5, 36, x + 5, 46], fill=ink)           # embarked troops
        d.rectangle([x - 7, 46, x + 7, 58], fill=ink)


def _draw_destroyer_sea_sea(d, ink):
    _ship_hull(d, ink)
    d.rectangle([38, 44, 60, 58], fill=ink)                   # turret
    d.line([(58, 48), (86, 40)], fill=ink, width=5)           # gun


def _draw_destroyer_aa(d, ink):
    _ship_hull(d, ink)
    d.line([(48, 56), (30, 20)], fill=ink, width=5)
    d.line([(48, 56), (66, 20)], fill=ink, width=5)           # AA guns up


def _draw_destroyer_sea_land(d, ink):
    _ship_hull(d, ink)
    d.line([(40, 52), (76, 22)], fill=ink, width=5)           # shore arc
    d.polygon([(76, 22), (62, 24), (72, 36)], fill=ink)       # arrowhead


def _draw_aircraft_carrier(d, ink):
    d.polygon([(6, 46), (90, 46), (78, 66), (14, 66)], fill=ink)
    d.line([(12, 42), (84, 42)], fill=ink, width=4)           # flight deck
    d.rectangle([62, 26, 74, 42], fill=ink)                   # island


def _draw_fighter(d, ink):
    _plane(d, ink, wing_span=72, wing_y=40, wing_chord=11, tail=80)


def _draw_bomber(d, ink):
    _plane(d, ink, wing_span=86, wing_y=42, wing_chord=14, tail=86,
           body_w=11, tail_span=38)
    d.ellipse([22, 40, 34, 58], fill=ink)                     # engines
    d.ellipse([62, 40, 74, 58], fill=ink)


def _draw_airforce_command(d, ink):
    _plane(d, ink, wing_span=66, wing_y=44, wing_chord=11, tail=80)
    _flag(d, ink, x=16, top=14, h=36)


def _draw_transport_air(d, ink):
    _plane(d, ink, wing_span=80, wing_y=36, wing_chord=12, tail=64,
           body_w=10)
    d.arc([28, 62, 68, 92], 180, 360, fill=ink, width=5)      # parachute
    d.line([(32, 78), (48, 92)], fill=ink, width=3)
    d.line([(64, 78), (48, 92)], fill=ink, width=3)


# ------------------------------------------------------------ map symbols
# The city icons are drawn white with a black outline: tinting the
# texture with the faction colour paints the buildings while the
# outline stays black.

_WHITE = (255, 255, 255, 255)
_BLACK = (14, 12, 10, 255)


def _building(d, x0, y0, x1, y1):
    d.rectangle([x0, y0, x1, y1], fill=_WHITE, outline=_BLACK, width=4)


def _draw_city(d, ink):
    _building(d, 10, 44, 34, 86)
    _building(d, 30, 24, 56, 86)
    _building(d, 52, 52, 74, 86)
    _building(d, 70, 36, 88, 86)
    d.rectangle([6, 84, 92, 90], fill=_BLACK)
    # windows
    for bx in (18, 40, 60, 76):
        for wy in (58, 70):
            d.rectangle([bx, wy, bx + 6, wy + 6], fill=_BLACK)
    d.rectangle([38, 34, 44, 40], fill=_BLACK)
    d.rectangle([38, 46, 44, 52], fill=_BLACK)


def _draw_capital(d, ink):
    _draw_city(d, ink)
    # star over the capital
    import math as _m
    cx, cy, r1, r2 = 48, 12, 11, 4.5
    pts = []
    for i in range(10):
        r = r1 if i % 2 == 0 else r2
        a = -_m.pi / 2 + i * _m.pi / 5
        pts.append((cx + r * _m.cos(a), cy + r * _m.sin(a)))
    d.polygon(pts, fill=_WHITE, outline=_BLACK)


def _draw_airfield(d, ink):
    """ATC tower: tapered shaft, control cab, antenna."""
    _building(d, 38, 40, 58, 88)                              # shaft
    d.polygon([(26, 26), (70, 26), (64, 46), (32, 46)],
              fill=_WHITE, outline=_BLACK)                    # cab
    d.line([(48, 26), (48, 8)], fill=_BLACK, width=4)         # mast
    d.ellipse([44, 4, 52, 12], fill=_BLACK)
    d.rectangle([16, 86, 80, 92], fill=_BLACK)                # apron
    d.rectangle([34, 32, 62, 40], fill=_BLACK)                # cab glass


def _draw_depot(d, ink):
    """Stacked supply crates."""
    for (x0, y0) in ((16, 52), (52, 52), (34, 20)):
        d.rectangle([x0, y0, x0 + 30, y0 + 30], fill=_WHITE,
                    outline=_BLACK, width=4)
        d.line([(x0, y0), (x0 + 30, y0 + 30)], fill=_BLACK, width=3)
        d.line([(x0 + 30, y0), (x0, y0 + 30)], fill=_BLACK, width=3)
    d.rectangle([10, 84, 86, 90], fill=_BLACK)


def _draw_bunker(d, ink):
    """Concrete dome with a firing slit."""
    d.pieslice([14, 30, 82, 92], 180, 360, fill=_WHITE, outline=_BLACK)
    d.rectangle([30, 52, 66, 60], fill=_BLACK)                # slit
    d.rectangle([10, 84, 86, 90], fill=_BLACK)


def _draw_supply_ship(d, ink):
    _ship_hull(d, ink)
    for x0 in (26, 50):
        d.rectangle([x0, 34, x0 + 20, 54], fill=ink)
        d.line([(x0, 34), (x0 + 20, 54)], fill=(0, 0, 0, 0), width=2)
    d.line([(40, 20), (40, 54)], fill=ink, width=4)           # crane
    d.line([(40, 20), (62, 30)], fill=ink, width=3)


def _draw_nosupply(d, ink):
    """Empty jerrycan warning (drawn in the requested ink colour)."""
    d.rectangle([26, 26, 70, 84], outline=ink, width=6)
    d.rectangle([34, 14, 50, 26], fill=ink)
    d.line([(32, 78), (64, 32)], fill=ink, width=6)


def _draw_bridge_map(d, ink):
    """Top-down bridge for the map: flared abutments, deck, girders.
    Drawn tall (deck runs vertically = along the road)."""
    d.polygon([(18, 4), (78, 4), (62, 18), (34, 18)], fill=_BLACK)
    d.polygon([(18, 92), (78, 92), (62, 78), (34, 78)], fill=_BLACK)
    d.rectangle([32, 14, 64, 82], fill=(122, 96, 62, 255),
                outline=_BLACK, width=3)
    for y in (28, 42, 56, 70):
        d.line([(34, y), (62, y)], fill=_BLACK, width=3)      # girders
    d.line([(48, 18), (48, 78)], fill=(235, 229, 205, 255), width=2)


def _draw_cursor_default(d, ink):
    """The pointer: a draughtsman's wing dividers (the measuring
    compass used to step off distances on a chart), in shiny silver."""
    silver = (176, 182, 190, 255)      # polished steel body
    shine = (244, 247, 250, 255)       # specular highlight
    dk = (44, 48, 54, 255)             # dark steel edge
    piv = (48, 12)
    lpt = (26, 88)
    rpt = (70, 88)
    # the curved 'wing' arc joining the legs, with its thumbscrew
    d.arc([24, 46, 72, 84], 18, 162, fill=dk, width=9)
    d.arc([26, 48, 70, 82], 18, 162, fill=silver, width=4)
    d.arc([27, 49, 69, 81], 30, 110, fill=shine, width=2)
    # the two legs (dark border, silver over, bright highlight streak)
    for pt in (lpt, rpt):
        d.line([piv, pt], fill=dk, width=10)
    for pt in (lpt, rpt):
        d.line([piv, pt], fill=silver, width=5)
    for pt in (lpt, rpt):
        d.line([(piv[0], piv[1] + 2), (pt[0], pt[1] - 2)],
               fill=shine, width=1)
    # sharp steel points
    d.polygon([(lpt[0] - 6, lpt[1] - 10), (lpt[0] + 6, lpt[1] - 10),
               (lpt[0] - 1, lpt[1] + 2)], fill=dk)
    d.polygon([(rpt[0] - 6, rpt[1] - 10), (rpt[0] + 6, rpt[1] - 10),
               (rpt[0] + 1, rpt[1] + 2)], fill=dk)
    # thumbscrew nut on the wing
    d.ellipse([41, 56, 55, 70], fill=dk)
    d.ellipse([43, 58, 53, 68], fill=silver)
    d.ellipse([45, 59, 49, 63], fill=shine)
    # pivot head at the top
    d.ellipse([piv[0] - 9, piv[1] - 9, piv[0] + 9, piv[1] + 9], fill=dk)
    d.ellipse([piv[0] - 5, piv[1] - 5, piv[0] + 5, piv[1] + 5], fill=silver)
    d.ellipse([piv[0] - 3, piv[1] - 3, piv[0], piv[1]], fill=shine)


def _draw_cursor_attack(d, ink):
    """Red gunsight -- the pointer itself over a valid target."""
    red = (205, 30, 20, 255)
    dk = (60, 8, 6, 255)
    cx = cy = 48
    d.ellipse([20, 20, 76, 76], outline=dk, width=8)
    d.ellipse([22, 22, 74, 74], outline=red, width=5)
    for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        d.line([(cx + dx * 8, cy + dy * 8), (cx + dx * 34, cy + dy * 34)],
               fill=dk, width=8)
        d.line([(cx + dx * 8, cy + dy * 8), (cx + dx * 32, cy + dy * 32)],
               fill=red, width=4)
    d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=red)


def _draw_cursor_embark(d, ink):
    """Loading a transport: down-arrow into an open hold."""
    pale = (240, 236, 220, 255)
    dk = (38, 30, 22, 255)
    grn = (40, 145, 55, 255)
    d.rectangle([26, 54, 70, 86], fill=pale, outline=dk, width=4)
    d.rectangle([26, 54, 70, 60], fill=dk)                    # deck lip
    d.line([(48, 8), (48, 44)], fill=dk, width=10)
    d.line([(48, 8), (48, 44)], fill=grn, width=6)
    d.polygon([(48, 52), (32, 32), (64, 32)], fill=dk)
    d.polygon([(48, 49), (35, 34), (61, 34)], fill=grn)       # arrow down


def _draw_cursor_disembark(d, ink):
    """Unloading a transport: up-arrow out of a hold."""
    pale = (240, 236, 220, 255)
    dk = (38, 30, 22, 255)
    org = (214, 132, 30, 255)
    d.rectangle([26, 54, 70, 86], fill=pale, outline=dk, width=4)
    d.rectangle([26, 54, 70, 60], fill=dk)
    d.line([(48, 50), (48, 14)], fill=dk, width=10)
    d.line([(48, 50), (48, 14)], fill=org, width=6)
    d.polygon([(48, 6), (32, 26), (64, 26)], fill=dk)
    d.polygon([(48, 9), (35, 24), (61, 24)], fill=org)        # arrow up


def _draw_info_button(d, ink):
    """A brass/parchment rounded-square button bearing an 'i' -- used
    for the unit-briefing control (drawn full-colour, ink ignored)."""
    d.rounded_rectangle([5, 5, 90, 90], radius=22,
                        fill=(216, 205, 168, 255),
                        outline=(54, 44, 34, 255), width=6)
    col = (44, 35, 26, 255)
    d.ellipse([41, 22, 55, 36], fill=col)                     # the dot
    d.rounded_rectangle([42, 44, 54, 76], radius=4, fill=col)  # the stem
    d.rectangle([37, 44, 59, 50], fill=col)                   # serif top
    d.rectangle([35, 70, 61, 77], fill=col)                   # serif base


_DRAWERS = {
    'city': _draw_city,
    'capital': _draw_capital,
    'airfield': _draw_airfield,
    'depot': _draw_depot,
    'bunker': _draw_bunker,
    'nosupply': _draw_nosupply,
    'bridge_map': _draw_bridge_map,
    'info_button': _draw_info_button,
    'cursor_default': _draw_cursor_default,
    'cursor_attack': _draw_cursor_attack,
    'cursor_embark': _draw_cursor_embark,
    'cursor_disembark': _draw_cursor_disembark,
    'supply_ship': _draw_supply_ship,
    'infantry': _draw_infantry,
    'tank': _draw_tank,
    'supply_truck': _draw_supply_truck,
    'transport_truck': _draw_transport_truck,
    'aa_artillery': _draw_aa_artillery,
    'army_command': _draw_army_command,
    'engineer': _draw_engineer,
    'naval_command': _draw_naval_command,
    'personnel_transport': _draw_personnel_transport,
    'destroyer_sea_sea': _draw_destroyer_sea_sea,
    'destroyer_aa': _draw_destroyer_aa,
    'destroyer_sea_land': _draw_destroyer_sea_land,
    'aircraft_carrier': _draw_aircraft_carrier,
    'fighter': _draw_fighter,
    'bomber': _draw_bomber,
    'airforce_command': _draw_airforce_command,
    'transport_air': _draw_transport_air,
}




# ------------------------------------------------- top-down unit sprites
# White fill + black outline: tinted with the faction colour at runtime
# (black outlines survive tinting).  Drawn nose-up: +Y is the direction
# of travel.

def _o(d, pts):
    d.polygon(pts, fill=_WHITE, outline=_BLACK)


def _orect(d, x0, y0, x1, y1, w=3):
    d.rectangle([x0, y0, x1, y1], fill=_WHITE, outline=_BLACK, width=w)


def _hull_top(d, bow=6, stern=90, half=13):
    cx = 48
    _o(d, [(cx, bow), (cx + half, bow + 18), (cx + half, stern - 6),
           (cx + half - 5, stern), (cx - half + 5, stern),
           (cx - half, stern - 6), (cx - half, bow + 18)])


def _plane_top(d, span=40, chord=13, fus=8, nose=10, tail=88,
               tail_span=16, engines=0):
    cx = 48
    _orect(d, cx - fus, nose, cx + fus, tail)                  # fuselage
    _orect(d, cx - span, 38, cx + span, 38 + chord)            # wings
    _orect(d, cx - tail_span, tail - 10, cx + tail_span, tail - 2)
    d.ellipse([cx - fus - 1, nose - 6, cx + fus + 1, nose + 8],
              fill=_WHITE, outline=_BLACK)
    if engines:
        for sx in (-1, 1):
            x = cx + sx * span // 2
            _orect(d, x - 5, 32, x + 5, 56, 2)


def _tu_infantry(d, ink):
    _o(d, [(30, 40), (66, 40), (62, 62), (34, 62)])            # shoulders
    d.ellipse([38, 30, 58, 50], fill=_WHITE, outline=_BLACK)   # helmet
    d.line([(58, 44), (74, 16)], fill=_BLACK, width=4)         # rifle


def _tu_tank(d, ink):
    _orect(d, 22, 14, 34, 84)                                  # track L
    _orect(d, 62, 14, 74, 84)                                  # track R
    _orect(d, 32, 22, 64, 78)                                  # hull
    d.ellipse([36, 36, 60, 60], fill=_WHITE, outline=_BLACK)   # turret
    _orect(d, 45, 4, 51, 40, 2)                                # barrel


def _tu_truck(d, ink, canvas=False):
    _orect(d, 34, 12, 62, 32)                                  # cab
    _orect(d, 31, 34, 65, 86)                                  # bed
    if canvas:
        for y in (44, 54, 64, 74):
            d.line([(33, y), (63, y)], fill=_BLACK, width=2)
    else:
        d.line([(31, 34), (65, 86)], fill=_BLACK, width=2)
        d.line([(65, 34), (31, 86)], fill=_BLACK, width=2)


def _tu_supply_truck(d, ink):
    _tu_truck(d, ink, canvas=False)


def _tu_transport_truck(d, ink):
    _tu_truck(d, ink, canvas=True)


def _tu_aa(d, ink):
    d.ellipse([28, 34, 68, 74], fill=_WHITE, outline=_BLACK)   # platform
    d.line([(48, 54), (34, 10)], fill=_BLACK, width=4)         # barrels
    d.line([(48, 54), (62, 10)], fill=_BLACK, width=4)
    _orect(d, 42, 48, 54, 60, 2)


def _tu_command(d, ink):
    _orect(d, 34, 12, 62, 32)
    _orect(d, 31, 34, 65, 86)
    d.ellipse([43, 50, 53, 60], fill=_BLACK)                   # radio mast
    d.polygon([(48, 34), (62, 40), (48, 46)], fill=_BLACK)     # pennant


def _tu_engineer(d, ink):
    _orect(d, 34, 12, 62, 32)
    _orect(d, 31, 34, 65, 86)
    d.line([(48, 56), (76, 30)], fill=_BLACK, width=4)         # crane
    d.line([(76, 30), (76, 42)], fill=_BLACK, width=3)


def _tu_naval_command(d, ink):
    _hull_top(d)
    _orect(d, 38, 34, 58, 62)                                  # bridge
    d.ellipse([44, 40, 52, 48], fill=_BLACK)                   # mast
    d.polygon([(48, 24), (60, 29), (48, 34)], fill=_BLACK)


def _tu_personnel_transport(d, ink):
    _hull_top(d)
    for y in (32, 46, 60, 74):
        _orect(d, 40, y, 56, y + 8, 2)                         # hatches


def _tu_dd_sea(d, ink):
    _hull_top(d, half=11)
    d.ellipse([41, 26, 55, 40], fill=_WHITE, outline=_BLACK)   # A turret
    _orect(d, 46, 14, 50, 30, 2)
    d.ellipse([41, 62, 55, 76], fill=_WHITE, outline=_BLACK)   # X turret


def _tu_dd_aa(d, ink):
    _hull_top(d, half=11)
    d.line([(48, 52), (36, 22)], fill=_BLACK, width=4)
    d.line([(48, 52), (60, 22)], fill=_BLACK, width=4)
    _orect(d, 42, 48, 54, 58, 2)


def _tu_dd_land(d, ink):
    _hull_top(d, half=11)
    d.ellipse([39, 24, 57, 42], fill=_WHITE, outline=_BLACK)
    _orect(d, 45, 10, 51, 30, 2)                               # heavy gun


def _tu_carrier(d, ink):
    _o(d, [(38, 2), (58, 2), (61, 14), (61, 92), (35, 92), (35, 14)])
    d.line([(44, 6), (40, 88)], fill=_BLACK, width=2)          # runway
    d.line([(52, 6), (56, 88)], fill=_BLACK, width=2)
    _orect(d, 55, 42, 63, 62, 2)                               # island


def _tu_fighter(d, ink):
    _plane_top(d, span=34, chord=11, fus=6, tail=82, tail_span=13)


def _tu_bomber(d, ink):
    _plane_top(d, span=42, chord=14, fus=8, tail=88, tail_span=18,
               engines=1)


def _tu_air_command(d, ink):
    _plane_top(d, span=38, chord=12, fus=8, tail=86, tail_span=16)
    d.polygon([(48, 16), (62, 21), (48, 26)], fill=_BLACK)


def _tu_transport_air(d, ink):
    _plane_top(d, span=44, chord=13, fus=10, tail=84, tail_span=18)
    for y in (22, 30, 38):
        d.line([(40, y), (56, y)], fill=_BLACK, width=2)


def _tu_supply_ship(d, ink):
    _hull_top(d)
    for y in (34, 52, 70):
        _orect(d, 39, y, 57, y + 12, 2)
        d.line([(39, y), (57, y + 12)], fill=_BLACK, width=2)


_TOP_DOWN = {
    'infantry': _tu_infantry,
    'tank': _tu_tank,
    'supply_truck': _tu_supply_truck,
    'transport_truck': _tu_transport_truck,
    'aa_artillery': _tu_aa,
    'army_command': _tu_command,
    'engineer': _tu_engineer,
    'naval_command': _tu_naval_command,
    'personnel_transport': _tu_personnel_transport,
    'destroyer_sea_sea': _tu_dd_sea,
    'destroyer_aa': _tu_dd_aa,
    'destroyer_sea_land': _tu_dd_land,
    'aircraft_carrier': _tu_carrier,
    'fighter': _tu_fighter,
    'bomber': _tu_bomber,
    'airforce_command': _tu_air_command,
    'transport_air': _tu_transport_air,
    'supply_ship': _tu_supply_ship,
}


ICON_VERSION = 5   # bump when drawings change to invalidate the cache


def get_icon_path(unit_type, variant='dark'):
    """Path to the icon PNG, generating it on first request."""
    os.makedirs(ICON_DIR, exist_ok=True)
    path = os.path.join(ICON_DIR, "%s_%s_v%d.png"
                        % (unit_type, variant, ICON_VERSION))
    if not os.path.exists(path):
        img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        if variant == 'unit':
            _TOP_DOWN.get(unit_type, _tu_infantry)(d, _WHITE)
        else:
            ink = _INKS.get(variant, INK_DARK)
            _DRAWERS.get(unit_type, _draw_infantry)(d, ink)
        img.save(path)
    return path
