"""
Ground structures: airfields, supply depots, bunkers.

All are flat map markers like everything else.  Airfields hold parked
aircraft and an aviation-supply stock; depots buffer supplies for the
truck network; bunkers shelter infantry from bombs and shore guns.
"""

from panda3d.core import TextNode, Vec3

from config import COUNTRIES, GLOBE_RADIUS, LIFT_GROUND
from globe import orient_to_surface
from models import (make_flat_disc, make_flat_ring, make_icon_quad,
                    set_marker_layer, LAYER_STRUCT)
from utils import latlon_to_vec

AIRFIELD_STOCK_CAP = 6000.0     # lbs of aviation supply
AIRFIELD_HP = 260.0             # demolishable, like bridges
DEPOT_STOCK_CAP = 20000.0
BUNKER_RADIUS = 0.2             # infantry sheltered within this range
SORTIE_COST = 600.0             # lbs per aircraft takeoff


class Structure:
    """Base: a flat icon marker on the surface, owned by a faction."""

    ICON = 'depot'
    SEL_RING = 1.6

    def __init__(self, game, lat, lon, country, name):
        self.game = game
        self.lat, self.lon = lat, lon
        self.pos = latlon_to_vec(lat, lon)
        self.country = country
        self.name = name
        self.alive = True

        self.root = game.render.attachNewNode('struct_' + name)
        orient_to_surface(self.root, self.pos)
        self.holder = self.root.attachNewNode('holder')
        self.holder.setPos(0, 0, GLOBE_RADIUS * LIFT_GROUND)
        self.marker = None
        self.sel_ring = make_flat_ring('ssel', self.SEL_RING,
                                       (1.0, 0.9, 0.3, 0.95),
                                       thickness=2.0, segments=28)
        self.sel_ring.reparentTo(self.holder)
        set_marker_layer(self.sel_ring, LAYER_STRUCT + 3)
        self.sel_ring.hide()
        self.refresh_marker()

    def refresh_marker(self):
        if self.marker:
            self.marker.removeNode()
        c = COUNTRIES[self.country]['color']
        self.marker = make_icon_quad(self.game.loader, self.ICON, 'dark',
                                     half=1.05, depth=5)
        self.marker.setColorScale(c[0], c[1], c[2], 1.0)
        self.marker.reparentTo(self.holder)
        self.marker.setLightOff()
        set_marker_layer(self.marker, LAYER_STRUCT)

    def set_marker_scale(self, scale):
        self.holder.setScale(scale)

    def cleanup(self):
        self.root.removeNode()


class Airfield(Structure):
    """Aircraft park here (hidden); sorties draw on the supply stock."""

    ICON = 'airfield'

    def __init__(self, game, lat, lon, country, name, city=None):
        self.city = city                # linked city, if beside one
        self.stock = AIRFIELD_STOCK_CAP
        self.hp = AIRFIELD_HP
        self.max_hp = AIRFIELD_HP
        Structure.__init__(self, game, lat, lon, country, name)

        # parked-aircraft badge (plane pictogram + count)
        c = COUNTRIES[country]['color']
        self.badge = self.holder.attachNewNode('air_badge')
        pill = make_flat_disc('pill', 0.46, (c[0], c[1], c[2], 0.96),
                              segments=20)
        pill.setPos(0, -1.45, 0)
        pill.reparentTo(self.badge)
        rim = make_flat_ring('rim', 0.46, (0.13, 0.11, 0.09, 1.0),
                             thickness=1.6, segments=20)
        rim.setPos(0, -1.45, 0)
        rim.reparentTo(self.badge)
        plane = make_icon_quad(game.loader, 'fighter', 'dark', half=0.30,
                               depth=8)
        plane.setPos(-0.14, -1.45, 0)
        plane.reparentTo(self.badge)
        tn = TextNode('count')
        tn.setAlign(TextNode.ALeft)
        if game.hud_font:
            tn.setFont(game.hud_font)
        tn.setTextColor(0.13, 0.11, 0.09, 1)
        self.count_tn = tn
        np_ = self.badge.attachNewNode(tn)
        np_.setP(-90)
        np_.setScale(0.5)
        np_.setPos(0.10, -1.62, 0)
        np_.setDepthOffset(8)
        set_marker_layer(self.badge, LAYER_STRUCT + 2)
        self.badge.hide()

    def set_count(self, n):
        if n > 0:
            self.count_tn.setText("x%d" % n)
            if self.badge.isHidden():
                self.badge.show()
        elif not self.badge.isHidden():
            self.badge.hide()

    def take_damage(self, amount, attacker=None):
        if not self.alive:
            return
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0.0
            self.alive = False
            self.game.on_airfield_destroyed(self, attacker)


class Depot(Structure):
    """Supply cache: trucks deliver to and draw from it."""

    ICON = 'depot'

    def __init__(self, game, lat, lon, country, name):
        self.stock = 0.0
        Structure.__init__(self, game, lat, lon, country, name)


class Bunker(Structure):
    """Infantry within BUNKER_RADIUS take a third of the damage from
    bombs and naval shellfire."""

    ICON = 'bunker'
