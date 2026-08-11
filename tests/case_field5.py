"""The two-ocean batch: carrier powers sail flat-tops from day one
and open navy-first, the American main lines bind six cities, the
US roster slims, a supply ship anchors as a floating station on the
chain, the ease-aside walks at marching pace, sea routes run taut
instead of hugging the coast, and the bar furniture holds."""
from harness import boot, step, check, finish
from utils import latlon_to_vec, angle_between
from config import GLOBE_RADIUS, UNIT_SPEED_FACTOR
from panda3d.core import Vec3
import tech

g = boot('germany')

# ---------- THE CARRIER POWERS
for nat, has in (('usa', True), ('japan', True), ('germany', False),
                 ('britain', False)):
    got = 'aircraft_carrier' in tech.unlocked_units(nat, [])
    check(got == has, "%s %s the flat-top from day one"
          % (nat, "sails" if has else "must research"))
slate = g._default_budget_counts('usa', 40000)
check(slate.get('aircraft_carrier') == 1,
      "the American opening slate puts a carrier to sea")
check(slate.get('destroyer_sea_sea', 0) >= 3
      and slate.get('battleship', 0) >= 1,
      "and a heavier screen behind her (navy-first)")
check(slate.get('tank', 0) <= 1,
      "while the garage thins to pay for it (%d tanks)"
      % slate.get('tank', 0))
jslate = g._default_budget_counts('japan', 40000)
check(jslate.get('aircraft_carrier') == 1,
      "Japan's slate carries her flat-top too")

# ---------- THE AMERICAN MAIN LINES bind the six biggest cities
from geodata import CITY_POPULATION
us = [c for c in g.cities if c.country == 'usa']
check(len(us) == 30,
      "the American roster slims to %d towns" % len(us))
top6 = sorted(us, key=lambda c: -CITY_POPULATION.get(c.name, 120))[:6]
ends = []
for curve in g.world.rail_paths:
    ends.append(latlon_to_vec(*curve[0]))
    ends.append(latlon_to_vec(*curve[-1]))
for c in top6:
    near = min(angle_between(c.pos, e) * GLOBE_RADIUS for e in ends)
    check(near < 0.4,
          "a main line serves %s (%.2fwu)" % (c.name, near))

# ---------- THE FLOATING SUPPLY STATION
ship = g.spawn_unit('supply_ship', 'germany', 54.5, 10.5, seed=10,
                    water=True)
ship.supply = 1000.0
g.toggle_supply_station(ship)
check(ship.is_supply_station, "the anchor goes down")
ship.give_order({'kind': 'move', 'goal': latlon_to_vec(55.0, 11.0)})
check(ship.current_order is None and not ship.order_queue,
      "no order moves a station at anchor")
# a jobless full carrier DUMPS into the anchored station
mate = g.spawn_unit('supply_ship', 'germany', 54.5, 10.52, seed=11,
                    water=True)
mate.supply = mate.stats['supply_cap']
before = ship.supply
g._tick_supply()
check(ship.supply > before,
      "the chain pumps INTO the station (%d -> %d lbs)"
      % (before, ship.supply))
g.toggle_supply_station(ship)
check(not ship.is_supply_station, "anchor aweigh")
ship.give_order({'kind': 'move', 'goal': latlon_to_vec(55.0, 11.0)})
check(ship.current_order is not None or ship.order_queue
      or ship.plan_pending, "and she takes orders again")
ship.clear_orders()

# ---------- THE EASE-ASIDE WALKS, never teleports
a1 = g.spawn_unit('tank', 'germany', 52.0, 13.0, seed=20)
a2 = g.spawn_unit('tank', 'germany', 52.0, 13.0, seed=21)
a2.pos = Vec3(a1.pos)
p0 = Vec3(a2.pos)
g._tick_separation()
hop = max(angle_between(p0, a2.pos) * GLOBE_RADIUS,
          angle_between(Vec3(a1.pos), p0) * GLOBE_RADIUS)
pace = a1.stats['speed'] * UNIT_SPEED_FACTOR * g.game_speed * 0.4
check(hop <= pace * 1.15 + 1e-6,
      "one sweep moves a tank at most its own pace "
      "(%.4f <= %.4f wu, land-snap slack)" % (hop, pace))

# ---------- SEA ROUTES RUN TAUT: every leg is open water, and the
# string-pull leaves only the corners land forces
route = g.planner.plan('sea', latlon_to_vec(40.8, 14.2),
                       latlon_to_vec(45.2, 12.8))   # round the boot
check(route is not None, "the fleet rounds Italy")
pts = [p for (p, _m) in route]
legs_ok = all(g.planner._water_ok_lenient(a, b)
              for a, b in zip(pts[:-1], pts[1:]))
check(legs_ok, "every pulled leg is open water (router's own law)")
check(len(pts) <= 14,
      "and the route runs TAUT round the boot (%d waypoints)"
      % len(pts))

# ---------- THE FURNITURE
ar = g.getAspectRatio()
fs = g.top_bar.frame['frameSize']
check(fs[1] >= max(2.0, ar) - 1e-6,
      "the top bar plate runs wall to wall (%.2f >= %.2f)"
      % (fs[1], max(2.0, ar)))
# a transport's menu stands actions LEFT, units RIGHT, keys bigger
tpt = g.spawn_unit('personnel_transport', 'germany', 54.6, 10.6,
                   seed=30, water=True)
rider = g.spawn_unit('infantry', 'germany', 54.0, 10.0, seed=31)
rider.carried_by = tpt
tpt.cargo.append(rider)
g.clear_selection()
g.selected = [tpt]
tpt.set_selected(True)
g._refresh_selection_ui()
xs = sorted(b.getX() for b in g.bottom_bar.buttons
            if hasattr(b, 'getX'))
check(xs and xs[0] < -1.1 and xs[-1] > 0.2,
      "actions stand left, the roster right (%.2f .. %.2f)"
      % (xs[0], xs[-1]))
g.clear_selection()

finish()
