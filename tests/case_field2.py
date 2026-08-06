"""The field laws added after 1.3.0: no counter stands on another,
a fleet ordered onto land spreads across water, deposits belong to
their own town, rails keep off the sea, the laboratories are funded
by cities alone, and a threatened town defends itself."""
from harness import boot, check, finish
from utils import angle_between, latlon_to_vec, vec_to_latlon
from config import GLOBE_RADIUS, FORMATION_SPACING
import numpy as np

g = boot('germany', ai=True)

# --- DEPOSITS belong to the town whose name they carry
strays = [d.name for d in g.deposits
          if min(g.cities, key=lambda c: angle_between(d.pos, c.pos))
          is not d.city]
check(not strays, "every deposit is nearest its OWN town (%s)"
      % strays[:3])

# --- RAILS keep off the sea
wet = 0
for curve in g.world.rail_paths:
    lat = np.array([p[0] for p in curve])
    lon = np.array([p[1] for p in curve])
    wet += int((~g.world.fine_flags(lat, lon)).sum())
check(wet == 0, "no main line runs over water (%d wet points)" % wet)

# --- THE LABORATORIES take nothing from the taxes
check(all(v == 0 for v in g.research_pct.values()),
      "no tithe is skimmed from any treasury")
# the claim is that NO TITHE is skimmed for the laboratories --
# not that the treasury grows (a fortnight's budget may well cost
# more than a fortnight's taxes)
for c in g.cities:
    if c.country == 'germany':
        c.focus = 'finance'         # no town working for the chart
rp0 = g.research_points['germany']
g._fortnight_rollover()
check(g.research_points['germany'] == rp0,
      "the taxes pay the treasury, never the laboratories")

# --- THE OPENING SLATE is a staff and a handful, not an army
from units import stats_for
slate = g._default_budget_counts('germany', 40000)
for cmd in ('army_command', 'naval_command', 'airforce_command'):
    check(slate.get(cmd) == 1, "one %s on the opening slate" % cmd)
total = sum(n for n in slate.values())
check(total <= 20, "the opening slate is a handful (%d pieces)" % total)
check(slate.get('supply_ship') == 3, "three supply ships")
check(slate.get('destroyer_sea_sea') == 2, "two destroyers")
check(slate.get('personnel_transport') == 2, "two transports")
check(slate.get('aa_artillery') == 1, "one AA battery")
cost = sum(stats_for(u, 'germany')['cost'] * n
           for u, n in slate.items())
check(cost < 40000,
      "and the treasury still has money in hand ($%d of $40000)"
      % cost)

# --- NO TWO COUNTERS STAND ON THE SAME GROUND
# on GERMAN soil: a column ordered across a closed frontier is
# turned back now, which would leave the mover below orderless
pile = []
for i in range(6):
    u = g.spawn_unit('infantry', 'germany', 52.0, 13.0, seed=500 + i)
    pile.append(u)
anchor = pile[0].pos
for u in pile:
    u.pos = anchor
check(min(angle_between(a.pos, b.pos) for i, a in enumerate(pile)
          for b in pile[i + 1:]) == 0.0, "six counters stacked dead")
for _ in range(60):
    g._tick_separation()
worst = min(angle_between(a.pos, b.pos) * GLOBE_RADIUS
            for i, a in enumerate(pile) for b in pile[i + 1:])
check(worst >= FORMATION_SPACING * 0.9,
      "the pile unpicks itself to formation spacing (%.4fwu)" % worst)

# a column UNDER ORDERS is left alone by the sweep
mover = g.spawn_unit('infantry', 'germany', 52.0, 13.0, seed=600)
mover.pos = anchor
mover.give_order({'kind': 'move', 'goal': latlon_to_vec(52.3, 13.3),
                  'auto': True})
check(mover.current_order is not None or mover.order_queue,
      "the mover holds an order on home ground")
held = mover.pos
g._tick_separation()
check(mover.pos == held, "a unit under orders is not shoved about")

# --- A FLEET ORDERED ONTO LAND SPREADS ACROSS WATER
ships = [g.spawn_unit('personnel_transport', 'germany',
                      54.45 + i * 0.02, 10.3, seed=610 + i, water=True)
         for i in range(4)]
goals = g._formation_goals(latlon_to_vec(54.30, 10.60), ships)
check(len(set((round(p.x, 5), round(p.y, 5), round(p.z, 5))
              for p in goals)) == 4,
      "four hulls get four distinct waypoints")
dry = [p for p in goals
       if g.world.is_land(*vec_to_latlon(p))]
check(not dry, "every waypoint lies on WATER (%d on land)" % len(dry))
spread = min(angle_between(a, b) * GLOBE_RADIUS
             for i, a in enumerate(goals) for b in goals[i + 1:])
check(spread > 0.01, "and they stand apart (%.3fwu)" % spread)

# --- A THREATENED TOWN DEFENDS ITSELF
sov = g._nation_ais['soviet']
minsk = next(c for c in g.cities if c.name == 'Minsk')
g.wars.add(frozenset(('germany', 'soviet')))
g._rebuild_war_sets()
army = [g.spawn_unit('tank', 'soviet', minsk.lat + 2.0, minsk.lon + 2.0,
                     seed=700 + i) for i in range(6)]
for u in army:
    u.supply = u.stats['supply_cap']
for i in range(3):
    u = g.spawn_unit('tank', 'germany', minsk.lat, minsk.lon,
                     seed=800 + i)
    u.pos = minsk.pos
    u.supply = u.stats['supply_cap']
n0 = sum(1 for u in g.units if u.alive and u.country == 'soviet'
         and u.unit_type == 'infantry'
         and angle_between(u.pos, minsk.pos) < 0.05)
g._pending_ai_orders.clear()
sov._defend()
n1 = sum(1 for u in g.units if u.alive and u.country == 'soviet'
         and u.unit_type == 'infantry'
         and angle_between(u.pos, minsk.pos) < 0.05)
check(n1 > n0, "the town calls its own men up (%d raised)" % (n1 - n0))
sent = sum(1 for u, o in g._pending_ai_orders
           if o.get('goal') is not None
           and angle_between(o['goal'], minsk.pos) < 0.01)
check(sent >= 3, "and the field army marches to it (%d columns)" % sent)

finish()
