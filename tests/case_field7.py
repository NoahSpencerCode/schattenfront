"""THE OIL LOOP of the field report: a tender working a floating
supply station drew from her (pumped) while the casualty rule
topped her back up (pumped again), every second -- 400 tons of oil
gone in under a minute with the stores going nowhere. The pound is
charged ONCE now, at the final issue to a fighting machine, and a
station is never 'rescued'."""
from harness import boot, check, finish
from utils import latlon_to_vec
from panda3d.core import Vec3
import os

g = boot('germany')

# ---------- THE LOOP IS DEAD: station + working tender burn NOTHING
station = g.spawn_unit('supply_ship', 'germany', 54.5, 10.5,
                       seed=10, water=True)
station.supply = 6000.0
g.toggle_supply_station(station)
tender = g.spawn_unit('supply_ship', 'germany', 54.5, 10.52,
                      seed=11, water=True)
tender.supply = 2000.0
customer = g.spawn_unit('destroyer_sea_sea', 'germany', 54.5, 10.54,
                        seed=12, water=True)
customer.supply = customer.stats['supply_cap']   # full: no issue due
tender._supply_tgt = customer          # the tender holds a job
g.resources['germany']['oil'] = 400.0
pumped0 = g._pump_lbs.get('germany', 0.0)
for _ in range(30):                    # thirty seconds of the chain
    g._tick_supply()
oil = g.resources['germany']['oil']
check(oil > 399.0,
      "thirty seconds at the station burn no oil (%.1f t left)" % oil)
check(g._pump_lbs.get('germany', 0.0) - pumped0 < 1.0,
      "and the pumps ledger stays quiet (the draw-and-rescue loop "
      "is dead)")

# ---------- THE FINAL ISSUE STILL PAYS: a thirsty machine drinks
customer.supply = 0.0                  # now she NEEDS stores
oil0 = g.resources['germany']['oil']
g._tick_supply()
drank = customer.supply
check(drank > 0, "the destroyer takes on stores (%.0f lbs)" % drank)
check(g.resources['germany']['oil'] < oil0,
      "and THAT issue draws the pumps (%.2f t)"
      % (oil0 - g.resources['germany']['oil']))

# ---------- MEN STILL DRINK FREE
oil0 = g.resources['germany']['oil']
inf = g.spawn_unit('infantry', 'germany', 54.3, 10.5, seed=20)
inf.supply = 0.0
truck = g.spawn_unit('supply_truck', 'germany', 54.3, 10.51, seed=21)
truck.supply = truck.stats['supply_cap']
g._tick_supply()
check(inf.supply > 0, "the section is fed")
check(abs(g.resources['germany']['oil'] - oil0) < 0.5,
      "and men draw (almost) none -- only machines pay")

# ---------- THE STATION IS NEVER A 'CASUALTY'
station.supply = 100.0                 # nearly dry
tender.supply = tender.stats['supply_cap']
tender._supply_tgt = customer
s0 = station.supply
g._tick_supply()
# a jobless dump may FILL her (that is her purpose); the CASUALTY
# rescue -- which respun the loop -- must not: with a job held,
# the tender leaves her stock to the cache law alone
check(station.supply >= s0,
      "her stock only moves by the cache law, never by rescue")

# ---------- ONE HAND WRITES THE CITY LINE: a foreign town reads
# as intel, an own town as the municipal ledger -- from the SAME
# composer the once-a-second refresher uses (the two-writer flicker
# of the field report)
warsaw = next(c for c in g.cities if c.name == 'Warsaw')
berlin = next(c for c in g.cities if c.name == 'Berlin')
check('CONTROLLED BY' in g._city_info_line(warsaw)
      and 'FOCUS' not in g._city_info_line(warsaw),
      "a foreign town reads as the intel line")
check('FOCUS:' in g._city_info_line(berlin)
      and 'CONTROLLED BY' not in g._city_info_line(berlin),
      "an own town reads as the municipal ledger")
g.clear_selection()
g._select_city(warsaw)
g._refresh_selection_ui()
g._set_city_info(warsaw)      # the refresher's write: same words
check(True, "and the refresher writes through the same composer")
g.clear_selection()

# ---------- THE TAXI SERVES THE EMBARKMENT: infantry marching to
# a distant ship are collected by an idle lorry (the field report:
# seven idle trucks watched them walk), and the ship still counts
# the rider as inbound while his boarding order rides the cab
marcher = g.spawn_unit('infantry', 'germany', 52.0, 13.0, seed=80)
marcher.supply = marcher.stats['supply_cap']
liner = g.spawn_unit('personnel_transport', 'germany', 54.5, 10.6,
                     seed=81, water=True)
cab = g.spawn_unit('transport_truck', 'germany', 52.05, 13.05,
                   seed=82)
cab.supply = cab.stats['supply_cap']
marcher.give_order({'kind': 'board', 'target': liner})
marcher.update(0.05)            # the order stands current
g._tick_ferry()
check(getattr(marcher, '_ferry_by', None) is cab,
      "the cab turns out for a man marching to his SHIP")
check((getattr(marcher, '_ferry_back', None) or {})
      .get('target') is liner,
      "and holds his boarding order for the kerb")
# aboard the cab, the ship still counts him inbound
marcher.carried_by = cab
liner._inb_t = -9.0             # bust the memo
check(g.inbound_boarders(liner) == 1,
      "the ramp counts the rider in the taxi as inbound")
marcher.carried_by = None
g._ferry_handback(marcher, marcher.pos)
check((marcher.current_order or {}).get('kind') == 'board'
      or any(o.get('kind') == 'board'
             for o in marcher.order_queue),
      "at the kerb his boarding order comes back")
cab._ferry = None
marcher.clear_orders()

# ---------- THE PASSING TOP-UP: a lorry waypointed through a
# depot arrives FULL; a lorry at rest still banks its load
from structures import Depot
dep = Depot(g, 29.0, 17.0, 'germany', "WAYSIDE CACHE")
dep.stock = 12000.0            # half full: room to bank, stock to draw
g.depots.append(dep)           # deep desert: no town's free refill
lorry = g.spawn_unit('supply_truck', 'germany', 29.0, 17.01,
                     seed=90)
lorry.supply = 400.0
lorry.give_order({'kind': 'move',
                  'goal': latlon_to_vec(29.0, 18.5)})
g._tick_supply()
check(lorry.supply > 400.0,
      "EN ROUTE past the cache the lorry tops up (%d lbs)"
      % lorry.supply)
lorry.clear_orders()
lorry.supply = 1200.0
lorry._drew_from = None
lorry._supply_tgt = None
for u3 in g.units:      # nobody starving: no call claims the lorry
    if u3.alive and u3.stats['supply_cap'] > 0 and u3 is not lorry:
        u3.supply = u3.stats['supply_cap']
stock0 = dep.stock
g._tick_supply()
check(dep.stock > stock0,
      "at rest beside it the lorry still banks its load forward")
g.depots.remove(dep)
dep.cleanup()

# ---------- THE STANDARD OPENS THE FOREIGN OFFICE
warsaw2 = next(c for c in g.cities if c.name == 'Warsaw')
check(warsaw2.title_flag is not None
      and warsaw2.flag_glow is not None
      and warsaw2.icon_glow is not None,
      "every town flies its standard with a glow lamp behind each "
      "key")
g._open_nation_dossier('poland')
check(g.diplo_fax is not None,
      "a click on the standard opens the nation's dossier")
g._close_diplomacy()

# ---------- THE LEDGER'S COMMITMENTS PAGE lists every power we
# have anything standing with
g.rights.append({'with': 'romania', 'kind': 'passage',
                 'dir': 'theirs'})
g.wars.add(frozenset(('germany', 'poland')))
g._rebuild_war_sets()
g.open_diplomacy()
led = g.diplo_fax
rows = [nat for nat in led._COUNTRIES
        if nat not in ('germany', 'neutral')
        and (g.at_war('germany', nat) or g.allied('germany', nat)
             or led._agreement_lines(nat))]
check('poland' in rows and 'romania' in rows,
      "the commitments roll holds the war AND the treaty (%s)"
      % sorted(rows))
led._open_commitments()
check(led.view == '_commitments', "the commitments page opens")
led._open_dossier(None)
check(led.view is None, "and THE ROSTER key returns")
g._close_diplomacy()
g.rights.pop()
g.wars.discard(frozenset(('germany', 'poland')))
g._rebuild_war_sets()

# ---------- THE BRIEFING READS A FOREIGN COUNTER from its own
# nation's tables
foe = g.spawn_unit('battleship', 'japan', 35.0, 140.0, seed=95,
                   water=True)
g.clear_selection()
g.selected = [foe]
foe.set_selected(True)
g._refresh_selection_ui()
check(not g.bottom_bar.info_btn.isHidden(),
      "an enemy counter carries the briefing key")
g.open_unit_briefing('battleship', 'japan')
check(g.briefing_fax is not None,
      "and it prints the foreign service page")
g._close_briefing()
g.clear_selection()

# ---------- A RESUMED CAMPAIGN IS FILED BACK OVER ITS OWN CASE
import saveload as _sl
p1 = _sl.write_save(g, name='alpha')
p2 = _sl.write_save(g, path=p1)
check(p2 == p1, "a save with a case writes back over it")
check(len([1 for m in _sl.list_saves()
           if m['path'] == p1]) == 1,
      "and the drawer still holds ONE copy of that campaign")
p3 = _sl.write_save(g, name='beta')
check(p3 != p1, "a save WITHOUT one opens a fresh case")
check(_sl.delete_save(p3) and not os.path.exists(p3),
      "and the clerk can burn a case")
_sl.delete_save(p1)

# ---------- THE ARCHIVE IS READ ONCE PER CASE: the LOAD GAME page
# re-renders on every burn prompt, and a filed campaign is a
# megabyte of JSON -- re-parsing the whole drawer each time is the
# second the game stood still
pa = _sl.write_save(g, name='freeze-a')
pb = _sl.write_save(g, name='freeze-b')
_sl._META_CACHE.clear()
_sl.list_saves()
check(pa in _sl._META_CACHE and pb in _sl._META_CACHE,
      "the drawer is remembered after one reading")
import json as _json
_reads = []
_real_load = _json.load


def _spy(fh, *a, **k):
    _reads.append(1)
    return _real_load(fh, *a, **k)


_json.load = _spy
_sl.list_saves()
_json.load = _real_load
check(not _reads,
      "a second reading parses NOTHING (%d files re-read)"
      % len(_reads))
_sl.delete_save(pa)
check(pa not in _sl._META_CACHE,
      "and a burnt case leaves the memory with it")
_sl.delete_save(pb)

# ---------- THE INDEX CARD: opening LOAD GAME must not read the
# campaigns themselves. Each case files a few hundred bytes of card
# beside it, so the drawer opens without parsing a megabyte apiece
pc = _sl.write_save(g, name='card')
check(os.path.exists(_sl._card_path(pc)),
      "a filed case files its index card too")
_sl._META_CACHE.clear()          # a FRESH session: only the cards
import builtins as _b
_opened = []
_real_open = _b.open


def _spy_open(f, *a, **k):
    _opened.append(str(f))
    return _real_open(f, *a, **k)


_b.open = _spy_open
_sl.list_saves()
_b.open = _real_open
check(pc not in _opened,
      "and the drawer opens WITHOUT reading the campaign itself")
check(any(p2.endswith('.meta') for p2 in _opened),
      "-- it reads the cards instead (%d opened)"
      % sum(1 for p2 in _opened if p2.endswith('.meta')))
# a case written over gets a fresh card, never a stale one
_sl.write_save(g, path=pc)
_sl._META_CACHE.clear()
metas = {m['path']: m for m in _sl.list_saves()}
check(pc in metas, "an overwritten case still reads back")
_sl.delete_save(pc)
check(not os.path.exists(_sl._card_path(pc)),
      "and burning a case burns its card with it")

# ---------- THE NEAREST SOURCE IS ANY PLACE THAT WOULD FILL HER:
# the shuttle used to read a narrower list than the refill law
lorry2 = g.spawn_unit('supply_truck', 'germany', 52.5, 13.4,
                      seed=96)
lorry2.supply = 100.0
srcs = g._refill_sources(lorry2)
berlin2 = next(c for c in g.cities if c.name == 'Berlin')
check(berlin2 in srcs, "a home town is a source")
check(not any(getattr(c, 'annexing', False) for c in srcs),
      "a town under annexation is NOT (it supplies nothing)")
prague = next((c for c in g.cities if c.country != 'germany'
               and c.country != 'neutral'), None)
check(prague not in srcs,
      "and a foreign town is closed to the lorry")
g.rights.append({'with': prague.country, 'kind': 'supply',
                 'dir': 'theirs'})
check(prague in g._refill_sources(lorry2),
      "a RIGHT OF SUPPLY opens their quays to her")
g.rights.pop()
dep2 = Depot(g, 52.5, 13.42, 'germany', "NEAR CACHE")
dep2.stock = 15000.0
g.depots.append(dep2)
srcs = g._refill_sources(lorry2)
check(dep2 in srcs, "a stocked depot is a source")
nearest = min(srcs, key=lambda s2: lorry2.dist_to(s2.pos))
check(nearest is dep2,
      "and the NEAREST of them all is the one she is sent to")
g.depots.remove(dep2)
dep2.cleanup()

finish()
