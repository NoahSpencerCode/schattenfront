"""1.3.2: the version stands, and every selected combatant wears a
thin red ring at its guns' longest reach -- the gunnery law's best
case, which for the long arms is NOT the vision circle."""
from harness import boot, step, check, finish
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

finish()
