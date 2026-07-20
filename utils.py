"""
Utility math for a spherical world.

Positions are stored as unit vectors (Vec3-like tuples or panda Vec3) on the
unit sphere; multiply by GLOBE_RADIUS for render coordinates.
Latitude/longitude are in degrees, lon in [-180, 180], lat in [-90, 90].
"""

import math

import numpy as np
import os

from panda3d.core import Vec3


# ---------------------------------------------------------------- conversions

def latlon_to_vec(lat, lon):
    """Lat/lon degrees -> unit vector on sphere."""
    la = math.radians(lat)
    lo = math.radians(lon)
    return Vec3(math.cos(la) * math.cos(lo),
                math.cos(la) * math.sin(lo),
                math.sin(la))


def vec_to_latlon(v):
    """Unit vector -> (lat, lon) degrees."""
    n = Vec3(v)
    n.normalize()
    lat = math.degrees(math.asin(max(-1.0, min(1.0, n.z))))
    lon = math.degrees(math.atan2(n.y, n.x))
    return lat, lon


def angle_between(a, b):
    """Angle in radians between two unit vectors.

    Computed from the CHORD, not the dot product: float32 dots
    quantize to 1.0 below ~5e-4 rad, which made every angle smaller
    than half a millirad read as zero -- units teleported across dense
    path points. The chord keeps full precision at small angles."""
    dx = b.x - a.x
    dy = b.y - a.y
    dz = b.z - a.z
    half = 0.5 * math.sqrt(dx * dx + dy * dy + dz * dz)
    if half >= 1.0:
        return math.pi
    if half < 0.3:
        # asin is ill-conditioned only near 1; here it is exact
        return 2.0 * math.asin(half)
    d = max(-1.0, min(1.0, a.dot(b)))
    return math.acos(d)


def surface_distance(a, b, radius):
    """Great-circle distance between two unit vectors, in world units."""
    return angle_between(a, b) * radius


def slerp(a, b, t):
    """Spherical interpolation between unit vectors a and b. Small
    arcs use normalized linear interpolation, which is exact where
    float32 trigonometry runs out of digits."""
    omega = angle_between(a, b)
    if omega < 1e-9:
        return Vec3(b)
    if omega < 1e-2:
        out = Vec3(a) * (1.0 - t) + Vec3(b) * t
        out.normalize()
        return out
    so = math.sin(omega)
    va = Vec3(a) * (math.sin((1.0 - t) * omega) / so)
    vb = Vec3(b) * (math.sin(t * omega) / so)
    out = va + vb
    out.normalize()
    return out


def north_tangent(v):
    """Tangent vector pointing toward geographic north at surface point v."""
    z = Vec3(0, 0, 1)
    east = z.cross(v)
    if east.lengthSquared() < 1e-9:      # at a pole
        return Vec3(1, 0, 0)
    east.normalize()
    n = Vec3(v).cross(east)
    n.normalize()
    return n


# ------------------------------------------------------- 2D segment geometry
# Used for river-crossing tests in lon/lat space.

def segments_intersect(p1, p2, p3, p4):
    """True if 2D segments p1-p2 and p3-p4 intersect. Points are (x, y)."""
    def orient(a, b, c):
        val = (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])
        if abs(val) < 1e-12:
            return 0
        return 1 if val > 0 else 2

    def on_seg(a, b, c):
        return (min(a[0], b[0]) - 1e-12 <= c[0] <= max(a[0], b[0]) + 1e-12 and
                min(a[1], b[1]) - 1e-12 <= c[1] <= max(a[1], b[1]) + 1e-12)

    o1 = orient(p1, p2, p3)
    o2 = orient(p1, p2, p4)
    o3 = orient(p3, p4, p1)
    o4 = orient(p3, p4, p2)
    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and on_seg(p1, p2, p3):
        return True
    if o2 == 0 and on_seg(p1, p2, p4):
        return True
    if o3 == 0 and on_seg(p3, p4, p1):
        return True
    if o4 == 0 and on_seg(p3, p4, p2):
        return True
    return False


def segment_intersection_point(p1, p2, p3, p4):
    """Intersection point of two 2D segments, or None."""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-12:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = ((x1 - x3) * (y1 - y2) - (y1 - y3) * (x1 - x2)) / denom
    if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
    return None


def latlon_dist_deg(a, b):
    """Cheap planar distance in degrees between (lon, lat) points."""
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return math.sqrt(dx * dx + dy * dy)


# ----------------------------------------------------------------- fonts

_FONT_CANDIDATES = [
    # macOS
    "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
    "/System/Library/Fonts/Supplemental/Courier New.ttf",
    "/System/Library/Fonts/Supplemental/American Typewriter.ttc",
    "/System/Library/Fonts/Monaco.ttf",
    # Windows
    "C:/Windows/Fonts/courbd.ttf",
    "C:/Windows/Fonts/cour.ttf",
    "C:/Windows/Fonts/consola.ttf",
    # Linux
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
]

_REGULAR_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Courier New.ttf",
    "C:/Windows/Fonts/cour.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
]


def find_typewriter_font_path():
    """Path to a bold monospace/typewriter TTF on this system, or None."""
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def find_regular_font_path():
    """Regular-weight companion to the typewriter font, or None."""
    for path in _REGULAR_FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def smooth_polyline(pts, max_seg_deg=0.008):
    """Resample a polyline through a Catmull-Rom spline: the result
    passes through every control point, bends with continuous tangents
    (C1 -- no corners anywhere), and is dense enough that no segment
    spans more than max_seg_deg. Coordinate-order agnostic: rows go in,
    rows come out."""
    P = np.asarray(pts, dtype=np.float64)
    if len(P) < 3:
        return P
    ext = np.vstack([2.0 * P[0] - P[1], P, 2.0 * P[-1] - P[-2]])
    out = []
    for k in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[k - 1], ext[k], ext[k + 1], ext[k + 2]
        seg = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        n = max(1, int(math.ceil(seg / max_seg_deg)))
        t = np.linspace(0.0, 1.0, n, endpoint=False)[:, None]
        t2 = t * t
        t3 = t2 * t
        out.append(0.5 * ((2.0 * p1)
                          + (p2 - p0) * t
                          + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2
                          + (3.0 * p1 - p0 - 3.0 * p2 + p3) * t3))
    out.append(P[-1][None, :])
    return np.vstack(out)
