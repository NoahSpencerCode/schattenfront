"""Command chaining: tank -> embark -> landing -> queued march.

Drives the real order machinery: a tank is ordered aboard a
personnel transport, the landing is sited on Germany's own Baltic
coast, and a follow-up march is queued -- all before the tank has
even reached the quay. The case then runs the sim until the tank
stands ashore at the far end, marching on its queued goal.
"""
from harness import boot, step, until, check, finish
from utils import latlon_to_vec, vec_to_latlon, angle_between
from config import GLOBE_RADIUS

g = boot('germany')
g.game_speed = 8.0

# a quiet stage on the German Baltic shore: Kiel bay -> Ruegen
tank = g.spawn_unit('tank', 'germany', 54.35, 10.20, seed=1)
tank.supply = tank.stats['supply_cap']
tr = g.spawn_unit('personnel_transport', 'germany', 54.50, 10.35,
                  seed=2, water=True)
tr.supply = tr.stats['supply_cap']
step(g, 10)

# 1. embark: the pending voyage is detected
g.selected = [tank]
g._order_board(tr, [tank], False)
check(g._chain_pending(tank) is tr, "board order opens a chain")

# 2. the next ground click sites the LANDING on the carrier
shore = latlon_to_vec(54.35, 13.60)      # near Ruegen, German soil
g._order_landing(tr, shore)
pend = ([tr.current_order] if tr.current_order else []) \
    + list(tr.order_queue)
check(any(o.get('kind') == 'unload' for o in pend),
      "landing click queues unload on the carrier")

# 3. further clicks queue the march after the landing
inland = latlon_to_vec(54.10, 13.90)
tank.give_order({'kind': 'move', 'goal': inland}, queue=True)
check(any(o.get('kind') == 'move' for o in tank.order_queue),
      "post-landing march queued on the passenger")

# 4. the transport holds at anchor until the tank is aboard
step(g, 60)
aboard = tank in tr.cargo
moved = angle_between(tr.pos, latlon_to_vec(54.50, 10.35)) \
    * GLOBE_RADIUS
check(aboard or moved < 0.3,
      "carrier holds (or tank already aboard) while boarding")

ok = until(g, lambda: tank in tr.cargo, 300, "tank aboard")
check(ok, "tank embarks")
check(any(o.get('kind') == 'move' for o in tank.order_queue),
      "queued march survives embarkation")

# 5. the voyage runs and the tank steps ashore
ok = until(g, lambda: tank.carried_by is None and tank.alive,
           600, "tank ashore")
check(ok, "carrier sails and puts the tank ashore")
if ok:
    la, lo = vec_to_latlon(tank.pos)
    check(lo > 12.0, "ashore at the FAR coast (lon %.1f)" % lo)
    ok2 = until(g, lambda: (tank.current_order or {})
                .get('kind') == 'move' or
                angle_between(tank.pos, inland) * GLOBE_RADIUS < 0.6,
                240, "march resumes")
    check(ok2, "tank resumes its queued march ashore")

finish()
