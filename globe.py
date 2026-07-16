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

from config import (COUNTRIES,
                    GLOBE_RADIUS, GLOBE_SEGMENTS, GLOBE_RINGS,
                    NIGHT_DARKNESS, DETAIL_ACTIVATE_ALT, DETAIL_TEX_SIZE,
                    DETAIL_TIER_ALTS,
                    FOG_BRIGHTNESS, FOG_SATURATION, MAX_VISION_SOURCES,
                    LIFT_PATCH, LIFT_RING)
from geodata import CACHE_DIR, TEXTURE_VERSION

# owner index order for the border shader (5 = neutral, never tinted)
NAT_ORDER = ('britain', 'germany', 'usa', 'japan', 'soviet', 'neutral')
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
// national territory: Voronoi cells around the cities. sites.w is the
// owner index; owner 5 (neutral) draws no tint. The frontier is the
// locus halfway between nearest cities of DIFFERENT owners.
uniform int site_count;          // 0 until the border bake has landed
uniform vec3 nat_tint[6];
uniform sampler2D border_dA;     // bilinear float: empires 0-3 smooth-
uniform sampler2D border_dB;     // min distance fields; 4-5 in B
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
    // national territory tint + dotted frontier. WHICH two sites matter
    // per pixel comes from a small baked ID map (no per-fragment site
    // loop = cheap); the frontier itself is analytic: gradient-
    // normalized so the dotted line keeps a CONSTANT width and regular
    // dashes however the cities happen to lie.
    if (site_count > 0) {
        vec2 buv = vec2(atan(nrm.y, nrm.x) * 0.15915494 + 0.5,
                        asin(clamp(nrm.z, -1.0, 1.0)) * 0.31830988 + 0.5);
        // ONE globally continuous smooth-min distance field PER EMPIRE
        // (baked over every city that empire owns). The shader argmins
        // six smooth numbers -- there are no site pairs anywhere, so no
        // seams, wedges or staircases can exist, even at triple points.
        // Line thickness comes from screen-space derivatives: exactly
        // constant pixel width at every zoom.
        vec4 fA = texture2D(border_dA, buv);
        vec4 fB = texture2D(border_dB, buv);
        bool land_px = distance(tex.rgb, vec3(0.173, 0.227, 0.310)) > 0.12
                    && distance(tex.rgb, vec3(0.243, 0.329, 0.431)) > 0.07;
        float d1 = fA.r; int owner = 0;
        if (fA.g < d1) { d1 = fA.g; owner = 1; }
        if (fA.b < d1) { d1 = fA.b; owner = 2; }
        if (fA.a < d1) { d1 = fA.a; owner = 3; }
        if (fB.r < d1) { d1 = fB.r; owner = 4; }
        if (fB.g < d1) { d1 = fB.g; owner = 5; }
        float d2 = 9.0;
        if (owner != 0 && fA.r < d2) d2 = fA.r;
        if (owner != 1 && fA.g < d2) d2 = fA.g;
        if (owner != 2 && fA.b < d2) d2 = fA.b;
        if (owner != 3 && fA.a < d2) d2 = fA.a;
        if (owner != 4 && fB.r < d2) d2 = fB.r;
        if (owner != 5 && fB.g < d2) d2 = fB.g;
        // screen-space derivatives MUST run in uniform control flow
        // (inside a divergent branch they are undefined and speckle the
        // whole map on tile-based GPUs)
        float sdr = d2 - d1;                  // 0 on the frontier
        float wpx = abs(sdr) / max(fwidth(sdr), 1e-6);
        float rpx_den = max(fwidth(d1), 1e-6);
        // the empire's writ runs only so far; the cap undulates on
        // smooth sines so empty country gets an organic frontier
        float wob = 0.004 * (sin(nrm.x * 21.0) + sin(nrm.y * 17.0)
                             + sin(nrm.z * 25.0));
        float reach = 0.11 + wob;
        float rpx = abs(reach - d1) / rpx_den;
        if (land_px && d1 < reach && owner < 5) {
            c = mix(c, nat_tint[owner], 0.22);
            // round screen-space dots: identical size and spacing at
            // every zoom, a true dotted line (no checkering)
            vec2 dp = fract(gl_FragCoord.xy / 7.0) - 0.5;
            bool dot_on = dot(dp, dp) < 0.09;
            if (dot_on && (wpx < 1.4 || rpx < 1.4)) {
                c = mix(c, vec3(0.06, 0.05, 0.04), 0.85);
            }
        }
    }
    gl_FragColor = vec4(c, 1.0);
}
""" % {'nvis': MAX_VISION_SOURCES, 'nsites': 200}


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
        # national borders: Voronoi sites (the cities) + owner tints
        from panda3d.core import PTA_LVecBase3f
        self._sites_pta = PTA_LVecBase4f.emptyArray(200)
        self._tint_pta = PTA_LVecBase3f.emptyArray(6)
        for i, key in enumerate(NAT_ORDER):
            col = COUNTRIES[key]['color']
            self._tint_pta.setElement(i, Vec3(col[0], col[1], col[2]))
        self.root.setShaderInput('sites', self._sites_pta)
        self.root.setShaderInput('site_count', 0)
        self.root.setShaderInput('nat_tint', self._tint_pta)
        self.root.setShaderInput('border_eps', 0.0022)
        self._border_gen = 0
        self._border_bake = None
        self._pending_site_count = 0
        for name in ('border_dA', 'border_dB'):
            fdummy = Texture(name)
            fdummy.setup2dTexture(1, 1, Texture.TFloat, Texture.FRgba32)
            fdummy.setRamImage(
                np.full(4, 9.0, dtype=np.float32).tobytes())
            self.root.setShaderInput(name, fdummy)

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
        """Scale the outline half-widths with camera altitude so the
        lines stay a few pixels wide at every zoom."""
        eps = max(0.000075, min(0.002, 0.000045 * alt))
        self.root.setShaderInput('comm_cos_eps', math.cos(eps))
        self.root.setShaderInput('comm_sin_eps', math.sin(eps))
        self.root.setShaderInput('border_eps',
                                 max(0.0001, min(0.0015, 0.00003 * alt)))

    # ------------------------------------------------- national borders
    # The per-pixel "which two cities matter" question is baked into a
    # small ID map on a worker thread (once per ownership change); the
    # shader then does constant-time analytic work per fragment.
    BIDS_W, BIDS_H = 2048, 1024
    _bids_grid = None               # cached texel unit vectors

    def _border_grid(self):
        if Globe._bids_grid is None:
            lon = (np.arange(self.BIDS_W, dtype=np.float32) + 0.5) \
                / self.BIDS_W * 2.0 * np.pi - np.pi
            lat = (np.arange(self.BIDS_H, dtype=np.float32) + 0.5) \
                / self.BIDS_H * np.pi - np.pi / 2.0
            cl = np.cos(lat)[:, None]
            g = np.empty((self.BIDS_H, self.BIDS_W, 3), dtype=np.float32)
            g[:, :, 0] = cl * np.cos(lon)[None, :]
            g[:, :, 1] = cl * np.sin(lon)[None, :]
            g[:, :, 2] = np.sin(lat)[:, None]
            Globe._bids_grid = g.reshape(-1, 3)
        return Globe._bids_grid

    def set_borders(self, entries):
        """entries: [(unit_vec, owner_index 0..5), ...]. Bakes, on a
        worker thread, the COMPLETE smooth-min distance fields over
        every city of every empire: signed frontier distance + own-
        empire distance per texel (float, bilinear at draw), plus the
        owner pair per texel. Globally continuous by construction, so
        the drawn borders can have no seams or slivers."""
        self._border_gen += 1
        gen = self._border_gen
        n = len(entries)
        self._pending_site_count = n
        S = np.array([[p.x, p.y, p.z] for (p, o) in entries],
                     dtype=np.float32).T          # (3, n)
        owners = np.array([o for (p, o) in entries], dtype=np.int64)
        onehot = np.zeros((n, 6), dtype=np.float32)
        onehot[np.arange(n), owners] = 1.0

        def bake():
            K = 0.02                # smooth-min radius, radians
            grid = self._border_grid()
            total = grid.shape[0]
            dist6 = np.empty((total, 6), dtype=np.float32)
            step = 65536
            for a in range(0, total, step):
                b = min(total, a + step)
                with np.errstate(all='ignore'):
                    dots = grid[a:b] @ S              # (chunk, n)
                np.clip(dots, -1.0, 1.0, out=dots)
                ang = np.arccos(dots)
                # smooth-min distance to EVERY empire at once
                with np.errstate(all='ignore'):
                    E = np.exp(ang * (-1.0 / K)) @ onehot   # (chunk, 6)
                dist6[a:b] = -K * np.log(np.maximum(E, 1e-30))
            fa = np.zeros((total, 4), dtype=np.float32)
            fa[:, 2] = dist6[:, 0]                    # BGRA: R at [2]
            fa[:, 1] = dist6[:, 1]                    # G at [1]
            fa[:, 0] = dist6[:, 2]                    # B at [0]
            fa[:, 3] = dist6[:, 3]                    # A at [3]
            fb = np.zeros((total, 4), dtype=np.float32)
            fb[:, 2] = dist6[:, 4]
            fb[:, 1] = dist6[:, 5]
            self._border_bake = (gen, fa.tobytes(), fb.tobytes())

        threading.Thread(target=bake, daemon=True).start()

    def tick_border_bake(self):
        """Main thread: upload a finished border bake (cheap, rare)."""
        bake = self._border_bake
        if bake is None or bake[0] != self._border_gen:
            return
        self._border_bake = None
        gen, fa_data, fb_data = bake
        for name, data in (('border_dA', fa_data), ('border_dB', fb_data)):
            ftex = Texture(name)
            ftex.setup2dTexture(self.BIDS_W, self.BIDS_H,
                                Texture.TFloat, Texture.FRgba32)
            ftex.setRamImage(data)
            ftex.setMinfilter(SamplerState.FTLinear)
            ftex.setMagfilter(SamplerState.FTLinear)
            ftex.setWrapU(SamplerState.WMRepeat)
            ftex.setWrapV(SamplerState.WMClamp)
            self.root.setShaderInput(name, ftex)
        self.root.setShaderInput('site_count', self._pending_site_count)

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
