"""The fortnight focus and the base economy: bases produce, focus
directives pay their distinct coins, refunds when no base stands."""
from harness import boot, step, until, check, finish

g = boot('germany')

berlin = next(c for c in g.cities if c.name == 'Berlin')
essen = next(c for c in g.cities if c.name == 'Essen')

# --- the opening: Germany holds ONE army base, nothing else
mine_posts = [p for p in g.armyposts if p.country == 'germany']
mine_air = [a for a in g.airfields
            if a.country == 'germany' and a.is_base]
mine_yards = [h for h in g.harbors
              if h.country == 'germany' and h.is_base]
check(len(mine_posts) == 1 and not mine_air and not mine_yards,
      "Germany opens with one PRODUCING base only")
check(any(h.country == 'germany' and not h.is_base
          for h in g.harbors),
      "...but her ports stand dressed on the coast")

# --- production: land builds at the base; air is REFUNDED
g.funds['germany'] = 10000
g.resources['germany']['steel'] = 200
f0 = g.funds['germany']
q0 = len(mine_posts[0].production)
g._distribute_production('germany', {'tank': 1, 'fighter': 1})
check(len(mine_posts[0].production) == q0 + 1,
      "tank on the army base line")
check(g.funds['germany'] == f0 + 460,
      "fighter refunded: no airforce base (%d)"
      % (g.funds['germany'] - f0))

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

# --- focus: raise an airforce base (pays $ and steel, founds it)
g.funds['germany'] = 2000
g.resources['germany']['steel'] = 50
berlin.focus = 'base_air'
g._apply_city_focus(berlin)
check(g.base_of_city(berlin, 'air') is not None,
      "airforce base founded at Berlin")
check(g.funds['germany'] == 1500, "base cost drawn ($500)")
check(berlin.focus == 'finance', "focus resets after the founding")

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

# --- AI foci: a nation with no bases wants them first
g2_towns = [c for c in g.cities if c.country == 'soviet']
g._ai_set_foci('soviet')
foci = [c.focus for c in g2_towns]
check('base_air' in foci or 'base_naval' in foci,
      "AI reaches for its missing bases (%s)" %
      [f for f in foci if f.startswith('base')])

finish()
