"""
Flat map markers — no 3D models, no billboards.

Everything (units, cities, bridges, hit flashes) is drawn flat on the
planet surface like symbols inked onto a war map.  All geometry here is
built in the local XY plane facing +Z; parent it to a "holder" node that
sits at surface height under a node oriented by globe.orient_to_surface.
"""

import math

from panda3d.core import (CardMaker, Geom, GeomNode, GeomTriangles,
                          GeomTristrips,
                          GeomVertexData, GeomVertexFormat, GeomVertexWriter,
                          LineSegs, NodePath, SamplerState, TextNode,
                          TransparencyAttrib, Vec3)

from icons import get_icon_path
from utils import angle_between

_icon_tex_cache = {}


def set_marker_layer(np_, sort):
    """Deterministic draw order for flat map markers.

    Everything lies at almost the same height above the globe, so the
    depth buffer cannot order the pieces — they bleed into each other.
    Instead: explicit paint order in the 'fixed' bin, no depth writes
    (pieces never fight), depth test kept (the planet still occludes
    markers on the far side).
    """
    np_.setBin('fixed', sort)
    np_.setDepthWrite(False)
    np_.setDepthTest(True)


# marker layer plan (fixed-bin sort values):
#   40        path/survey lines stay in the opaque bin (under markers)
#   50-59     bridges
#   60-79     cities, airfields, depots, bunkers (+badges)
#   100-4099  land/sea unit counters: base = 100 + (id%400)*10
#   4100-8199 aircraft counters (always above surface units)
#   9000      cluster pie markers
#   9800      hover glow
#   9900      hit flashes
LAYER_BRIDGE = 50
LAYER_STRUCT = 60
LAYER_CLUSTER = 9000
LAYER_HOVER = 9800
LAYER_FLASH = 9900


def unit_layer_base(unit_id, is_air):
    return (4100 if is_air else 100) + (unit_id % 400) * 10


def make_flat_quad(name, w, h, color):
    """Solid rectangle in the XY plane, centred on the origin."""
    fmt = GeomVertexFormat.getV3c4()
    vdata = GeomVertexData(name, fmt, Geom.UHStatic)
    vw = GeomVertexWriter(vdata, 'vertex')
    cw = GeomVertexWriter(vdata, 'color')
    hw, hh = w / 2.0, h / 2.0
    for (x, y) in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)):
        vw.addData3(x, y, 0)
        cw.addData4(*color)
    tris = GeomTriangles(Geom.UHStatic)
    tris.addVertices(0, 1, 2)
    tris.addVertices(0, 2, 3)
    geom = Geom(vdata)
    geom.addPrimitive(tris)
    gn = GeomNode(name)
    gn.addGeom(geom)
    return NodePath(gn)


def make_flat_ring(name, radius, color, thickness=2.0, segments=32):
    """Circle outline in the XY plane, centred on the origin."""
    segs = LineSegs()
    segs.setThickness(thickness)
    segs.setColor(*color)
    for i in range(segments + 1):
        a = 2 * math.pi * i / segments
        p = (radius * math.cos(a), radius * math.sin(a), 0)
        if i == 0:
            segs.moveTo(*p)
        else:
            segs.drawTo(*p)
    np_ = NodePath(segs.create())
    np_.setLightOff()
    return np_


def make_shiny_ring(name, r_in, r_out, segments=32, base=0.72, sheen=0.26):
    """Annulus with a silver gradient around it — reads as polished
    metal trim on the unit counters."""
    fmt = GeomVertexFormat.getV3c4()
    vdata = GeomVertexData(name, fmt, Geom.UHStatic)
    vw = GeomVertexWriter(vdata, 'vertex')
    cw = GeomVertexWriter(vdata, 'color')
    for i in range(segments + 1):
        a = 2 * math.pi * i / segments
        # highlight toward the upper-left, shadow lower-right
        v = base + sheen * math.cos(a - math.pi * 0.75)
        ca, sa = math.cos(a), math.sin(a)
        vw.addData3(r_in * ca, r_in * sa, 0)
        cw.addData4(v * 0.82, v * 0.82, v * 0.86, 1.0)
        vw.addData3(r_out * ca, r_out * sa, 0)
        cw.addData4(v, v, v * 1.04, 1.0)
    tris = GeomTriangles(Geom.UHStatic)
    for i in range(segments):
        a0 = i * 2
        tris.addVertices(a0, a0 + 1, a0 + 2)
        tris.addVertices(a0 + 1, a0 + 3, a0 + 2)
    geom = Geom(vdata)
    geom.addPrimitive(tris)
    gn = GeomNode(name)
    gn.addGeom(geom)
    np_ = NodePath(gn)
    np_.setLightOff()
    return np_


def make_flat_disc(name, radius, color, segments=24):
    """Solid circle in the XY plane."""
    fmt = GeomVertexFormat.getV3c4()
    vdata = GeomVertexData(name, fmt, Geom.UHStatic)
    vw = GeomVertexWriter(vdata, 'vertex')
    cw = GeomVertexWriter(vdata, 'color')
    vw.addData3(0, 0, 0)
    cw.addData4(*color)
    for i in range(segments):
        a = 2 * math.pi * i / segments
        vw.addData3(radius * math.cos(a), radius * math.sin(a), 0)
        cw.addData4(*color)
    tris = GeomTriangles(Geom.UHStatic)
    for i in range(segments):
        tris.addVertices(0, 1 + i, 1 + (i + 1) % segments)
    geom = Geom(vdata)
    geom.addPrimitive(tris)
    gn = GeomNode(name)
    gn.addGeom(geom)
    return NodePath(gn)


def _icon_texture(loader, name, variant, nation=None):
    key = (name, variant, nation)
    tex = _icon_tex_cache.get(key)
    if tex is None:
        tex = loader.loadTexture(get_icon_path(name, variant,
                                               nation=nation))
        tex.setMinfilter(SamplerState.FTLinearMipmapLinear)
        tex.setMagfilter(SamplerState.FTLinear)
        tex.setAnisotropicDegree(8)     # keeps glancing angles crisp
        _icon_tex_cache[key] = tex
    return tex


def make_icon_quad(loader, name, variant, half=0.55, depth=7,
                   nation=None, flat=True):
    """Textured square carrying one of the generated pictograms; flat
    lies on the map, flat=False leaves it upright for billboarding."""
    cm = CardMaker('icon_' + name)
    cm.setFrame(-half, half, -half, half)
    icon = NodePath(cm.generate())
    if flat:
        icon.setP(-90)          # lay the card flat into the XY plane
    icon.setTexture(_icon_texture(loader, name, variant, nation))
    icon.setTransparency(TransparencyAttrib.MAlpha)
    icon.setDepthOffset(depth)
    return icon


_flag_tex_cache = {}


def make_flag_quad(loader, country, half=0.34, depth=8, flat=True):
    """A nation's tiny standard, flown above foreign units and works
    so ownership reads at a glance now every counter wears the same
    ink. 3:2 cloth; flat lies on the map, upright rides a billboard."""
    from icons import flag_texture
    tex = _flag_tex_cache.get(country)
    if tex is None:
        tex = loader.loadTexture(flag_texture(country))
        tex.setMinfilter(SamplerState.FTLinearMipmapLinear)
        tex.setMagfilter(SamplerState.FTLinear)
        tex.setAnisotropicDegree(8)
        _flag_tex_cache[country] = tex
    hh = half * 2.0 / 3.0
    cm = CardMaker('flag_' + country)
    cm.setFrame(-half, half, -hh, hh)
    np_ = NodePath(cm.generate())
    if flat:
        np_.setP(-90)
    np_.setTexture(tex)
    np_.setTransparency(TransparencyAttrib.MAlpha)
    np_.setDepthOffset(depth)
    return np_


def make_counter(loader, unit_type, faction_color, layer_base=100):
    """A unit counter: round faction-coloured disc with polished silver
    trim and the unit's pictogram, lying flat on the map.  Pieces are
    painted in a fixed order: disc, trim, pictogram."""
    root = NodePath('counter_' + unit_type)
    c = faction_color
    disc = make_flat_disc('disc', 0.72, (c[0], c[1], c[2], 0.96),
                          segments=28)
    disc.reparentTo(root)
    set_marker_layer(disc, layer_base + 0)
    border = make_shiny_ring('border', 0.66, 0.82, segments=32)
    border.reparentTo(root)
    set_marker_layer(border, layer_base + 1)

    lum = 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
    variant = 'dark' if lum > 0.45 else 'light'
    icon = make_icon_quad(loader, unit_type, variant, half=0.42)
    icon.reparentTo(root)
    set_marker_layer(icon, layer_base + 2)
    root.setLightOff()
    return root


def make_city_marker(loader, faction_color, capital):
    """A city pictogram (building skyline; star for capitals) tinted in
    the owner's colour, with a baked black outline."""
    root = NodePath('city_marker')
    c = faction_color
    icon = make_icon_quad(loader, 'capital' if capital else 'city',
                          'dark', half=1.35, depth=5)
    icon.setColorScale(c[0], c[1], c[2], 1.0)
    icon.reparentTo(root)
    root.setLightOff()
    return root


def make_road_ribbon(name, pts, half_w, color, radius):
    """A road as REAL surface geometry: a triangle strip of fixed
    WORLD width riding the sphere at the given radius. Fixed world
    size means it scales with zoom exactly like the terrain, and real
    geometry means the day/night shader can light it like the map."""
    # sanitize: duplicated consecutive points give a ZERO tangent,
    # whose normalize() breeds NaN vertices -- one NaN voids the whole
    # strip's bounds (invisible roads) and near-degenerates paint the
    # long sliver spikes
    clean = [pts[0]]
    for p in pts[1:]:
        if (p - clean[-1]).lengthSquared() > 1e-12:
            clean.append(p)
    pts = clean
    n = len(pts)
    if n < 2:
        return GeomNode(name)
    fmt = GeomVertexFormat.getV3c4()
    vdata = GeomVertexData(name, fmt, Geom.UHStatic)
    vw = GeomVertexWriter(vdata, 'vertex')
    cw = GeomVertexWriter(vdata, 'color')
    strip = GeomTristrips(Geom.UHStatic)
    last_side = None
    for i in range(n):
        p = pts[i]
        t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        t = t - p * t.dot(p)
        if t.lengthSquared() > 1e-12:
            t.normalize()
            side = t.cross(p)
        elif last_side is not None:
            side = last_side          # carry the last good frame
        else:
            side = Vec3(0, 0, 1).cross(p)
        if side.lengthSquared() < 1e-12:
            side = Vec3(0, 1, 0).cross(p)
        side.normalize()
        last_side = Vec3(side)
        a = p + side * half_w
        b = p - side * half_w
        a.normalize()
        b.normalize()
        vw.addData3(a * radius)
        cw.addData4(*color)
        vw.addData3(b * radius)
        cw.addData4(*color)
        strip.addVertex(2 * i)
        strip.addVertex(2 * i + 1)
    strip.closePrimitive()
    geom = Geom(vdata)
    geom.addPrimitive(strip)
    node = GeomNode(name)
    node.addGeom(geom)
    return node


def make_bridge_marker(loader):
    """A bridge pictogram at river scale, lying flat on the map so the
    holder's heading can lay the deck along its road."""
    root = NodePath('bridge_marker')
    cm = CardMaker('bridge_icon')
    cm.setFrame(-0.011, 0.011, -0.011, 0.011)   # 1:1, deck along +Y
    icon = root.attachNewNode(cm.generate())
    icon.setP(-90)
    icon.setTexture(_icon_texture(loader, 'bridge_map', 'dark'))
    icon.setTransparency(TransparencyAttrib.MAlpha)
    set_marker_layer(icon, LAYER_BRIDGE)
    root.setLightOff()
    return root


def make_pie_slice(name, radius, a0, a1, color, segments=18):
    """Filled arc slice of a disc in the XY plane (angles in radians)."""
    fmt = GeomVertexFormat.getV3c4()
    vdata = GeomVertexData(name, fmt, Geom.UHStatic)
    vw = GeomVertexWriter(vdata, 'vertex')
    cw = GeomVertexWriter(vdata, 'color')
    vw.addData3(0, 0, 0)
    cw.addData4(*color)
    n = max(2, int(segments * (a1 - a0) / (2 * math.pi)) + 1)
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        vw.addData3(radius * math.cos(a), radius * math.sin(a), 0)
        cw.addData4(*color)
    tris = GeomTriangles(Geom.UHStatic)
    for i in range(n):
        tris.addVertices(0, 1 + i, 2 + i)
    geom = Geom(vdata)
    geom.addPrimitive(tris)
    gn = GeomNode(name)
    gn.addGeom(geom)
    return NodePath(gn)


def make_cluster_marker(font, count, frac_friendly, friend_color):
    """Stacked units collapse into one counter: a pie of friendly vs
    enemy presence, silver trim, and the head-count."""
    root = NodePath('cluster')
    foe_color = (0.16, 0.13, 0.12, 0.96)
    fc = (friend_color[0], friend_color[1], friend_color[2], 0.96)
    two_pi = 2 * math.pi
    split = max(0.0, min(1.0, frac_friendly)) * two_pi
    # slices start at 12 o'clock, friendly clockwise first
    start = math.pi / 2
    if split > 1e-3:
        make_pie_slice('friend', 0.72, start - split, start, fc,
                       segments=28).reparentTo(root)
    if split < two_pi - 1e-3:
        make_pie_slice('foe', 0.72, start - two_pi, start - split,
                       foe_color, segments=28).reparentTo(root)
    ring = make_shiny_ring('trim', 0.66, 0.82, segments=32)
    ring.reparentTo(root)
    ring.setDepthOffset(6)

    tn = TextNode('count')
    tn.setText(str(count))
    tn.setAlign(TextNode.ACenter)
    if font:
        tn.setFont(font)
    tn.setTextColor(0.95, 0.93, 0.85, 1)
    tn.setShadow(0.06, 0.06)
    tn.setShadowColor(0.05, 0.05, 0.05, 1)
    np_ = root.attachNewNode(tn)
    np_.setP(-90)
    np_.setScale(0.72)
    np_.setPos(0, -0.24, 0)
    np_.setDepthOffset(8)
    root.setLightOff()
    root.setDepthOffset(5)
    return root


def make_hit_flash_template():
    """Red ring used for combat hit flashes (scaled/faded at runtime)."""
    ring = make_flat_ring('hit_flash', 1.0, (0.95, 0.15, 0.10, 0.95),
                          thickness=2.5, segments=24)
    ring.setTransparency(TransparencyAttrib.MAlpha)
    set_marker_layer(ring, LAYER_FLASH)
    return ring


def _side_frames(pts):
    """Per-point unit side vectors along a surface polyline, with the
    same dedupe/carry discipline as make_road_ribbon (zero tangents
    inherit the last good side, so no NaN can void the bounds)."""
    out = []
    last_side = None
    for i in range(len(pts)):
        a = pts[max(0, i - 1)]
        b = pts[min(len(pts) - 1, i + 1)]
        t = Vec3(b) - Vec3(a)
        n = Vec3(pts[i])
        t -= n * t.dot(n)
        if t.lengthSquared() > 1e-14:
            t.normalize()
            side = t.cross(n)
            if side.lengthSquared() > 1e-14:
                side.normalize()
                last_side = side
        out.append(Vec3(last_side) if last_side is not None
                   else Vec3(0, 0, 0))
    return out


def make_rail_node(name, pts, R):
    """A RAILROAD's drawn form: two silver running rails with dark
    brown cross-ties between them, all one GeomNode, road-sized."""
    from panda3d.core import (Geom, GeomNode, GeomTriangles,
                              GeomVertexData, GeomVertexFormat,
                              GeomVertexWriter)
    gauge = 0.000042        # half-distance between the two rails, rad
    rail_hw = 0.000014      # each rail's half-width
    verge_hw = 0.000026     # dark verge under each rail, wider
    tie_hl = 0.000090       # ties POKE OUT past the outer rail edges
    tie_hw = 0.000016       # tie half-width along the track
    tie_gap = 0.000167      # radians of arc between tie centres
    silver = (0.72, 0.74, 0.78, 1.0)
    verge_c = (0.24, 0.19, 0.14, 1.0)
    brown = (0.30, 0.22, 0.14, 1.0)

    fmt = GeomVertexFormat.getV3c4()
    vdata = GeomVertexData(name, fmt, Geom.UHStatic)
    vw = GeomVertexWriter(vdata, 'vertex')
    cw = GeomVertexWriter(vdata, 'color')
    tris = GeomTriangles(Geom.UHStatic)
    vcount = 0
    sides = _side_frames(pts)

    def quad(p0, p1, p2, p3, col):
        nonlocal vcount
        for p in (p0, p1, p2, p3):
            v = Vec3(p)
            v.normalize()
            v *= R
            vw.addData3(v)
            cw.addData4(*col)
        tris.addVertices(vcount, vcount + 1, vcount + 2)
        tris.addVertices(vcount, vcount + 2, vcount + 3)
        vcount += 4

    # the ties: even arc spacing along the WHOLE section (segments
    # are far shorter than a tie interval, so the walk must carry
    # across them or no tie would ever fit)
    arcs = [0.0]
    for i in range(len(pts) - 1):
        arcs.append(arcs[-1] + angle_between(Vec3(pts[i]),
                                             Vec3(pts[i + 1])))
    total = arcs[-1]
    seg_i = 0
    k = 1
    while k * tie_gap < total:
        t = k * tie_gap
        k += 1
        while seg_i < len(arcs) - 2 and arcs[seg_i + 1] < t:
            seg_i += 1
        seg = arcs[seg_i + 1] - arcs[seg_i]
        if seg < 1e-9:
            continue
        f = (t - arcs[seg_i]) / seg
        a, b = Vec3(pts[seg_i]), Vec3(pts[seg_i + 1])
        mid = a + (b - a) * f
        side = sides[seg_i]
        fwd = b - a
        n = Vec3(mid)
        if n.lengthSquared() > 1e-12:
            nn = Vec3(n)
            nn.normalize()
            fwd -= nn * fwd.dot(nn)
        if fwd.lengthSquared() > 1e-14:
            fwd.normalize()
        if side.lengthSquared() < 1e-14:
            continue
        quad(mid - side * tie_hl - fwd * tie_hw,
             mid + side * tie_hl - fwd * tie_hw,
             mid + side * tie_hl + fwd * tie_hw,
             mid - side * tie_hl + fwd * tie_hw, brown)

    # the running rails ride OVER the ties: dark verge under each,
    # silver on top
    for off in (-gauge, gauge):
        for hw_, col in ((verge_hw, verge_c), (rail_hw, silver)):
            for i in range(len(pts) - 1):
                s0, s1 = sides[i], sides[i + 1]
                a = Vec3(pts[i]) + s0 * off
                b = Vec3(pts[i + 1]) + s1 * off
                quad(a - s0 * hw_, a + s0 * hw_,
                     b + s1 * hw_, b - s1 * hw_, col)

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    node = GeomNode(name)
    node.addGeom(geom)
    return node
