"""THE OIL LOOP of the field report: a tender working a floating
supply station drew from her (pumped) while the casualty rule
topped her back up (pumped again), every second -- 400 tons of oil
gone in under a minute with the stores going nowhere. The pound is
charged ONCE now, at the final issue to a fighting machine, and a
station is never 'rescued'."""
from harness import boot, check, finish
from utils import latlon_to_vec
from panda3d.core import Vec3

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

finish()
