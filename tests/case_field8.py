"""1.3.3: THE WORKS ARE GROUND. A bunker is no longer a force field
that shoves vehicles off its rim (and trapped every one that began
inside, the engineer that built it above all) -- the ROUTER goes
round it, exactly as it goes round the sea and a closed frontier. A
bunker on a road blocks that road. And the capture banner no longer
locks a town away for a fortnight after it changes hands twice."""
from harness import boot, step, until, check, finish
from utils import latlon_to_vec, angle_between
from config import GLOBE_RADIUS
from structures import Bunker, BUNKER_RADIUS
from panda3d.core import Vec3
from config import GAME_VERSION

check(GAME_VERSION == '1.3.3', "the colours fly 1.3.3 (%s)"
      % GAME_VERSION)

g = boot('germany')


def clear_of(path, b, start=None):
    """Does this plotted route keep out of the works?"""
    pts = [p for (p, _m) in path]
    if start is not None:
        pts = [start] + pts
    worst = min(angle_between(p, b.pos) * GLOBE_RADIUS for p in pts)
    return worst, worst >= BUNKER_RADIUS * 0.95


# ---------- A BUNKER ON A ROAD BLOCKS THE ROAD
road = next(s for s in g.road_sections if s.kind == 'road'
            and g.territory_of(s.pos) == 'germany')
mid = Vec3(road.pts[len(road.pts) // 2])
a = Vec3(road.pts[0])
b_end = Vec3(road.pts[-1])
open_path = g.planner.plan('land', a, b_end)
check(open_path is not None, "the road carries a column end to end")
bunk = Bunker(g, *[float(x) for x in __import__('utils')
                   .vec_to_latlon(mid)], country='germany',
              name="ROADBLOCK")
g.bunkers.append(bunk)
g.sync_bunkers()
blocked = g.planner._ensure_bunker_edges()
check(bool(blocked),
      "the works close the ways they stand on (%d edge(s))"
      % len(blocked))
routed = g.planner.plan('land', a, b_end, avoid_bunkers=True)
check(routed is not None, "a vehicle still gets through")
worst, ok = clear_of(routed, bunk, a)
check(ok, "and its route goes ROUND the works (nearest %.3fwu of "
      "%.3f)" % (worst, BUNKER_RADIUS))
# a man on foot shelters in them: his road is not closed
foot = g.planner.plan('land', a, b_end, avoid_bunkers=False)
check(foot is not None, "the road is still a road to men on foot")

# ---------- A VEHICLE CAUGHT INSIDE DRIVES OUT
inside = Vec3(bunk.pos)
held = g.planner.bunkers_holding(inside)
check(id(bunk) in held, "the router knows what a point stands in")
out = g.planner.plan('land', inside, b_end, avoid_bunkers=True,
                     open_bunkers=held)
check(out is not None,
      "a vehicle inside the works can plot its way OUT")
shut = g.planner.plan('land', b_end, inside, avoid_bunkers=True)
if shut is not None:
    worst2 = min(angle_between(p, bunk.pos) * GLOBE_RADIUS
                 for (p, _m) in shut[:-1])
    check(worst2 >= BUNKER_RADIUS * 0.95,
          "but no vehicle plots its way IN (nearest %.3fwu)" % worst2)
else:
    check(True, "but no vehicle plots its way IN (refused outright)")

# ---------- THE ENGINEER THAT BUILT IT IS NOT TRAPPED
eng = g.spawn_unit('engineer', 'germany', 0, 0, seed=10)
eng.pos = Vec3(bunk.pos)
eng.supply = eng.stats['supply_cap']
goal = latlon_to_vec(*__import__('utils').vec_to_latlon(b_end))
g.game_speed = 8.0
eng.give_order({'kind': 'move', 'goal': goal})
got_out = until(g, lambda: angle_between(eng.pos, bunk.pos)
                * GLOBE_RADIUS > BUNKER_RADIUS * 1.5, 120,
                "the engineer drives clear")
check(got_out, "the engineer drives out of the works it built")
eng.clear_orders()

# ---------- A GOAL INSIDE THE WORKS BERTHS AT THE RIM
tank = g.spawn_unit('tank', 'germany', 0, 0, seed=11)
tank.pos = Vec3(a)
gl = g._legal_goal(tank, Vec3(bunk.pos))
check(angle_between(gl, bunk.pos) * GLOBE_RADIUS >= BUNKER_RADIUS,
      "a vehicle ordered onto the works stands at its edge")
foot2 = g.spawn_unit('infantry', 'germany', 0, 0, seed=12)
foot2.pos = Vec3(a)
gl2 = g._legal_goal(foot2, Vec3(bunk.pos))
check(angle_between(gl2, bunk.pos) * GLOBE_RADIUS < 1e-6,
      "a man on foot is sent straight in")

g.bunkers.remove(bunk)
bunk.cleanup()
g.sync_bunkers()
check(not g.planner._ensure_bunker_edges(),
      "and a struck work opens its ground again")

# ---------- THE CAPTURE LOCKOUT: a town traded back and forth must
# stay takeable (the field report's Warsaw, stuck till the fortnight)
warsaw = next(c for c in g.cities if c.name == 'Warsaw')
g.wars.add(frozenset(('germany', 'poland')))
g.wars.add(frozenset(('germany', 'soviet')))
g._rebuild_war_sets()
for u in list(g.units):
    if (u.alive and u.country in ('poland', 'soviet')
            and angle_between(u.pos, warsaw.pos) * GLOBE_RADIUS < 2.0):
        u.alive = False


def garrison(country, n):
    out = []
    for i in range(n):
        s = g.spawn_unit('infantry', country, warsaw.lat, warsaw.lon,
                         seed=200 + len(g.units) + i)
        s.pos = Vec3(warsaw.pos)
        out.append(s)
    return out


need = warsaw.required_infantry()
for round_no in range(3):
    garrison('germany', need)
    g._tick_capture_banners()
    check(warsaw.cap_np is not None and not warsaw.cap_np.isHidden(),
          "round %d: the banner flies over Warsaw" % (round_no + 1))
    check(g.attempt_capture(warsaw, 'germany'),
          "round %d: and the flag goes up" % (round_no + 1))
    check(warsaw.annexing,
          "round %d: the town is annexing (not yet taxable)"
          % (round_no + 1))
    # the Soviets take it straight back, annexing flag and all
    garrison('soviet', need)
    check(g.attempt_capture(warsaw, 'soviet'),
          "round %d: the Soviets take it back" % (round_no + 1))
check(warsaw.annexing,
      "the town stands ANNEXING after all that trading")
garrison('germany', need)
g._tick_capture_banners()
check(warsaw.cap_np is not None and not warsaw.cap_np.isHidden(),
      "AND THE BANNER STILL FLIES -- no lockout until the fortnight")

# ---------- THE LORRY WEIGHS SAFETY BESIDE DISTANCE
lorry = g.spawn_unit('supply_truck', 'germany', 52.0, 14.5, seed=300)
tankman = g.spawn_unit('tank', 'germany', 52.0, 14.5, seed=301)
check(g.hostile_ground(lorry),
      "a carrier at war carries a risk map (%s)"
      % sorted(g.hostile_ground(lorry)))
check(not g.hostile_ground(tankman),
      "a fighting column does not -- it is SENT into enemy country")
# the same run, priced with and without the danger
a2 = latlon_to_vec(52.0, 14.5)          # German ground
b2 = latlon_to_vec(52.3, 17.5)          # across the Polish frontier
plain = g.planner.plan('land', a2, b2)
careful = g.planner.plan('land', a2, b2,
                         risky=g.hostile_ground(lorry))
check(plain is not None and careful is not None,
      "both routes exist -- danger is a PRICE, not a wall")


def crosses(path, risky):
    n = 0
    for (p, _m) in path:
        o = g.territory_of(p)
        if o in risky:
            n += 1
    return n


risky = g.hostile_ground(lorry)
c_plain = crosses(plain, risky)
c_care = crosses(careful, risky)
check(c_care <= c_plain,
      "the careful route spends no longer in hostile country "
      "(%d vs %d waypoints)" % (c_care, c_plain))
# and she fills up at a source she can reach without running the
# gauntlet, when one is within reach
srcs = g._refill_sources(lorry)
pick = g._safest_source(lorry, srcs)
own = g.planner._arc_owners(Vec3(lorry.pos), Vec3(pick.pos))
check(not own or not (own & risky),
      "and she fills up by a road clear of the enemy")
g.wars.discard(frozenset(('germany', 'poland')))
g.wars.discard(frozenset(('germany', 'soviet')))
g._rebuild_war_sets()

finish()
