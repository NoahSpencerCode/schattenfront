"""
3D globe rendering: the base sphere with the paper-map texture, a
rotating day/night terminator, country name labels, surface-hugging
decal helpers — and the zoom detail overlay, a spherical patch whose
texture is repainted in realtime (on a worker thread) from the 10m
vector data whenever the camera closes in.  Google-maps style, but 1939.
"""

import math
import os
import shutil
import threading

import numpy as np
from panda3d.core import (Geom, GeomNode, GeomTriangles, GeomVertexData,
                          GeomVertexFormat, GeomVertexWriter, LineSegs,
                          Mat3, NodePath, Quat, Shader, TextNode, Texture,
                          TransparencyAttrib, Vec3, SamplerState,
                          ColorBlendAttrib)

from config import (GLOBE_RADIUS, GLOBE_SEGMENTS, GLOBE_RINGS,
                    NIGHT_DARKNESS, DETAIL_ACTIVATE_ALT, DETAIL_TEX_SIZE,
                    DETAIL_TIER_ALTS,
                    FOG_BRIGHTNESS, FOG_SATURATION, MAX_VISION_SOURCES,
                    LIFT_PATCH, LIFT_RING)
from geodata import CACHE_DIR, TEXTURE_VERSION
from utils import latlon_to_vec, north_tangent

# Detail tiles are static for a given map version (units, bridges and
# engineer roads are separate markers, not painted into the texture), so
# finished tiles are cached on disk ready for upload -- revisiting an
# area loads in milliseconds instead of re-rendering.
TILE_CACHE_DIR = os.path.join(
    CACHE_DIR, "tiles_v%d_%d" % (TEXTURE_VERSION, DETAIL_TEX_SIZE))


def _prune_stale_tile_caches():
    """Drop tile caches from older map versions."""
    try:
        for name in os.listdir(CACHE_DIR):
            path = os.path.join(CACHE_DIR, name)
            if (name.startswith('tiles_v') and os.path.isdir(path)
                    and path != TILE_CACHE_DIR):
                shutil.rmtree(path, ignore_errors=True)
    except OSError:
        pass


# --------------------------------------------------------------- sphere mesh

def make_sphere_mesh(radius, segments, rings):
    """UV sphere with normals and equirectangular texture coordinates."""
    fmt = GeomVertexFormat.getV3n3t2()
    vdata = GeomVertexData('globe', fmt, Geom.UHStatic)
    vdata.setNumRows((rings + 1) * (segments + 1))
    vw = GeomVertexWriter(vdata, 'vertex')
    nw = GeomVertexWriter(vdata, 'normal')
    tw = GeomVertexWriter(vdata, 'texcoord')

    for r in range(rings + 1):
        lat = 90.0 - 180.0 * r / rings
        v = 1.0 - r / rings
        for s in range(segments + 1):
            lon = -180.0 + 360.0 * s / segments
            n = latlon_to_vec(lat, lon)
            vw.addData3(n * radius)
            nw.addData3(n)
            tw.addData2(s / segments, v)

    tris = GeomTriangles(Geom.UHStatic)
    stride = segments + 1
    for r in range(rings):
        for s in range(segments):
            a = r * stride + s
            b = a + 1
            c = a + stride
            d = c + 1
            tris.addVertices(a, c, b)
            tris.addVertices(b, c, d)
    geom = Geom(vdata)
    geom.addPrimitive(tris)
    node = GeomNode('globe')
    node.addGeom(geom)
    return NodePath(node)


def make_lonlat_patch(radius, lon0, lat0, lon1, lat1, segs=40):
    """Spherical surface patch over a lon/lat window, UV-mapped 0..1."""
    fmt = GeomVertexFormat.getV3n3t2()
    vdata = GeomVertexData('patch', fmt, Geom.UHStatic)
    vdata.setNumRows((segs + 1) * (segs + 1))
    vw = GeomVertexWriter(vdata, 'vertex')
    nw = GeomVertexWriter(vdata, 'normal')
    tw = GeomVertexWriter(vdata, 'texcoord')
    for iy in range(segs + 1):
        lat = lat0 + (lat1 - lat0) * iy / segs
        for ix in range(segs + 1):
            lon = lon0 + (lon1 - lon0) * ix / segs
            n = latlon_to_vec(lat, lon)
            vw.addData3(n * radius)
            nw.addData3(n)
            tw.addData2(ix / segs, iy / segs)
    tris = GeomTriangles(Geom.UHStatic)
    stride = segs + 1
    for iy in range(segs):
        for ix in range(segs):
            a = iy * stride + ix
            b = a + 1
            c = a + stride
            d = c + 1
            tris.addVertices(a, b, c)
            tris.addVertices(b, d, c)
    geom = Geom(vdata)
    geom.addPrimitive(tris)
    gn = GeomNode('detail_patch')
    gn.addGeom(geom)
    return NodePath(gn)


# ---------------------------------------------------------- day/night shader

DAYNIGHT_VERT = """
#version 120
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
attribute vec4 p3d_Vertex;
attribute vec3 p3d_Normal;
attribute vec2 p3d_MultiTexCoord0;
varying vec2 uv;
varying vec3 world_normal;
void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    uv = p3d_MultiTexCoord0;
    world_normal = normalize(mat3(p3d_ModelMatrix) * p3d_Normal);
}
"""

DAYNIGHT_FRAG = """
#version 120
uniform sampler2D p3d_Texture0;
uniform vec3 sun_dir;
uniform float night_darkness;
uniform vec4 vision[%(nvis)d];    // xyz = centre dir, w = cos(radius)
uniform int vision_count;
// wireless net: xyz = centre dir, w = cos(radius); the outline drawn is
// the PERIMETER OF THE UNION -- arcs inside another circle are negated
uniform vec4 comm[%(nvis)d];
uniform int comm_count;
uniform float comm_cos_eps;       // cos/sin of the outline half-width
uniform float comm_sin_eps;
uniform float fog_brightness;
uniform float fog_saturation;
varying vec2 uv;
varying vec3 world_normal;
void main() {
    vec3 nrm = normalize(world_normal);
    vec4 tex = texture2D(p3d_Texture0, uv);
    float d = dot(nrm, normalize(sun_dir));
    float daylight = smoothstep(-0.08, 0.18, d);
    float shade = mix(1.0 - night_darkness, 1.0, daylight);
    vec3 c = tex.rgb * shade;
    // sharp-edged vision fields: outside them the map is darker and
    // drained of colour
    bool seen = false;
    for (int i = 0; i < %(nvis)d; i++) {
        if (i >= vision_count) break;
        if (dot(nrm, vision[i].xyz) > vision[i].w) { seen = true; break; }
    }
    if (!seen) {
        float g = dot(c, vec3(0.299, 0.587, 0.114));
        c = mix(vec3(g), c, fog_saturation) * fog_brightness;
    }
    // merged comm-area outline
    bool near_edge = false;
    bool inside = false;
    for (int i = 0; i < %(nvis)d; i++) {
        if (i >= comm_count) break;
        float w = comm[i].w;
        float s = sqrt(max(0.0, 1.0 - w * w));
        float c_in  = w * comm_cos_eps + s * comm_sin_eps;  // cos(r-eps)
        float c_out = w * comm_cos_eps - s * comm_sin_eps;  // cos(r+eps)
        float dc = dot(nrm, comm[i].xyz);
        if (dc > c_in) { inside = true; break; }
        if (dc >= c_out) near_edge = true;
    }
    if (near_edge && !inside) {
        c = mix(c, vec3(0.98, 0.98, 0.96), 0.8);   // white signals line
    }
    gl_FragColor = vec4(c, 1.0);
}
""" % {'nvis': MAX_VISION_SOURCES}


class Globe:
    """The world sphere plus its cosmetic layers."""

    def __init__(self, base, world_data):
        self.base = base
        self.world = world_data
        self.radius = GLOBE_RADIUS
        self.root = base.render.attachNewNode('globe_root')

        self.node = make_sphere_mesh(GLOBE_RADIUS, GLOBE_SEGMENTS, GLOBE_RINGS)
        self.node.reparentTo(self.root)

        tex = base.loader.loadTexture(world_data.texture_path)
        tex.setMinfilter(SamplerState.FTLinearMipmapLinear)
        tex.setMagfilter(SamplerState.FTLinear)
        tex.setAnisotropicDegree(4)
        self.node.setTexture(tex)

        self.shader = Shader.make(Shader.SL_GLSL, DAYNIGHT_VERT,
                                  DAYNIGHT_FRAG)
        self.node.setShader(self.shader)
        # shader inputs live on the root so the detail patch (a child)
        # inherits them too
        from panda3d.core import PTA_LVecBase4f, Vec4
        self._vision_pta = PTA_LVecBase4f.emptyArray(MAX_VISION_SOURCES)
        self._comm_pta = PTA_LVecBase4f.emptyArray(MAX_VISION_SOURCES)
        self.root.setShaderInput('sun_dir', Vec3(1, 0, 0))
        self.root.setShaderInput('night_darkness', NIGHT_DARKNESS)
        self.root.setShaderInput('vision', self._vision_pta)
        self.root.setShaderInput('vision_count', 0)
        self.root.setShaderInput('comm', self._comm_pta)
        self.root.setShaderInput('comm_count', 0)
        eps = 0.0015                    # outline half-width, radians
        self.root.setShaderInput('comm_cos_eps', math.cos(eps))
        self.root.setShaderInput('comm_sin_eps', math.sin(eps))
        self.root.setShaderInput('fog_brightness', FOG_BRIGHTNESS)
        self.root.setShaderInput('fog_saturation', FOG_SATURATION)

        self.detail = DetailOverlay(base, world_data, self.root, self.shader)
        self._make_country_labels()

    def set_sun_direction(self, sun_dir):
        self.root.setShaderInput('sun_dir', sun_dir)

    def set_vision(self, entries):
        """entries: [(unit_vec, radius_world_units), ...] — the sharp
        vision fields inside which the map keeps its full colour."""
        from panda3d.core import Vec4
        n = min(len(entries), MAX_VISION_SOURCES)
        for i in range(n):
            pos, radius = entries[i]
            self._vision_pta.setElement(
                i, Vec4(pos.x, pos.y, pos.z,
                        math.cos(radius / GLOBE_RADIUS)))
        self.root.setShaderInput('vision_count', n)

    def set_comm(self, entries):
        """entries: [(unit_vec, radius_world_units), ...] — the shader
        draws only the union perimeter of these circles."""
        from panda3d.core import Vec4
        n = min(len(entries), MAX_VISION_SOURCES)
        for i in range(n):
            pos, radius = entries[i]
            self._comm_pta.setElement(
                i, Vec4(pos.x, pos.y, pos.z,
                        math.cos(radius / GLOBE_RADIUS)))
        self.root.setShaderInput('comm_count', n)

    def set_comm_width(self, alt):
        """Scale the outline half-width with camera altitude so the ink
        line stays a few pixels wide at every zoom."""
        eps = max(0.000075, min(0.002, 0.000045 * alt))
        self.root.setShaderInput('comm_cos_eps', math.cos(eps))
        self.root.setShaderInput('comm_sin_eps', math.sin(eps))

    # -------------------------------------------------------- country labels
    def _make_country_labels(self):
        """Light-grey names etched onto the map, shown only zoomed out."""
        self.label_root = self.root.attachNewNode('country_labels')
        self.label_root.setTransparency(TransparencyAttrib.MAlpha)
        self.label_root.setLightOff()
        for (name, lat, lon) in self.world.country_labels:
            tn = TextNode('label_' + name)
            tn.setText(name)
            tn.setTextColor(0.82, 0.82, 0.80, 0.85)
            tn.setAlign(TextNode.ACenter)
            if self.base.map_font:
                tn.setFont(self.base.map_font)
            np_ = self.label_root.attachNewNode(tn)
            pos = latlon_to_vec(lat, lon) * (self.radius * 1.002)
            np_.setPos(pos)
            np_.lookAt(self.root, (0, 0, 0), Vec3(0, 0, 1))
            np_.setScale(self.radius * 0.02)
            np_.setDepthOffset(2)
        self.label_root.flattenStrong()

    def set_labels_visible(self, visible):
        if visible and self.label_root.isHidden():
            self.label_root.show()
        elif not visible and not self.label_root.isHidden():
            self.label_root.hide()

    def destroy(self):
        self.detail.destroy()
        self.root.removeNode()


class DetailOverlay:
    """High-detail map patch under the camera, repainted in realtime.

    When the camera altitude drops below DETAIL_ACTIVATE_ALT a worker
    thread renders a lon/lat window from the 10m vector data and drapes
    it over the globe as a slightly-raised spherical patch.

    The zoom range is quantized into THREE fixed tiers: each tier
    renders one fixed-size window, so zooming within a tier changes
    NOTHING -- no re-render, no shifting stroke widths, no fidelity
    wiggle. Only crossing a tier boundary (or panning past the recentre
    step) triggers a repaint. Each window is painted as an n x n mosaic
    of DETAIL_TEX_SIZE tiles delivered at most one per frame, so the
    main thread never uploads more than one small texture per frame --
    a tier switch costs the same per frame as the old continuous path.
    """

    LIFT = LIFT_PATCH
    # per-tier half-height of the rendered window, degrees (the 1.43
    # factor = the old 1.1 view margin grown 30%); tier 0 is the
    # ultra-close street-level stretch
    TIER_HALF_LAT = tuple(a * 1.43 for a in DETAIL_TIER_ALTS) + (39.0,)
    # each tier renders as an n x n mosaic of DETAIL_TEX_SIZE tiles:
    # tier 0 uses a 5x5 (10240 effective) so street level stays sharp
    # over its doubled range; every main-thread upload stays one small
    # proven-cheap tile
    TIER_TILES = (5, 3, 3)

    def __init__(self, base, world, parent, shader):
        _prune_stale_tile_caches()
        self.base = base
        self.world = world
        self.parent = parent
        self.shader = shader
        self.tiles = []             # tile NodePaths of the shown window
        self.window = None          # (lon0, lat0, lon1, lat1) on display
        self._want = None           # window we should be showing
        self._tier = None           # current render tier (0 = closest)
        self._worker = None
        self._render_window = None  # window the worker is delivering
        self._incoming = []         # tile NodePaths delivered so far
        self._queue = []            # finished renders [(win, bytes, w, h)]
        self._qlock = threading.Lock()
        self._done = False          # worker finished the current mosaic
        self._lift_b = False        # alternate lift per generation
        self._gen = 0               # bumping this aborts the worker

    # ------------------------------------------------------------- window
    @staticmethod
    def _quantize(value, step):
        return round(value / step) * step

    def _tier_for(self, alt):
        """Which fixed render tier covers this altitude. A little
        hysteresis stops flapping right at a boundary."""
        bounds = DETAIL_TIER_ALTS
        cur = self._tier
        if cur is None:
            for i, b in enumerate(bounds):
                if alt <= b:
                    return i
            return len(bounds)
        t = cur
        while t < len(bounds) and alt > bounds[t] * 1.06:
            t += 1
        while t > 0 and alt < bounds[t - 1] * 0.94:
            t -= 1
        return t

    def _window_for(self, cam_lat, cam_lon, tier):
        half_lat = self.TIER_HALF_LAT[tier]
        step = half_lat / 2.0
        clat = max(-88.0, min(88.0, self._quantize(cam_lat, step)))
        clon = self._quantize(cam_lon, step)
        coslat = max(0.15, math.cos(math.radians(clat)))
        half_lon = min(45.0, half_lat / coslat)
        lat0 = max(-90.0, clat - half_lat)
        lat1 = min(90.0, clat + half_lat)
        return (clon - half_lon, lat0, clon + half_lon, lat1)

    # ------------------------------------------------------------- update
    def update(self, cam_lat, cam_lon, cam_dist, sun_dir):
        alt = cam_dist - GLOBE_RADIUS
        if alt > DETAIL_ACTIVATE_ALT:
            for t in self.tiles:
                t.hide()
            self._want = None
            self._tier = None
            return
        self._tier = self._tier_for(alt)
        self._want = self._window_for(cam_lat, cam_lon, self._tier)
        for t in self.tiles:
            t.show()
        # a fast zoom/pan made the in-flight mosaic obsolete: abort it
        # NOW rather than letting its remaining tiles render first
        if (self._render_window is not None
                and self._render_window != self._want):
            self._abort_render()
        # deliver AT MOST ONE finished tile per frame: the main-thread
        # cost per frame never exceeds one small texture upload, so a
        # tier switch cannot stall the game
        self._deliver_one()
        self._promote_if_complete()
        # kick off a mosaic render if the wanted window changed
        if (self._want != self.window
                and self._render_window is None):
            self._launch(self._want, self._tier)

    def _abort_render(self):
        self._gen += 1                  # worker exits at its next check
        with self._qlock:
            self._queue = []
        for t in self._incoming:
            t.removeNode()
        self._incoming = []
        self._render_window = None
        self._done = False

    def _launch(self, window, tier):
        n = self.TIER_TILES[tier]
        self._render_window = window
        self._done = False
        self._gen += 1
        gen = self._gen
        lon0, lat0, lon1, lat1 = window
        dlon = (lon1 - lon0) / n
        dlat = (lat1 - lat0) / n
        # render the CENTRE of the view first, then spiral outward, so
        # the part the player is looking at refreshes soonest
        order = sorted(((i, j) for i in range(n) for j in range(n)),
                       key=lambda ij: ((ij[0] + 0.5 - n / 2.0) ** 2 +
                                       (ij[1] + 0.5 - n / 2.0) ** 2))

        nbytes = DETAIL_TEX_SIZE * DETAIL_TEX_SIZE * 3

        def work():
            for (i, j) in order:
                if self._gen != gen:
                    return              # superseded by a newer window
                sw = (lon0 + i * dlon, lat0 + j * dlat,
                      lon0 + (i + 1) * dlon, lat0 + (j + 1) * dlat)
                key = os.path.join(TILE_CACHE_DIR,
                                   "%.4f_%.4f_%.4f_%.4f.bgr" % sw)
                data = None
                try:                    # cache hit: ready-to-upload bytes
                    with open(key, 'rb') as f:
                        data = f.read()
                    if len(data) != nbytes:
                        data = None
                except OSError:
                    data = None
                if data is None:
                    img = self.world.render_region(
                        sw[0], sw[1], sw[2], sw[3],
                        DETAIL_TEX_SIZE, DETAIL_TEX_SIZE,
                        border_w=3, road_w=4, mottle=True)
                    if self._gen != gen:
                        return
                    arr = np.asarray(img, dtype=np.uint8)
                    data = np.flipud(arr)[:, :, ::-1].tobytes()
                    try:
                        os.makedirs(TILE_CACHE_DIR, exist_ok=True)
                        tmp = key + '.tmp%d' % gen
                        with open(tmp, 'wb') as f:
                            f.write(data)
                        os.replace(tmp, key)
                    except OSError:
                        pass
                if self._gen != gen:
                    return
                with self._qlock:
                    self._queue.append((sw, data,
                                        DETAIL_TEX_SIZE, DETAIL_TEX_SIZE))
            if self._gen == gen:
                self._done = True
                self._worker = None

        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()

    def _deliver_one(self):
        with self._qlock:
            item = self._queue.pop(0) if self._queue else None
        if item is None:
            return
        sw, data, w, h = item
        tex = Texture('detail')
        tex.setup2dTexture(w, h, Texture.TUnsignedByte, Texture.FRgb8)
        tex.setRamImage(data)
        tex.setMinfilter(SamplerState.FTLinear)
        tex.setMagfilter(SamplerState.FTLinear)
        tex.setWrapU(SamplerState.WMClamp)
        tex.setWrapV(SamplerState.WMClamp)
        # incoming generation sits at the alternate lift so it draws
        # over the tiles it is replacing without z-fighting
        lift = self.LIFT * (1.0003 if self._lift_b else 1.0)
        p = make_lonlat_patch(GLOBE_RADIUS * lift,
                              sw[0], sw[1], sw[2], sw[3], segs=20)
        p.reparentTo(self.parent)
        p.setTexture(tex)
        p.setShader(self.shader)    # inputs inherited from parent
        p.setDepthOffset(2 if self._lift_b else 1)
        self._incoming.append(p)

    def _promote_if_complete(self):
        if (self._render_window is None or not self._done
                or self._queue or self._worker is not None):
            return
        for t in self.tiles:
            t.removeNode()
        self.tiles = self._incoming
        self._incoming = []
        self.window = self._render_window
        self._render_window = None
        self._done = False
        self._lift_b = not self._lift_b

    def destroy(self):
        self._want = None
        self._abort_render()            # stops the worker between tiles
        for t in self.tiles:
            t.removeNode()
        self.tiles = []


# -------------------------------------------------- surface rings and discs

def make_surface_ring(parent, radius, angular_radius, color, thickness=1.5,
                      segments=48):
    """A circle on the sphere surface around the +Z axis.

    Parent it to a node oriented so +Z points through the desired centre.
    """
    segs = LineSegs()
    segs.setThickness(thickness)
    segs.setColor(*color)
    sin_a = math.sin(angular_radius)
    cos_a = math.cos(angular_radius)
    lift = LIFT_RING
    for i in range(segments + 1):
        ang = 2 * math.pi * i / segments
        p = Vec3(sin_a * math.cos(ang), sin_a * math.sin(ang), cos_a)
        p *= radius * lift
        if i == 0:
            segs.moveTo(p)
        else:
            segs.drawTo(p)
    np_ = parent.attachNewNode(segs.create())
    np_.setLightOff()
    np_.setDepthOffset(4)
    return np_


def make_surface_disc(parent, radius, angular_radius, color, rings=5,
                      segments=28, additive=True):
    """A translucent spherical cap (used as the vision-field highlight)."""
    fmt = GeomVertexFormat.getV3c4()
    vdata = GeomVertexData('disc', fmt, Geom.UHStatic)
    vw = GeomVertexWriter(vdata, 'vertex')
    cw = GeomVertexWriter(vdata, 'color')
    lift = 1.003

    vw.addData3(Vec3(0, 0, 1) * radius * lift)
    cw.addData4(*color)
    for r in range(1, rings + 1):
        a = angular_radius * r / rings
        sin_a, cos_a = math.sin(a), math.cos(a)
        edge = 1.0 - (r / rings) ** 3  # soft edge falloff
        for s in range(segments):
            ang = 2 * math.pi * s / segments
            p = Vec3(sin_a * math.cos(ang), sin_a * math.sin(ang), cos_a)
            vw.addData3(p * radius * lift)
            cw.addData4(color[0], color[1], color[2], color[3] * edge)

    tris = GeomTriangles(Geom.UHStatic)
    for s in range(segments):
        tris.addVertices(0, 1 + s, 1 + (s + 1) % segments)
    for r in range(rings - 1):
        base0 = 1 + r * segments
        base1 = base0 + segments
        for s in range(segments):
            s2 = (s + 1) % segments
            tris.addVertices(base0 + s, base1 + s, base0 + s2)
            tris.addVertices(base0 + s2, base1 + s, base1 + s2)
    geom = Geom(vdata)
    geom.addPrimitive(tris)
    gn = GeomNode('disc')
    gn.addGeom(geom)
    np_ = parent.attachNewNode(gn)
    np_.setTransparency(TransparencyAttrib.MAlpha)
    if additive:
        np_.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd,
                                            ColorBlendAttrib.OIncomingAlpha,
                                            ColorBlendAttrib.OOne))
    np_.setDepthWrite(False)
    np_.setLightOff()
    np_.setBin('transparent', 10)
    return np_


def orient_to_surface(node, unit_vec):
    """Rotate node so its +Z axis points along unit_vec (from globe centre),
    +Y toward geographic north and +X toward east — flat map markers and
    text parented to it read upright and unmirrored from outside."""
    n = Vec3(unit_vec)
    n.normalize()
    t = north_tangent(n)
    e = t.cross(n)          # east
    mat = Mat3(e.x, e.y, e.z,
               t.x, t.y, t.z,
               n.x, n.y, n.z)
    q = Quat()
    q.setFromMatrix(mat)
    node.setPos(0, 0, 0)
    node.setQuat(q)
