"""Field laws: the bunker wall turns vehicles and quarters fire on
Enlisted; no city falls while enemies stand near it."""
from harness import boot, step, until, check, finish
from utils import latlon_to_vec, angle_between
from config import GLOBE_RADIUS
from structures import Bunker, BUNKER_RADIUS

g = boot('germany')
g.game_speed = 8.0

# a bunker on open German ground
b = Bunker(g, 52.0, 12.0, 'germany', "TEST BUNKER")
g.bunkers.append(b)

# --- the wall: a tank ordered straight through deflects around
tank = g.spawn_unit('tank', 'germany', 52.0, 11.2, seed=11)
tank.supply = tank.stats['supply_cap']
inf = g.spawn_unit('infantry', 'germany', 52.0, 11.2, seed=12)
inf.supply = inf.stats['supply_cap']
step(g, 5)
goal = latlon_to_vec(52.0, 12.8)        # dead through the works
tank.give_order({'kind': 'move', 'goal': goal, 'auto': True})
inf.give_order({'kind': 'move', 'goal': goal, 'auto': True})

breached = []


def watch():
    d = angle_between(tank.pos, b.pos) * GLOBE_RADIUS
    if d < BUNKER_RADIUS - 0.02:
        breached.append(d)
    done = angle_between(tank.pos, goal) * GLOBE_RADIUS < 0.15
    return done


until(g, watch, 300, "tank crosses")
check(not breached,
      "the tank never enters the wall (breaches: %d)" % len(breached))
check(angle_between(tank.pos, goal) * GLOBE_RADIUS < 0.2,
      "the tank still reaches the far side, around the works")

# --- the shelter: fire on Enlisted inside drops to a quarter
inf2 = g.spawn_unit('infantry', 'germany', 52.0, 12.0, seed=13)
inf2.pos = latlon_to_vec(52.0, 12.0)
foe = g.spawn_unit('tank', 'soviet', 52.1, 12.05, seed=14)
foe.supply = foe.stats['supply_cap']
g.wars.add(frozenset(('germany', 'soviet')))
g._rebuild_war_sets()
import random
random.seed(7)
hp0 = inf2.hp
g.resolve_shot(foe, inf2)
sheltered_dmg = hp0 - inf2.hp
inf3 = g.spawn_unit('infantry', 'germany', 40.0, 5.0, seed=15)
hp1 = inf3.hp
random.seed(7)
g.resolve_shot(foe, inf3)
open_dmg = hp1 - inf3.hp
if open_dmg > 0:
    check(abs(sheltered_dmg / open_dmg - 0.25) < 0.05,
          "bunkered fire lands at a quarter (%.2f)"
          % (sheltered_dmg / open_dmg))
else:
    check(sheltered_dmg == 0 and open_dmg == 0,
          "peace holds fire entirely (both zero)")

# --- capture wants a cleared field (same world: war on Poland)
g2 = g
warsaw = next(c for c in g2.cities if c.name == 'Warsaw')
g2.wars.add(frozenset(('germany', 'poland')))
g2._rebuild_war_sets()
check(g2.at_war('germany', 'poland'), "state of war exists")

need = warsaw.required_infantry()
for i in range(need):
    u = g2.spawn_unit('infantry', 'germany', warsaw.lat, warsaw.lon,
                      seed=300 + i)
    u.pos = warsaw.pos
    u.supply = u.stats['supply_cap']
step(g2, 5)
# polish garrison stands ON the town: capture must refuse
foes = g2.enemies_near_city(warsaw, 'germany')
check(foes > 0, "%d defenders stand near Warsaw" % foes)
check(not g2.attempt_capture(warsaw, 'germany'),
      "no capture under the enemy's guns")

# clear the field: the defenders fall; capture proceeds
for u in list(g2.units):
    if u.alive and u.country == 'poland' and \
            u.dist_to(warsaw.pos) < 1.0:
        g2.unit_destroyed(u, None)
step(g2, 5)
check(g2.enemies_near_city(warsaw, 'germany') == 0, "field cleared")
check(g2.attempt_capture(warsaw, 'germany'),
      "the flag rises over a cleared town")

finish()
