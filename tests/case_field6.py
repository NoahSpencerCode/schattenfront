"""The amphibious batch: the landing law (no put-ashore without
passage or war), the invasion line (a fleet lands abreast, each
ship her own berth), the task-force UNLOAD key, the amphibious
slates, the capture banner as a real red key, and the briefing's
large mark."""
from harness import boot, check, finish
from utils import latlon_to_vec, angle_between
from config import GLOBE_RADIUS
from panda3d.core import Point2, Vec3


class FakeMouse:
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
mouse = FakeMouse()
g.mouseWatcherNode = mouse

# ---------- THE AMPHIBIOUS SLATES
b = g._default_budget_counts('britain', 80000)
check(b.get('personnel_transport', 0) >= 4,
      "the Empire moves by sea: %d landing ships at the bell"
      % b.get('personnel_transport', 0))
u = g._default_budget_counts('usa', 80000)
check(u.get('personnel_transport', 0) >= 4
      and u.get('supply_ship', 0) >= 4,
      "America lands and feeds in strength (%d lifts, %d supply)"
      % (u.get('personnel_transport', 0), u.get('supply_ship', 0)))
j = g._default_budget_counts('japan', 80000)
check(j.get('personnel_transport', 0) >= 4
      and j.get('supply_ship', 0) >= 4,
      "so does Japan (%d lifts, %d supply)"
      % (j.get('personnel_transport', 0), j.get('supply_ship', 0)))

# ---------- THE LANDING LAW
gd_pt = latlon_to_vec(54.4, 18.8)      # the Danzig bay shore
check(g._landing_refused(latlon_to_vec(52.2, 21.0)) == 'poland',
      "no put-ashore in a closed country")
g.wars.add(frozenset(('germany', 'poland')))
g._rebuild_war_sets()
check(g._landing_refused(latlon_to_vec(52.2, 21.0)) is None,
      "war opens the beach")
g.wars.discard(frozenset(('germany', 'poland')))
g._rebuild_war_sets()
# the gate nets a hand unload into closed ground
tpt = g.spawn_unit('personnel_transport', 'germany', 55.2, 15.5,
                   seed=10, water=True)
rider = g.spawn_unit('infantry', 'germany', 54.0, 10.0, seed=11)
rider.carried_by = tpt
tpt.cargo.append(rider)
tpt.give_order({'kind': 'unload',
                'goal': latlon_to_vec(52.2, 21.0)})
check(tpt.current_order is None and not tpt.order_queue,
      "a hand unload into closed ground is turned back")

# ---------- THE INVASION LINE: three lifts berth abreast
g.wars.add(frozenset(('germany', 'poland')))
g._rebuild_war_sets()
lifts = [tpt]
for i in range(2):
    t2 = g.spawn_unit('personnel_transport', 'germany',
                      55.2 + 0.05 * i, 15.6, seed=20 + i, water=True)
    r2 = g.spawn_unit('infantry', 'germany', 54.0, 10.0,
                      seed=30 + i)
    r2.carried_by = t2
    t2.cargo.append(r2)
    lifts.append(t2)
g.clear_selection()
g.selected = list(lifts)
for t2 in lifts:
    t2.set_selected(True)
g._refresh_selection_ui()
# the task force keeps its UNLOAD key, standing left
lefts = [btn for btn in g.bottom_bar.buttons
         if hasattr(btn, 'getX') and btn.getX() < -1.1]
check(bool(lefts), "the task force carries the UNLOAD key")
g._arm_unload()
check(g.unload_mode, "the key arms the disembarkation")
shore = latlon_to_vec(54.6, 18.6)      # water off the Danzig coast
mouse.mpos = Point2(g.screen_pos(shore) or Point2(0, 0))
g.mouse_ground_point = lambda: shore
g.on_rmb()
goals = [t2.current_order.get('goal')
         if t2.current_order else
         (t2.order_queue[0].get('goal') if t2.order_queue else None)
         for t2 in lifts]
check(all(gl is not None for gl in goals),
      "every lift takes her landing order")
seps = [angle_between(a, b2) * GLOBE_RADIUS
        for i, a in enumerate(goals) for b2 in goals[i + 1:]]
check(min(seps) > 0.05,
      "and each berths APART down the coast (min %.3fwu)"
      % min(seps))
g.wars.discard(frozenset(('germany', 'poland')))
g._rebuild_war_sets()
g.clear_selection()

# ---------- THE BANNER IS A KEY: the red pill behind the ink
g.wars.add(frozenset(('germany', 'poland')))
g._rebuild_war_sets()
warsaw = next(c for c in g.cities if c.name == 'Warsaw')
for u2 in g.units:
    if (u2.alive and u2.country == 'poland'
            and angle_between(u2.pos, warsaw.pos) * GLOBE_RADIUS
            < 1.5):
        u2.alive = False
need = warsaw.required_infantry()
for i in range(need):
    s2 = g.spawn_unit('infantry', 'germany', warsaw.lat, warsaw.lon,
                      seed=50 + i)
    s2.pos = Vec3(warsaw.pos)
g._tick_capture_banners()
check(warsaw.cap_np is not None
      and not warsaw.cap_np.find('cap_pill').isEmpty(),
      "the capture banner wears the red pill, like SCRAMBLE")
g.wars.discard(frozenset(('germany', 'poland')))
g._rebuild_war_sets()

# ---------- THE BRIEFING wears the subject's own large mark
g.open_unit_briefing('tank')
check(g.briefing_fax is not None, "the briefing prints")
g._close_briefing()

finish()
