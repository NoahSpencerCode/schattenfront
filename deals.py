"""
The negotiating table.

Diplomacy is not a row of buttons: it is a SHEET on which each side
lays tokens -- money, cargo, rights of passage, the use of a supply
net, a pact of alliance -- and the other party weighs the whole
basket against its standing with you and answers in its own voice.

A token is a plain dict so it serialises with the save:

    {'kind': 'funds_ftn', 'amount': 200}
    {'kind': 'res_ftn', 'res': 'oil', 'amount': 40}
    {'kind': 'passage'}

Valuation is in MARKS -- the same unit as the treasury -- so a
right of passage can be priced against a tanker of oil.
"""

from config import TRADE_PRICES

# how many fortnights of a standing payment the negotiators discount
# to when they price it against a lump sum
HORIZON = 8

# base worth of the rights and pacts, in marks
BASE = {
    'passage': 900,        # march my columns across your country
    'supply': 1400,        # water them at your towns and quays
    'comms': 1100,         # my columns under your wireless net
    'nonaggression': 1200,  # no war between us for a year
    'alliance': 3600,      # your wars are my wars
    'peace': 2000,         # the guns fall silent
}

KIND_LABEL = {
    'funds_once': 'FUNDS (ONE PAYMENT)',
    'funds_ftn': 'FUNDS EACH FORTNIGHT',
    'res_once': 'CARGO (ONE SHIPMENT)',
    'res_ftn': 'CARGO EACH FORTNIGHT',
    'passage': 'RIGHT OF PASSAGE',
    'supply': 'USE OF OUR SUPPLY NET',
    'comms': 'USE OF OUR WIRELESS NET',
    'nonaggression': 'PACT OF NON-AGGRESSION',
    'alliance': 'PACT OF ALLIANCE',
    'peace': 'AN END TO THE WAR',
}

# a token one side may not offer at all
GIVE_ONLY_MUTUAL = ('nonaggression', 'alliance', 'peace')


def token_text(tok):
    k = tok['kind']
    if k == 'funds_once':
        return "$%d" % tok['amount']
    if k == 'funds_ftn':
        return "$%d EACH FORTNIGHT" % tok['amount']
    if k == 'res_once':
        return "%d %s" % (tok['amount'], tok['res'].upper())
    if k == 'res_ftn':
        return "%d %s EACH FORTNIGHT" % (tok['amount'],
                                         tok['res'].upper())
    return KIND_LABEL.get(k, k.upper())


def token_value(tok):
    """What a token is worth in marks, before any attitude."""
    k = tok['kind']
    if k == 'funds_once':
        return float(tok['amount'])
    if k == 'funds_ftn':
        return float(tok['amount']) * HORIZON
    if k == 'res_once':
        return tok['amount'] * TRADE_PRICES[tok['res']] * 1.0
    if k == 'res_ftn':
        return tok['amount'] * TRADE_PRICES[tok['res']] * HORIZON
    return float(BASE.get(k, 500))


def basket_value(tokens):
    return sum(token_value(t) for t in tokens)


# ------------------------------------------------------- standing
# What a foreign office thinks of you, on the Civ model: an approach
# that colours every price it quotes.
STANDING = (
    (70, 'WARM', 0.75),        # they shade their prices for a friend
    (30, 'CORRECT', 0.95),
    (-10, 'COOL', 1.25),
    (-45, 'GUARDED', 1.7),
    (-999, 'HOSTILE', 2.6),
)


def standing_word(score):
    for floor, word, mult in STANDING:
        if score >= floor:
            return word, mult
    return STANDING[-1][1], STANDING[-1][2]


VOICE = {
    # verdict -> attitude -> line
    'accept': {
        'WARM': "Between friends this hardly wanted an envoy. "
                "Signed, and gladly.",
        'CORRECT': "The terms are sound. Our seal is on the "
                   "instrument.",
        'COOL': "We have no love for you, but we can count. "
                "Agreed.",
        'GUARDED': "We sign with one hand on the sword. Agreed, "
                   "for now.",
        'HOSTILE': "We take your terms because they favour us, "
                   "not because we favour you.",
    },
    'refuse': {
        'WARM': "Even friendship has a ledger, and this one does "
                "not balance. Sweeten it and we will look again.",
        'CORRECT': "The sheet is short. Our answer must be no.",
        'COOL': "You ask a great deal and offer little. No.",
        'GUARDED': "You would have to pay a very great deal more "
                   "than this to move us.",
        'HOSTILE': "Take your paper back across the frontier.",
    },
    'insult': {
        'WARM': "You cannot have meant this. We will pretend the "
                "envoy never arrived.",
        'CORRECT': "This is not a proposal, it is a demand. "
                   "Refused.",
        'COOL': "You mistake us for a beggar nation. Refused.",
        'GUARDED': "Every such note hardens us further. Refused.",
        'HOSTILE': "The envoy is given his coat and shown the "
                   "door.",
    },
    'ungated': {
        'WARM': "A pact of that kind wants more than goodwill -- "
                "come back when our peoples have marched "
                "together.",
        'CORRECT': "We do not sign such pacts with powers we "
                   "scarcely know.",
        'COOL': "You presume a closeness that does not exist.",
        'GUARDED': "With you? Never on these terms.",
        'HOSTILE': "You may as well ask for the moon.",
    },
}


def evaluate(offer, ask, standing_score, gates):
    """Weigh a sheet from the RECEIVING nation's side.

    offer  -- tokens the player lays down (they receive these)
    ask    -- tokens the player wants (they give these up)
    gates  -- {'alliance': bool, 'funds_once': bool, ...} rights the
              player has earned; a token whose gate is False is
              refused outright however rich the sheet.

    Returns (verdict, word, reply, gain) where verdict is one of
    'accept' | 'refuse' | 'insult' | 'ungated'.
    """
    word, demand = standing_word(standing_score)
    for tok in ask:
        if gates.get(tok['kind'], True) is False:
            return 'ungated', word, VOICE['ungated'][word], 0.0
    give_up = basket_value(ask) * demand
    receive = basket_value(offer)
    gain = receive - give_up
    if not offer and ask:
        return 'insult', word, VOICE['insult'][word], gain
    if receive >= give_up:
        return 'accept', word, VOICE['accept'][word], gain
    # a near miss reads as a refusal with the door left ajar
    return 'refuse', word, VOICE['refuse'][word], gain


def shortfall_hint(gain):
    """A line the envoy can carry home: how far short the sheet ran."""
    if gain >= 0:
        return "They would find these terms acceptable."
    if gain > -600:
        return "They would want a little more."
    if gain > -2500:
        return "They would want a great deal more."
    return "They would laugh the envoy out of the room."
