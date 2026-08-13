"""The field laws of the passage-and-works batch: the router
honours the frontier (no course is plotted through a country that
has not granted passage), and an engineer lays a way STRETCH BY
STRETCH, advancing along his own survey -- which also proves a rail
leg completes without the _dry_the_line crash of the field report."""
from harness import boot, step, until, check, finish
from utils import latlon_to_vec, angle_between
from config import GLOBE_RADIUS
from panda3d.core import Vec3
import numpy as np

g = boot('germany')

# ---------- THE FRONTIER LAW: who is closed ground
inf = g.spawn_unit('infantry', 'germany', 52.5, 13.4, seed=10)
banned = g.closed_frontiers(inf)
check('poland' in banned, "Poland is closed ground before the war")
check('germany' not in banned, "home ground is never closed")

g.rights.append({'with': 'poland', 'kind': 'passage',
                 'dir': 'theirs'})
check('poland' not in g.closed_frontiers(inf),
      "a signed right of passage opens the frontier")
g.rights.pop()

g.wars.add(frozenset(('germany', 'poland')))
g._rebuild_war_sets()
check('poland' not in g.closed_frontiers(inf),
      "war opens the frontier unasked")
g.wars.discard(frozenset(('germany', 'poland')))
g._rebuild_war_sets()

ship = g.spawn_unit('personnel_transport', 'germany', 54.5, 10.5,
                    seed=11, water=True)
check(g.closed_frontiers(ship) == frozenset(),
      "the sea knows no frontier")

# ---------- THE ROUTE ITSELF: at war with the Soviet Union but not
# with Poland, a column ordered to the Soviet front finds every road
# running through closed ground -- and the router refuses to sneak
# through where the goal-gate cannot see
g.wars.add(frozenset(('germany', 'soviet')))
g._rebuild_war_sets()
banned = g.closed_frontiers(inf)
check('soviet' not in banned and 'poland' in banned,
      "war opens the Soviet frontier; Poland stays shut")
minsk = next(c for c in g.cities if c.name == 'Minsk')
berlin = next(c for c in g.cities if c.name == 'Berlin')


def transits(path):
    """Every country whose ground the path touches, judged by the
    same discs the frontier law itself rules by."""
    terr = g.planner._terr
    arr = np.array([[p.x, p.y, p.z] for (p, _m) in path])
    idx = g.planner._owners_of_np(arr, terr)
    return {terr[1][int(x)]
            for x in set(idx.tolist()) if int(x) >= 0}


open_path = g.planner.plan('land', Vec3(berlin.pos), Vec3(minsk.pos))
check(open_path is not None, "with open borders a route exists")
crossed = transits(open_path)
check(bool(crossed & banned),
      "and it runs through closed ground (%s)"
      % sorted(crossed & banned))
sealed = g.planner.plan('land', Vec3(berlin.pos), Vec3(minsk.pos),
                        banned=banned)
if sealed is None:
    check(True, "the frontier law refuses the march outright")
else:
    check(not (transits(sealed) & banned),
          "the plotted detour never enters closed ground (%s)"
          % sorted(transits(sealed) & banned))
# treaties reopen the road: grant passage over every country the
# open route transited, and the same march is legal again
warpath = g.planner.plan('land', Vec3(berlin.pos), Vec3(minsk.pos),
                         banned=banned - crossed)
check(warpath is not None,
      "rights of passage over %s reopen the road east"
      % sorted(banned & crossed))
g.wars.discard(frozenset(('germany', 'soviet')))
g._rebuild_war_sets()

# ---------- THE PROGRESSIVE WAY: a road grows stretch by stretch,
# the party advancing along its own survey
eng = g.spawn_unit('engineer', 'germany', 52.0, 13.0, seed=20)
eng.supply = eng.stats['supply_cap']
a = latlon_to_vec(52.0, 13.0)
b = latlon_to_vec(52.0, 19.0)
eng.pos = Vec3(a)
n0 = len(getattr(g.world, 'custom_road_paths', []))
eng.give_order({'kind': 'build', 'what': 'road', 'site': Vec3(a),
                'points': [Vec3(b)], 'from': Vec3(a), 't': 40.0,
                'cost': 0})
g.game_speed = 24.0
partial = until(
    g, lambda: (len(getattr(g.world, 'custom_road_paths', [])) > n0
                and eng.current_order is not None),
    180, "a stretch stands while the party still works")
check(partial,
      "the way grows WHILE the party works -- not at the last second")
done = until(g, lambda: eng.current_order is None
             and not eng.order_queue, 300, "the road leg completes")
check(done, "the whole leg stands")
slices = g.world.custom_road_paths[n0:]
check(len(slices) >= 2,
      "the leg was laid in stretches (%d of them)" % len(slices))
joined = all(abs(s1[-1][0] - s2[0][0]) < 1e-9
             and abs(s1[-1][1] - s2[0][1]) < 1e-9
             for s1, s2 in zip(slices[:-1], slices[1:]))
check(joined, "and the stretches join end to end")
arrived = until(g, lambda: angle_between(eng.pos, b) * GLOBE_RADIUS
                < 0.5, 180, "the party walks out the way")
check(arrived, "the party stands at the head of its own way")

# ---------- THE RAIL LEG COMPLETES (the crash of the field report:
# _complete_build called a _dry_the_line that never existed, and a
# finishing railroad took the game down)
eng2 = g.spawn_unit('engineer', 'germany', 51.0, 10.0, seed=21)
eng2.supply = eng2.stats['supply_cap']
a2 = latlon_to_vec(51.0, 10.0)
b2 = latlon_to_vec(51.0, 16.0)
eng2.pos = Vec3(a2)
nr0 = len(getattr(g.world, 'custom_rail_paths', []))
eng2.give_order({'kind': 'build', 'what': 'rail', 'site': Vec3(a2),
                 'points': [Vec3(b2)], 'from': Vec3(a2), 't': 160.0,
                 'cost': 0})
done2 = until(g, lambda: eng2.current_order is None
              and not eng2.order_queue, 400, "the rail leg completes")
check(done2, "a RAILROAD leg completes -- the field crash is dead")
rails = g.world.custom_rail_paths[nr0:]
check(len(rails) >= 2, "the line too was laid in stretches (%d)"
      % len(rails))
wet = tot = 0
for curve in rails:
    la = np.array([p[0] for p in curve])
    lo = np.array([p[1] for p in curve])
    wet += int((~g.world.fine_flags(la, lo)).sum())
    tot += len(la)
check(wet == 0, "and the laid line is DRY (%d wet of %d)"
      % (wet, tot))

# ---------- the incrementally-grown overlay IS the canonical one:
# a save's section state is zipped back by INDEX, so the standing
# list must match what a restore-time full rebuild produces
key = [(s.kind, round(s.pos.x, 5), round(s.pos.y, 5),
        round(s.pos.z, 5)) for s in g.road_sections]
g._build_road_overlay()
key2 = [(s.kind, round(s.pos.x, 5), round(s.pos.y, 5),
         round(s.pos.z, 5)) for s in g.road_sections]
check(key == key2,
      "the grown overlay equals a full rebuild (%d sections) -- "
      "saved section state stays index-true" % len(key))

finish()
