"""The field batch after 1.3.2's ways: war tears up the papers,
USE OF THE WIRELESS NET is bought at the table, the capture order
flies as a banner over the town, the bunker wall matches the drawn
works and flings nobody, works can be decommissioned, and the unit
marks on sheets ride an A/B switch."""
from harness import boot, step, check, finish
from utils import latlon_to_vec, angle_between
from config import GLOBE_RADIUS
from panda3d.core import Vec3

g = boot('germany')

# ---------- WAR TEARS UP THE PAPERS -- however the war arrived
g.rights.append({'with': 'romania', 'kind': 'passage',
                 'dir': 'theirs'})
g.trade_deals.append({'with': 'romania', 'res': 'oil',
                      'amount': 40, 'price': 0, 'dir': 'in',
                      'gift': True})
g.declare_war('germany', 'romania')
check(not any(r['with'] == 'romania' for r in g.rights),
      "a declaration voids the rights")
check(not any(t.get('with') == 'romania' for t in g.trade_deals),
      "and the standing arrangements")
g.wars.discard(frozenset(('germany', 'romania')))
g._rebuild_war_sets()

# dragged IN through an ally's war: the papers still burn
g.rights.append({'with': 'soviet', 'kind': 'passage',
                 'dir': 'theirs'})
g.make_alliance('germany', 'italy')
g.declare_war('soviet', 'italy')
check(g.at_war('germany', 'soviet'),
      "the bloc drags Germany into the war")
check(not any(r['with'] == 'soviet' for r in g.rights),
      "and the Soviet papers burn with it")
g.wars.discard(frozenset(('germany', 'soviet')))
g.wars.discard(frozenset(('italy', 'soviet')))
g.alliances['germany'].discard('italy')
g.alliances['italy'].discard('germany')
g._rebuild_war_sets()

# ---------- USE OF THE WIRELESS NET: a right at the table
import deals as _d
check('comms' in _d.BASE and 'comms' in _d.KIND_LABEL,
      "the wireless net is priced at the table ($%d)"
      % _d.BASE.get('comms', 0))
check(g.deal_gates('romania').get('comms') is True,
      "and may be asked of a power at peace")
inf = g.spawn_unit('infantry', 'germany', 44.43, 26.10, seed=10)
g._tick_vision_comm()
check(not inf.in_contact,
      "a section at Bucharest stands outside every German net")
g.rights.append({'with': 'romania', 'kind': 'comms',
                 'dir': 'theirs'})
g._tick_vision_comm()
check(inf.in_contact,
      "USE OF THE WIRELESS NET puts it back in contact")
g.rights.pop()
g._tick_vision_comm()

# ---------- THE CAPTURE BANNER flies over a town ready to fall
g.wars.add(frozenset(('germany', 'poland')))
g._rebuild_war_sets()
warsaw = next(c for c in g.cities if c.name == 'Warsaw')
for u in g.units:      # clear the standing garrison: no contest
    if (u.alive and u.country == 'poland'
            and angle_between(u.pos, warsaw.pos) * GLOBE_RADIUS
            < 1.5):
        u.alive = False
need = warsaw.required_infantry()
troops = []
for i in range(need):
    u = g.spawn_unit('infantry', 'germany', warsaw.lat, warsaw.lon,
                     seed=30 + i)
    u.pos = Vec3(warsaw.pos)
    troops.append(u)
g._tick_capture_banners()
check(warsaw.cap_np is not None and not warsaw.cap_np.isHidden(),
      "the town flies its >CAPTURE< banner")
check(warsaw._cap_txt == ">CAPTURE< (-%d)" % need,
      "and the banner names the garrison bill (%s)" % warsaw._cap_txt)
foe = g.spawn_unit('infantry', 'poland', warsaw.lat, warsaw.lon,
                   seed=60)
foe.pos = Vec3(warsaw.pos)
g._tick_capture_banners()
check(warsaw.cap_np.isHidden(),
      "a contesting enemy hauls the banner down")
foe.alive = False
g.wars.discard(frozenset(('germany', 'poland')))
g._rebuild_war_sets()
g._tick_capture_banners()

# ---------- THE BUNKER WALL matches the drawn works, and slings
# nobody across the map
from structures import BUNKER_RADIUS, Bunker, Depot, Airfield
check(BUNKER_RADIUS <= 0.06,
      "the wall stands at the works' own footprint (%.2fwu)"
      % BUNKER_RADIUS)
b = Bunker(g, 50.0, 20.0, 'germany', "TEST BUNKER")
g.bunkers.append(b)
tank = g.spawn_unit('tank', 'germany', 50.0, 20.0, seed=70)
tank.supply = tank.stats['supply_cap']
tank.pos = Vec3(b.pos)          # dead centre of the works
tank.path = [(latlon_to_vec(50.0, 20.6), 1.0)]
worst = 0.0
prev = Vec3(tank.pos)
for _ in range(40):
    tank.update(0.05)
    worst = max(worst, angle_between(prev, tank.pos) * GLOBE_RADIUS)
    prev = Vec3(tank.pos)
check(worst < 0.05,
      "no frame flings the tank (worst hop %.4fwu)" % worst)

# ---------- DECOMMISSION: the party strikes its own works
dep = Depot(g, 50.5, 20.5, 'germany', "TEST CACHE")
g.depots.append(dep)
g._decommission(dep)
check(dep not in g.depots, "a depot is struck off")
bk = Bunker(g, 50.6, 20.6, 'germany', "TEST WORKS")
g.bunkers.append(bk)
g._decommission(bk)
check(bk not in g.bunkers, "a bunker is struck off")
af = Airfield(g, 50.7, 20.7, 'germany', "TEST FIELD")
g.airfields.append(af)
wing = g.spawn_unit('fighter', 'germany', 50.7, 20.7, seed=80)
wing.based_at = af
g._decommission(af)
check(af in g.airfields,
      "a field with wings on it REFUSES the charge")
wing.based_at = None
wing.alive = False
g._decommission(af)
check(af not in g.airfields, "an empty field is struck off")

# ---------- THE A/B TRIAL: unit marks on sheets and keys
from icons import unit_ui_icon
g.unit_sprites_ui = False
a_path = unit_ui_icon('tank')
g.unit_sprites_ui = True
b_path = unit_ui_icon('tank')
g.unit_sprites_ui = False
check(a_path != b_path,
      "the switch changes the mark (%s -> %s)"
      % (a_path.split('/')[-2], b_path.split('/')[-2]))
check('units' in b_path.replace('\\', '/').split('/'),
      "arm B wears the top-down field sprite")

# ---------- THE FURNITURE: hamburger key, centred rank, scramble
check(getattr(g.top_bar, 'menu_btn', None) is not None,
      "the three-bar key stands on the top bar")
kz = [g.top_bar.factory_btn.getZ(), g.top_bar.resource_btn.getZ(),
      g.top_bar.tech_btn.getZ(), g.top_bar.diplo_btn.getZ()]
check(all(abs(z + 0.0775) < 1e-4 for z in kz),
      "the report keys sit centred on the strip (%s)" % kz)
gap = (g.top_bar.factory_btn.getX() - 0.048) \
    - (g.top_bar.budget_btn.getX() + 0.155)
check(gap > 0.04,
      "clear margin between budget and the report keys (%.3f)" % gap)
from ui import FaxPanel
left = min(-1.35, 1.35 + FaxPanel.MACH_X1 + FaxPanel.BORDER
           - 2.0 * g.getAspectRatio())
check(abs(g.bottom_bar.scramble_btn.getX() - (left + 1.35) / 2.0)
      < 1e-4,
      "SCRAMBLE is centred over the visible bar, not the screen")

# ---------- the ledger prints with MANY wars raging (the board
# scrolls instead of truncating), and carries the comms row
for a, b2 in (('usa', 'japan'), ('britain', 'italy'),
              ('france', 'hungary'), ('spain', 'turkey'),
              ('sweden', 'norway'), ('brazil', 'argentina'),
              ('china', 'japan'), ('greece', 'bulgaria'),
              ('iran', 'iraq')):
    if a in g.alliances and b2 in g.alliances:
        g.wars.add(frozenset((a, b2)))
g._rebuild_war_sets()
g.open_diplomacy()
check(g.diplo_fax is not None, "the ledger prints under a long war "
      "list -- the board scrolls")
g._close_diplomacy()

finish()
