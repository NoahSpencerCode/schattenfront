"""The fortnight focus and the base economy: bases produce, focus
directives pay their distinct coins, refunds when no base stands."""
from harness import boot, step, until, check, finish

g = boot('germany')

berlin = next(c for c in g.cities if c.name == 'Berlin')
essen = next(c for c in g.cities if c.name == 'Essen')

# --- the opening: ONE base of each type
mine_posts = [p for p in g.armyposts if p.country == 'germany']
mine_air = [a for a in g.airfields
            if a.country == 'germany' and a.is_base]
mine_yards = [h for h in g.harbors
              if h.country == 'germany' and h.is_base]
check(len(mine_posts) == 1 and len(mine_air) == 1
      and len(mine_yards) == 1,
      "Germany opens with one base of EACH type")
check(not any(not getattr(h, 'is_base', False)
              for h in g.harbors)
      and not any(not getattr(a, 'is_base', False)
                  for a in g.airfields),
      "NO ports and NO airfields at the bell -- engineers' trade")

# --- production: every arm builds at its own base
g.funds['germany'] = 10000
g.resources['germany']['steel'] = 200
q0 = len(mine_posts[0].production)
qa0 = len(mine_air[0].production)
g._distribute_production('germany', {'tank': 1, 'fighter': 1})
check(len(mine_posts[0].production) == q0 + 1,
      "tank on the army base line")
check(len(mine_air[0].production) == qa0 + 1,
      "fighter on the airforce base line")

# bring the TANK to the head of the line and to the moment of
# delivery -- the works tick only ever advances its FIRST item, and
# the opening slate may hold other work ahead of it
line = mine_posts[0].production
mine_posts[0].production = ([it for it in line if it[0] == 'tank']
                            + [it for it in line if it[0] != 'tank'])
mine_posts[0].production[0][1] = 0.1
n0 = sum(1 for u in g.units if u.alive and u.country == 'germany'
         and u.unit_type == 'tank')
step(g, 40)
n1 = sum(1 for u in g.units if u.alive and u.country == 'germany'
         and u.unit_type == 'tank')
check(n1 == n0 + 1, "tank rolls out onto the map from the base")

# --- focus: finance heals industry
berlin.industry = 80.0
berlin.focus = 'finance'
g._apply_city_focus(berlin)
check(abs(berlin.industry - 85.0) < 0.01, "finance heals +5 industry")

# --- THE LEDGER: a level costs money alone, and pays exponentially
from config import (TRACK_COSTS, AGRI_FOOD_CUM, CITY_FOOD_BASE,
                    WORKS_SPEED_MULT, LAB_YIELD_MULT,
                    BUDGET_PERIOD_DAYS)
g.funds['germany'] = 10000
food0 = g._daily_income('germany')['food']
funds0 = g.funds['germany']
berlin.focus = 'agriculture'
g._apply_city_focus(berlin)
food1 = g._daily_income('germany')['food']
check(berlin.agri_level == 1 and food1 > food0,
      "a farmed level feeds the take (+%.2f/day)" % (food1 - food0))
check(g.funds['germany'] == funds0 - TRACK_COSTS[0],
      "and costs MONEY ALONE ($%d)" % TRACK_COSTS[0])
gain1 = (AGRI_FOOD_CUM[2] - AGRI_FOOD_CUM[1])
gain0 = (AGRI_FOOD_CUM[1] - AGRI_FOOD_CUM[0])
check(gain1 > gain0,
      "the SECOND level pays more than the first (%d > %d)"
      % (gain1, gain0))
check(g.city_food_output(berlin)
      == CITY_FOOD_BASE + AGRI_FOOD_CUM[1],
      "the town's ledger reads base + the table")

# --- the works: ANY town may expand them now, no deposit wanted
berlin.focus = 'works'
g._apply_city_focus(berlin)
check(berlin.works_level == 1,
      "Berlin (no deposit) expands the works -- tracks are free of "
      "deposits")
# and the level speeds the town's own bases
post = mine_posts[0]
check(abs(g._works_rate(post)
          - WORKS_SPEED_MULT[post.city.works_level]) < 1e-9,
      "the base builds at its town's works rate (x%.2f)"
      % g._works_rate(post))

# --- a track level the treasury cannot cover WAITS
poor = next(c for c in g.cities
            if c.country == 'germany' and c is not berlin
            and c is not essen)
g.funds['germany'] = 10
poor.focus = 'agriculture'
lvl0 = poor.agri_level
g._apply_city_focus(poor)
check(poor.agri_level == lvl0 and poor.focus == 'agriculture',
      "an unaffordable level WAITS instead of lapsing")
g.funds['germany'] = 10000

# --- the laboratories multiply the research focus
rp0 = g.research_points['germany']
berlin.focus = 'research'
g._apply_city_focus(berlin)
base_rp = g.research_points['germany'] - rp0
check(base_rp > 0, "the labs pay %.1f RP unlevelled" % base_rp)
berlin.labs_level = 3
rp1 = g.research_points['germany']
g._apply_city_focus(berlin)
lab_rp = g.research_points['germany'] - rp1
check(abs(lab_rp - base_rp * LAB_YIELD_MULT[3]) < 1e-6,
      "at labs L3 the same focus pays x%.1f (%.1f RP)"
      % (LAB_YIELD_MULT[3], lab_rp))
berlin.labs_level = 0

# --- the breadbaskets open pre-levelled; imports are NO MORE
kiev = next(c for c in g.cities if c.name == 'Kiev')
check(kiev.agri_level == 3, "Kiev opens at agriculture L3")
check(g._daily_income('germany')['oil'] == 0.0,
      "no free oil imports: Germany's oil is ZERO without a "
      "deposit or the market")

# --- focus: raise a SECOND airforce base at another town
munich = next(c for c in g.cities if c.name == 'Munich')
g.funds['germany'] = 2000
g.resources['germany']['steel'] = 50
munich.focus = 'base_air'
g._apply_city_focus(munich)
ab = g.base_of_city(munich, 'air')
check(ab is not None, "airforce base founded at Munich by focus")
check(g.funds['germany'] == 1500, "base cost drawn ($500)")
check(munich.focus == 'finance', "focus resets after the founding")
check('Munich' in g.world.airfield_spurs,
      "a town with no map site gets its spur laid")

# --- naval base refused inland
berlin.focus = 'base_naval'
g._apply_city_focus(berlin)
check(g.base_of_city(berlin, 'naval') is None,
      "no naval base at an inland town")

# --- base too poor: waits, keeps trying
g.funds['germany'] = 10
essen.focus = 'base_air'
g._apply_city_focus(essen)
check(g.base_of_city(essen, 'air') is None
      and essen.focus == 'base_air',
      "unaffordable base WAITS instead of lapsing")

# --- a captured town's directive dies with the flag: a track
# focus BILLS the treasury, and no owner inherits a purchase
posen = next(c for c in g.cities if c.country == 'poland')
posen.focus = 'agriculture'
g._capture_city(posen, 'germany')
check(posen.focus == 'finance',
      "a captured town's focus resets to finance")

# --- AI foci: all bases stand, so the staff turns to the land
g2_towns = [c for c in g.cities if c.country == 'soviet']
g._ai_set_foci('soviet')
foci = [c.focus for c in g2_towns]
check(not any(f.startswith('base_') for f in foci),
      "AI wants no base it already has")
check(any(f in ('agriculture', 'works', 'laboratories',
                'finance', 'research') for f in foci),
      "AI works its towns instead")

finish()
