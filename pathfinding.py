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
import time

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
OFFROAD_KNN = 8               # off-road links per node (nearest first)
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
        self._nodes_np = None          # numpy mirror for fast queries
        self._adj_cache = None         # static adjacency, built once
        # fleets ordered together share one route computation
        self._sea_route_cache = {}
        # river-crossing verdicts for static node pairs; valid until the
        # set of intact bridges changes
        self._river_ok_cache = {}

    def notify_bridge_change(self):
        self._river_ok_cache.clear()
        self._adj_cache = None

    def add_custom_road(self, poly):
        """Engineer-built road: the DRAWN centre-line polyline becomes a
        chain of fast road edges (nodes at every bend plus evenly spaced
        infill), identical in function to a map road -- traffic follows
        the laid curve exactly and can join it anywhere along the way."""
        if self._static_edges is None:
            self._build_land_graph()
        nodes, edges = self._nodes, self._static_edges
        vecs = [Vec3(v) for v in poly]
        arc = [0.0]
        for va, vb in zip(vecs[:-1], vecs[1:]):
            arc.append(arc[-1] + angle_between(va, vb) * GLOBE_RADIUS)
        total = arc[-1]
        nseg = max(1, int(total / ROAD_NODE_SPACING))
        target = total / nseg
        # ends SNAP onto the existing network so laid roads join it
        # instead of floating beside it
        snap_a = self.nearest_node(vecs[0], max_deg=0.30)
        snap_b = self.nearest_node(vecs[-1], max_deg=0.30)
        if snap_a is not None:
            prev = snap_a
        else:
            prev = len(nodes)
            nodes.append((vecs[0], *vec_to_latlon(vecs[0])))
        prev_i, k = 0, 1
        for idx in range(1, len(vecs)):
            last = idx == len(vecs) - 1
            if not last and (arc[idx] < k * target or k >= nseg):
                continue
            if last and snap_b is not None:
                nn = snap_b
            else:
                nn = len(nodes)
                nodes.append((vecs[idx], *vec_to_latlon(vecs[idx])))
            seg_len = max(1e-6, arc[idx] - arc[prev_i])
            geom = vecs[prev_i + 1:idx] or None
            edges.append((prev, nn, seg_len / ROAD_SPEED_MULTIPLIER,
                          True, [], geom))
            prev, prev_i = nn, idx
            k += 1
        self._adj_cache = None

    def _stitch(self, nodes, edges, P):
        """STITCHING: the KNN pass leaves pockets (mountain shadows,
        coastal strips) and can split a continent -- Vladivostok sat
        alone, Paris and Moscow lived apart. Components sharing a
        landmass are sewn by their nearest OVERLAND pairs; where no
        clean chord exists the FINE MASK walks the corridor and a wild
        track is laid along it. True islands stay separate. The sewn
        set is cached: the survey is paid for once."""
        import os as _os
        from geodata import CACHE_DIR as _CD
        base_n = len(nodes)
        cache = _os.path.join(_CD, 'land_stitch_v1_%d.npz' % base_n)
        if _os.path.exists(cache):
            z = np.load(cache)
            for la, lo in z['pts']:
                nodes.append((latlon_to_vec(float(la), float(lo)),
                              float(la), float(lo)))
            for i, j, c in z['links']:
                edges.append((int(i), int(j), float(c), False, None,
                              None))
            return
        new_pts = []
        new_links = []
        parent = list(range(base_n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for e in edges:
            union(e[0], e[1])
        refines_left = 40
        for _round in range(8):
            comps = {}
            for i in range(len(parent)):
                comps.setdefault(find(i), []).append(i)
            if len(comps) <= 1:
                break
            order_c = sorted(comps.values(), key=len, reverse=True)
            main = order_c[0]
            main_np = P[np.array([i for i in main if i < base_n])]
            main_ids = [i for i in main if i < base_n]
            scored = []
            for comp in order_c[1:]:
                ids = [i for i in comp if i < base_n]
                if not ids:
                    continue
                sub = P[np.array(ids)]
                with np.errstate(all='ignore'):
                    D = sub @ main_np.T
                f = int(np.argmax(D))
                scored.append((float(D.flat[f]), ids[f // len(main_ids)],
                               main_ids[f % len(main_ids)], ids, D))
            # NEAREST pockets first: the far ones are usually islands
            scored.sort(key=lambda t: -t[0])
            merged = False
            for _best, _a0, _b0, ids, D in scored:
                flat = np.argsort(-D, axis=None)[:60]
                linked = False
                for f in flat:
                    ci, mi = int(f // len(main_ids)), int(f % len(main_ids))
                    a, b = ids[ci], main_ids[mi]
                    ang = math.acos(max(-1.0, min(1.0, float(D[ci, mi]))))
                    if math.degrees(ang) > OFFROAD_MAX_ARC_DEG * 1.5:
                        break
                    if not self.segment_land_ok(nodes[a][0], nodes[b][0]):
                        continue
                    fac = self.world.terrain.offroad_cost_factor(
                        nodes[a][1], nodes[a][2], nodes[b][1], nodes[b][2])
                    if fac is None:
                        fac = 6.0
                    edges.append((a, b, ang * GLOBE_RADIUS * fac,
                                  False, None, None))
                    new_links.append((a, b, ang * GLOBE_RADIUS * fac))
                    union(a, b)
                    linked = merged = True
                    break
                if linked or not len(flat):
                    continue
                ci, mi = int(flat[0] // len(main_ids)), \
                    int(flat[0] % len(main_ids))
                a, b = ids[ci], main_ids[mi]
                ang = math.acos(max(-1.0, min(1.0, float(D[ci, mi]))))
                if math.degrees(ang) > OFFROAD_MAX_ARC_DEG * 1.5 \
                        or refines_left <= 0:
                    continue
                refines_left -= 1
                fine = self._refine_land(nodes[a][0], nodes[b][0])
                if not fine:
                    continue            # truly cut off: an island
                prev = a
                run = 0.0
                last_v = nodes[a][0]
                for (wp, _m) in fine:
                    step_ = angle_between(last_v, wp) * GLOBE_RADIUS
                    run += step_
                    last_v = wp
                    if run < 0.6:
                        continue
                    nn = len(nodes)
                    la_, lo_ = vec_to_latlon(wp)
                    nodes.append((Vec3(wp), la_, lo_))
                    parent.append(nn)
                    edges.append((prev, nn, run * 1.5, False, None,
                                  None))
                    new_pts.append((la_, lo_))
                    new_links.append((prev, nn, run * 1.5))
                    union(prev, nn)
                    prev, run = nn, 0.0
                edges.append((prev, b, max(run, 0.05) * 1.5, False,
                              None, None))
                new_links.append((prev, b, max(run, 0.05) * 1.5))
                union(prev, b)
                merged = True
            if not merged:
                break
        np.savez(cache,
                 pts=np.array(new_pts, dtype=np.float64).reshape(-1, 2),
                 links=np.array(new_links, dtype=np.float64
                                ).reshape(-1, 3))

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

    FORD_CLEAR_DEG = 3.0    # a crossing this far from EVERY bridge is
                            # wild country and may be forded (slowly)
    FORD_COST_MULT = 3.0

    def river_passage(self, a_vec, b_vec):
        """Routing verdict for a leg: 1.0 = clear or bridged;
        FORD_COST_MULT = every crossing is in wild country, ford it;
        None = an unbridged crossing in bridge country -- blocked, go
        find the bridge. This is what lets a column cross Siberia
        without making Europe's bridges optional."""
        lat_a, lon_a = self._sample_latlon(a_vec, b_vec, RIVER_STEP_DEG)
        n = len(lat_a) - 1
        pts = list(zip(lon_a.tolist(), lat_a.tolist()))
        alive = None
        mult = 1.0
        for i in range(n):
            p1, p2 = pts[i], pts[i + 1]
            if abs(p1[0] - p2[0]) > 180.0:
                continue
            mid = ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)
            for seg in self.world.river_segments_near(mid[0], mid[1]):
                hit = segment_intersection_point(p1, p2, seg[0], seg[1])
                if hit is None:
                    continue
                if alive is None:
                    alive = self._alive_bridges()
                dmin = min((latlon_dist_deg((b.lon, b.lat), hit)
                            for b in alive), default=1e9)
                if dmin <= BRIDGE_TOLERANCE_DEG:
                    continue            # crosses ON a bridge
                if dmin >= self.FORD_CLEAR_DEG:
                    mult = self.FORD_COST_MULT
                    continue            # wild country: wade it
                return None             # bridge country: use the bridge
        return mult

    def nearest_node(self, vec, max_deg=0.35):
        """Nearest graph node within max_deg -- for snapping a new
        road's ends onto the existing network."""
        if self._static_edges is None:
            self._build_land_graph()
        best, best_a = None, math.radians(max_deg)
        for idx, (v, _la, _lo) in enumerate(self._nodes):
            a = angle_between(vec, v)
            if a < best_a:
                best, best_a = idx, a
        return best

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

        def road_chain(node_a, node_b, dense, bs):
            """One chained road along its DENSE smooth centre-line:
            graph nodes at coarse spacing, the exact curve between them
            riding on each edge as geometry -- a column follows the
            drawn ribbon precisely without bloating the node count."""
            vecs = [latlon_to_vec(la, lo) for (la, lo) in dense]
            arc = [0.0]
            for va, vb in zip(vecs[:-1], vecs[1:]):
                arc.append(arc[-1] + angle_between(va, vb) * GLOBE_RADIUS)
            total = arc[-1]
            nseg = max(1, int(total / ROAD_NODE_SPACING))
            cuts = []
            target = total / nseg
            k = 1
            for idx in range(1, len(vecs) - 1):
                if arc[idx] >= k * target and k < nseg:
                    cuts.append(idx)
                    k += 1

            def emit(a, bn, i0, i1):
                seg_len = max(1e-6, arc[i1] - arc[i0])
                mid = vecs[(i0 + i1) // 2]
                gate = [bi for bi in bs
                        if angle_between(self.bridges[bi].pos, mid) *
                        GLOBE_RADIUS <= seg_len * 0.6 + 0.05]
                geom = [Vec3(v) for v in vecs[i0 + 1:i1]] or None
                edges.append((a, bn, seg_len / ROAD_SPEED_MULTIPLIER,
                              True, gate, geom))

            prev, prev_i = node_a, 0
            for idx in cuts:
                la, lo = dense[idx]
                nn = len(nodes)
                nodes.append((Vec3(vecs[idx]), la, lo))
                emit(prev, nn, prev_i, idx)
                prev, prev_i = nn, idx
            emit(prev, node_b, prev_i, len(vecs) - 1)

        # spur roads: city to its airfield. The graph is woven through
        # the DRAWN spur polyline vertex by vertex, so a column on the
        # spur follows the road's curves exactly (render == route).
        af_spurs = getattr(w, 'airfield_spurs', {})
        for i, (name, country, lat, lon) in enumerate(w.cities):
            spur = af_spurs.get(name)
            if not spur or len(spur) < 2:
                continue
            end_la, end_lo = spur[-1]
            end_n = len(nodes)
            nodes.append((latlon_to_vec(end_la, end_lo), end_la, end_lo))
            road_chain(i, end_n, list(spur), [])

        for (i, j) in w.roads:
            bs = bridges_by_road.get((i, j), [])
            path = getattr(w, 'road_paths', {}).get((i, j))
            if not path or len(path) < 2:
                a, b = w.cities[i], w.cities[j]
                path = [(a[2], a[3]), (b[2], b[3])]
            road_chain(i, j, list(path), bs)

        # Off-road: each node links to its nearest neighbours on land.
        # Candidate search is fully vectorized (the graph is thousands
        # of nodes now); land checks run only on the K best per node.
        n = len(nodes)
        # WILDERNESS WAYPOINTS: a coarse lattice over the empty
        # country. Without it the KNN pass only ever links neighbours
        # inside dense clusters, and no chain of hops could ever span
        # Siberia, the Sahara or the outback -- routes just died at
        # the edge of the map's road networks.
        P0 = np.array([[v.x, v.y, v.z] for (v, _la, _lo) in nodes])
        n0 = np.linalg.norm(P0, axis=1, keepdims=True)
        P0 = P0 / np.maximum(n0, 1e-12)
        cos_dedupe = math.cos(math.radians(2.5))
        for la in range(-54, 69, 6):
            step = max(6, int(round(6.0 / max(0.2, math.cos(
                math.radians(la))))))
            for lo in range(-180, 180, step):
                if not self.world.is_land(float(la), float(lo)):
                    continue
                v = latlon_to_vec(float(la), float(lo))
                with np.errstate(all='ignore'):
                    dmax = float((P0 @ np.array([v.x, v.y, v.z])).max())
                if dmax > cos_dedupe:
                    continue        # settled country: nodes exist here
                nodes.append((v, float(la), float(lo)))
        n = len(nodes)

        P = np.array([[v.x, v.y, v.z] for (v, _la, _lo) in nodes])
        norms = np.linalg.norm(P, axis=1, keepdims=True)
        P = P / np.maximum(norms, 1e-12)
        cos_max = math.cos(math.radians(OFFROAD_MAX_ARC_DEG))
        seen = set()
        for i in range(n):
            # errstate: Apple's Accelerate BLAS raises spurious FP flags
            # on matmul; the products themselves are exact
            with np.errstate(all='ignore'):
                dots = P @ P[i]
            dots[i] = -2.0
            cand = np.nonzero(dots > cos_max)[0]
            if len(cand) == 0:
                continue
            order = cand[np.argsort(-dots[cand])]
            linked = 0
            for j in order:
                if linked >= OFFROAD_KNN:
                    break
                j = int(j)
                key = (min(i, j), max(i, j))
                if key in seen:
                    linked += 1
                    continue
                seen.add(key)
                if not self.segment_land_ok(nodes[i][0], nodes[j][0]):
                    continue
                fac = self.world.terrain.offroad_cost_factor(
                    nodes[i][1], nodes[i][2], nodes[j][1], nodes[j][2])
                if fac is None:
                    continue        # too steep for any column
                ang = math.acos(max(-1.0, min(1.0, float(dots[j]))))
                edges.append((key[0], key[1], ang * GLOBE_RADIUS * fac,
                              False, None, None))
                linked += 1

        self._stitch(nodes, edges, P)

        self._nodes = nodes
        self._static_edges = edges
        # river verdicts are checked lazily during A* (the planner runs
        # on a worker thread, so the cost never lands on a frame)

    def _static_river_ok(self, i, j):
        key = (min(i, j), max(i, j))
        hit = self._river_ok_cache.get(key)
        if hit is None:
            hit = self.river_passage(self._nodes[i][0],
                                     self._nodes[j][0])
            self._river_ok_cache[key] = ('X' if hit is None else hit)
        return None if hit == 'X' else hit

    def _land_edges_usable(self, edge):
        i, j, cost, is_road, bs = edge[:5]
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

        # adjacency: the static half is built ONCE and reused by every
        # plan (rebuilt only when a bridge changes or a road is laid);
        # each query adds just its start/goal links in a tiny overlay
        if self._adj_cache is None:
            cache = {}
            for k, e in enumerate(self._static_edges):
                if k % 4096 == 0:
                    time.sleep(0.0005)  # one-time build; frames first
                if self._land_edges_usable(e):
                    cache.setdefault(e[0], []).append(
                        (e[1], e[2], e[3], e[5], True))
                    cache.setdefault(e[1], []).append(
                        (e[0], e[2], e[3], e[5], False))
            self._adj_cache = cache
        static_adj = self._adj_cache
        extra = {}

        def add(i, j, cost, is_road, geom=None):
            extra.setdefault(i, []).append((j, cost, is_road, geom, True))
            extra.setdefault(j, []).append((i, cost, is_road, geom,
                                            False))
        # dynamic edges: start/goal to their nearest nodes (and each
        # other). The candidate search is VECTORIZED: the old per-node
        # Python loop held the GIL for tens of ms per plan and froze
        # the game when a mass order queued dozens of plans.
        n_static = len(self._nodes)
        if (self._nodes_np is None
                or len(self._nodes_np) != n_static):
            self._nodes_np = np.array(
                [[v.x, v.y, v.z] for (v, _la, _lo) in self._nodes])
        cos_arc = math.cos(math.radians(OFFROAD_MAX_ARC_DEG))
        for dyn in (start_i, goal_i):
            dv = nodes[dyn][0]
            with np.errstate(all='ignore'):
                dots = self._nodes_np @ np.array([dv.x, dv.y, dv.z])
            near = np.nonzero(dots > cos_arc)[0]
            order_ = near[np.argsort(-dots[near])][:40]
            cands = [(math.degrees(math.acos(
                          max(-1.0, min(1.0, float(dots[j]))))), int(j))
                     for j in order_
                     if float(dots[j]) < 1.0 - 1e-12]
            other = goal_i if dyn == start_i else start_i
            ango = math.degrees(angle_between(nodes[dyn][0],
                                              nodes[other][0]))
            if 1e-6 < ango <= OFFROAD_MAX_ARC_DEG:
                cands.append((ango, other))
            cands.sort()
            linked = 0
            for ang, j in cands:
                if linked >= 14 and j < n_static:
                    break
                if not self.segment_land_ok(nodes[dyn][0], nodes[j][0]):
                    continue
                fac = self.world.terrain.offroad_cost_factor(
                    nodes[dyn][1], nodes[dyn][2],
                    nodes[j][1], nodes[j][2])
                if fac is None:
                    continue        # a wall of rock between them
                add(dyn, j, math.radians(ang) * GLOBE_RADIUS * fac, False)
                linked += 1

        # river checks: persistent cache for static pairs, per-call
        # for edges touching the start/goal
        river_cache = {}

        def river_mult(i, j):
            if i < n_static and j < n_static:
                return self._static_river_ok(i, j)
            key = (min(i, j), max(i, j))
            if key not in river_cache:
                river_cache[key] = self.river_passage(nodes[i][0],
                                                      nodes[j][0])
            return river_cache[key]

        def h(i):
            return (angle_between(nodes[i][0], nodes[goal_i][0]) *
                    GLOBE_RADIUS / ROAD_SPEED_MULTIPLIER)

        dist = {start_i: 0.0}
        prev = {}
        prev_road = {}
        prev_geom = {}
        pq = [(h(start_i), start_i)]
        seen = set()
        pops = 0
        while pq:
            _, cur = heapq.heappop(pq)
            if cur in seen:
                continue
            seen.add(cur)
            pops += 1
            if pops % 256 == 0:
                time.sleep(0.0005)  # breathe: the frame goes first
            if cur == goal_i:
                break
            neigh = static_adj.get(cur, [])
            if cur in extra:
                neigh = neigh + extra[cur]
            for (nxt, cost, is_road, geom, fwd) in neigh:
                if nxt in seen:
                    continue
                if not is_road:
                    rm = river_mult(cur, nxt)
                    if rm is None:
                        continue
                    cost = cost * rm    # fording wild rivers is slow
                nd = dist[cur] + cost
                if nd < dist.get(nxt, float('inf')):
                    dist[nxt] = nd
                    prev[nxt] = cur
                    prev_road[nxt] = is_road
                    prev_geom[nxt] = (geom, fwd)
                    heapq.heappush(pq, (nd + h(nxt), nxt))
        if goal_i not in prev and start_i != goal_i:
            # graph couldn't connect them: try a fine mask-accurate A*
            # (coastal walks, lake shores — as accurate as the map)
            return self._refine_land(start_vec, goal_vec)
        # reconstruct -- splicing each road edge\'s dense curve back
        # in, so the column marches the exact ribbon that is drawn
        path = []
        cur = goal_i
        while cur != start_i:
            mult = ROAD_SPEED_MULTIPLIER if prev_road.get(cur) else 1.0
            path.append((Vec3(nodes[cur][0]), mult))
            geom, fwd = prev_geom.get(cur, (None, True))
            if geom:
                seq = reversed(geom) if fwd else geom
                for v in seq:
                    path.append((Vec3(v), mult))
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
