"""The civilian draft: quota decree, fortnight muster, industry
grind above the volunteer line, ration gating unchanged."""
from harness import boot, step, until, check, finish

g = boot('germany')

berlin = next(c for c in g.cities if c.name == 'Berlin')
v = berlin.draft_rate()
check(v >= 1, "Berlin volunteer line %d" % v)
check(berlin.draft_quota == 0, "quota opens at zero")

# the fax plumbing signs a decree (UI-less: call the transmit hook)
g.resources['germany']['food'] = 500
before_pool = berlin.draft_pool
g._draft_transmit(berlin, v + 2, 0)
check(berlin.draft_quota == v + 2, "decree sets quota %d" % (v + 2))

# an immediate call-up drains the pool
n_units0 = sum(1 for u in g.units if u.alive
               and u.country == 'germany'
               and u.unit_type == 'infantry')
g._draft_transmit(berlin, v + 2, min(2, before_pool))
n_units1 = sum(1 for u in g.units if u.alive
               and u.country == 'germany'
               and u.unit_type == 'infantry')
check(n_units1 - n_units0 == min(2, before_pool),
      "immediate muster raises %d" % (n_units1 - n_units0))

# the fortnight musters the quota and grinds industry
ind0 = berlin.industry
g._fortnight_rollover()
n_units2 = sum(1 for u in g.units if u.alive
               and u.country == 'germany'
               and u.unit_type == 'infantry')
check(n_units2 - n_units1 >= berlin.draft_quota - 1,
      "fortnight musters the quota (%d new)" % (n_units2 - n_units1))
expected_grind = 0.8 * 2          # two sections over the line
drift = berlin.industry - ind0
check(drift <= -expected_grind + 0.6,
      "conscription grinds industry (%.2f)" % drift)

# within the volunteer line: no grind
g._draft_transmit(berlin, v, 0)
ind1 = berlin.industry
g._fortnight_rollover()
check(berlin.industry >= ind1 - 0.1,
      "volunteer-line quota leaves industry alone (%.2f)"
      % (berlin.industry - ind1))

# rations still gate the muster
g.resources['germany']['food'] = 0
g._draft_transmit(berlin, v + 2, 0)
n3 = sum(1 for u in g.units if u.alive and u.country == 'germany'
         and u.unit_type == 'infantry')
g._fortnight_rollover()
n4 = sum(1 for u in g.units if u.alive and u.country == 'germany'
         and u.unit_type == 'infantry')
check(n4 == n3, "no rations, no muster")

finish()
