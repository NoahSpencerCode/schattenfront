"""Command chaining, driven through the REAL right-click dispatch
(on_rmb) rather than the order handlers underneath it -- the first
version of this case called _order_board/_order_landing directly and
so never noticed that boarding emptied the player's selection and
killed the chain stone dead.

Select infantry, right-click the transport, let them board, then
right-click ground for the landing and again for the march inland.
"""
from harness import boot, step, until, check, finish
from panda3d.core import Point2
from utils import latlon_to_vec, vec_to_latlon, angle_between
from config import GLOBE_RADIUS


class FakeMouse:
    """Stands in for the mouse watcher so a case can click."""

    def __init__(self):
        self.mpos = Point2(0, 0)
        self.shift = False

    def hasMouse(self):
        return True

    def getMouse(self):
        return self.mpos

    def isButtonDown(self, key):
        return self.shift


g = boot('germany')
g.game_speed = 8.0
mouse = FakeMouse()
g.mouseWatcherNode = mouse


def click(world_pos):
    """A right-click on a point of the world."""
    mouse.mpos = Point2(g.screen_pos(world_pos))
    g.mouse_ground_point = lambda: world_pos
    g.on_rmb()


# a quiet stage on the German Baltic shore
inf = []
for i in range(5):
    u = g.spawn_unit('infantry', 'germany', 54.42 + i * 0.01, 10.28,
                     seed=i)
    u.supply = u.stats['supply_cap']
    inf.append(u)
tr = g.spawn_unit('personnel_transport', 'germany', 54.45, 10.30,
                  seed=99, water=True)
tr.supply = tr.stats['supply_cap']
g.cam_lat = g.cam_lat_target = 54.4
g.cam_lon = g.cam_lon_target = 10.3
g.cam_dist = g.cam_dist_target = GLOBE_RADIUS + 1.0
step(g, 30)

g.selected = list(inf)
for u in inf:
    u.set_selected(True)

# CLICK 1 -- the transport: everyone is ordered aboard
click(g._unit_world_pos(tr))
ordered = sum(1 for u in inf
              if any(o.get('kind') == 'board'
                     for o in ([u.current_order] if u.current_order
                               else []) + u.order_queue))
check(ordered == 5, "all five ordered aboard (%d)" % ordered)
check(all(g._chain_pending(u) is tr for u in inf),
      "the chain is open on every man")

# they march aboard -- AND THE SELECTION MUST SURVIVE IT
ok = until(g, lambda: all(u.carried_by is tr for u in inf), 400,
           "aboard")
check(ok, "the party embarks")
check(len(g.selected) == 5,
      "the selection survives boarding (%d held)" % len(g.selected))

# CLICK 2 -- open ground: this is the LANDING, queued on the carrier
dest = latlon_to_vec(54.30, 13.60)
click(dest)
pend = ([tr.current_order] if tr.current_order else []) \
    + list(tr.order_queue)
check(any(o.get('kind') == 'unload' for o in pend),
      "the landing is set on the carrier")

# CLICK 3 -- further ground: queues on the PASSENGERS for the shore
inland = latlon_to_vec(54.10, 13.90)
click(inland)
check(all(any(o.get('kind') == 'move' for o in u.order_queue)
          for u in inf),
      "the march inland queues on the shore party")

# and it all comes true
ok = until(g, lambda: all(u.carried_by is None and u.alive
                          for u in inf), 900, "ashore")
check(ok, "the carrier sails and puts the party ashore")
if ok:
    la, lo = vec_to_latlon(inf[0].pos)
    check(lo > 12.0, "ashore on the FAR coast (lon %.1f)" % lo)
    ok2 = until(g, lambda: all(
        angle_between(u.pos, inland) * GLOBE_RADIUS < 0.8
        or (u.current_order or {}).get('kind') == 'move'
        for u in inf), 400, "marching")
    check(ok2, "the party takes up its queued march ashore")

finish()
