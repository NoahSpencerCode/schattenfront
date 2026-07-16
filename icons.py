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
    """Top-down aerodrome in the CITY SKETCH palette (the same tans and
    street-ink the towns are drawn with): two clean crossing runways,
    taxiway, apron, hangar row, tower. No runway markings."""
    rw = (176, 161, 127, 255)          # rooftop tan (city palette)
    ln = (96, 83, 63, 255)             # street ink (city palette)

    def runway(p0, p1, w):
        (x0, y0), (x1, y1) = p0, p1
        dx, dy = x1 - x0, y1 - y0
        ll = max(1.0, (dx * dx + dy * dy) ** 0.5)
        px, py = -dy / ll * w, dx / ll * w
        d.polygon([(x0 + px, y0 + py), (x1 + px, y1 + py),
                   (x1 - px, y1 - py), (x0 - px, y0 - py)],
                  fill=rw, outline=ln)

    runway((14, 78), (86, 30), 8)      # main strip, NE-SW
    runway((28, 12), (60, 88), 6)      # crossing strip
    # taxiway to the apron
    d.line([(64, 44), (78, 58), (78, 74)], fill=ln, width=3)
    d.rectangle([66, 74, 90, 88], fill=rw, outline=ln)        # apron
    # hangar row (bold roof caps)
    for x0 in (68, 79):
        d.rectangle([x0, 62, x0 + 9, 72], fill=rw, outline=ln, width=2)
        d.line([(x0, 62), (x0 + 9, 62)], fill=ln, width=3)
    # control tower: square base, dot cab
    d.rectangle([8, 12, 20, 24], fill=rw, outline=ln, width=2)
    d.ellipse([11, 15, 17, 21], fill=ln)


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
    """A clean stone arch bridge, top-down: slim deck with parapets,
    two pier cutwaters, gently flared approaches."""
    deck = (188, 172, 140, 255)
    edge = (52, 42, 32, 255)
    # flared approaches
    d.polygon([(30, 6), (66, 6), (58, 18), (38, 18)], fill=deck,
              outline=edge)
    d.polygon([(30, 90), (66, 90), (58, 78), (38, 78)], fill=deck,
              outline=edge)
    # deck with parapet lines
    d.rectangle([38, 14, 58, 82], fill=deck, outline=edge, width=3)
    d.line([(41, 16), (41, 80)], fill=edge, width=1)
    d.line([(55, 16), (55, 80)], fill=edge, width=1)
    # pier cutwaters (pointed, breasting the stream)
    for y in (36, 60):
        d.polygon([(38, y - 5), (30, y), (38, y + 5)], fill=edge)
        d.polygon([(58, y - 5), (66, y), (58, y + 5)], fill=edge)


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


def _draw_tax_button(d, ink):
    """Parchment button bearing the taxman's mark: a bold percent sign
    over a coin -- opens the city's tax decree."""
    d.rounded_rectangle([5, 5, 90, 90], radius=22,
                        fill=(216, 205, 168, 255),
                        outline=(54, 44, 34, 255), width=6)
    col = (44, 35, 26, 255)
    d.line([(30, 70), (66, 26)], fill=col, width=7)            # the slash
    d.ellipse([26, 24, 44, 42], outline=col, width=6)          # top ring
    d.ellipse([52, 54, 70, 72], outline=col, width=6)          # low ring


def _draw_factory_button(d, ink):
    """Parchment button bearing a war factory: sawtooth roof, chimney,
    smoke -- opens the production-state FAX."""
    d.rounded_rectangle([5, 5, 90, 90], radius=22,
                        fill=(216, 205, 168, 255),
                        outline=(54, 44, 34, 255), width=6)
    col = (44, 35, 26, 255)
    d.rectangle([22, 52, 76, 74], fill=col)                   # hall
    d.polygon([(22, 52), (22, 38), (40, 52)], fill=col)       # sawtooth
    d.polygon([(40, 52), (40, 38), (58, 52)], fill=col)
    d.polygon([(58, 52), (58, 38), (76, 52)], fill=col)
    d.rectangle([64, 24, 72, 52], fill=col)                   # chimney
    for (cx, cy, r) in ((60, 20, 4), (52, 14, 5), (42, 10, 6)):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col,
                  width=3)                                    # smoke


_DRAWERS = {
    'city': _draw_city,
    'capital': _draw_capital,
    'airfield': _draw_airfield,
    'factory_button': _draw_factory_button,
    'tax_button': _draw_tax_button,
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


def _tracks(d, xl0, xl1, xr0, xr1, y0, y1):
    """Track pair with tread ticks."""
    for (x0, x1) in ((xl0, xl1), (xr0, xr1)):
        _orect(d, x0, y0, x1, y1)
        for y in range(y0 + 5, y1 - 3, 8):
            d.line([(x0 + 2, y), (x1 - 2, y)], fill=_BLACK, width=1)


def _turret(d, cx, cy, r, blen, bw=5, brake=False):
    """Turret + forward gun; optional muzzle brake."""
    d.line([(cx, cy), (cx, cy - blen)], fill=_BLACK, width=bw)
    if brake:
        d.rectangle([cx - 4, cy - blen, cx + 4, cy - blen + 6],
                    fill=_BLACK)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=_WHITE,
              outline=_BLACK, width=3)
    d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=_BLACK)   # hatch


def _funnel(d, cx, cy, r=5):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=_BLACK)


# ---- ARMY ----------------------------------------------------------------

def _tu_infantry(d, ink, nat=None):
    _o(d, [(30, 40), (66, 40), (62, 62), (34, 62)])            # shoulders
    d.ellipse([38, 30, 58, 50], fill=_WHITE, outline=_BLACK)   # helmet
    d.line([(58, 44), (74, 16)], fill=_BLACK, width=4)         # rifle
    d.line([(34, 62), (30, 78)], fill=_BLACK, width=3)         # pack strap
    d.line([(62, 62), (66, 78)], fill=_BLACK, width=3)


def _tu_tank(d, ink, nat=None):
    """National silhouettes: Tiger I, T-34, Sherman, Churchill, Chi-Ha."""
    if nat == 'germany':            # Tiger I: wide, boxy, the long 88
        _tracks(d, 18, 31, 65, 78, 14, 84)
        _orect(d, 29, 18, 67, 80)
        for y in (66, 72):          # engine deck louvres
            d.line([(33, y), (63, y)], fill=_BLACK, width=2)
        _turret(d, 48, 44, 13, 40, bw=5, brake=True)
    elif nat == 'soviet':           # T-34: sloped glacis, round turret
        _tracks(d, 22, 33, 63, 74, 14, 84)
        _o(d, [(35, 30), (48, 16), (61, 30), (61, 80), (35, 80)])
        d.line([(38, 74), (58, 74)], fill=_BLACK, width=2)
        _turret(d, 48, 44, 11, 34, bw=4)
    elif nat == 'britain':          # Churchill: long hull, all-round track
        _tracks(d, 20, 32, 64, 76, 8, 88)
        _orect(d, 30, 18, 66, 82)
        for y in (68, 74):
            d.line([(34, y), (62, y)], fill=_BLACK, width=2)
        _turret(d, 48, 42, 10, 26, bw=4)
    elif nat == 'japan':            # Chi-Ha: small, thin gun
        _tracks(d, 27, 37, 59, 69, 20, 80)
        _orect(d, 35, 26, 61, 76)
        _turret(d, 48, 44, 9, 26, bw=3)
    else:                           # Sherman: tall narrow, round turret
        _tracks(d, 25, 36, 60, 71, 16, 82)
        _orect(d, 34, 22, 62, 78)
        d.line([(38, 70), (58, 70)], fill=_BLACK, width=2)
        _turret(d, 48, 46, 11, 32, bw=4)


def _tu_truck(d, ink, canvas=False, axles=2):
    _orect(d, 34, 12, 62, 30)                                  # cab
    d.rectangle([38, 16, 58, 24], fill=_BLACK)                 # windscreen
    _orect(d, 31, 32, 65, 86)                                  # bed
    if canvas:
        for y in (42, 52, 62, 72):
            d.line([(33, y), (63, y)], fill=_BLACK, width=2)
    else:
        d.line([(31, 32), (65, 86)], fill=_BLACK, width=2)
        d.line([(65, 32), (31, 86)], fill=_BLACK, width=2)
    for i in range(axles):                                     # wheels
        y = 40 + i * (38 // max(1, axles - 1))
        d.rectangle([26, y, 31, y + 10], fill=_BLACK)
        d.rectangle([65, y, 70, y + 10], fill=_BLACK)


def _tu_supply_truck(d, ink, nat=None):
    _tu_truck(d, ink, canvas=False,
              axles=3 if nat in ('usa', 'soviet') else 2)


def _tu_halftrack(d, ink):
    """Armoured personnel halftrack: wheels forward, tracks aft."""
    _o(d, [(34, 10), (62, 10), (66, 30), (66, 84), (30, 84), (30, 30)])
    d.rectangle([38, 14, 58, 22], fill=_BLACK)
    d.rectangle([24, 18, 30, 30], fill=_BLACK)                 # front wheels
    d.rectangle([66, 18, 72, 30], fill=_BLACK)
    _tracks(d, 24, 30, 66, 72, 38, 82)
    for y in (44, 56, 68):
        d.line([(36, y), (60, y)], fill=_BLACK, width=2)       # benches


def _tu_transport_truck(d, ink, nat=None):
    if nat in ('germany', 'usa'):
        _tu_halftrack(d, ink)
    elif nat == 'britain':          # Bren carrier: low open tracked box
        _tracks(d, 22, 32, 64, 74, 24, 78)
        _orect(d, 30, 28, 66, 74)
        d.rectangle([36, 34, 60, 44], fill=_BLACK)             # open bay
        d.line([(36, 56), (60, 56)], fill=_BLACK, width=2)
    else:
        _tu_truck(d, ink, canvas=True,
                  axles=3 if nat == 'soviet' else 2)


def _tu_aa(d, ink, nat=None):
    if nat == 'germany':            # the 88: cruciform mount, one barrel
        for (p0, p1) in (((30, 44), (66, 64)), ((30, 64), (66, 44))):
            d.line([p0, p1], fill=_BLACK, width=6)             # outriggers
        d.ellipse([36, 42, 60, 66], fill=_WHITE, outline=_BLACK)
        d.line([(48, 54), (48, 6)], fill=_BLACK, width=5)      # long barrel
        d.rectangle([45, 6, 51, 12], fill=_BLACK)
    else:
        d.ellipse([28, 34, 68, 74], fill=_WHITE, outline=_BLACK)
        d.line([(48, 54), (36, 12)], fill=_BLACK, width=4)     # twin guns
        d.line([(48, 54), (60, 12)], fill=_BLACK, width=4)
        _orect(d, 42, 48, 54, 60, 2)
    d.ellipse([44, 50, 52, 58], fill=_BLACK)


def _tu_command(d, ink, nat=None):
    _tu_truck(d, ink, canvas=True)
    d.ellipse([43, 48, 53, 58], fill=_BLACK)                   # radio mast
    d.line([(48, 53), (48, 36)], fill=_BLACK, width=2)         # aerial
    d.polygon([(48, 36), (62, 41), (48, 46)], fill=_BLACK)     # pennant


def _tu_engineer(d, ink, nat=None):
    _tu_truck(d, ink, canvas=False)
    d.line([(48, 56), (76, 30)], fill=_BLACK, width=4)         # crane jib
    d.line([(76, 30), (76, 42)], fill=_BLACK, width=3)
    d.ellipse([73, 42, 79, 48], outline=_BLACK, width=2)       # hook


# ---- NAVY ----------------------------------------------------------------

def _tu_naval_command(d, ink, nat=None):
    if nat == 'japan':              # Yamato: massive beam, pagoda mast
        _hull_top(d, half=15)
        d.ellipse([40, 24, 56, 40], fill=_WHITE, outline=_BLACK)
        d.line([(48, 32), (48, 12)], fill=_BLACK, width=6)     # main guns
        _orect(d, 39, 42, 57, 66)                              # pagoda
        d.ellipse([44, 48, 52, 56], fill=_BLACK)
        d.ellipse([41, 66, 55, 80], fill=_WHITE, outline=_BLACK)
    else:
        _hull_top(d)
        _orect(d, 38, 34, 58, 62)                              # bridge
        d.ellipse([44, 40, 52, 48], fill=_BLACK)               # mast
        _funnel(d, 48, 68)
        d.polygon([(48, 24), (60, 29), (48, 34)], fill=_BLACK)


def _tu_personnel_transport(d, ink, nat=None):
    _hull_top(d)
    for y in (32, 46, 60, 74):
        _orect(d, 40, y, 56, y + 8, 2)                         # hatches
    _funnel(d, 48, 52, r=4)
    for sx in (36, 60):                                        # boat davits
        d.line([(sx, 40), (sx, 70)], fill=_BLACK, width=2)


def _tu_dd_sea(d, ink, nat=None):
    _hull_top(d, half=11)
    d.ellipse([42, 24, 54, 36], fill=_WHITE, outline=_BLACK)   # A turret
    _orect(d, 46, 12, 50, 28, 2)
    if nat == 'japan':              # Fubuki: Long Lance tube mounts
        for y in (46, 56):
            _orect(d, 43, y, 53, y + 7, 2)
        _funnel(d, 48, 40, r=4)
    else:
        _funnel(d, 48, 44, r=4)
        _funnel(d, 48, 56, r=4)
    d.ellipse([42, 64, 54, 76], fill=_WHITE, outline=_BLACK)   # X turret
    if nat == 'britain':            # Tribal: second forward turret
        d.ellipse([43, 38, 53, 48], fill=_WHITE, outline=_BLACK)


def _tu_dd_aa(d, ink, nat=None):
    _hull_top(d, half=11)
    d.line([(48, 52), (36, 20)], fill=_BLACK, width=4)         # AA battery
    d.line([(48, 52), (60, 20)], fill=_BLACK, width=4)
    d.line([(48, 60), (38, 34)], fill=_BLACK, width=3)
    d.line([(48, 60), (58, 34)], fill=_BLACK, width=3)
    _orect(d, 42, 48, 54, 60, 2)
    _funnel(d, 48, 70, r=4)


def _tu_dd_land(d, ink, nat=None):
    _hull_top(d, half=12)
    d.ellipse([39, 22, 57, 40], fill=_WHITE, outline=_BLACK)   # big turret
    _orect(d, 44, 8, 47, 26, 2)                                # twin heavies
    _orect(d, 49, 8, 52, 26, 2)
    _funnel(d, 48, 50, r=4)
    d.ellipse([41, 60, 55, 74], fill=_WHITE, outline=_BLACK)


def _tu_carrier(d, ink, nat=None):
    if nat == 'britain':            # Illustrious: armoured, rounded deck
        _o(d, [(37, 6), (59, 6), (62, 20), (62, 88), (34, 88), (34, 20)])
        d.rounded_rectangle([38, 10, 58, 84], radius=8, outline=_BLACK,
                            width=2)
        _orect(d, 58, 40, 66, 58, 2)                           # island
    elif nat == 'japan':            # Kido Butai: clean flush deck
        _o(d, [(38, 2), (58, 2), (61, 14), (61, 92), (35, 92), (35, 14)])
        d.line([(44, 6), (40, 88)], fill=_BLACK, width=2)
        d.line([(52, 6), (56, 88)], fill=_BLACK, width=2)
        _orect(d, 30, 44, 36, 56, 2)                           # port island
    else:                           # Essex and kin: big starboard island
        _o(d, [(38, 2), (58, 2), (61, 14), (61, 92), (35, 92), (35, 14)])
        d.line([(44, 6), (40, 88)], fill=_BLACK, width=2)
        d.line([(52, 6), (56, 88)], fill=_BLACK, width=2)
        for y in (18, 30):          # deck park
            d.line([(40, y), (55, y)], fill=_BLACK, width=2)
        _orect(d, 55, 38, 64, 64, 2)


def _tu_supply_ship(d, ink, nat=None):
    _hull_top(d)
    for y in (32, 50, 68):
        _orect(d, 39, y, 57, y + 12, 2)                        # holds
        d.line([(39, y), (57, y + 12)], fill=_BLACK, width=2)
    d.line([(48, 26), (48, 84)], fill=_BLACK, width=2)         # derrick run


# ---- AIR FORCE -----------------------------------------------------------

def _fuselage(d, fus, nose, tail, canopy_y=30):
    cx = 48
    _orect(d, cx - fus, nose, cx + fus, tail)
    d.ellipse([cx - fus - 1, nose - 6, cx + fus + 1, nose + 8],
              fill=_WHITE, outline=_BLACK)                     # cowl
    d.ellipse([cx - 3, nose - 3, cx + 3, nose + 3], fill=_BLACK)
    d.ellipse([cx - 4, canopy_y, cx + 4, canopy_y + 12],
              fill=_BLACK)                                     # canopy


def _tailplane(d, tail, span, rounded=False):
    cx = 48
    if rounded:
        d.ellipse([cx - span, tail - 12, cx + span, tail],
                  fill=_WHITE, outline=_BLACK)
    else:
        _orect(d, cx - span, tail - 10, cx + span, tail - 2)


def _tu_fighter(d, ink, nat=None):
    cx = 48
    if nat == 'britain':            # Spitfire: the elliptical wing
        _fuselage(d, 6, 10, 80)
        d.ellipse([cx - 38, 34, cx + 38, 54], fill=_WHITE,
                  outline=_BLACK, width=3)
        _tailplane(d, 82, 12, rounded=True)
    elif nat == 'germany':          # Bf 109: slim, square-cut wings
        _fuselage(d, 5, 10, 82)
        _o(d, [(cx - 36, 36), (cx + 36, 36), (cx + 32, 50),
               (cx - 32, 50)])
        _tailplane(d, 84, 11)
    elif nat == 'japan':            # Zero: broad rounded span
        _fuselage(d, 6, 8, 80)
        d.rounded_rectangle([cx - 41, 34, cx + 41, 52], radius=9,
                            fill=_WHITE, outline=_BLACK, width=3)
        _tailplane(d, 82, 13, rounded=True)
    elif nat == 'soviet':           # Yak-3: short and stubby
        _fuselage(d, 6, 12, 78)
        _o(d, [(cx - 29, 36), (cx + 29, 36), (cx + 24, 52),
               (cx - 24, 52)])
        _tailplane(d, 80, 11)
    else:                           # Mustang: laminar taper
        _fuselage(d, 6, 10, 82)
        _o(d, [(cx - 37, 36), (cx + 37, 36), (cx + 28, 52),
               (cx - 28, 52)])
        _tailplane(d, 84, 12)


def _tu_bomber(d, ink, nat=None):
    cx = 48
    if nat in ('usa', 'britain'):   # four-engined heavies
        _fuselage(d, 7, 8, 90, canopy_y=24)
        _o(d, [(cx - 44, 34), (cx + 44, 34), (cx + 38, 50), (cx - 38, 50)])
        for sx in (-30, -16, 16, 30):
            _orect(d, cx + sx - 4, 28, cx + sx + 4, 54, 2)
        if nat == 'britain':        # Lancaster twin fins
            _orect(d, cx - 20, 78, cx + 20, 84, 2)
            d.rectangle([cx - 22, 74, cx - 16, 88], fill=_BLACK)
            d.rectangle([cx + 16, 74, cx + 22, 88], fill=_BLACK)
        else:                       # B-17 broad single fin
            _tailplane(d, 90, 18)
            d.polygon([(cx - 3, 74), (cx + 8, 88), (cx - 3, 88)],
                      fill=_BLACK)
    elif nat == 'soviet':           # Il-2: single engine, hunched canopy
        _fuselage(d, 7, 10, 84, canopy_y=32)
        _o(d, [(cx - 36, 38), (cx + 36, 38), (cx + 28, 54), (cx - 28, 54)])
        d.ellipse([cx - 4, 44, cx + 4, 54], fill=_BLACK)       # gunner
        _tailplane(d, 86, 14)
    else:                           # Ju 88 / G4M: twin-engined mediums
        _fuselage(d, 7, 10, 86, canopy_y=22)
        _o(d, [(cx - 42, 36), (cx + 42, 36), (cx + 34, 52), (cx - 34, 52)])
        for sx in (-20, 20):
            _orect(d, cx + sx - 5, 30, cx + sx + 5, 56, 2)
        if nat == 'japan':          # glazed round nose
            d.ellipse([cx - 6, 6, cx + 6, 18], outline=_BLACK, width=2)
        _tailplane(d, 88, 16)


def _tu_air_command(d, ink, nat=None):
    _tu_bomber(d, ink, nat)
    d.polygon([(48, 14), (63, 19), (48, 24)], fill=_BLACK)     # command flash


def _tu_transport_air(d, ink, nat=None):
    cx = 48
    _fuselage(d, 10, 10, 84, canopy_y=20)
    _o(d, [(cx - 44, 36), (cx + 44, 36), (cx + 36, 52), (cx - 36, 52)])
    for sx in (-24, 24):
        _orect(d, cx + sx - 4, 30, cx + sx + 4, 54, 2)
    for y in (24, 32, 40):          # cabin windows
        d.line([(cx - 8, y), (cx + 8, y)], fill=_BLACK, width=2)
    _tailplane(d, 86, 16)


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


ICON_VERSION = 7   # bump when drawings change to invalidate the cache


def get_icon_path(unit_type, variant='dark', nation=None):
    """Path to the icon PNG, generating it on first request. Top-down
    unit sprites vary by nation (each power fields its own marks)."""
    os.makedirs(ICON_DIR, exist_ok=True)
    tag = ("%s@%s" % (unit_type, nation)
           if (nation and variant == 'unit') else unit_type)
    path = os.path.join(ICON_DIR, "%s_%s_v%d.png"
                        % (tag, variant, ICON_VERSION))
    if not os.path.exists(path):
        img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        if variant == 'unit':
            _TOP_DOWN.get(unit_type, _tu_infantry)(d, _WHITE, nation)
        else:
            ink = _INKS.get(variant, INK_DARK)
            _DRAWERS.get(unit_type, _draw_infantry)(d, ink)
        img.save(path)
    return path
