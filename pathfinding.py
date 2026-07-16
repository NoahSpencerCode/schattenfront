"""
Movement planning on the globe.

- Air units fly great circles, ignoring terrain.
- Naval units find routes across water with A* on a coarse ocean grid.
- Land units use a graph of cities, roads, and bridges.  Roads carry
  traffic at 10x speed and pathfinding prefers them.  Rivers block
  off-road movement except within a small tolerance of an intact bridge.
"""

import heapq
import math

import numpy as np
from panda3d.core import Vec3

from config import (GLOBE_RADIUS, ROAD_SPEED_MULTIPLIER,
                    BRIDGE_TOLERANCE_DEG)
from utils import (latlon_to_vec, vec_to_latlon, angle_between, slerp,
                   segments_intersect, segment_intersection_point,
                   latlon_dist_deg)

SEA_GRID_DEG = 0.5             # coarse routing grid (permissive: straits
SEA_LAND_FRAC = 0.85           # must stay open; the corridor refinement
                               # pass supplies the coastal fidelity)
OFFROAD_MAX_ARC_DEG = 18.0     # longest allowed single off-road hop
OFFROAD_KNN = 10               # off-road links per node (nearest first)
ROAD_NODE_SPACING = 0.09       # world units between road entry nodes
                               # (finer = a column hugs the snaking road
                               # more closely and can join it nearer the
                               # closest point; ~2x the node density)
SAMPLE_STEP_DEG = 0.03   # ~3 px of the fine coastline mask per sample,
                         # so headland tips can't slip between samples
RIVER_STEP_DEG = 0.16    # river crossings are judged against a 0.45-deg
                         # bridge tolerance -- coarse sampling suffices


class MovementPlanner:
    def __init__(self, world, bridges):
        """bridges: live list of Bridge objects owned by the game."""
        self.world = world
        self.bridges = bridges
        self._static_edges = None      # lazy: [(i, j, cost, is_road, bridges)]
        self._nodes = None             # [(vec, lat, lon)]
        self._sea_grid = None
        # fleets ordered together share one route computation
        self._sea_route_cache = {}
        # river-crossing verdicts for static node pairs; valid until the
        # set of intact bridges changes
        self._river_ok_cache = {}

    def notify_bridge_change(self):
        self._river_ok_cache.clear()

    def add_custom_road(self, a_vec, b_vec):
        """Engineer-built road: a chain of fast edges with evenly
        spaced nodes so traffic can join anywhere along it."""
        if self._static_edges is None:
            self._build_land_graph()
        nodes, edges = self._nodes, self._static_edges
        total = angle_between(a_vec, b_vec) * GLOBE_RADIUS
        nseg = max(1, int(total / ROAD_NODE_SPACING))
        prev = len(nodes)
        nodes.append((Vec3(a_vec), *vec_to_latlon(a_vec)))
        for k in range(1, nseg + 1):
            v = slerp(a_vec, b_vec, k / nseg)
            idx = len(nodes)
            nodes.append((Vec3(v), *vec_to_latlon(v)))
            seg = angle_between(nodes[prev][0], v) * GLOBE_RADIUS
            edges.append((prev, idx, seg / ROAD_SPEED_MULTIPLIER, True, []))
            prev = idx

    # ------------------------------------------------------------ helpers
    def _alive_bridges(self):
        return [b for b in self.bridges if b.alive]

    @staticmethod
    def _sample_latlon(a_vec, b_vec, step_deg):
        """Vectorized great-circle sampling -> (lat_array, lon_array)."""
        a = np.array((a_vec.x, a_vec.y, a_vec.z))
        b = np.array((b_vec.x, b_vec.y, b_vec.z))
        ang = math.acos(max(-1.0, min(1.0, float(a.dot(b)))))
        n = max(2, int(math.degrees(ang) / step_deg) + 1)
        t = np.linspace(0.0, 1.0, n + 1)
        if ang < 1e-6:
            pts = np.tile(a, (n + 1, 1))
        else:
            so = math.sin(ang)
            wa = np.sin((1.0 - t) * ang) / so
            wb = np.sin(t * ang) / so
            pts = wa[:, None] * a + wb[:, None] * b
        lat = np.degrees(np.arcsin(np.clip(pts[:, 2], -1.0, 1.0)))
        lon = np.degrees(np.arctan2(pts[:, 1], pts[:, 0]))
        return lat, lon

    def _land_flags(self, lat, lon):
        # the FINE bit-packed mask: legality checks agree with the drawn
        # coastline (the coarse raster is only used for routing grids)
        return self.world.fine_flags(lat, lon)

    def segment_land_ok(self, a_vec, b_vec):
        """True if the great-circle segment stays on land."""
        lat, lon = self._sample_latlon(a_vec, b_vec, SAMPLE_STEP_DEG)
        return bool(self._land_flags(lat, lon).all())

    def segment_water_ok(self, a_vec, b_vec):
        lat, lon = self._sample_latlon(a_vec, b_vec, SAMPLE_STEP_DEG)
        return not bool(self._land_flags(lat[1:-1], lon[1:-1]).any())

    def _water_ok_lenient(self, a_vec, b_vec, max_run=1):
        """Water check that forgives slivers up to max_run samples —
        harbour spits and piers, not real coastlines. The fine mask is
        vector-accurate, so anything wider gets routed around."""
        lat, lon = self._sample_latlon(a_vec, b_vec, SAMPLE_STEP_DEG)
        land = self._land_flags(lat[1:-1], lon[1:-1])
        run = worst = 0
        for flag in land:
            run = run + 1 if flag else 0
            worst = max(worst, run)
        return worst <= max_run

    def segment_river_ok(self, a_vec, b_vec, ignore_all_bridges=False):
        """True if segment doesn't cross a river away from an intact bridge."""
        lat_a, lon_a = self._sample_latlon(a_vec, b_vec, RIVER_STEP_DEG)
        n = len(lat_a) - 1
        pts = list(zip(lon_a.tolist(), lat_a.tolist()))
        alive = None
        for i in range(n):
            p1, p2 = pts[i], pts[i + 1]
            if abs(p1[0] - p2[0]) > 180.0:
                continue  # antimeridian wrap; no gameplay rivers there
            mid = ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)
            for seg in self.world.river_segments_near(mid[0], mid[1]):
                hit = segment_intersection_point(p1, p2, seg[0], seg[1])
                if hit is None:
                    continue
                if ignore_all_bridges:
                    return False
                if alive is None:
                    alive = self._alive_bridges()
                ok = any(latlon_dist_deg((b.lon, b.lat), hit) <=
                         BRIDGE_TOLERANCE_DEG for b in alive)
                if not ok:
                    return False
        return True

    # ------------------------------------------------------- land network
    def _build_land_graph(self):
        """Static nodes and edges, built once.

        Roads are subdivided into evenly spaced intermediate nodes so a
        column can join the road at its closest point instead of
        marching to the nearest city or bridge first.
        """
        w = self.world
        nodes = []
        for (name, country, lat, lon) in w.cities:
            nodes.append((latlon_to_vec(lat, lon), lat, lon))
        self._bridge_node_start = len(nodes)
        for b in self.bridges:
            nodes.append((latlon_to_vec(b.lat, b.lon), b.lat, b.lon))

        edges = []
        bridges_by_road = {}
        for bi, b in enumerate(self.bridges):
            bridges_by_road.setdefault(b.road, []).append(bi)

        def road_chain(va, vb, node_a, node_b, bs):
            """Chain of road sub-edges with intermediate nodes; each
            sub-edge is gated only by the bridges that sit on it."""
            total = angle_between(va, vb) * GLOBE_RADIUS
            nseg = max(1, int(total / ROAD_NODE_SPACING))
            chain = [node_a]
            for k in range(1, nseg):
                v = slerp(va, vb, k / nseg)
                lat, lon = vec_to_latlon(v)
                chain.append(len(nodes))
                nodes.append((Vec3(v), lat, lon))
            chain.append(node_b)
            for a, bn in zip(chain[:-1], chain[1:]):
                pa, pb = nodes[a][0], nodes[bn][0]
                seg_len = angle_between(pa, pb) * GLOBE_RADIUS
                mid = slerp(pa, pb, 0.5)
                gate = [bi for bi in bs
                        if angle_between(self.bridges[bi].pos, mid) *
                        GLOBE_RADIUS <= seg_len * 0.6 + 0.05]
                edges.append((a, bn, seg_len / ROAD_SPEED_MULTIPLIER,
                              True, gate))

        # spur roads: city to its airfield (fast final approach)
        af_sites = getattr(w, 'airfield_sites', {})
        for i, (name, country, lat, lon) in enumerate(w.cities):
            site = af_sites.get(name)
            if site is None:
                continue
            v = latlon_to_vec(site[0], site[1])
            nn = len(nodes)
            nodes.append((Vec3(v), site[0], site[1]))
            road_chain(nodes[i][0], v, i, nn, [])

        for (i, j) in w.roads:
            bs = bridges_by_road.get((i, j), [])
            path = getattr(w, 'road_paths', {}).get((i, j))
            if not path or len(path) < 2:
                road_chain(nodes[i][0], nodes[j][0], i, j, bs)
                continue
            # weave the graph through the road's snaking centre-line so a
            # column actually follows the drawn road
            prev = i
            for pk in range(1, len(path) - 1):
                la, lo = path[pk]
                v = latlon_to_vec(la, lo)
                nn = len(nodes)
                nodes.append((v, la, lo))
                road_chain(nodes[prev][0], v, prev, nn, bs)
                prev = nn
            road_chain(nodes[prev][0], nodes[j][0], prev, j, bs)

        # Off-road: each node links to its nearest neighbours on land
        n = len(nodes)
        seen = set()
        for i in range(n):
            cands = []
            for j in range(n):
                if j == i:
                    continue
                ang = math.degrees(angle_between(nodes[i][0], nodes[j][0]))
                if 1e-6 < ang <= OFFROAD_MAX_ARC_DEG:
                    cands.append((ang, j))
            cands.sort()
            linked = 0
            for ang, j in cands:
                if linked >= OFFROAD_KNN:
                    break
                key = (min(i, j), max(i, j))
                if key in seen:
                    linked += 1
                    continue
                seen.add(key)
                if not self.segment_land_ok(nodes[i][0], nodes[j][0]):
                    continue
                dist = math.radians(ang) * GLOBE_RADIUS
                edges.append((key[0], key[1], dist, False, None))
                linked += 1

        self._nodes = nodes
        self._static_edges = edges
        # prewarm river verdicts so the first in-game plans don't hitch
        for (i, j, _cost, is_road, _bs) in edges:
            if not is_road:
                self._static_river_ok(i, j)

    def _static_river_ok(self, i, j):
        key = (min(i, j), max(i, j))
        hit = self._river_ok_cache.get(key)
        if hit is None:
            hit = self.segment_river_ok(self._nodes[i][0],
                                        self._nodes[j][0])
            self._river_ok_cache[key] = hit
        return hit

    def _land_edges_usable(self, edge):
        i, j, cost, is_road, bs = edge
        if is_road:
            return all(self.bridges[bi].alive for bi in (bs or []))
        return True  # off-road rivers are re-checked lazily during A*

    def plan_land(self, start_vec, goal_vec):
        """A* over the land graph. Returns [(vec, speed_mult), ...] or None."""
        if self._static_edges is None:
            self._build_land_graph()
        nodes = list(self._nodes)
        start_i = len(nodes)
        goal_i = start_i + 1
        nodes.append((Vec3(start_vec), *vec_to_latlon(start_vec)))
        nodes.append((Vec3(goal_vec), *vec_to_latlon(goal_vec)))

        # adjacency
        adj = {}

        def add(i, j, cost, is_road):
            adj.setdefault(i, []).append((j, cost, is_road))
            adj.setdefault(j, []).append((i, cost, is_road))

        for e in self._static_edges:
            if self._land_edges_usable(e):
                add(e[0], e[1], e[2], e[3])
        # dynamic edges: start/goal to their nearest nodes (and each other)
        n_static = len(self._nodes)
        for dyn in (start_i, goal_i):
            cands = []
            for j in range(len(nodes)):
                if j == dyn:
                    continue
                ang = math.degrees(angle_between(nodes[dyn][0], nodes[j][0]))
                if ang > OFFROAD_MAX_ARC_DEG or ang < 1e-6:
                    continue
                cands.append((ang, j))
            cands.sort()
            linked = 0
            for ang, j in cands:
                if linked >= 14 and j < n_static:
                    break
                if not self.segment_land_ok(nodes[dyn][0], nodes[j][0]):
                    continue
                add(dyn, j, math.radians(ang) * GLOBE_RADIUS, False)
                linked += 1

        # river checks: persistent cache for static pairs, per-call
        # for edges touching the start/goal
        river_cache = {}

        def river_ok(i, j):
            if i < n_static and j < n_static:
                return self._static_river_ok(i, j)
            key = (min(i, j), max(i, j))
            if key not in river_cache:
                river_cache[key] = self.segment_river_ok(nodes[i][0],
                                                         nodes[j][0])
            return river_cache[key]

        def h(i):
            return (angle_between(nodes[i][0], nodes[goal_i][0]) *
                    GLOBE_RADIUS / ROAD_SPEED_MULTIPLIER)

        dist = {start_i: 0.0}
        prev = {}
        prev_road = {}
        pq = [(h(start_i), start_i)]
        seen = set()
        while pq:
            _, cur = heapq.heappop(pq)
            if cur in seen:
                continue
            seen.add(cur)
            if cur == goal_i:
                break
            for (nxt, cost, is_road) in adj.get(cur, ()):
                if nxt in seen:
                    continue
                if not is_road and not river_ok(cur, nxt):
                    continue
                nd = dist[cur] + cost
                if nd < dist.get(nxt, float('inf')):
                    dist[nxt] = nd
                    prev[nxt] = cur
                    prev_road[nxt] = is_road
                    heapq.heappush(pq, (nd + h(nxt), nxt))
        if goal_i not in prev and start_i != goal_i:
            # graph couldn't connect them: try a fine mask-accurate A*
            # (coastal walks, lake shores — as accurate as the map)
            return self._refine_land(start_vec, goal_vec)
        # reconstruct
        path = []
        cur = goal_i
        while cur != start_i:
            mult = ROAD_SPEED_MULTIPLIER if prev_road.get(cur) else 1.0
            path.append((Vec3(nodes[cur][0]), mult))
            cur = prev[cur]
        path.reverse()
        return path

    # --------------------------------------------------------- sea routing
    def _build_sea_grid(self):
        """Downsample the land mask to a navigation grid.

        A cell is navigable water unless it is almost entirely land, so
        that narrow straits (Dover, Skagerrak, Tsushima...) stay open.
        """
        import numpy as np
        mask = self.world.land_mask.astype(np.int32)
        h, w = mask.shape
        cols = int(360 / SEA_GRID_DEG)
        rows = int(180 / SEA_GRID_DEG)
        xs = (np.arange(cols) * w) // cols
        ys = (np.arange(rows) * h) // rows
        col_sum = np.add.reduceat(mask, xs, axis=1)
        cell_sum = np.add.reduceat(col_sum, ys, axis=0)
        x_edges = np.append(xs, w)
        y_edges = np.append(ys, h)
        counts = np.outer(np.diff(y_edges), np.diff(x_edges))
        land_frac = cell_sum / counts
        self._sea_grid = (land_frac < SEA_LAND_FRAC)
        self._sea_cols = cols
        self._sea_rows = rows

    def _cell_of(self, lat, lon):
        c = int((lon + 180.0) / SEA_GRID_DEG) % self._sea_cols
        r = int((90.0 - lat) / SEA_GRID_DEG)
        return max(0, min(self._sea_rows - 1, r)), c

    def _cell_center(self, r, c):
        lat = 90.0 - (r + 0.5) * SEA_GRID_DEG
        lon = -180.0 + (c + 0.5) * SEA_GRID_DEG
        return lat, lon

    def _nearest_water_cell(self, r, c, max_r=5):
        if self._sea_grid[r][c]:
            return r, c
        for radius in range(1, max_r + 1):
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    rr = r + dr
                    cc = (c + dc) % self._sea_cols
                    if 0 <= rr < self._sea_rows and self._sea_grid[rr][cc]:
                        return rr, cc
        return None

    def plan_sea(self, start_vec, goal_vec):
        if self._sea_grid is None:
            self._build_sea_grid()
        # short hauls (harbours, bays, inlets) skip the coarse grid and
        # navigate straight on the full-resolution mask
        if math.degrees(angle_between(start_vec, goal_vec)) < 3.0:
            fine = self._refine_grid_once(start_vec, goal_vec, 1.2,
                                          120000, want_water=True)
            if fine is not None:
                return [(Vec3(v), 1.0) for v in fine]
        s_lat, s_lon = vec_to_latlon(start_vec)
        g_lat, g_lon = vec_to_latlon(goal_vec)
        start = self._nearest_water_cell(*self._cell_of(s_lat, s_lon))
        goal = self._nearest_water_cell(*self._cell_of(g_lat, g_lon))
        if start is None or goal is None:
            return None
        # a fleet ordered together shares the leader's route
        cache_key = (start, goal)
        hit = self._sea_route_cache.get(cache_key)
        if hit is not None:
            return [(Vec3(v), m) for (v, m) in hit]

        def h(cell):
            la, lo = self._cell_center(*cell)
            a = latlon_to_vec(la, lo)
            b = latlon_to_vec(*self._cell_center(*goal))
            return angle_between(a, b)

        dist = {start: 0.0}
        prev = {}
        pq = [(h(start), start)]
        seen = set()
        found = False
        while pq:
            _, cur = heapq.heappop(pq)
            if cur in seen:
                continue
            seen.add(cur)
            if cur == goal:
                found = True
                break
            r, c = cur
            lat, _ = self._cell_center(r, c)
            coslat = max(0.05, math.cos(math.radians(lat)))
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr = r + dr
                    cc = (c + dc) % self._sea_cols
                    if not (0 <= rr < self._sea_rows):
                        continue
                    if not self._sea_grid[rr][cc]:
                        continue
                    step = math.sqrt((dc * coslat) ** 2 + dr ** 2)
                    nd = dist[cur] + step
                    nxt = (rr, cc)
                    if nd < dist.get(nxt, float('inf')):
                        dist[nxt] = nd
                        prev[nxt] = cur
                        heapq.heappush(pq, (nd + math.degrees(h(nxt)) /
                                            SEA_GRID_DEG, nxt))
        if not found:
            return None
        cells = []
        cur = goal
        while cur != start:
            cells.append(cur)
            cur = prev[cur]
        cells.append(start)
        cells.reverse()

        # to vectors (cell centres snapped onto actual water), then
        # smooth with water line-of-sight
        vecs = [Vec3(start_vec)]
        for cell in cells:
            la, lo = self._cell_center(*cell)
            if self.world.is_land(la, lo):
                la, lo = self.world.nearest_water(la, lo, max_deg=1.5)
            vecs.append(latlon_to_vec(la, lo))
        vecs.append(Vec3(goal_vec))
        smoothed = [vecs[0]]
        i = 0
        while i < len(vecs) - 1:
            j = len(vecs) - 1
            while j > i + 1:
                if self.segment_water_ok(vecs[i], vecs[j]):
                    break
                j -= 1
            smoothed.append(vecs[j])
            i = j
        # corridor refinement: any hop that truly crosses the coast is
        # re-routed on the full-resolution land mask — ships must never
        # sail over land
        repaired = [smoothed[0]]
        for k in range(len(smoothed) - 1):
            a, b = smoothed[k], smoothed[k + 1]
            if self._water_ok_lenient(a, b):
                repaired.append(b)
            else:
                repaired.extend(self._refine_hop(a, b))
        result = [(v, 1.0) for v in repaired[1:]]
        if len(self._sea_route_cache) > 48:
            self._sea_route_cache.clear()
        self._sea_route_cache[cache_key] = \
            [(Vec3(v), m) for (v, m) in result]
        return result

    def _refine_hop(self, a_vec, b_vec):
        """Fine A* on the land mask around the hop; the search box grows
        until the detour fits (a peninsula can force a long way round).
        Returns waypoints from a to b (a excluded)."""
        for pad_deg, budget in ((1.5, 30000), (4.0, 120000),
                                (9.0, 400000)):
            out = self._refine_grid_once(a_vec, b_vec, pad_deg, budget,
                                         want_water=True)
            if out is not None:
                return out
        return [b_vec]      # nowhere to go (canal transit): allow it

    def _refine_land(self, a_vec, b_vec):
        """Mask-accurate land fallback when the node graph can't connect
        two points (coastal walks, lake shores).  Rivers still apply."""
        if math.degrees(angle_between(a_vec, b_vec)) > 15.0:
            return None
        for pad_deg, budget in ((1.5, 40000), (4.5, 200000)):
            out = self._refine_grid_once(a_vec, b_vec, pad_deg, budget,
                                         want_water=False)
            if out is not None:
                # rivers must still be crossed at bridges
                prev = a_vec
                for v in out:
                    if not self.segment_river_ok(prev, v):
                        return None
                    prev = v
                return [(Vec3(v), 1.0) for v in out]
        return None

    def _refine_grid_once(self, a_vec, b_vec, pad_deg, max_budget,
                          want_water=True):
        la1, lo1 = vec_to_latlon(a_vec)
        la2, lo2 = vec_to_latlon(b_vec)
        if abs(lo1 - lo2) > 180.0:
            return [b_vec]              # antimeridian hop: leave it be
        mask = self.world.land_mask
        h, w = mask.shape
        y0 = max(0, int((90.0 - (max(la1, la2) + pad_deg)) / 180.0 * h))
        y1 = min(h - 1, int((90.0 - (min(la1, la2) - pad_deg)) / 180.0 * h))
        x0 = max(0, int(((min(lo1, lo2) - pad_deg) + 180.0) / 360.0 * w))
        x1 = min(w - 1, int(((max(lo1, lo2) + pad_deg) + 180.0) / 360.0 * w))
        sub = mask[y0:y1 + 1, x0:x1 + 1]
        water = ~sub if want_water else sub
        rows, cols = water.shape
        if rows < 2 or cols < 2:
            return [b_vec]              # degenerate box: give up quietly

        def cell_of(lat, lon):
            r = min(rows - 1, max(0, int((90.0 - lat) / 180.0 * h) - y0))
            c = min(cols - 1, max(0, int((lon + 180.0) / 360.0 * w) - x0))
            return r, c

        def open_at(r, c):
            """Water with breathing room — skips sealed pockets."""
            r0, r1_ = max(0, r - 2), min(rows, r + 3)
            c0, c1_ = max(0, c - 2), min(cols, c + 3)
            return water[r, c] and water[r0:r1_, c0:c1_].sum() >= 15

        def nearest_water_cell(r, c):
            if open_at(r, c):
                return (r, c)
            fallback = (r, c) if water[r, c] else None
            for radius in range(1, 24):
                r0, r1_ = max(0, r - radius), min(rows, r + radius + 1)
                c0, c1_ = max(0, c - radius), min(cols, c + radius + 1)
                sub = np.argwhere(water[r0:r1_, c0:c1_])
                if len(sub):
                    d = ((sub[:, 0] + r0 - r) ** 2 +
                         (sub[:, 1] + c0 - c) ** 2)
                    for k in np.argsort(d)[:24]:
                        rr = int(sub[k][0]) + r0
                        cc = int(sub[k][1]) + c0
                        if open_at(rr, cc):
                            return (rr, cc)
                        if fallback is None:
                            fallback = (rr, cc)
            return fallback

        start = nearest_water_cell(*cell_of(la1, lo1))
        goal = nearest_water_cell(*cell_of(la2, lo2))
        if start is None or goal is None:
            return None                 # let the caller widen the box

        dist = {start: 0.0}
        prev = {}
        pq = [(0.0, start)]
        seen = set()
        found = False
        budget = max_budget
        while pq and budget > 0:
            budget -= 1
            _, cur = heapq.heappop(pq)
            if cur in seen:
                continue
            seen.add(cur)
            if cur == goal:
                found = True
                break
            r, c = cur
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr, cc = r + dr, c + dc
                    if not (0 <= rr < rows and 0 <= cc < cols):
                        continue
                    if not water[rr, cc]:
                        continue
                    if dr and dc and not (water[rr, c] and water[r, cc]):
                        continue    # no cutting corners over headlands
                    nd = dist[cur] + math.sqrt(dr * dr + dc * dc)
                    nxt = (rr, cc)
                    if nd < dist.get(nxt, 1e18):
                        dist[nxt] = nd
                        prev[nxt] = cur
                        hh = math.hypot(goal[0] - rr, goal[1] - cc)
                        heapq.heappush(pq, (nd + hh, nxt))
        if not found:
            return None                 # let the caller widen the box
        cells = []
        cur = goal
        while cur != start:
            cells.append(cur)
            cur = prev[cur]
        cells.reverse()

        def cell_vec(rc):
            lat = 90.0 - (rc[0] + y0 + 0.5) / h * 180.0
            lon = (rc[1] + x0 + 0.5) / w * 360.0 - 180.0
            # the A* ran on the coarse routing raster: nudge the waypoint
            # onto vector-true terrain so the path matches the drawn coast
            if want_water:
                if self.world.is_land(lat, lon):
                    lat, lon = self.world.nearest_water(lat, lon,
                                                        max_deg=0.2)
            elif not self.world.is_land(lat, lon):
                lat, lon = self.world.nearest_land(lat, lon, max_deg=0.2)
            return latlon_to_vec(lat, lon)

        # line-of-sight merge over the full cell chain removes the
        # staircase without ever cutting across forbidden terrain
        los = (self._water_ok_lenient if want_water
               else self.segment_land_ok)
        pts = [a_vec] + [cell_vec(rc) for rc in cells] + [b_vec]
        out = []
        i = 0
        while i < len(pts) - 1:
            j = len(pts) - 1
            while j > i + 1 and not los(pts[i], pts[j]):
                j -= 1
            out.append(pts[j])
            i = j
        return out

    # -------------------------------------------------------------- public
    def plan(self, domain, start_vec, goal_vec):
        """Returns [(unit_vec, speed_mult), ...] or None if unreachable."""
        if domain == 'air':
            return [(Vec3(goal_vec), 1.0)]
        if domain == 'sea':
            return self.plan_sea(start_vec, goal_vec)
        return self.plan_land(start_vec, goal_vec)
