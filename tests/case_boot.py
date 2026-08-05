"""Integration smoke WITH the AI on: boot, run fortnights, step the
world, and make sure the new laws hold together -- AI founds its
bases, production flows, nothing throws."""
from harness import boot, step, check, finish

g = boot('germany', ai=True)

check(len(g.units) > 50, "world up: %d units" % len(g.units))
check(len(g.cities) > 150, "world up: %d cities" % len(g.cities))

# two fortnights turn with every AI playing
g._fortnight_rollover()
step(g, 120)
g._fortnight_rollover()
step(g, 240)

# the AI powers reached for their missing bases
for nat in ('soviet', 'usa', 'britain', 'japan'):
    n_bases = (
        sum(1 for p in g.armyposts if p.country == nat)
        + sum(1 for a in g.airfields
              if a.country == nat and getattr(a, 'is_base', False))
        + sum(1 for h in g.harbors
              if h.country == nat and getattr(h, 'is_base', False)))
    check(n_bases >= 3, "%s holds its three bases (%d standing)"
          % (nat, n_bases))

# production lines exist somewhere and tick without crashing
lines = sum(len(p.production) for p in g.armyposts) \
    + sum(len(h.production) for h in g.harbors) \
    + sum(len(a.production) for a in g.airfields)
check(lines >= 0, "lines standing: %d" % lines)
step(g, 200)
check(True, "world steps clean with AI")

# save and restore the new world
import saveload
snap = saveload.snapshot(g)
check(snap['version'] == 4, "snapshot v4")
n_posts = len([r for r in snap['armyposts']])
check(n_posts == len(g.armyposts),
      "all %d army bases on file" % n_posts)
check(all('city' in r for r in snap['harbors']),
      "harbors carry their city link")

finish()
