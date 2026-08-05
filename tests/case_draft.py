"""The civilian draft, immediate: rolls free, conscription mines
industry to nought, rations gate, rolls refill at the fortnight."""
from harness import boot, check, finish

g = boot('germany')

berlin = next(c for c in g.cities if c.name == 'Berlin')
v = berlin.draft_rate()
pool0 = berlin.draft_pool
check(v >= 1 and pool0 >= 1, "Berlin rolls hold %d" % pool0)

g.resources['germany']['food'] = 5000


def count():
    return sum(1 for u in g.units if u.alive
               and u.country == 'germany'
               and u.unit_type == 'infantry')


# --- free muster from the rolls: industry untouched
n0 = count()
ind0 = berlin.industry
g._draft_transmit(berlin, pool0)
check(count() - n0 == pool0, "the rolls muster at once (%d)" % pool0)
check(berlin.industry == ind0, "rolls are free of industry")
check(berlin.draft_pool == 0, "the rolls are spent")

# --- beyond the rolls: conscription mines industry immediately
n1 = count()
g._draft_transmit(berlin, 10)
check(count() - n1 == 10, "conscripts muster at once")
check(abs(berlin.industry - (ind0 - 8.0)) < 0.01,
      "10 conscripts cost 8 industry points (%.1f)"
      % (ind0 - berlin.industry))

# --- the ceiling: industry stops at nought, never below
big = g.draft_ceiling(berlin) + 50
n2 = count()
g._draft_transmit(berlin, big)
check(berlin.industry >= 0.0, "industry floors at nought (%.1f)"
      % berlin.industry)
check(berlin.industry < 1.0, "the town was drafted to the bone")
raised = count() - n2
check(raised <= big - 50, "the ask beyond the ceiling was trimmed")

# --- drained town: nothing left to raise
n3 = count()
g._draft_transmit(berlin, 5)
check(count() == n3, "a spent town raises nobody")

# --- the fortnight refills the rolls
g._fortnight_rollover()
check(berlin.draft_pool >= v, "the rolls refill at the fortnight")

# --- rations still gate
essen = next(c for c in g.cities if c.name == 'Essen')
g.resources['germany']['food'] = 0
n4 = count()
g._draft_transmit(essen, essen.draft_pool)
check(count() == n4, "no rations, no muster")

finish()
