"""The map: one base of each type per power (the USA, a two-ocean
nation, opens with TWO -- the second full set at Los Angeles), each
standing on the map's own station site so the spur road already
drawn there serves it -- and NO spur drawn to a site nobody built
on."""
from harness import boot, check, finish
from utils import angle_between, latlon_to_vec
from config import GLOBE_RADIUS, PLAYABLE

g = boot('germany')

# --- one base of each type, every power, human and AI alike
for nat in PLAYABLE:
    army = [p for p in g.armyposts if p.country == nat]
    air = [a for a in g.airfields if a.country == nat and a.is_base]
    navy = [h for h in g.harbors if h.country == nat and h.is_base]
    want = 2 if nat == 'usa' else 1
    check(len(army) == want and len(air) == want
          and len(navy) == want,
          "%s opens with %d of each base (%d/%d/%d)"
          % (nat, want, len(army), len(air), len(navy)))
    if nat == 'usa':
        la = [b for b in army + air + navy
              if b.city and b.city.name == 'Los Angeles']
        check(len(la) == 3,
              "the second American set stands at Los Angeles (%d)"
              % len(la))

# --- nothing else stands: PORTS and AIRFIELDS are the engineers'
check(not [h for h in g.harbors if not h.is_base],
      "no PORT stands at the bell")
check(not [a for a in g.airfields if not a.is_base],
      "no AIRFIELD stands at the bell")

# --- every base stands on the map's OWN site (which has a spur);
# a town the map drew no site for (Los Angeles' second set) lays
# its spur by the map's own rule instead, checked by the road test
for b in g.armyposts + g.airfields + g.harbors:
    kind = ('army' if b in g.armyposts else
            'air' if b in g.airfields else 'naval')
    if b.city and b.city.name == 'Los Angeles':
        continue
    check(g.base_site(b.city, kind)[2],
          "%s stands on the map's station site" % b.name)

# --- and the roads reach them
roads = [sec for sec in g.road_sections if sec.kind == 'road']


def nearest_road(pos):
    return min(angle_between(pos, p) * GLOBE_RADIUS
               for sec in roads for p in sec.pts)


for b in g.armyposts + g.airfields + g.harbors:
    d = nearest_road(b.pos)
    check(d < 0.02, "%s sits on its road (%.3fwu)" % (b.name, d))

# --- NO SPUR LEADS NOWHERE: every drawn spur ends at a station
stations = [b for b in g.armyposts + g.airfields + g.harbors]
drawn = g._live_spurs()
check(len(drawn) == len(stations),
      "one spur drawn per station (%d spurs, %d stations)"
      % (len(drawn), len(stations)))
check(len(drawn) < len(getattr(g.world, 'spur_paths', [])),
      "the map's unused spurs (%d) are NOT drawn"
      % (len(getattr(g.world, 'spur_paths', [])) - len(drawn)))
orphans = 0
for spur in drawn:
    end = latlon_to_vec(spur[-1][0], spur[-1][1])
    if min(angle_between(end, b.pos) * GLOBE_RADIUS
           for b in stations) > 0.05:
        orphans += 1
check(orphans == 0, "no drawn spur ends at empty ground")

# --- structures keep their FIXED map size, like every other building
sample = g.armyposts[0]
before = sample.holder.getScale()[0]
g.cam_dist = GLOBE_RADIUS + 25.0
g._apply_marker_scale()
check(abs(sample.holder.getScale()[0] - before) < 1e-6,
      "a base holds its fixed size when the camera pulls out")
check(abs(before - sample.FIXED_SCALE) < 1e-6,
      "...exactly the structure's fixed scale")

finish()
