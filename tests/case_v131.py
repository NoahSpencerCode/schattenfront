"""The 1.3.1 field batch: prices, lorries, the frontier, the envoy,
cargo by return, junctions and the rail preference."""
from harness import boot, step, check, finish
from utils import latlon_to_vec, angle_between
from units import UNIT_TYPES, material_cost, stats_for
from config import GLOBE_RADIUS

# --- PRICES TRIPLE, the steel bill does not
check(UNIT_TYPES['tank']['cost'] == 960,
      "a tank costs $%d" % UNIT_TYPES['tank']['cost'])
check(UNIT_TYPES['battleship']['cost'] == 6000,
      "a battleship costs $%d" % UNIT_TYPES['battleship']['cost'])
check(material_cost('tank')['steel'] == 3,
      "and still bills 3 steel (%d)" % material_cost('tank')['steel'])
check(material_cost('battleship')['steel'] == 40,
      "and a battleship 40 (%d)"
      % material_cost('battleship')['steel'])

g = boot('germany')

# --- THE OPENING MANIFEST as the admiralty asked
slate = g._default_budget_counts('germany', 40000)
for ut, n in (('supply_ship', 3), ('naval_command', 1),
              ('destroyer_sea_sea', 2), ('aa_artillery', 1),
              ('personnel_transport', 2)):
    check(slate.get(ut) == n, "%d x %s on the manifest (%s)"
          % (n, ut, slate.get(ut)))

# --- A LORRY CARRIES MEN, NOT LORRIES
truck = g.spawn_unit('transport_truck', 'germany', 52.0, 13.0, seed=1)
rider = g.spawn_unit('infantry', 'germany', 52.01, 13.0, seed=2)
other = g.spawn_unit('supply_truck', 'germany', 52.01, 13.01, seed=3)
g._order_board(truck, [rider, other], False)
rider_ok = any(o.get('kind') == 'board'
               for o in ([rider.current_order] if rider.current_order
                         else []) + rider.order_queue)
other_ok = any(o.get('kind') == 'board'
               for o in ([other.current_order] if other.current_order
                         else []) + other.order_queue)
check(rider_ok, "infantry may board a lorry")
check(not other_ok, "a lorry may NOT be stacked on a lorry")

# --- THE FRONTIER BINDS THE LORRIES TOO
warsaw = next(c for c in g.cities if c.name == 'Warsaw')
sup = g.spawn_unit('supply_truck', 'germany', 52.0, 14.0, seed=4)
sup.supply = sup.stats['supply_cap']
sup.give_order({'kind': 'move', 'goal': latlon_to_vec(warsaw.lat,
                                                      warsaw.lon),
                'auto': True})
check(not sup.current_order and not sup.order_queue,
      "an automatic march across a closed frontier is refused")
g.wars.add(frozenset(('germany', 'poland')))
g._rebuild_war_sets()
sup.give_order({'kind': 'move', 'goal': latlon_to_vec(warsaw.lat,
                                                      warsaw.lon),
                'auto': True})
check(sup.current_order or sup.order_queue,
      "and the declaration opens it")

# --- CARGO BY RETURN: a one-time shipment lands at once
g.funds['germany'] = 90000
oil0 = g.resources['germany']['oil']
verdict = g.propose_deal('romania',
                         [{'kind': 'funds_once', 'amount': 9000}],
                         [{'kind': 'res_once', 'res': 'oil',
                           'amount': 60}])
check(verdict == 'accept', "the one-shipment purchase is accepted")
check(g.resources['germany']['oil'] == oil0 + 60,
      "and the cargo is landed at once (%d -> %d)"
      % (oil0, g.resources['germany']['oil']))

# --- THE ENVOY: nothing binds us until we sign
check(not g.allied('germany', 'italy'), "no pact with Italy yet")
ok = g.envoy_arrives('italy', [{'kind': 'alliance'}],
                     [{'kind': 'funds_once', 'amount': 1000}])
check(ok, "an envoy is admitted")
check(not g.allied('germany', 'italy'),
      "and NOTHING is bound while he waits")
check(not g.envoy_arrives('japan', [{'kind': 'peace'}], []),
      "a second envoy is turned away at the door")
g._envoy_decline()
check(not g.allied('germany', 'italy'), "declining binds nothing")
check(g.envoy_fax is None, "the anteroom is clear")
g.envoy_arrives('italy', [{'kind': 'alliance'}],
                [{'kind': 'funds_once', 'amount': 1000}])
g._envoy_accept()
check(g.allied('germany', 'italy'), "accepting signs the pact")

# --- THE WAYS MEET: one fixed ring size, and rail is preferred
from pathfinding import RAIL_ROUTE_PREFERENCE, JUNCTION_DEG
check(RAIL_ROUTE_PREFERENCE > 1.5,
      "the router prefers a railway (x%.2f)" % RAIL_ROUTE_PREFERENCE)
check(JUNCTION_DEG > 0, "and wires the ways where they cross")
check(abs(g.WAYPOINT_RING - 0.0315) < 1e-6,
      "the survey ring is fixed size (%.4f)" % g.WAYPOINT_RING)
# the JOIN rings keep their ORIGINAL small size -- folding them
# into the survey ring's size was an unasked change, and wrong
check(abs(g.PATH_JOIN_RING - 0.0072) < 1e-6,
      "the join rings keep their original size (%.4f)"
      % g.PATH_JOIN_RING)

finish()
