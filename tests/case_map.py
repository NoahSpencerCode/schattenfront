"""The map reads at every altitude: bases are one of each type per
power, they never shrink to specks on the strategic view, and every
one of them is wired to its town by road."""
from harness import boot, step, check, finish
from utils import angle_between
from config import GLOBE_RADIUS, PLAYABLE

g = boot('germany')

# --- one base of each type, every power, human and AI alike
for nat in PLAYABLE:
    army = [p for p in g.armyposts if p.country == nat]
    air = [a for a in g.airfields
           if a.country == nat and a.is_base]
    navy = [h for h in g.harbors if h.country == nat and h.is_base]
    check(len(army) == 1 and len(air) == 1 and len(navy) == 1,
          "%s opens with one of each base (%d/%d/%d)"
          % (nat, len(army), len(air), len(navy)))

# --- nothing else stands: ports and airfields are the engineers'
check(not [h for h in g.harbors if not h.is_base],
      "no PORT stands at the bell")
check(not [a for a in g.airfields if not a.is_base],
      "no AIRFIELD stands at the bell")

# --- every base is ON the road network (a quay ends at the shore)
roads = [sec for sec in g.road_sections if sec.kind == 'road']


def nearest_road(pos):
    best = 9e9
    for sec in roads:
        for p in sec.pts:
            d = angle_between(pos, p) * GLOBE_RADIUS
            if d < best:
                best = d
    return best


for b in g.armyposts + [a for a in g.airfields if a.is_base]:
    d = nearest_road(b.pos)
    check(d < 0.05, "%s stands on the road (%.3fwu)" % (b.name, d))
for h in [x for x in g.harbors if x.is_base]:
    d = nearest_road(h.pos)
    check(d < 0.35, "%s reached by road to the quay (%.3fwu)"
          % (h.name, d))

# --- the strategic view: marks GROW with altitude, never vanish
g.cam_dist = GLOBE_RADIUS + 25.0        # the opening altitude
g._apply_marker_scale()
step(g, 2)
far = g.struct_factor
check(far > 3.0, "marks grow on the strategic map (x%.1f)" % far)
check(getattr(g, "_structs_shown", True),
      "structures still drawn at the opening view")
sample = g.armyposts[0]
check(sample.holder.getScale()[0] > 0.15,
      "a base reads at %0.2f world units when zoomed out"
      % sample.holder.getScale()[0])

g.cam_dist = GLOBE_RADIUS + 1.0         # close in
g._apply_marker_scale()
check(abs(g.struct_factor - 1.0) < 0.001,
      "close in, marks hold their drawn size")
check(abs(sample.holder.getScale()[0] - sample.FIXED_SCALE) < 1e-6,
      "...exactly the fixed size")

finish()
