"""1.3.2: the version stands, and every selected combatant wears a
thin red ring at its guns' longest reach -- the gunnery law's best
case, which for the long arms is NOT the vision circle."""
from harness import boot, step, check, finish
from panda3d.core import Vec3
from config import GAME_VERSION, VISION_SCALE, AIR_VISION_MULT

check(GAME_VERSION == '1.3.2', "the colours fly 1.3.2 (%s)"
      % GAME_VERSION)

g = boot('germany')

# --- THE REACH LAW, arm by arm (day figures, in world units)
tank = g.spawn_unit('tank', 'germany', 52.0, 13.0, seed=1)
art = g.spawn_unit('artillery', 'germany', 52.1, 13.0, seed=2)
inf = g.spawn_unit('infantry', 'germany', 52.2, 13.0, seed=3)
ftr = g.spawn_unit('fighter', 'germany', 52.3, 13.0, seed=4)
bmb = g.spawn_unit('bomber', 'germany', 52.4, 13.0, seed=5)
bb = g.spawn_unit('battleship', 'germany', 54.5, 10.5, seed=6,
                  water=True)
lorry = g.spawn_unit('supply_truck', 'germany', 52.5, 13.0, seed=7)

# tanks and artillery: twice their eyes (indirect fire with an
# observer); infantry: capped by its own eyes
check(abs(tank.max_attack_range()
          - min(tank.stats['range'],
                tank.stats['vision'] * VISION_SCALE * 2)) < 1e-9,
      "a tank reaches twice its eyes (%.3f wu)"
      % tank.max_attack_range())
check(art.max_attack_range() > art.stats['vision'] * VISION_SCALE,
      "artillery ranges BEYOND its own vision (%.3f wu)"
      % art.max_attack_range())
check(abs(inf.max_attack_range()
          - inf.stats['vision'] * VISION_SCALE) < 1e-9,
      "infantry is capped by its own eyes (%.3f wu)"
      % inf.max_attack_range())
# warships: twice their eyes; aircraft: shorter than they see
check(abs(bb.max_attack_range()
          - min(bb.stats['range'],
                bb.stats['vision'] * VISION_SCALE * 2)) < 1e-9,
      "a battleship reaches twice its eyes (%.3f wu)"
      % bb.max_attack_range())
air_vis = bmb.stats['vision'] * VISION_SCALE * AIR_VISION_MULT
check(bmb.max_attack_range() < air_vis,
      "a bomber strikes far shorter than it sees (%.3f < %.3f)"
      % (bmb.max_attack_range(), air_vis))
check(ftr.max_attack_range() <= ftr.stats['vision'] * VISION_SCALE
      * AIR_VISION_MULT + 1e-9,
      "a fighter's reach never exceeds its eyes")
check(lorry.max_attack_range() == 0.0,
      "a lorry has no reach at all")

# --- THE RING ITSELF: appears on selection, at true world radius,
# and goes away with the selection
check(tank.range_ring is None, "no ring is built before selection")
tank.set_selected(True)
step(g, 2)
check(tank.range_ring is not None
      and not tank.range_ring.isHidden(),
      "selecting shows the red reach ring")
tank.set_selected(False)
check(tank.range_ring.isHidden(),
      "deselecting puts the ring away")
lorry.set_selected(True)
check(lorry.range_ring is None,
      "a unit without guns wears no ring")
lorry.set_selected(False)

# --- A DIRECT MOVE OUTRANKS THE RAMP: a transport waiting on a
# boarder who never comes must never be pinned to the quay
from utils import latlon_to_vec
ship = g.spawn_unit('personnel_transport', 'germany', 54.5, 10.6,
                    seed=20, water=True)
walker = g.spawn_unit('infantry', 'germany', 53.0, 10.0, seed=21)
g._order_board(ship, [walker], False)
check(g.inbound_boarders(ship) == 1, "one boarder stands inbound")
# a QUEUED move holds at the ramp, as it should
ship.give_order({'kind': 'move',
                 'goal': latlon_to_vec(55.0, 11.5)}, queue=True)
ship.update(0.1)
check(ship.current_order is None,
      "a queued move HOLDS for the boarder")
# a DIRECT move sails at once
ship.clear_orders()
ship.give_order({'kind': 'move',
                 'goal': latlon_to_vec(55.0, 11.5)})
ship.update(0.1)
check(ship.current_order is not None
      and ship.current_order.get('kind') == 'move',
      "a DIRECT move overrides the wait and sails")
walker.clear_orders()

# --- AN ATTACK ORDER CHASES ITS PREY while it stays in sight
g.wars.add(frozenset(('germany', 'poland')))
g._rebuild_war_sets()
hunter = g.spawn_unit('tank', 'germany', 52.0, 18.0, seed=22)
hunter.supply = hunter.stats['supply_cap']
prey = g.spawn_unit('infantry', 'poland', 52.0, 18.05, seed=23)
hunter.give_order({'kind': 'attack', 'target': prey})
hunter._pursuit_t = -9.0
hunter.update(0.05)         # promotes the order; the chase ticks
o = hunter.current_order
check(o is not None and o.get('_last_seen') is not None,
      "the hunter marks where the prey stands")
seen0 = Vec3(o['_last_seen'])
# the prey bolts BEYOND sight: the mark must NOT follow
prey.pos = latlon_to_vec(52.0, 25.0)
hunter._pursuit_t = -9.0
g.tick_attack_pursuit(hunter)
check((Vec3(o['_last_seen']) - seen0).length() < 1e-6,
      "sight lost: the column keeps the LAST KNOWN place")
# the prey walks back into view: the chase locks on again
prey.pos = latlon_to_vec(52.0, 18.10)
hunter._pursuit_t = -9.0
g.tick_attack_pursuit(hunter)
check((Vec3(o['_last_seen']) - Vec3(prey.pos)).length() < 1e-6,
      "sight regained: the chase locks onto the new position")

finish()
