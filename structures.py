"""
Ground structures: airfields, supply depots, bunkers.

All are flat map markers like everything else.  Airfields hold parked
aircraft and an aviation-supply stock; depots buffer supplies for the
truck network; bunkers shelter infantry from bombs and shore guns.
"""

from panda3d.core import TextNode, Vec3

from config import COUNTRIES, GLOBE_RADIUS, LIFT_GROUND
from globe import orient_to_surface
from models import (make_flat_disc, make_flat_ring, make_flag_quad,
                    make_icon_quad, set_marker_layer, LAYER_STRUCT)
from utils import latlon_to_vec

AIRFIELD_STOCK_CAP = 6000.0     # lbs of aviation supply
AIRFIELD_HP = 260.0             # demolishable, like bridges
DEPOT_STOCK_CAP = 20000.0
HARBOR_STOCK_CAP = 24000.0
BUNKER_RADIUS = 0.2             # infantry sheltered within this range
BUNKER_HP = 220.0               # field works take a pounding first
SORTIE_COST = 600.0             # lbs per aircraft takeoff


class Structure:
    """Base: an icon marker on the surface, owned by a faction. The
    pictogram is a BILLBOARD at a fixed world size: it faces the camera
    and never rescales with zoom."""

    ICON = 'depot'
    SEL_RING = 1.6
    FIXED_SCALE = 0.06          # world size, constant across zoom
    ICON_ROLL = 0.0             # per-instance roll, set by subclasses

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
        self.holder.setScale(self.FIXED_SCALE)
        # billboard carrier: only the pictogram turns to the camera; the
        # selection ring and badges stay flat on the map
        self.bb = self.holder.attachNewNode('bb')
        self.bb.setBillboardPointEye()
        self.marker = None
        self.flag = None
        self.sel_ring = make_flat_ring('ssel', self.SEL_RING,
                                       (1.0, 0.9, 0.3, 0.95),
                                       thickness=2.0, segments=28)
        self.sel_ring.reparentTo(self.holder)
        set_marker_layer(self.sel_ring, LAYER_STRUCT + 3)
        self.sel_ring.hide()
        self.refresh_marker()

    TINT = 0.0                  # every nation's works wear the same
                                # ink; ownership flies on the standard

    def refresh_marker(self):
        if self.marker:
            self.marker.removeNode()
        if getattr(self, 'flag', None):
            self.flag.removeNode()
            self.flag = None
        c = COUNTRIES[self.country]['color'] if self.country else \
            (1.0, 1.0, 1.0)
        self.marker = make_icon_quad(self.game.loader, self.ICON, 'dark',
                                     half=1.05, depth=5, flat=False)
        t = self.TINT
        self.marker.setColorScale(1 - t + t * c[0], 1 - t + t * c[1],
                                  1 - t + t * c[2], 1.0)
        self.marker.setR(self.ICON_ROLL)
        self.marker.reparentTo(self.bb)
        self.marker.setLightOff()
        set_marker_layer(self.marker, LAYER_STRUCT)
        # FOREIGN works fly their nation's standard above the mark --
        # rebuilt here, so a capture re-hoists the new colours
        if (self.country and self.country != 'neutral'
                and self.country != self.game.player_country):
            self.flag = make_flag_quad(self.game.loader, self.country,
                                       half=0.44, flat=False)
            self.flag.setPos(0, 0, 1.55)
            self.flag.reparentTo(self.bb)
            self.flag.setLightOff()
            set_marker_layer(self.flag, LAYER_STRUCT + 2)

    def set_marker_scale(self, scale):
        pass                    # structures keep their fixed size

    def cleanup(self):
        self.root.removeNode()


class Airfield(Structure):
    """Aircraft park here (hidden); sorties draw on the supply stock."""

    ICON = 'airfield'
    FIXED_SCALE = 0.034         # an aerodrome reads bigger than a depot
    TINT = 0.0                  # drawn in the city-sketch palette, like
                                # the towns; owner shows in the badge

    def __init__(self, game, lat, lon, country, name, city=None):
        self.city = city                # linked city, if beside one
        self.stock = AIRFIELD_STOCK_CAP
        self.hp = AIRFIELD_HP
        self.max_hp = AIRFIELD_HP
        self.production = []            # wings on the line: [type, time]
        self.garrison = []              # land units stored on the field
        self.shells = []                # finished airframes, no crews
        self.crews = 0                  # Enlisted stationed here
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

        # second pill: the LAND GARRISON stored on the field
        self.gbadge = self.holder.attachNewNode('garrison_badge')
        gp = make_flat_disc('gpill', 0.46, (c[0], c[1], c[2], 0.96),
                            segments=20)
        gp.setPos(0, -2.45, 0)
        gp.reparentTo(self.gbadge)
        grim = make_flat_ring('grim', 0.46, (0.13, 0.11, 0.09, 1.0),
                              thickness=1.6, segments=20)
        grim.setPos(0, -2.45, 0)
        grim.reparentTo(self.gbadge)
        foot = make_icon_quad(game.loader, 'infantry', 'dark',
                              half=0.30, depth=8)
        foot.setPos(-0.14, -2.45, 0)
        foot.reparentTo(self.gbadge)
        gtn = TextNode('gcount')
        gtn.setAlign(TextNode.ALeft)
        if game.hud_font:
            gtn.setFont(game.hud_font)
        gtn.setTextColor(0.13, 0.11, 0.09, 1)
        self.gcount_tn = gtn
        gnp = self.gbadge.attachNewNode(gtn)
        gnp.setP(-90)
        gnp.setScale(0.5)
        gnp.setPos(0.10, -2.62, 0)
        gnp.setDepthOffset(8)
        set_marker_layer(self.gbadge, LAYER_STRUCT + 2)
        self.gbadge.hide()

    def set_count(self, n):
        if n > 0:
            self.count_tn.setText("x%d" % n)
            if self.badge.isHidden():
                self.badge.show()
        elif not self.badge.isHidden():
            self.badge.hide()

    def set_garrison_count(self, n):
        if n > 0:
            self.gcount_tn.setText("x%d" % n)
            if self.gbadge.isHidden():
                self.gbadge.show()
        elif not self.gbadge.isHidden():
            self.gbadge.hide()

    def take_damage(self, amount, attacker=None):
        if not self.alive:
            return
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0.0
            self.alive = False
            self.game.on_airfield_destroyed(self, attacker)


class Harbor(Structure):
    """Fleet yard on the water. New hulls take the water the moment
    they are finished, anchoring at some scatter off the yard."""

    ICON = 'harbor'
    FIXED_SCALE = 0.045
    TINT = 0.0                  # city-sketch palette, like the towns

    STOCK_CAP = HARBOR_STOCK_CAP

    def __init__(self, game, lat, lon, country, name, city=None):
        self.city = city
        self.production = []            # hulls on the ways: [type, time]
        self.shells = []                # finished hulls awaiting crews
        self.crews = 0                  # Enlisted stationed at the quay
        self.stock = 0.0                # the quayside supply cache
        Structure.__init__(self, game, lat, lon, country, name)

        # ways badge (ship pictogram + count of hulls building)
        c = COUNTRIES[country]['color']
        self.badge = self.holder.attachNewNode('hull_badge')
        pill = make_flat_disc('pill', 0.46, (c[0], c[1], c[2], 0.96),
                              segments=20)
        pill.setPos(0, -1.45, 0)
        pill.reparentTo(self.badge)
        rim = make_flat_ring('rim', 0.46, (0.13, 0.11, 0.09, 1.0),
                             thickness=1.6, segments=20)
        rim.setPos(0, -1.45, 0)
        rim.reparentTo(self.badge)
        ship = make_icon_quad(game.loader, 'destroyer_sea_sea', 'dark',
                              half=0.30, depth=8)
        ship.setPos(-0.14, -1.45, 0)
        ship.reparentTo(self.badge)
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


class Depot(Structure):
    """Supply cache: trucks deliver to and draw from it."""

    ICON = 'depot'
    FIXED_SCALE = 0.03          # half the standard structure footprint
    STOCK_CAP = DEPOT_STOCK_CAP

    def __init__(self, game, lat, lon, country, name):
        self.stock = 0.0
        Structure.__init__(self, game, lat, lon, country, name)


class ArmyPost(Structure):
    """The army's harbor: land vehicles arrive here as empty shells
    and wait for Enlisted crews to march in and take them out. Also
    a quayside-sized supply cache for the trucks."""

    ICON = 'army_post'
    FIXED_SCALE = 0.045
    TINT = 0.0                  # city-sketch palette, like the towns
    STOCK_CAP = 20000.0

    def __init__(self, game, lat, lon, country, name, city=None):
        self.city = city
        self.production = []            # vehicles building: [type, s]
        self.shells = []                # finished, waiting for crews
        self.crews = 0                  # Enlisted stationed here
        self.stock = 0.0
        Structure.__init__(self, game, lat, lon, country, name)
        c = COUNTRIES[country]['color']
        self.badge = self.holder.attachNewNode('shell_badge')
        pill = make_flat_disc('pill', 0.46, (c[0], c[1], c[2], 0.96),
                              segments=20)
        pill.setPos(0, -1.45, 0)
        pill.reparentTo(self.badge)
        rim = make_flat_ring('rim', 0.46, (0.13, 0.11, 0.09, 1.0),
                             thickness=1.6, segments=20)
        rim.setPos(0, -1.45, 0)
        rim.reparentTo(self.badge)
        veh = make_icon_quad(game.loader, 'tank', 'dark',
                             half=0.30, depth=8)
        veh.setPos(-0.14, -1.45, 0)
        veh.reparentTo(self.badge)
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


class Bunker(Structure):
    """Infantry within BUNKER_RADIUS take a third of the damage from
    bombs and naval shellfire."""

    ICON = 'bunker'
    FIXED_SCALE = 0.042         # reads smaller than a depot

    def __init__(self, game, lat, lon, country, name):
        self.hp = BUNKER_HP
        self.max_hp = BUNKER_HP
        Structure.__init__(self, game, lat, lon, country, name)


class Radar(Structure):
    """Research-gated early-warning station: a tall mast that watches
    and relays far beyond any field observer, day and night."""

    ICON = 'radar'
    FIXED_SCALE = 0.040
    TINT = 0.0
