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

# --- focus: agriculture is a permanent level in the daily take
food0 = g._daily_income('germany')['food']
berlin.focus = 'agriculture'
g._apply_city_focus(berlin)
food1 = g._daily_income('germany')['food']
check(berlin.agri_level == 1 and food1 > food0,
      "agriculture level feeds the take (+%.2f/day)" % (food1 - food0))

# --- focus: steel works only at a deposit town
berlin.focus = 'steel'
g._apply_city_focus(berlin)
check(berlin.works_level == 0 and berlin.focus == 'finance',
      "no deposit at Berlin: steel focus falls back")
essen.focus = 'steel'
g._apply_city_focus(essen)
check(essen.works_level == 1, "Essen (steel town) gains a works level")

# --- focus: research pays points
rp0 = g.research_points['germany']
berlin.focus = 'research'
g._apply_city_focus(berlin)
check(g.research_points['germany'] > rp0,
      "laboratories pay %.1f RP" % (g.research_points['germany'] - rp0))

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

# --- AI foci: all bases stand, so the staff turns to the land
g2_towns = [c for c in g.cities if c.country == 'soviet']
g._ai_set_foci('soviet')
foci = [c.focus for c in g2_towns]
check(not any(f.startswith('base_') for f in foci),
      "AI wants no base it already has")
check(any(f in ('agriculture', 'steel', 'finance', 'research')
          for f in foci),
      "AI works its towns instead")

finish()
