"""
Global topography from the real ETOPO1 ice-surface relief model.

One arc-minute of resolution (~1.8 km at the equator) drives three
systems at once:

* MOVEMENT -- climbing costs speed, and grades beyond a mountain
  soldier's limit are impassable; the route planner detours through
  the valleys and passes exactly where the real armies did.
* THE MAP -- the paper is hillshaded and high country tinted, so the
  ranges read at a glance in the FAX palette.
* LINE OF SIGHT -- a land or sea observer's vision field is no longer
  a circle: rays are marched over the relief, so a unit sees UP a
  slope but never OVER the crest, and a ridge casts a real shadow.
  Aircraft fly above all that and keep their full circles.

The dataset (~322 MB zipped) is fetched once into data/cache and kept
as a memory-mapped int16 grid; nothing is held in RAM beyond the pages
actually touched.
"""

import math
import os
import zipfile
import urllib.request

import numpy as np

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
DEM_NPY = os.path.join(CACHE_DIR, "etopo1_60s_i2.npy")
DEM_ZIP = os.path.join(CACHE_DIR, "etopo1_ice_g_i2.zip")
DEM_URL = ("https://www.ngdc.noaa.gov/mgg/global/relief/ETOPO1/data/"
           "ice_surface/grid_registered/binary/etopo1_ice_g_i2.zip")

DEM_W, DEM_H = 21600, 10800     # one arc-minute cells
EARTH_R_M = 6371000.0

# ---- gameplay tuning (moderate doctrine) --------------------------------
OBSERVER_M = 60.0               # observation mast above local ground
TARGET_M = 25.0                 # a division shows this much above its
                                # ground: dust, vehicles, smoke
GRADE_BLOCK = 0.13              # mean grade beyond which land cannot pass
GRADE_SLOW = 6.0                # speed = 1 / (1 + GRADE_SLOW * climb)
SPEED_FLOOR = 0.35              # never slower than this on a legal slope
LOS_AZIMUTHS = 64               # rays per vision field
LOS_STEPS = 20                  # samples per ray


def _log(msg):
    print("[terrain] %s" % msg)


def ensure_dem(log=_log):
    """Download and unpack the ETOPO1 grid on first run."""
    if os.path.exists(DEM_NPY):
        return DEM_NPY
    os.makedirs(CACHE_DIR, exist_ok=True)
    if not os.path.exists(DEM_ZIP):
        log("downloading ETOPO1 relief (322 MB, first run only)...")
        tmp = DEM_ZIP + ".part"
        urllib.request.urlretrieve(DEM_URL, tmp)
        os.replace(tmp, DEM_ZIP)
    log("unpacking the relief grid...")
    with zipfile.ZipFile(DEM_ZIP) as zf:
        name = next(n for n in zf.namelist() if n.endswith(".bin"))
        raw = zf.read(name)
    # grid-registered: 21601 x 10801, int16 LE, row 0 at 90N/180W.
    grid = np.frombuffer(raw, dtype="<i2").reshape(10801, 21601)
    np.save(DEM_NPY, np.ascontiguousarray(grid[:DEM_H, :DEM_W]))
    del raw, grid
    try:
        os.remove(DEM_ZIP)
    except OSError:
        pass
    log("relief ready: %s" % DEM_NPY)
    return DEM_NPY


class Terrain:
    """Sampling, movement grades, hillshade and line-of-sight, all off
    one memory-mapped elevation grid."""

    def __init__(self, log=_log):
        self.elev = np.load(ensure_dem(log), mmap_mode="r")

    # ------------------------------------------------------- sampling
    def sample_m(self, lat, lon):
        """Elevation in metres (vectorized; sea clamps to 0)."""
        lat = np.asarray(lat, dtype=np.float64)
        lon = np.asarray(lon, dtype=np.float64)
        r = np.clip(((90.0 - lat) * 60.0).astype(np.int64), 0, DEM_H - 1)
        c = ((lon + 180.0) * 60.0).astype(np.int64) % DEM_W
        e = self.elev[r, c].astype(np.float32)
        return np.maximum(e, 0.0)

    def elev_at(self, lat, lon):
        return float(self.sample_m(np.float64(lat), np.float64(lon)))

    def sample_bilinear(self, lat, lon):
        """Smooth elevation for the hillshade art."""
        lat = np.asarray(lat, dtype=np.float64)
        lon = np.asarray(lon, dtype=np.float64)
        rf = np.clip((90.0 - lat) * 60.0 - 0.5, 0.0, DEM_H - 1.001)
        cf = ((lon + 180.0) * 60.0 - 0.5) % DEM_W
        r0 = rf.astype(np.int64)
        c0 = cf.astype(np.int64)
        r1 = np.minimum(r0 + 1, DEM_H - 1)
        c1 = (c0 + 1) % DEM_W
        wr = (rf - r0).astype(np.float32)
        wc = (cf - c0).astype(np.float32)
        e00 = self.elev[r0, c0].astype(np.float32)
        e01 = self.elev[r0, c1].astype(np.float32)
        e10 = self.elev[r1, c0].astype(np.float32)
        e11 = self.elev[r1, c1].astype(np.float32)
        e = (e00 * (1 - wr) * (1 - wc) + e01 * (1 - wr) * wc
             + e10 * wr * (1 - wc) + e11 * wr * wc)
        return np.maximum(e, 0.0)

    # ------------------------------------------------------- movement
    def climb_profile(self, la1, lo1, la2, lo2, step_deg=0.02):
        """(mean uphill grade, max segment grade) along a great-ish
        line, sampled every ~2 km. Grades are rise/run."""
        d_deg = math.hypot(la2 - la1,
                           (lo2 - lo1) * math.cos(math.radians(
                               0.5 * (la1 + la2))))
        n = max(2, int(d_deg / step_deg) + 1)
        t = np.linspace(0.0, 1.0, n + 1)
        las = la1 + (la2 - la1) * t
        los = lo1 + (lo2 - lo1) * t
        e = self.sample_m(las, los)
        run_m = max(1.0, d_deg * 111120.0 / n)   # metres per sample step
        rise = np.diff(e)
        grades = rise / run_m
        up = grades[grades > 0]
        mean_up = float(up.mean()) if len(up) else 0.0
        max_g = float(np.abs(grades).max()) if len(grades) else 0.0
        return mean_up, max_g

    def passable(self, la1, lo1, la2, lo2):
        _mean_up, max_g = self.climb_profile(la1, lo1, la2, lo2)
        return max_g <= GRADE_BLOCK

    def offroad_cost_factor(self, la1, lo1, la2, lo2):
        """Cost multiplier for an off-road edge, or None if the ground
        is too steep to cross at all."""
        mean_up, max_g = self.climb_profile(la1, lo1, la2, lo2)
        if max_g > GRADE_BLOCK:
            return None
        return 1.0 / max(SPEED_FLOOR, 1.0 / (1.0 + GRADE_SLOW * mean_up))

    def speed_factor(self, la1, lo1, la2, lo2):
        """Live march-rate factor for one path segment (uphill bites,
        downhill is free)."""
        mean_up, max_g = self.climb_profile(la1, lo1, la2, lo2,
                                            step_deg=0.03)
        return max(SPEED_FLOOR, 1.0 / (1.0 + GRADE_SLOW * mean_up))

    # ---------------------------------------------------- hillshade art
    def shade_window(self, lon0, lat0, lon1, lat1, w, h,
                     strength=0.45, azimuth=315.0, altitude=45.0):
        """(shade, high) for a lon/lat window at w x h: 'shade' is a
        multiplicative hillshade around 1.0, 'high' a 0..1 mask easing
        in above ~800 m for the hypsometric stone tint."""
        lats = lat1 - (lat1 - lat0) * ((np.arange(h) + 0.5) / h)
        lons = lon0 + (lon1 - lon0) * ((np.arange(w) + 0.5) / w)
        e = self.sample_bilinear(lats[:, None], lons[None, :])
        # metres per pixel for the gradient
        mpp_y = max(1.0, (lat1 - lat0) / h * 111120.0)
        mpp_x = max(1.0, (lon1 - lon0) / w * 111120.0 *
                    max(0.15, math.cos(math.radians(0.5 * (lat0 + lat1)))))
        gy, gx = np.gradient(e, mpp_y, mpp_x)
        az = math.radians(azimuth)
        alt = math.radians(altitude)
        # standard Lambertian hillshade
        slope = np.arctan(np.hypot(gx, gy))
        aspect = np.arctan2(-gx, gy)
        hs = (np.sin(alt) * np.cos(slope) +
              np.cos(alt) * np.sin(slope) * np.cos(az - aspect))
        shade = 1.0 + strength * (hs - np.sin(alt)) / max(0.2, np.sin(alt))
        high = np.clip((e - 400.0) / 1600.0, 0.0, 1.0)
        return shade.astype(np.float32), high.astype(np.float32)

    # ---------------------------------------------------- line of sight
    def los_profile(self, lat, lon, range_rad,
                    n_az=LOS_AZIMUTHS, n_steps=LOS_STEPS):
        """Angular visibility radius per azimuth (radians), marched
        over the relief with earth-curvature drop. A ray ends at the
        first crest that hides the ground beyond."""
        h0 = self.elev_at(lat, lon) + OBSERVER_M
        # azimuth convention MATCHES the fog shader: angle from local
        # EAST, counter-clockwise, -pi..pi (texel k = (az+pi)/2pi * n)
        az = np.linspace(-math.pi, math.pi, n_az, endpoint=False)
        steps = np.linspace(range_rad / n_steps, range_rad, n_steps)
        # local flat-earth stepping is fine at these ranges (< 100 km)
        coslat = max(0.15, math.cos(math.radians(lat)))
        dlat = np.degrees(steps)[None, :] * np.sin(az)[:, None]
        dlon = np.degrees(steps)[None, :] * np.cos(az)[:, None] / coslat
        e = self.sample_m(lat + dlat, lon + dlon)      # (n_az, n_steps)
        dist_m = steps[None, :] * EARTH_R_M
        drop = dist_m * dist_m / (2.0 * EARTH_R_M)     # curvature
        ang = (e - h0 - drop) / dist_m                 # bare terrain
        # running maximum: crests set the sight line; ground behind is
        # hidden only when even a division's height of dust and metal
        # (TARGET_M) stays below that line -- low bumps on a plain do
        # not blind the observer, a real ridge does
        run_max = np.maximum.accumulate(ang, axis=1)
        ang_top = (e + TARGET_M - h0 - drop) / dist_m
        hidden = ang_top < (run_max - 1e-4)
        first_hidden = np.argmax(hidden, axis=1)
        none_hidden = ~hidden.any(axis=1)
        radii = steps[np.maximum(0, first_hidden - 1)]
        radii[none_hidden] = range_rad
        # seeing at least a step ahead keeps units from going blind in
        # a gully
        radii = np.maximum(radii, steps[0])
        # the FIELD is presentation as much as survey: smooth the
        # outline with a circular binomial blur so the shape flows in
        # subtle curves instead of ray-to-ray corners
        k = np.array([1.0, 6.0, 15.0, 20.0, 15.0, 6.0, 1.0])
        k /= k.sum()
        wrapped = np.concatenate([radii[-3:], radii, radii[:3]])
        radii = np.convolve(wrapped, k, mode='valid')
        return radii.astype(np.float32)
