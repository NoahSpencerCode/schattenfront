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
check(front == {'artillery', 'medium_bombers', 'naval_gunnery'},
      "three roots open the chart (%s)" % sorted(front))
front2 = set(available_nodes({'naval_gunnery'}))
check({'submarines', 'capital_gunnery'} <= front2,
      "gunnery opens the boats and the capital ships")
check('naval_aviation' not in front2,
      "carriers wait on the capital gunnery")

# --- locked arms are locked
kit = unlocked_units('germany', set())
check('bomber' not in kit and 'aircraft_carrier' not in kit
      and 'heavy_cruiser' not in kit
      and 'fast_battleship' not in kit,
      "bombers and the ADVANCED hulls are locked at the start")
check('fighter' in kit and 'tank' in kit,
      "the 1939 kit stands free")
# THE 1939 FLEET sails from the first day
for ship in ('supply_ship', 'battleship', 'destroyer_aa',
             'destroyer_sea_land', 'destroyer_sea_sea',
             'personnel_transport', 'naval_command'):
    check(ship in kit, "%s sails at the bell" % ship)
# and what research buys is a BETTER hull, in every measure
from units import stats_for
free_bb = stats_for('battleship', 'germany')
adv_bb = stats_for('fast_battleship', 'germany')
check(adv_bb['hp'] > free_bb['hp']
      and adv_bb['damage'] > free_bb['damage']
      and adv_bb['range'] > free_bb['range']
      and adv_bb['speed'] > free_bb['speed'],
      "the researched capital ship beats the free one everywhere")
free_dd = stats_for('destroyer_sea_sea', 'germany')
adv_ca = stats_for('heavy_cruiser', 'germany')
check(adv_ca['hp'] > free_dd['hp']
      and adv_ca['damage'] > free_dd['damage']
      and adv_ca['range'] > free_dd['range'],
      "the researched cruiser out-armours and out-guns a destroyer")
kit2 = unlocked_units('germany', {'medium_bombers'})
check('bomber' in kit2, "research unlocks the bomber")
check(not radar_unlocked('germany', set()), "radar locked")
check(radar_unlocked('germany', {'artillery', 'detection'}),
      "detection unlocks radar")

# --- legacy saves map onto the graph
old = normalize({('land', 1), ('sea', 0)})
check({'artillery', 'heavy_armour', 'naval_gunnery',
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

# --- the opening slate never commits to a locked arm
g2_locked = [ut for ut in g.budget_counts
             if ut not in g.buyable_units('germany')]
check(not g2_locked,
      "no locked line on the opening manifest (%s)" % g2_locked[:3])
buyable = g.buyable_units('germany')
check('supply_ship' in buyable,
      "supply ships are BUYABLE at the bell -- they need no lab")
check('heavy_cruiser' not in buyable,
      "the researched cruiser is not")

finish()
