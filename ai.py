"""
The general staffs of the computer powers.

Every nation AI plays by the PLAYER'S rules and nothing more: the same
standing fortnight budget executed against the same treasury, the same
production pipeline, the same movement orders through the same route
planner, and the same annexation law (infantry must stand ON the city
and are consumed as its garrison).  There are no free captures and no
hidden income.

Thinking follows a WW2 staff rhythm and is heavily throttled: each
nation runs ONE cheap planning stage every AI think tick (the stages
rotate), so the whole council of war costs well under a millisecond a
frame regardless of the size of the war.

The doctrine is period flavour: schwerpunkt (mass one strike group,
then punch), objectives picked by worth and nearness (with a taste for
cheap neutral annexations early), a garrison recalled to a threatened
capital, supply columns and engineers marching with the spearhead, air
cover over the assembly area, bombers ahead of the advance, fleets off
the objective coast, and -- when the objective lies over water -- an
amphibious lift by troop transport from the nearest home harbor.
"""

import random

from panda3d.core import Vec3

from geodata import CITY_POPULATION
from units import NATION_UNIT_STATS, UNIT_TYPES, stats_for
from utils import angle_between, latlon_to_vec

# how strongly each power leans into its historical doctrine when the
# fortnight appropriation is drawn up (multiplies its budget share)
DOCTRINE = {
    'germany': {'tank': 1.7, 'fighter': 1.3, 'infantry': 1.2,
                'supply_truck': 1.2, 'submarine': 1.8,
                'heavy_tank': 1.5, 'jet_fighter': 1.4},
    'soviet':  {'infantry': 1.9, 'tank': 1.4, 'aa_artillery': 1.2,
                'artillery': 1.7, 'heavy_tank': 1.5},
    'usa':     {'infantry': 1.3, 'bomber': 1.4, 'personnel_transport': 1.3,
                'supply_truck': 1.3, 'heavy_bomber': 1.6,
                'battleship': 1.3},
    'japan':   {'destroyer_sea_sea': 1.4, 'aircraft_carrier': 1.4,
                'personnel_transport': 1.4, 'fighter': 1.2,
                'battleship': 1.6, 'submarine': 1.3},
    'britain': {'fighter': 1.5, 'destroyer_sea_sea': 1.3, 'bomber': 1.2,
                'heavy_bomber': 1.5, 'battleship': 1.2},
}

MAX_ORDERS_PER_THINK = 12       # hard cap: thinking never floods a frame
# which programme chain each staff pursues first
RESEARCH_ORDER = {
    'germany': ('sea', 'land', 'air'),
    'usa': ('air', 'sea', 'land'),
    'britain': ('air', 'sea', 'land'),
    'japan': ('sea', 'air', 'land'),
    'soviet': ('land', 'air', 'sea'),
}
FORCE_CAP = 48                  # a nation fields at most this many units:
                                # WW2 armies were bounded by logistics, and
                                # so is the frame budget


class NationAI:
    STAGES = 4

    # the diplomatic tempo, in game days
    WAR_GRACE_DAYS = 8          # the world stays quiet at the start
    WAR_EVERY_DAYS = (16, 30)   # one declaration per nation per spell

    def __init__(self, game, country):
        self.g = game
        self.country = country
        self.timer = random.uniform(2.0, 8.0)   # staggers the nations
        self.stage = 0
        # each staff opens its first war on its own clock
        self.war_ok_minutes = (self.WAR_GRACE_DAYS
                               + random.uniform(2.0, 14.0)) * 1440.0
        self.budget_counts = {}
        self.objective = None       # the city the staff means to take
        self.staging = None         # own city the strike group masses at
        self.overseas = False       # objective needs an amphibious lift
        self.unreachable = set()    # names ruled out this ownership era
        self._reach = {}            # capital->city walkability cache
        self._gen = -1              # ownership generation of the cache

    # ------------------------------------------------------------ events
    def on_ownership_change(self):
        """A city changed hands somewhere: yesterday's map is stale."""
        self._gen += 1
        self.unreachable.clear()
        self._reach.clear()
        if self.objective is not None and \
                self.objective.country == self.country:
            self.objective = None

    # ------------------------------------------------- fortnight budget
    def plan_budget(self):
        """Draw up the standing budget the fortnight will execute --
        the same appropriation law the player's Exchequer follows,
        weighted by national doctrine and the needs of the front."""
        g = self.g
        funds = g.funds.get(self.country, 0) + \
            g.projected_revenue(self.country)
        has_harbor = any(c.harbor and c.country == self.country
                         for c in g.cities)
        weights = {}
        # the labs first: buy the cheapest affordable node on the
        # frontier, favourite branch first (research_pct is already
        # tithed at the rollover)
        from tech import available_nodes, NODES
        frontier = available_nodes(g.researched[self.country])
        order = RESEARCH_ORDER.get(self.country,
                                   ('land', 'air', 'sea'))
        frontier.sort(key=lambda nid: (
            order.index(NODES[nid]['branch'])
            if NODES[nid]['branch'] in order else 9,
            NODES[nid]['cost']))
        for nid in frontier:
            if g.research_points[self.country] >= NODES[nid]['cost']:
                g.research_node(self.country, nid)
                break
        buyable = set(g.buyable_units(self.country))
        doctrine = DOCTRINE.get(self.country, {})
        for ut in NATION_UNIT_STATS[self.country]:
            if ut not in buyable:
                continue
            if UNIT_TYPES[ut]['domain'] == 'sea' and not has_harbor:
                continue
            w = doctrine.get(ut, 1.0)
            if ut == 'infantry':
                # infantry is the currency of annexation: the bigger
                # the prize, the deeper the draft
                need = (self.objective.required_infantry()
                        if self.objective else 2)
                w *= 1.0 + 0.15 * min(8, need)
            if ut == 'personnel_transport' and self.overseas:
                w *= 1.6
            weights[ut] = w
        # the draft is bounded: never grow past the force cap, however
        # deep the treasury runs (the player faces the same logistics)
        alive = sum(1 for u in g.units
                    if u.alive and u.country == self.country)
        slots = max(0, FORCE_CAP - alive)
        total_w = sum(weights.values()) or 1.0
        counts = {}
        for ut, w in weights.items():
            share = funds * w / total_w
            n_funds = int(share // stats_for(ut, self.country)['cost'])
            n_slots = int(round(slots * w / total_w))
            counts[ut] = min(n_funds, n_slots)
        self.budget_counts = counts

    # --------------------------------------------------------- thinking
    def think(self):
        self._defend()              # every sitting: the homeland first
        stage = self.stage
        self.stage = (self.stage + 1) % self.STAGES
        # a power without an objective is not at war: pick one NOW,
        # whatever the rotation says -- expansion never pauses (the
        # probes are cached, so an exhausted map costs nothing)
        if self.objective is None and stage != 0:
            self._stage_strategy()
        if stage == 0:
            self._stage_strategy()
        elif stage == 1:
            self._stage_army()
        elif stage == 2:
            self._stage_capture_and_defense()
        else:
            self._stage_support()

    def _defend(self):
        """Enemy ground forces near ANY of our towns are met: the
        nearest soldiers drop what they are doing and intercept.  Runs
        every think tick so a marching column cannot stroll through the
        country unopposed."""
        g = self.g
        threat_city = None
        for c in g.cities:
            if c.country != self.country:
                continue
            for u in g.units:
                if (u.alive and not u.carried_by
                        and u.country not in (self.country, 'neutral')
                        and u.country not in g.eliminated
                        and u.stats['domain'] == 'land'
                        and u.stats['damage'] > 0
                        and angle_between(u.pos, c.pos) < 0.05):
                    threat_city = c
                    break
            if threat_city is not None:
                break
        if threat_city is None:
            return
        defenders = sorted(
            (u for u in g.units
             if u.alive and u.country == self.country
             and not u.carried_by and u.stats['domain'] == 'land'
             and u.stats['damage'] > 0),
            key=lambda u: angle_between(u.pos, threat_city.pos))
        sent = 0
        for u in defenders[:10]:
            if angle_between(u.pos, threat_city.pos) < 0.02:
                continue            # already on the spot
            cur = u.current_order or {}
            goal = cur.get('goal')
            if goal is not None and \
                    angle_between(goal, threat_city.pos) < 0.01:
                continue            # already marching there
            u.clear_orders()
            g._pending_ai_orders.append(
                (u, {'kind': 'move', 'goal': Vec3(threat_city.pos)}))
            sent += 1
            if sent >= 6:
                break

    # ---- stage 0: the war council picks THE objective ---------------
    def _war_council(self):
        """Opportunistic statecraft, heavily throttled. A power with
        no war to prosecute picks a neighbour and declares -- weak
        NPC nations are preferred prey, and nobody attacks a bloc
        overwhelmingly stronger than his own. A power AT war courts
        co-belligerents into alliance."""
        g = self.g
        from config import PLAYABLE
        me = self.country
        my_enemies = g.nation_enemies(me)
        # courtship: bind a nation fighting the same enemy
        if my_enemies and random.random() < 0.25:
            for other in list(g.nation_enemies(next(iter(my_enemies)))):
                if (other != me and not g.at_war(me, other)
                        and not g.allied(me, other)
                        and other not in g.eliminated
                        and g.alliance_answer(other, me)):
                    g.make_alliance(me, other)
                    break
        # declarations: only when the current wars offer no objective
        if my_enemies and any(
                g.at_war(me, c.country) for c in g.cities
                if c.name not in self.unreachable
                and c.country != me):
            return
        if g.clock_minutes < self.war_ok_minutes:
            return
        own = [c for c in g.cities if c.country == me]
        if not own:
            return
        centroid = Vec3(0, 0, 0)
        for c in own:
            centroid += c.pos
        centroid.normalize()
        my_forces = sum(1 for u in g.units
                        if u.alive and u.country in g._bloc(me))
        best, best_s = None, 0.0
        for c in g.cities:
            nat = c.country
            if (nat == me or nat in g.eliminated or nat == 'neutral'
                    or g.at_war(me, nat) or g.allied(me, nat)):
                continue
            d = angle_between(centroid, c.pos)
            if d > 0.5:
                continue            # wars begin next door
            pop = min(1500.0, CITY_POPULATION.get(c.name, 120))
            s = (150.0 + pop) / (0.02 + d) ** 1.7
            if nat not in PLAYABLE:
                s *= 1.6            # the weak are eaten first
            their = sum(1 for u in g.units
                        if u.alive and u.country in g._bloc(nat))
            if their > my_forces * 1.5:
                continue            # nobody duels a stronger bloc
            if s > best_s:
                best, best_s = nat, s
        if best is not None:
            g.declare_war(me, best)
            self.war_ok_minutes = g.clock_minutes + random.uniform(
                *self.WAR_EVERY_DAYS) * 1440.0

    def _stage_strategy(self):
        g = self.g
        own = [c for c in g.cities if c.country == self.country]
        if not own:
            return
        # the council of war sits before the maps come out: if no war
        # offers an objective, consider STARTING one (throttled), and
        # consider binding friends against a shared enemy
        self._war_council()
        if (self.objective is not None
                and self.objective.country not in (self.country,)
                and self.objective.country not in g.eliminated
                and g.at_war(self.country, self.objective.country)):
            return                  # the current objective stands
        centroid = Vec3(0, 0, 0)
        for c in own:
            centroid += c.pos
        centroid.normalize()
        # nearby prizes first: population counts, but the blitz begins
        # next door (capped pop influence, steep distance falloff).
        # ONLY cities of nations we are AT WAR with are on the maps.
        scored = []
        for c in g.cities:
            if c.country == self.country or c.country in g.eliminated:
                continue
            if not g.at_war(self.country, c.country):
                continue
            if c.name in self.unreachable:
                continue
            d = angle_between(centroid, c.pos)
            pop = min(1500.0, CITY_POPULATION.get(c.name, 120))
            score = (150.0 + pop) / (0.02 + d) ** 1.7
            scored.append((score, c))
        scored.sort(key=lambda s: -s[0])
        # a land-reachable objective is always preferred; only when the
        # best of the map lies over water does the staff draw up an
        # amphibious operation (a few cached probes, never a flood)
        overseas_pick = None
        cap = g.capital_of(self.country)
        for score, c in scored[:8]:
            staging = min(own, key=lambda o: angle_between(o.pos, c.pos))
            # a land pick needs BOTH legs on foot: army -> staging and
            # staging -> objective (an island army cannot walk to a
            # continental assembly area)
            if (self._reachable(cap, staging)
                    and g.planner.plan_land(staging.pos, c.pos)
                    is not None):
                self.objective, self.staging = c, staging
                self.overseas = False
                return
            self.unreachable.add(c.name)
            if overseas_pick is None and self._has_sealift():
                # embark where the army can actually assemble
                base = [o for o in own if self._reachable(cap, o)]
                st = min(base or [cap],
                         key=lambda o: angle_between(o.pos, c.pos))
                overseas_pick = (c, st)
        if overseas_pick is not None:
            self.objective, self.staging = overseas_pick
            self.overseas = True
            self.unreachable.discard(self.objective.name)

    def _reachable(self, cap, city):
        """Cached: can the army walk from the capital to this city?"""
        if city is cap:
            return True
        hit = self._reach.get(city.name)
        if hit is None:
            hit = self.g.planner.plan_land(cap.pos, city.pos) is not None
            self._reach[city.name] = hit
        return hit

    def _has_sealift(self):
        return any(u.alive and u.country == self.country
                   and u.unit_type == 'personnel_transport'
                   for u in self.g.units)

    # ---- stage 1: mass the schwerpunkt, then punch -------------------
    def _stage_army(self):
        g = self.g
        if self.objective is None or self.staging is None:
            return
        idle = [u for u in g.units
                if u.alive and u.country == self.country
                and not u.carried_by and not u.current_order
                and not u.order_queue
                and u.stats['domain'] == 'land'
                and not u.stats.get('supply_carrier')
                and u.unit_type != 'engineer']
        if not idle:
            return
        orders = 0
        if self.overseas:
            # the landing force is already on the far shore: it marches
            # on the objective rather than back to the home staging
            for u in idle:
                if angle_between(u.pos, self.objective.pos) < 0.12:
                    g._pending_ai_orders.append(
                        (u, {'kind': 'move',
                             'goal': Vec3(self.objective.pos)}))
                    orders += 1
                    if orders >= MAX_ORDERS_PER_THINK:
                        return
        near = [u for u in idle
                if angle_between(u.pos, self.staging.pos) < 0.05]
        need = self.objective.required_infantry()
        inf_near = sum(1 for u in near if u.unit_type == 'infantry')
        if inf_near >= need + 1 and len(near) >= need + 2 \
                and not self.overseas:
            # the group is massed: advance on the objective as one --
            # WITH its train, for no column outlives its stores
            for u in near:
                g._pending_ai_orders.append(
                    (u, {'kind': 'move', 'goal': Vec3(self.objective.pos)}))
                orders += 1
                if orders >= MAX_ORDERS_PER_THINK:
                    break
            lorries = [u for u in g.units
                       if u.alive and u.country == self.country
                       and u.unit_type == 'supply_truck'
                       and not u.carried_by
                       and getattr(u, '_supply_tgt', None) is None
                       and angle_between(u.pos, self.staging.pos) < 0.08]
            for u in lorries[:2]:
                u.give_order({'kind': 'move',
                              'goal': Vec3(self.objective.pos),
                              'auto': True})
        else:
            # still gathering: everyone idle marches to the staging city
            for u in idle:
                if u in near:
                    continue
                g._pending_ai_orders.append(
                    (u, {'kind': 'move', 'goal': Vec3(self.staging.pos)}))
                orders += 1
                if orders >= MAX_ORDERS_PER_THINK:
                    break

    # ---- stage 2: annex under the garrison law; guard the capital ----
    def _stage_capture_and_defense(self):
        g = self.g
        # the same law the player's CAPTURE button obeys: infantry must
        # stand on the town and are consumed as its garrison
        for city in g.cities:
            if city.country == self.country \
                    or city.country in g.eliminated:
                continue
            if len(g._capture_garrison(city, self.country)) \
                    >= city.required_infantry():
                g.attempt_capture(city, self.country)
                break               # one deed per sitting
        # a thin garrison net: spare infantry from the staging pool
        # picket the towns that stand empty (interception in _defend
        # does the heavy lifting; this keeps eyes and a tripwire there)
        if self.objective is None or self.staging is None:
            return
        own_land = [u for u in g.units
                    if u.alive and u.country == self.country
                    and not u.carried_by and u.stats['domain'] == 'land']
        bare = []
        for c in g.cities:
            if c.country != self.country:
                continue
            if not any(angle_between(u.pos, c.pos) < 0.02
                       for u in own_land):
                bare.append(c)
        if not bare:
            return
        need = self.objective.required_infantry() + 2
        spare = [u for u in own_land
                 if u.unit_type == 'infantry'
                 and not u.current_order and not u.order_queue
                 and angle_between(u.pos, self.staging.pos) < 0.05]
        surplus = spare[need:]      # the strike group keeps its draft
        for u, c in zip(surplus, bare[:2]):
            g._pending_ai_orders.append(
                (u, {'kind': 'move', 'goal': Vec3(c.pos)}))

    # ---- stage 3: air cover, fleets, logistics, the sea lift ---------
    def _stage_support(self):
        g = self.g
        if self.objective is None or self.staging is None:
            return
        orders = 0

        def send(u, goal_pos, queue_extra=None):
            nonlocal orders
            g._pending_ai_orders.append(
                (u, {'kind': 'move', 'goal': Vec3(goal_pos)}))
            if queue_extra is not None:
                u.order_queue.append(queue_extra)
            orders += 1
            return orders < MAX_ORDERS_PER_THINK

        idle = [u for u in g.units
                if u.alive and u.country == self.country
                and not u.carried_by and not u.current_order
                and not u.order_queue]
        obj_pos = self.objective.pos
        # supply columns and engineers keep pace with the spearhead
        for u in idle:
            if u.unit_type in ('supply_truck', 'engineer'):
                if angle_between(u.pos, self.staging.pos) > 0.05:
                    if not send(u, self.staging.pos):
                        return
        # fighters screen the assembly area; bombers work the objective
        for u in idle:
            if u.stats['domain'] != 'air' or u.based_at is None:
                continue
            if u.unit_type == 'fighter':
                if not send(u, self.staging.pos):
                    return
            elif u.unit_type == 'bomber':
                if not send(u, obj_pos):
                    return
        # the fleet stands off the objective coast (or the home quay)
        wl, wo = g.world.nearest_water(self.objective.lat,
                                       self.objective.lon, max_deg=2.5)
        sea_goal = None
        if g.world.is_water(wl, wo):
            sea_goal = latlon_to_vec(wl, wo)
        for u in idle:
            # warships, the supply vessel and the command ship all
            # stand off the objective coast; the troop lift stays home
            if u.stats['domain'] == 'sea' and sea_goal is not None \
                    and u.unit_type != 'personnel_transport':
                if not send(u, sea_goal):
                    return
        # the amphibious lift, in two sailings of the staff clock:
        # first the infantry file aboard at the quay; only when the
        # holds are full does the transport steam for the far shore
        if self.overseas and sea_goal is not None:
            lift = next((u for u in idle
                         if u.unit_type == 'personnel_transport'), None)
            if lift is not None:
                need = min(self.objective.required_infantry() + 1,
                           lift.stats['capacity'])
                if len(lift.cargo) >= need or (
                        lift.cargo
                        and g._board_capacity_left(lift) <= 0):
                    # loaded: sail and put the force ashore (the
                    # unload is QUEUED through the drain, or the move
                    # order would wipe it)
                    g._pending_ai_orders.append(
                        (lift, {'kind': 'move', 'goal': Vec3(sea_goal)}))
                    g._pending_ai_orders.append(
                        (lift, {'kind': 'unload', 'goal': Vec3(obj_pos)},
                         True))
                elif angle_between(lift.pos, self.staging.pos) > 0.035:
                    # bring the lift to the embarkation beach first: the
                    # infantry cannot wade out to a distant mooring
                    bl, bo = g.world.nearest_water(self.staging.lat,
                                                   self.staging.lon)
                    g._pending_ai_orders.append(
                        (lift, {'kind': 'move',
                                'goal': latlon_to_vec(bl, bo)}))
                else:
                    # moored off the staging city: call infantry aboard
                    # -- and ONE lorry of stores, or the beachhead
                    # starves before it reaches the objective
                    slots = g._board_capacity_left(lift)
                    riders = sorted(
                        (u for u in idle if u.unit_type == 'infantry'),
                        key=lambda u: angle_between(u.pos, lift.pos))
                    manifest = riders[:max(0, min(slots, need))]
                    if not any(p.unit_type == 'supply_truck'
                               for p in lift.cargo):
                        lorry = next(
                            (u for u in g.units
                             if u.alive and u.country == self.country
                             and u.unit_type == 'supply_truck'
                             and not u.carried_by
                             and getattr(u, '_supply_tgt', None) is None
                             and angle_between(u.pos, lift.pos) < 0.08),
                            None)
                        if lorry is not None and slots > len(manifest):
                            manifest.append(lorry)
                    for u in manifest:
                        g._pending_ai_orders.append(
                            (u, {'kind': 'board', 'target': lift}))
