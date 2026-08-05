"""The 1.2.0 economy core, re-covered in the repo battery: daily
accrual, rations, famine, trade settlement, the negotiating table's
valuation, directional rights."""
from harness import boot, step, check, finish

g = boot('germany')

# --- daily accrual: tons arrive when the day turns
inc = g._daily_income('germany')
check(inc['steel'] > inc['oil'], "Germany mines steel, not oil")
s0 = g.resources['germany']['steel']
g._accrue_resources(1)
check(g.resources['germany']['steel'] > s0, "a day pays steel")

# --- rations gate the muster
g.resources['germany']['food'] = 7        # one section's worth (4)
n = g._ration_out('germany', 5)
check(n == 1, "7 tons feeds exactly one section (got %d)" % n)

# --- famine grinds industry
b0 = next(c for c in g.cities if c.country == 'germany').industry
g._famine('germany', 10)
b1 = next(c for c in g.cities if c.country == 'germany').industry
check(b1 < b0, "famine sickens industry")

# --- trade: a purchase settles on the fortnight
g.resources['germany']['food'] = 100
g.funds['germany'] = 5000
g.trade_deals.append({'with': 'romania', 'res': 'food',
                      'amount': 20, 'price': 140, 'dir': 'in'})
f0 = g.resources['germany']['food']
m0 = g.funds['germany']
g._settle_trade()
check(g.resources['germany']['food'] == f0 + 20,
      "20 tons arrive on settlement day")
check(g.funds['germany'] == m0 - 140, "the bill is paid")

# --- the table: a naked demand insults; fair payment buys
import deals
v = deals.token_value({'kind': 'passage'})
check(v > 0, "passage is worth something (%d)" % v)
verdict, _, _, _ = deals.evaluate([], [{'kind': 'passage'}], 0,
                                  {'passage': True})
check(verdict == 'insult', "a naked demand is an insult")
offer = [{'kind': 'funds_once', 'amount': 5000}]
verdict, _, _, _ = deals.evaluate(offer, [{'kind': 'passage'}], 0,
                                  {'passage': True})
check(verdict == 'accept', "fair payment is accepted")

# --- directional rights
g.rights.append({'with': 'romania', 'kind': 'passage',
                 'dir': 'theirs'})
to_us, to_them = g.right_between('romania', 'passage')
check(to_us and not to_them, "a right granted TO US runs one way")
check(g.has_right('germany', 'romania', 'passage'),
      "we may enter their ground")
check(not g.has_right('romania', 'germany', 'passage'),
      "they may not enter ours")

finish()
