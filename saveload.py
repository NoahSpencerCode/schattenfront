"""
Save and load: the whole campaign folded into one JSON dispatch case.

Everything the fortunes of war have changed is recorded -- the clock,
the treasuries, every war and pact and courier bag in flight, every
city's owner and tax ledger, engineer works (depots, bunkers, radars,
fields, harbours, custom roads and their cuts, bridges standing or
dropped), and every unit with its strength, stores, cargo, garrison
posting and standing orders. What the world derives on its own (fog,
contact, pathfinding graphs, painted borders) is derived again on
load rather than stored.

Unit orders are saved as data and re-resolved by reference tables on
load; a reference that no longer resolves simply drops that order --
a unit would rather stand idle than follow a ghost.
"""

import json
import os
import sys
import time

from panda3d.core import Vec3

SAVE_VERSION = 4


# ------------------------------------------------------------ location

def save_dir():
    """A writable saves/ directory: beside the game when possible,
    else under the user's documents (a translocated mac install is
    read-only)."""
    cands = [os.path.abspath('saves'),
             os.path.expanduser('~/Documents/Global Operations 1939/saves')]
    for d in cands:
        try:
            os.makedirs(d, exist_ok=True)
            probe = os.path.join(d, '.probe')
            with open(probe, 'w') as fh:
                fh.write('x')
            os.remove(probe)
            return d
        except OSError:
            continue
    return cands[-1]


# path -> (mtime, size, meta): a filed campaign is a MEGABYTE of
# JSON and the archive drawer is read on every render of the LOAD
# GAME page -- arming or answering the burn prompt re-read and
# re-parsed every case in the drawer, which is the second the
# game stood still. A case is parsed once and remembered until the
# file itself changes.
_META_CACHE = {}


# the sidecar carries a case's INDEX CARD -- the few lines the
# archive drawer prints -- beside the case itself, so opening LOAD
# GAME reads a few hundred bytes per campaign instead of parsing a
# megabyte of situation map. Not a .json: list_saves scans for
# those, and an index card is not a campaign.
SIDECAR_VERSION = 1


def _card_path(path):
    return path + '.meta'


def _read_card(path, st):
    """The index card, if it is present and still describes THIS
    file (a case written or replaced since invalidates its card)."""
    try:
        with open(_card_path(path), 'r', encoding='utf-8') as fh:
            card = json.load(fh)
        if (card.get('v') == SIDECAR_VERSION
                and card.get('size') == st.st_size
                and abs(card.get('mtime', -1) - st.st_mtime) < 1e-6):
            return card.get('meta')
    except Exception:
        pass
    return None


def _write_card(path, meta):
    """File the index card beside its case. A read-only drawer just
    goes without -- the full parse still works."""
    try:
        st = os.stat(path)
        tmp = _card_path(path) + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            json.dump({'v': SIDECAR_VERSION, 'mtime': st.st_mtime,
                       'size': st.st_size, 'meta': meta}, fh)
        os.replace(tmp, _card_path(path))
    except Exception:
        pass


def forget_save(path):
    """Drop one case from the meta cache (it was burnt, or written
    over)."""
    _META_CACHE.pop(path, None)


def list_saves():
    """[(path, meta), ...] newest first; unreadable files skipped."""
    out = []
    seen = set()
    # the last entry is the game's PRE-RENAME documents folder: old
    # campaigns saved under the working title still show in LOAD GAME
    for d in (os.path.abspath('saves'),
              os.path.expanduser('~/Documents/Global Operations 1939/saves'),
              os.path.expanduser('~/Documents/Zero Hour 1939/saves'),
              os.path.expanduser('~/Documents/Schattenfront/saves')):
        if not os.path.isdir(d) or d in seen:
            continue
        seen.add(d)
        for name in os.listdir(d):
            if not name.endswith('.json'):
                continue
            path = os.path.join(d, name)
            try:
                st = os.stat(path)
                key = (st.st_mtime, st.st_size)
                hit = _META_CACHE.get(path)
                if hit is not None and hit[0] == key:
                    out.append(dict(hit[1]))   # callers may scribble
                    continue
                meta = _read_card(path, st)
                if meta is None:
                    # no card, or a stale one: read the case itself
                    # ONCE and write its card for every open after
                    with open(path, 'r', encoding='utf-8') as fh:
                        head = json.load(fh)
                    meta = head.get('meta', {})
                    _write_card(path, meta)
                meta = dict(meta)
                meta['path'] = path
                _META_CACHE[path] = (key, meta)
                out.append(dict(meta))
            except Exception:
                continue
    out.sort(key=lambda m: -m.get('saved_at', 0))
    return out


# ----------------------------------------------------------- snapshot

def _vec(v):
    return [v.x, v.y, v.z]


def _ref(game, obj, unit_ids):
    """Encode an order target as a stable reference."""
    if obj is None:
        return None
    if obj in unit_ids:
        return {'u': unit_ids[obj]}
    from structures import Airfield, ArmyPost, Harbor
    from game import Bridge
    if isinstance(obj, Airfield):
        return {'a': obj.name}
    if isinstance(obj, Harbor):
        return {'h': obj.name}
    if isinstance(obj, ArmyPost):
        return {'ap': obj.name}
    if isinstance(obj, Bridge):
        try:
            return {'b': game.bridges.index(obj)}
        except ValueError:
            return None
    if obj in getattr(game, 'road_sections', ()):
        return {'rs': game.road_sections.index(obj)}
    for c in game.cities:
        if obj is c:
            return {'c': c.name}
    return None


def _order(game, o, unit_ids):
    if not isinstance(o, dict):
        return None
    out = {'kind': o.get('kind')}
    if 'goal' in o and o['goal'] is not None:
        out['goal'] = _vec(o['goal'])
    if 'site' in o and o['site'] is not None:
        out['site'] = _vec(o['site'])
    if 'from' in o and o['from'] is not None:
        out['from'] = _vec(o['from'])
    if 'points' in o and o['points']:
        out['points'] = [_vec(p) for p in o['points']]
    if 't' in o:
        out['t'] = o['t']
    if 'what' in o:
        out['what'] = o['what']
    if 'cost' in o:
        out['cost'] = o['cost']     # refunded if the work is struck
    if 'target' in o:
        r = _ref(game, o['target'], unit_ids)
        if r is None:
            return None      # target gone or unencodable: drop order
        out['target'] = r
    return out


def snapshot(game):
    """The campaign as a plain dict."""
    units = [u for u in game.units if u.alive]
    unit_ids = {u: i for i, u in enumerate(units)}

    def uref(u):
        return unit_ids.get(u) if u is not None else None

    u_rows = []
    for u in units:
        row = {
            'type': u.unit_type, 'country': u.country,
            'station': bool(getattr(u, 'is_supply_station', False)),
            'pos': _vec(u.pos), 'hp': u.hp, 'supply': u.supply,
            'flown': getattr(u, '_flown', 0.0),
        }
        if getattr(u, 'submerged', False):
            row['submerged'] = True
        if getattr(u, 'deployed', False):
            row['deployed'] = True
        if u.path:
            row['path'] = [[_vec(p), m] for (p, m) in u.path]
        if u.cargo:
            row['cargo'] = [uref(c) for c in u.cargo if c.alive]
        if u.based_at is not None:
            r = _ref(game, u.based_at, unit_ids)
            if r:
                row['based_at'] = r
        if getattr(u, 'landing_at', None) is not None:
            r = _ref(game, u.landing_at, unit_ids)
            if r:
                row['landing_at'] = r
        if getattr(u, 'drop_at', None) is not None:
            row['drop_at'] = _vec(u.drop_at)
        if u.attack_target is not None and \
                getattr(u.attack_target, 'alive', False):
            r = _ref(game, u.attack_target, unit_ids)
            if r:
                row['attack_target'] = r
        if getattr(u, 'sortie_targets', None):
            refs = [_ref(game, t, unit_ids) for t in u.sortie_targets
                    if getattr(t, 'alive', False)]
            row['sortie_targets'] = [r for r in refs if r]
        if getattr(u, 'sortie_plan', None):
            plan = [_order(game, o, unit_ids) for o in u.sortie_plan]
            row['sortie_plan'] = [o for o in plan if o]
        if u.current_order:
            row['order'] = _order(game, u.current_order, unit_ids)
        if u.order_queue:
            q = [_order(game, o, unit_ids) for o in u.order_queue]
            row['queue'] = [o for o in q if o]
        u_rows.append(row)

    # units stored INSIDE airfields (the land garrison)
    garrisons = {}
    for f in game.airfields:
        ids = [uref(u) for u in getattr(f, 'garrison', ())
               if u.alive and u in unit_ids]
        if ids:
            garrisons[f.name] = ids

    data = {
        'version': SAVE_VERSION,
        'meta': {
            'nation': game.player_country,
            'campaign_date': game.campaign_date_text(),
            'saved_at': time.time(),
            'cities': sum(1 for c in game.cities
                          if c.country == game.player_country),
            'forces': sum(1 for u in units
                          if u.country == game.player_country),
        },
        'clock': {
            'minutes': game.clock_minutes,
            'sun': game.sun_angle,
            'fortnight_start': game.fortnight_start,
            'speed': game.game_speed,
        },
        'camera': [game.cam_lat, game.cam_lon, game.cam_dist],
        'player': game.player_country,
        'eliminated': sorted(game.eliminated),
        'kills': game.kills, 'losses': game.losses,
        'stats_ledger': dict(game.stats_ledger),
        'funds': dict(game.funds),
        'resources': {c: dict(r) for c, r in game.resources.items()},
        'trade': [dict(t) for t in game.trade_deals],
        'rights': [dict(r) for r in getattr(game, 'rights', [])],
        'research_points': dict(game.research_points),
        'researched': {c: sorted(s) for c, s in game.researched.items()},
        'research_pct': dict(game.research_pct),
        'budget_counts': dict(game.budget_counts),
        'fortnight_delivered': dict(getattr(game,
                                            'fortnight_delivered', {})),
        'wars': [sorted(w) for w in game.wars],
        'alliances': {c: sorted(s) for c, s in game.alliances.items()
                      if s},
        'pouches': [dict(p) for p in game.pouches],
        'news_queue': [dict(n) for n in game.news_queue],
        'ai_war_ok': {c: ai.war_ok_minutes
                      for c, ai in game._nation_ais.items()},
        'cities': [{
            'name': c.name, 'country': c.country,
            'annexing': bool(c.annexing), 'tax': c.tax_rate,
            'pending_tax': c.pending_tax, 'industry': c.industry,
            'draft': getattr(c, 'draft_pool', 0),
            'focus': getattr(c, 'focus', 'finance'),
            'agri': getattr(c, 'agri_level', 0),
            'works': getattr(c, 'works_level', 0),
            'labs': getattr(c, 'labs_level', 0),
            'production': [[t, s] for (t, s) in c.production],
        } for c in game.cities],
        'airfields': [{
            'name': f.name, 'country': f.country,
            'lat': f.lat, 'lon': f.lon,
            'stock': getattr(f, 'stock', 0.0),
            'production': [[t, s] for (t, s) in f.production],
            'built': f.city is None,
            'base': getattr(f, 'is_base', False),
            'city': f.city.name if f.city is not None else None,
        } for f in game.airfields],
        'harbors': [{
            'name': h.name, 'country': h.country,
            'lat': h.lat, 'lon': h.lon,
            'stock': getattr(h, 'stock', 0.0),
            'production': [[t, s] for (t, s) in h.production],
            'built': h.city is None,
            'base': getattr(h, 'is_base', False),
            'city': h.city.name if h.city is not None else None,
        } for h in game.harbors],
        'armyposts': [{
            'name': p.name, 'country': p.country,
            'lat': p.lat, 'lon': p.lon,
            'stock': p.stock,
            'city': p.city.name if p.city is not None else None,
            'production': [[t, s] for (t, s) in p.production],
        } for p in game.armyposts],
        'depots': [{'name': d.name, 'country': d.country,
                    'lat': d.lat, 'lon': d.lon, 'stock': d.stock}
                   for d in game.depots],
        'bunkers': [{'name': b.name, 'country': b.country,
                     'lat': b.lat, 'lon': b.lon}
                    for b in game.bunkers],
        'radars': [{'name': r.name, 'country': r.country,
                    'lat': r.lat, 'lon': r.lon}
                   for r in game.radars],
        'bridges': [{'alive': b.alive, 'hp': b.hp,
                     'lat': b.lat, 'lon': b.lon}
                    for b in game.bridges],
        'custom_roads': [
            [[la, lo] for (la, lo) in curve]
            for curve in getattr(game.world, 'custom_road_paths', [])],
        'custom_rails': [
            [[la, lo] for (la, lo) in curve]
            for curve in getattr(game.world, 'custom_rail_paths', [])],
        'road_sections': [[s.alive, s.hp]
                          for s in getattr(game, 'road_sections', [])],
        'units': u_rows,
        'garrisons': garrisons,
        'groups': {str(k): [uref(u) for u in v if u.alive
                            and u in unit_ids]
                   for k, v in game.groups.items() if v},
    }
    return data


def write_save(game, name=None, path=None):
    """File the campaign. With PATH given the case is written back
    over itself (a resumed campaign keeps one file instead of
    breeding a copy per save); the write is atomic either way, so a
    crash mid-save cannot eat the previous state."""
    data = snapshot(game)
    if path and os.path.isdir(os.path.dirname(path) or '.'):
        try:                            # the case must be writable
            with open(path, 'a', encoding='utf-8'):
                pass
        except OSError:
            path = None
    else:
        path = None
    if not path:
        stamp = time.strftime('%Y%m%d-%H%M%S')
        fname = (name or 'save') + '-' + stamp + '.json'
        path = os.path.join(save_dir(), fname)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(data, fh)
    os.replace(tmp, path)
    forget_save(path)
    _write_card(path, data.get('meta', {}))
    return path


def delete_save(path):
    """Burn one filed campaign. Returns True when the drawer is
    actually clear of it."""
    forget_save(path)
    try:
        os.remove(_card_path(path))
    except OSError:
        pass
    try:
        os.remove(path)
        return True
    except OSError:
        return not os.path.exists(path)


# ------------------------------------------------------------ restore

def _v3(a):
    return Vec3(a[0], a[1], a[2])


class _Resolver:
    def __init__(self, game, units):
        self.g = game
        self.units = units

    def ref(self, r):
        if r is None:
            return None
        g = self.g
        if 'u' in r:
            i = r['u']
            return self.units[i] if (i is not None
                                     and 0 <= i < len(self.units)) \
                else None
        if 'a' in r:
            return next((a for a in g.airfields
                         if a.name == r['a']), None)
        if 'h' in r:
            return next((h for h in g.harbors
                         if h.name == r['h']), None)
        if 'ap' in r:
            return next((p_ for p_ in g.armyposts
                         if p_.name == r['ap']), None)
        if 'b' in r:
            i = r['b']
            return g.bridges[i] if 0 <= i < len(g.bridges) else None
        if 'rs' in r:
            i = r['rs']
            secs = getattr(g, 'road_sections', [])
            return secs[i] if 0 <= i < len(secs) else None
        if 'c' in r:
            return next((c for c in g.cities
                         if c.name == r['c']), None)
        return None

    def order(self, o):
        if not o:
            return None
        out = {'kind': o.get('kind')}
        if 'goal' in o:
            out['goal'] = _v3(o['goal'])
        if 'site' in o:
            out['site'] = _v3(o['site'])
        if 'from' in o:
            out['from'] = _v3(o['from'])
        if 'points' in o:
            out['points'] = [_v3(p) for p in o['points']]
        if 't' in o:
            out['t'] = o['t']
        if 'what' in o:
            out['what'] = o['what']
        if 'cost' in o:
            out['cost'] = o['cost']
        if 'target' in o:
            tgt = self.ref(o['target'])
            if tgt is None or not getattr(tgt, 'alive', True):
                return None
            out['target'] = tgt
        return out


def restore(game, data):
    """Apply a snapshot to a freshly built (but unpopulated) world.
    Called from start_game once the map, structures-from-data and UI
    exist; the game is quiet (no faxes) throughout."""
    from structures import (Airfield, ArmyPost, Harbor, Depot,
                            Bunker, Radar)
    from units import stats_for
    from game import Bridge
    from units import Unit
    from utils import latlon_to_vec

    g = game
    g._loading_save = True
    try:
        # ---- clock, economy, war ----
        g.clock_minutes = data['clock']['minutes']
        g.sun_angle = data['clock']['sun']
        g.fortnight_start = data['clock']['fortnight_start']
        g.game_speed = data['clock'].get('speed', 1.0)
        g.cam_lat = g.cam_lat_target = data['camera'][0]
        g.cam_lon = g.cam_lon_target = data['camera'][1]
        g.cam_dist = g.cam_dist_target = data['camera'][2]
        g.eliminated = set(data['eliminated'])
        g.kills = data['kills']
        g.losses = data['losses']
        g.stats_ledger = dict(data['stats_ledger'])
        g.funds.update(data['funds'])
        for c, r in data.get('resources', {}).items():
            if c in g.resources:
                g.resources[c].update(r)
        g.trade_deals = [dict(t) for t in data.get('trade', [])]
        g.rights = [dict(r) for r in data.get('rights', [])]
        g.research_points.update(data['research_points'])
        for c, lst in data['researched'].items():
            g.researched[c] = set(lst)
        g.research_pct.update(data['research_pct'])
        g.budget_counts = dict(data['budget_counts'])
        g.fortnight_delivered = dict(data['fortnight_delivered'])
        g.wars = {frozenset(w) for w in data['wars']}
        g._rebuild_war_sets()
        for c in g.alliances:
            g.alliances[c] = set()
        for c, lst in data['alliances'].items():
            g.alliances[c] = set(lst)
        g.pouches = [dict(p) for p in data['pouches']]
        g.news_queue = [dict(n) for n in data['news_queue']]
        for c, t in data['ai_war_ok'].items():
            if c in g._nation_ais:
                g._nation_ais[c].war_ok_minutes = t

        # ---- cities ----
        by_name = {c.name: c for c in g.cities}
        for row in data['cities']:
            c = by_name.get(row['name'])
            if c is None:
                continue
            c.country = row['country']
            c.annexing = row['annexing']
            c.tax_rate = row['tax']
            c.pending_tax = row['pending_tax']
            c.industry = row['industry']
            c.draft_pool = row.get('draft', c.draft_rate())
            # the focus vocabulary moved with the Municipal Ledger:
            # an old save's 'steel' town now EXPANDS THE WORKS. An
            # unrecognized focus silently no-ops forever in
            # _apply_city_focus, so normalize HERE, the only door.
            focus = row.get('focus', 'finance')
            c.focus = {'steel': 'works'}.get(focus, focus)
            # a breadbasket keeps its birthright: old saves predate
            # the pre-levelled farm belts, so take the better of
            # the saved level and the seed
            c.agri_level = max(row.get('agri', 0), c.agri_level)
            c.works_level = row.get('works', 0)
            c.labs_level = row.get('labs', 0)
            c.production = [[t, s] for (t, s) in row['production']]
            c.refresh_marker()
        # deposits follow their city's flag
        for dep in getattr(g, 'deposits', ()):
            if dep.country != dep.city.country:
                dep.country = dep.city.country
                dep.refresh_marker()

        # ---- structures ----
        towns = {c.name: c for c in g.cities}

        def sync_yards(rows, fleet, ctor):
            have = {s.name: s for s in fleet}
            for row in rows:
                s = have.get(row['name'])
                if s is None:
                    # engineer-built works and city-founded bases
                    # alike are reconstructed from the record
                    s = ctor(row, towns.get(row.get('city')))
                    fleet.append(s)
                s.country = row['country']
                if hasattr(s, 'stock'):
                    s.stock = row.get('stock', 0.0)
                s.production = [[t, sec] for (t, sec)
                                in row['production']]
                for ut in row.get('shells', []):
                    # pre-1.3.0 save: warehoused shells are written
                    # off at cost -- the crew system is gone
                    game.funds[s.country] += \
                        stats_for(ut, s.country)['cost']
                game._refresh_station_badge(s)
                s.refresh_marker()

        # an early-1.3.0 save had no 'base' flag: a city link
        # meant a producing base then
        sync_yards(data['airfields'], g.airfields,
                   lambda r, c: Airfield(
                       g, r['lat'], r['lon'], r['country'],
                       r['name'], city=c,
                       is_base=r.get('base', c is not None)))
        sync_yards(data['harbors'], g.harbors,
                   lambda r, c: Harbor(
                       g, r['lat'], r['lon'], r['country'],
                       r['name'], city=c,
                       is_base=r.get('base', c is not None)))
        posts = {p_.name: p_ for p_ in g.armyposts}
        for row in data.get('armyposts', []):
            p_ = posts.get(row['name'])
            if p_ is None and 'lat' in row:
                p_ = ArmyPost(g, row['lat'], row['lon'],
                              row['country'], row['name'],
                              city=towns.get(row.get('city')))
                g.armyposts.append(p_)
            if p_ is None:
                continue
            p_.country = row['country']
            p_.stock = row['stock']
            for ut in row.get('shells', []):
                g.funds[p_.country] += stats_for(ut, p_.country)['cost']
            p_.production = [[t, sec] for (t, sec)
                             in row['production']]
            g._refresh_station_badge(p_)
            p_.refresh_marker()
        for row in data['depots']:
            d = Depot(g, row['lat'], row['lon'], row['country'],
                      row['name'])
            d.stock = row['stock']
            g.depots.append(d)
        for row in data['bunkers']:
            g.bunkers.append(Bunker(g, row['lat'], row['lon'],
                                    row['country'], row['name']))
        for row in data['radars']:
            g.radars.append(Radar(g, row['lat'], row['lon'],
                                  row['country'], row['name']))

        # engineer bridges beyond the map's own, then bridge states
        base_n = len(g.bridges)
        for i, row in enumerate(data['bridges']):
            if i >= base_n:
                g.bridges.append(Bridge(
                    g, {'lat': row['lat'], 'lon': row['lon'],
                        'road': (-1, -1)}, len(g.bridges)))
        for b, row in zip(g.bridges, data['bridges']):
            b.hp = row['hp']
            if not row['alive'] and b.alive:
                b.alive = False
                b.marker.setColorScale(0.35, 0.28, 0.25, 0.9)
        g.planner.notify_bridge_change()

        # ---- custom roads, overlay, cuts ----
        for curve in data['custom_roads']:
            pts = [(la, lo) for (la, lo) in curve]
            poly = [latlon_to_vec(la, lo) for (la, lo) in pts]
            g.planner.add_custom_road(poly)
            if not hasattr(g.world, 'custom_road_paths'):
                g.world.custom_road_paths = []
            g.world.custom_road_paths.append(pts)
        for curve in data.get('custom_rails', []):
            pts = [(la, lo) for (la, lo) in curve]
            poly = [latlon_to_vec(la, lo) for (la, lo) in pts]
            g.planner.add_custom_road(poly, rail=True)
            if not hasattr(g.world, 'custom_rail_paths'):
                g.world.custom_rail_paths = []
            g.world.custom_rail_paths.append(pts)
        g._build_road_overlay()
        secs = getattr(g, 'road_sections', [])
        for sec, (alive, hp) in zip(secs, data['road_sections']):
            sec.hp = hp
            if not alive and sec.alive:
                g._cut_road_section(sec)

        # ---- units: build, then resolve ----
        res = _Resolver(g, [])
        units = []
        for row in data['units']:
            u = Unit(g, row['type'], row['country'], _v3(row['pos']))
            u.hp = row['hp']
            if row.get('station'):
                u.is_supply_station = True
                from game import _ShipCache
                u._cache_face = _ShipCache(u)
                from models import _icon_texture
                u.counter.setTexture(_icon_texture(
                    g.loader, 'supply_station', 'unit', u.country))
            u.supply = row['supply']
            u._flown = row.get('flown', 0.0)
            g.units.append(u)
            units.append(u)
            if u.country != g.player_country:
                u.decals.hide()
                u.root.hide()
        res.units = units
        for u, row in zip(units, data['units']):
            if row.get('submerged'):
                g.set_submerged(u, True, forced=True)
            if row.get('deployed'):
                g.toggle_blimp(u)
            if 'path' in row:
                u.path = [(_v3(p), m) for (p, m) in row['path']]
            if 'based_at' in row:
                base = res.ref(row['based_at'])
                if base is not None:
                    u.based_at = base
                    u.pos = Vec3(base.pos) if not isinstance(base, Unit) \
                        else u.pos
                    u.root.hide()
            if 'landing_at' in row:
                u.landing_at = res.ref(row['landing_at'])
            if 'drop_at' in row:
                u.drop_at = _v3(row['drop_at'])
            if 'cargo' in row:
                for ci in row['cargo']:
                    c = res.units[ci] if (ci is not None
                                          and ci < len(res.units)) \
                        else None
                    if c is not None:
                        c.carried_by = u
                        c.root.hide()
                        u.cargo.append(c)
            if 'attack_target' in row:
                u.attack_target = res.ref(row['attack_target'])
            if 'sortie_targets' in row:
                u.sortie_targets = [t for t in
                                    (res.ref(r) for r
                                     in row['sortie_targets'])
                                    if t is not None]
            if 'sortie_plan' in row:
                plan = [res.order(o) for o in row['sortie_plan']]
                u.sortie_plan = [o for o in plan if o]
            if 'order' in row:
                o = res.order(row['order'])
                if o is not None:
                    u.current_order = o
            if 'queue' in row:
                q = [res.order(o) for o in row['queue']]
                u.order_queue = [o for o in q if o]
            u.update_visual()

        # amber ghosts take station again on every planned work (the
        # ghost list is keyed by ORDER IDENTITY, so the very dicts
        # just restored onto the engineers go into the entries; road
        # legs draw their survey viz from the orders instead)
        from globe import orient_to_surface
        for u in units:
            held = ([u.current_order] if u.current_order else []) \
                + list(u.order_queue)
            for o in held:
                if (isinstance(o, dict) and o.get('kind') == 'build'
                        and o.get('what')
                        and o['what'] not in ('road', 'rail')
                        and o.get('site') is not None):
                    np_ = g._make_ghost_np(
                        o['what'], (0.95, 0.82, 0.42, 0.55))
                    site_n = Vec3(o['site'])
                    site_n.normalize()
                    orient_to_surface(np_, site_n)
                    g._works_ghosts.append((u, o, np_))

        # the land garrisons stored inside airfields
        for fname, ids in data['garrisons'].items():
            f = next((a for a in g.airfields if a.name == fname), None)
            if f is None:
                continue
            for i in ids:
                if i is None or i >= len(units):
                    continue
                u = units[i]
                u.carried_by = f
                u.clear_orders()
                u.root.hide()
                f.garrison.append(u)
            if hasattr(f, 'set_garrison_count'):
                f.set_garrison_count(len(f.garrison))

        # control groups
        g.groups = {}
        for k, ids in data['groups'].items():
            members = [units[i] for i in ids
                       if i is not None and i < len(units)]
            if members:
                g.groups[int(k)] = members

        # parked wings show the right badge counts
        for f in g.airfields:
            g._refresh_air_base(f)
    finally:
        g._loading_save = False
