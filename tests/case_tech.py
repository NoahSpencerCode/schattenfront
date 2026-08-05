"""The branching research chart: graph sanity, gating, the
frontier, legacy-save migration, and the hiding of locked arms."""
from harness import boot, check, finish
import tech
from tech import (NODES, NAMES, BASE_UNITS, normalize,
                  available_nodes, unlocked_units, radar_unlocked)

# --- graph sanity: every wire lands, every power names every node
for nid, n in NODES.items():
    for r in n['req']:
        check(r in NODES, "%s req %s exists" % (nid, r))
for nat in ('germany', 'usa', 'britain', 'japan', 'soviet'):
    missing = [nid for nid in NODES if nid not in NAMES[nat]]
    check(not missing, "%s names complete" % nat)

# --- the frontier: only roots open at the start
front = set(available_nodes(set()))
check(front == {'artillery', 'medium_bombers', 'fleet_escorts'},
      "three roots open the chart (%s)" % sorted(front))
front2 = set(available_nodes({'fleet_escorts'}))
check({'submarines', 'fleet_train', 'capital_ships'} <= front2,
      "escorts open three sea paths")
check('naval_aviation' not in front2,
      "carriers wait on the fleet train")

# --- locked arms are locked
kit = unlocked_units('germany', set())
check('bomber' not in kit and 'destroyer_aa' not in kit
      and 'aircraft_carrier' not in kit,
      "bombers, escorts, carriers locked at the start")
check('fighter' in kit and 'tank' in kit,
      "the 1939 kit stands free")
kit2 = unlocked_units('germany', {'medium_bombers'})
check('bomber' in kit2, "research unlocks the bomber")
check(not radar_unlocked('germany', set()), "radar locked")
check(radar_unlocked('germany', {'artillery', 'detection'}),
      "detection unlocks radar")

# --- legacy saves map onto the graph
old = normalize({('land', 1), ('sea', 0)})
check({'artillery', 'heavy_armour', 'fleet_escorts',
       'submarines'} == old,
      "legacy pairs expand with their implied prerequisites")

# --- in the game: spending, gating, the budget filter
g = boot('germany')
g.research_points['germany'] = 100.0
check(not g.research_node('germany', 'heavy_armour'),
      "prerequisite bars the buy")
check(g.research_node('germany', 'artillery'), "root bought")
check(g.research_points['germany'] == 80.0, "20 RP spent")
check(g.research_node('germany', 'heavy_armour'),
      "opened node bought")
check(not g.research_node('germany', 'jet_propulsion'),
      "deep node still barred")

buyable = g.buyable_units('germany')
check('bomber' not in buyable, "budget roster hides the bomber")
check('heavy_tank' in buyable, "budget roster shows the unlock")

# the executor skips a stale order for a locked arm, no charge
g.funds['germany'] = 5000
g.resources['germany']['steel'] = 100
g._execute_budget('germany', {'bomber': 2}, False)
check(g.funds['germany'] == 5000,
      "stale locked order buys nothing")

finish()
