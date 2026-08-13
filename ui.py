"""
In-game UI, WW2 field-headquarters style.

A top bar with the main stats (including units out of W/T contact and
the BUDGET button), a bottom bar with controls and information on the
current selection, and the left and right sides of the screen kept
clear.  Anything that asks the player a question or reports an event
arrives as a FAX from HQ — including the fortnight budget manifest.
"""

import textwrap

from direct.gui.OnscreenImage import OnscreenImage
from direct.gui.DirectGui import DirectButton, DirectFrame, DGG
from panda3d.core import (SamplerState, TextNode, TexturePool,
                          Plane, PlaneNode, Point3, Vec3)

from icons import get_icon_path, sheet_texture, unit_ui_icon


def sheet_tex(kind):
    """A painted sheet as a FILTERED texture. frameTexture= handed a
    path loads it with plain bilinear; the minified sheets (the bar,
    the toast paper, the tooltip plate) then shimmer with grain.
    The pool shares textures by path, so one filtered load covers
    every later user of the same file."""
    tex = TexturePool.loadTexture(sheet_texture(kind))
    tex.setMinfilter(SamplerState.FTLinearMipmapLinear)
    tex.setAnisotropicDegree(8)
    return tex


def flag_tex(country):
    """A nation's standard, filtered, for gui chips. The map's flag
    quads set the same filters on the same pooled textures, but a
    chip drawn before any map exists -- the whole main menu -- was
    getting plain bilinear, order-dependent."""
    from icons import flag_texture
    tex = TexturePool.loadTexture(flag_texture(country))
    tex.setMinfilter(SamplerState.FTLinearMipmapLinear)
    tex.setAnisotropicDegree(8)
    return tex


def crisp_image(widget):
    """UI pictograms are 384 px sources minified onto ~50 px keys:
    DirectGui loads them with plain bilinear sampling, which skips
    texels at that ratio and pixelates the art (the MAP icons set
    mipmaps explicitly and stay clean). Give every texture under a
    gui widget trilinear mipmaps and a touch of anisotropy. Textures
    are shared by path, so one application covers every later user
    of the same file."""
    tc = widget.findAllTextures()
    for i in range(tc.getNumTextures()):
        tex = tc.getTexture(i)
        tex.setMinfilter(SamplerState.FTLinearMipmapLinear)
        tex.setAnisotropicDegree(8)
    return widget

PAPER = (0.91, 0.88, 0.78, 0.97)
PAPER_EDGE = (0.25, 0.22, 0.18, 1.0)
INK = (0.16, 0.13, 0.10, 1.0)
INK_FAINT = (0.35, 0.30, 0.24, 1.0)
BAR_BG = (0.10, 0.10, 0.09, 0.82)
BAR_TEXT = (0.88, 0.85, 0.72, 1.0)
ACCENT = (0.85, 0.72, 0.35, 1.0)
ALERT = (0.9, 0.45, 0.3, 1.0)

BTN_PAPER = ((0.82, 0.78, 0.64, 0.95), (0.95, 0.90, 0.72, 1.0),
             (0.70, 0.66, 0.54, 0.95), (0.5, 0.5, 0.5, 0.6))

# wire shorthand for the diplomatic traffic
NAT_CODE = {
    'britain': 'GBR', 'germany': 'GER', 'usa': 'USA', 'japan': 'JPN',
    'soviet': 'SOV', 'france': 'FRA', 'italy': 'ITA', 'china': 'CHN',
    'poland': 'POL', 'netherlands': 'NED', 'belgium': 'BEL',
    'norway': 'NOR', 'denmark': 'DEN', 'finland': 'FIN',
    'greece': 'GRE', 'yugoslavia': 'YUG', 'romania': 'ROM',
    'hungary': 'HUN', 'bulgaria': 'BUL', 'iraq': 'IRQ', 'iran': 'IRN',
    'siam': 'SIA', 'brit_med': 'EGY', 'raj': 'IND', 'fareast': 'MAL',
    'australia': 'AUS',
}


def _make_text(parent, font, pos, scale, color, align=TextNode.ALeft):
    tn = TextNode('uitext')
    tn.setAlign(align)
    if font:
        tn.setFont(font)
    tn.setTextColor(*color)
    np_ = parent.attachNewNode(tn)
    np_.setPos(pos[0], 0, pos[1])
    np_.setScale(scale)
    return tn, np_


def B(text):
    """Mark a span bold inside FAX signal text (TextProperties 'b')."""
    return "\1b\1%s\2" % text


def pill_button(parent, text, command, extraArgs=(), pos=(0, 0, 0),
                hw=0.14, hh=0.033, text_scale=0.030, text_fg=INK,
                font=None, kind='panel', latched=False, corner=0.42,
                **extra):
    """A physical WW2 console key: rounded, shaded, glows on hover
    and sits down when pressed. The art is painted FOR this button's
    aspect, so the corner curves are true at every size. latched=True
    keeps it pressed in (an engaged toggle)."""
    from icons import button_assets
    imgs, sx, sz = button_assets(kind, hw, hh, corner=corner)
    if latched:
        imgs = (imgs[1],) * 4
    # long labels shrink to stay inside the key instead of spilling
    if isinstance(text, str) and text:
        fit = (2.0 * hw * 0.90) / (0.62 * len(text))
        text_scale = min(text_scale, fit)
    kwargs = dict(parent=parent, text=text, text_scale=text_scale,
                  text_fg=text_fg, text_font=font,
                  text_pos=(0, -text_scale * 0.36),
                  image=imgs,
                  image_scale=(sx, 1, sz),
                  relief=None, frameColor=(0, 0, 0, 0),
                  frameSize=(-hw, hw, -hh, hh),
                  command=command, extraArgs=list(extraArgs), pos=pos)
    kwargs.update(extra)
    b = DirectButton(**kwargs)
    b.setTransparency(True)
    return crisp_image(b)


def add_tooltip(btn, text, font=None, dy=0.085, left=None):
    """A hover slip naming the control: WHITE text on a dark plate
    above the button (or, with left=<button half-width>, off its left
    edge for controls hugging the screen's right side). The slip is
    DEAD to the mouse -- an interactive tooltip near the cursor
    steals the hover and flickers."""
    scale = 0.026
    hw = 0.31 * scale * len(text) + 0.014
    pos = ((-(left + hw + 0.015), 0, 0) if left is not None
           else (0, 0, dy))
    f = DirectFrame(parent=btn, frameColor=(1, 1, 1, 0.96),
                    frameTexture=sheet_tex('plate'),
                    frameSize=(-hw, hw, -0.020, 0.032),
                    relief=DGG.FLAT, state=DGG.DISABLED, pos=pos)
    f.setTransparency(True)
    edge = DirectFrame(parent=f, frameColor=(0.55, 0.48, 0.34, 1.0),
                       frameSize=(-hw - 0.003, hw + 0.003,
                                  -0.023, 0.035), relief=DGG.FLAT,
                       state=DGG.DISABLED)
    edge.setBin('gui-popup', 0)
    f.setBin('gui-popup', 1)
    for w in (f, edge):
        try:
            w.guiItem.setActive(False)
        except Exception:
            pass
    tn = TextNode('tip')
    tn.setAlign(TextNode.ACenter)
    if font:
        tn.setFont(font)
    tn.setTextColor(0.96, 0.94, 0.88, 1.0)
    tn.setText(text)
    np_ = f.attachNewNode(tn)
    np_.setPos(0, 0, -0.008)
    np_.setScale(scale)
    np_.setBin('gui-popup', 2)
    f._tip_tn = tn
    f.hide()
    btn.bind(DGG.WITHIN, lambda e, f=f: f.show())
    btn.bind(DGG.WITHOUT, lambda e, f=f: f.hide())
    btn._tip = f
    return f


class TopBar:
    """Main stats strip: each stat is a titled column, value beneath."""

    COLUMNS = [
        ('NATION', -1.56, TextNode.ALeft),
        ('TREASURY', -1.31, TextNode.ALeft),
        ('OIL', -1.09, TextNode.ALeft),
        ('STEEL', -0.90, TextNode.ALeft),
        ('FOOD', -0.69, TextNode.ALeft),
        ('FORCES', -0.47, TextNode.ALeft),
        ('CITIES', -0.29, TextNode.ALeft),
        ('TIME', 0.10, TextNode.ACenter),
        ('[OUT OF CONTACT]', 0.54, TextNode.ACenter),
        ('KILLS', 0.84, TextNode.ACenter),
        ('LOSSES', 1.02, TextNode.ACenter),
        ('SPEED', 1.20, TextNode.ACenter),
    ]

    RESOURCE_COLS = ('OIL', 'STEEL', 'FOOD')

    def __init__(self, base, on_budget, on_factory=None,
                 on_resources=None, on_tech=None, on_diplomacy=None,
                 on_menu=None):
        self.base = base
        self.frame = DirectFrame(parent=base.a2dTopCenter,
                                 frameColor=(1, 1, 1, 0.92),
                                 frameTexture=sheet_tex('bar'),
                                 frameSize=(-2.0, 2.0, -0.155, 0.0),
                                 state=DGG.NORMAL)
        self.frame.setTransparency(True)
        # EVERY MARK ON THE STRIP hangs from this node, so a window
        # narrower than the layout was drawn for squeezes the whole
        # rank down together instead of walking its right-hand end
        # off the screen (the report keys were doing exactly that)
        self.content = self.frame.attachNewNode('bar_content')
        self.values = {}
        for (title, x, align) in self.COLUMNS:
            head, _ = _make_text(self.content, base.hud_font,
                                 (x, -0.048), 0.024,
                                 (0.55, 0.53, 0.45, 1.0), align)
            head.setText(title)
            color = (ALERT if title == '[OUT OF CONTACT]'
                     else (ACCENT if title == 'TIME' else BAR_TEXT))
            val, _ = _make_text(self.content, base.hud_font,
                                (x, -0.118), 0.040, color, align)
            self.values[title] = val
        self.budget_btn = pill_button(
            self.content, "BUDGET", on_budget, pos=(1.44, 0, -0.068),
            hw=0.155, hh=0.037, text_scale=0.034, font=base.hud_font)
        # war-industries report, beside the budget: a proper console
        # key, not a bare pictogram floating on the panel. The rank
        # of report keys is CENTRED on the strip (the bar spans
        # 0..-0.155) and stands a clear margin off the budget key --
        # flush against it the whole corner read as one squashed lump
        KEY_Z = -0.0775
        self.factory_btn = pill_button(
            self.content, '', on_factory, pos=(1.70, 0, KEY_Z),
            hw=0.048, hh=0.048, corner=0.30, font=base.hud_font)
        pic = OnscreenImage(image=get_icon_path('factory_button',
                                                'dark'),
                            parent=self.factory_btn, scale=0.034,
                            pos=(0, 0, 0))
        pic.setTransparency(True)
        crisp_image(pic)
        add_tooltip(self.factory_btn, "WAR INDUSTRIES -- PRODUCTION "
                    "REPORT", font=base.hud_font, dy=-0.105)
        # the quartermaster's ledger, beside the factory key
        self.resource_btn = pill_button(
            self.content, '', on_resources, pos=(1.81, 0, KEY_Z),
            hw=0.048, hh=0.048, corner=0.30, font=base.hud_font)
        pic = OnscreenImage(image=get_icon_path('resource_button',
                                                'dark'),
                            parent=self.resource_btn, scale=0.034,
                            pos=(0, 0, 0))
        pic.setTransparency(True)
        crisp_image(pic)
        add_tooltip(self.resource_btn, "STRATEGIC RESOURCES -- "
                    "STOCKS AND SUPPLY", font=base.hud_font,
                    dy=-0.105)
        # the research chart, beside the ledger
        self.tech_btn = pill_button(
            self.content, '', on_tech, pos=(1.92, 0, KEY_Z),
            hw=0.048, hh=0.048, corner=0.30, font=base.hud_font)
        pic = OnscreenImage(image=get_icon_path('research_button',
                                                'dark'),
                            parent=self.tech_btn, scale=0.034,
                            pos=(0, 0, 0))
        pic.setTransparency(True)
        crisp_image(pic)
        add_tooltip(self.tech_btn, "THE RESEARCH CHART -- "
                    "PROGRAMMES [R]", font=base.hud_font, dy=-0.105)
        # the Foreign Office ledger, last in the rank (moved up from
        # the right screen edge to sit with its fellow report keys)
        self.diplo_btn = pill_button(
            self.content, '', on_diplomacy, pos=(2.03, 0, KEY_Z),
            hw=0.048, hh=0.048, corner=0.30, font=base.hud_font)
        pic = OnscreenImage(image=get_icon_path('diplomacy_button',
                                                'dark'),
                            parent=self.diplo_btn, scale=0.034,
                            pos=(0, 0, 0))
        pic.setTransparency(True)
        crisp_image(pic)
        add_tooltip(self.diplo_btn, "DIPLOMACY LEDGER -- WARS, "
                    "PACTS AND PEACE", font=base.hud_font, dy=-0.105)
        # the three-bar stack, far LEFT of the strip: the same FIELD
        # ORDERS menu ESC summons, for the hand on the mouse
        self.menu_btn = pill_button(
            self.content, '', on_menu, pos=(-1.72, 0, KEY_Z),
            hw=0.048, hh=0.048, corner=0.30, font=base.hud_font)
        pic = OnscreenImage(image=get_icon_path('menu_button',
                                                'dark'),
                            parent=self.menu_btn, scale=0.034,
                            pos=(0, 0, 0))
        pic.setTransparency(True)
        crisp_image(pic)
        add_tooltip(self.menu_btn, "FIELD ORDERS -- SAVE, RESUME, "
                    "STAND DOWN [ESC]", font=base.hud_font, dy=-0.105)
        # fourteen dots: the days of the running fortnight
        self.day_dots = []
        for i in range(14):
            dot = DirectFrame(parent=self.content,
                              frameColor=(0.32, 0.30, 0.26, 1.0),
                              frameSize=(-0.008, 0.008, -0.008, 0.008),
                              pos=(1.44 - 0.169 + i * 0.026,
                                   0, -0.132))
            self.day_dots.append(dot)
        self._fortnight_day = 0
        # THE RIGHT-HAND CLUSTER RIDES THE SCREEN EDGE. Placed at
        # fixed coordinates it walked off the side of any window
        # narrower than 16:9 -- at 16:10 the factory, resource and
        # research keys all stood past the edge, invisible.
        self._fit_to_screen()
        # Panda names this event aspectRatioChanged -- the
        # hyphenated spelling never fired, so neither bar
        # refitted and the bar drifted off the facsimile
        base.accept('aspectRatioChanged',
                    self._fit_to_screen)
        # the RESOURCE STRIP explains itself on hover: each column
        # carries an invisible plate whose tooltip itemizes the flow
        self.res_tips = {}
        for res, x, _a in self.COLUMNS:
            if res not in self.RESOURCE_COLS:
                continue
            hov = DirectButton(parent=self.content, relief=None,
                              frameColor=(0, 0, 0, 0),
                              frameSize=(-0.02, 0.18, -0.150, -0.02),
                              pos=(x, 0, 0), state=DGG.NORMAL)
            tip = add_tooltip(
                hov, "AWAITING THE FORTNIGHT'S FIRST RETURNS",
                font=base.hud_font, dy=-0.175)
            self.res_tips[res] = tip
        # a red pip on the factory key while any line stands halted
        self.factory_pip = DirectFrame(
            parent=self.factory_btn, relief=DGG.FLAT,
            frameColor=(0.72, 0.18, 0.10, 1.0),
            frameSize=(-0.009, 0.009, -0.009, 0.009),
            pos=(0.036, 0, 0.036))
        self.factory_pip.hide()

    def set_resource_detail(self, res, text):
        tip = self.res_tips.get(res)
        if tip is not None:
            tip._tip_tn.setText(text)

    def set_resource_color(self, res, color):
        if res in self.values:
            self.values[res].setTextColor(*color)

    def set_factory_alert(self, on):
        if on and self.factory_pip.isHidden():
            self.factory_pip.show()
        elif not on and not self.factory_pip.isHidden():
            self.factory_pip.hide()

    LAYOUT_HALF = 2.09          # the half-width the rank is drawn at

    def _fit_to_screen(self):
        """The strip is drawn for a wide window; a narrower one
        squeezes the whole rank to fit rather than losing its
        right-hand end off the edge."""
        if not self.frame or self.frame.isEmpty():
            return
        try:
            right = self.base.getAspectRatio()
        except Exception:
            right = 4.0 / 3.0
        # the strip PLATE runs wall to wall whatever the window --
        # an ultrawide screen used to see it end mid-air at x=2
        w = max(2.0, right)
        self.frame['frameSize'] = (-w, w, -0.155, 0.0)
        self.content.setScale(min(1.0, right / self.LAYOUT_HALF))

    def set_stats(self, stats):
        """stats: dict keyed by column title."""
        for title, value in stats.items():
            if title in self.values:
                self.values[title].setText(str(value))

    def set_budget_label(self, label):
        self.budget_btn['text'] = label

    def set_fortnight_day(self, day):
        """Fill one dot per elapsed day of the fortnight (1..14)."""
        if day == self._fortnight_day:
            return
        self._fortnight_day = day
        for i, dot in enumerate(self.day_dots):
            if i < day:
                dot['frameColor'] = (0.88, 0.80, 0.56, 1.0)
            else:
                dot['frameColor'] = (0.32, 0.30, 0.26, 1.0)

    def destroy(self):
        self.frame.destroy()


class BottomBar:
    """Controls and information on the current selection."""

    def __init__(self, base):
        self.base = base
        # flush with the RIGHT edge of the screen, and STRETCHED
        # left to meet the facsimile machine: no dead corner between
        # them at any window aspect
        self.frame = DirectFrame(parent=base.a2dBottomRight,
                                 frameColor=(1, 1, 1, 0.92),
                                 frameTexture=sheet_tex('bar'),
                                 frameSize=(-1.35, 1.35, 0.0, 0.35),
                                 pos=(-1.35, 0, 0),
                                 state=DGG.NORMAL)
        self.frame.setTransparency(True)
        self.title_tn, self._title_np = _make_text(
            self.frame, base.hud_font, (-1.30, 0.290), 0.05, ACCENT)
        self.info_tn, self._info_np = _make_text(
            self.frame, base.hud_font, (-1.30, 0.225), 0.036,
            BAR_TEXT)
        self.info_tn.setText('')
        # the SIGNALS line rides above the bar: short despatches
        # ("REPORTING FOR DUTY", refused orders) print here and fade,
        # never touching the selection's own info line
        self.signal_tn, self._signal_np = _make_text(
            self.frame, base.hud_font, (-1.30, 0.360), 0.034,
            (0.95, 0.82, 0.48, 1.0))
        self.signal_tn.setText('')
        self.hint_tn, self._hint_np = _make_text(
            self.frame, base.hud_font, (-1.30, 0.035), 0.033,
            (0.62, 0.60, 0.52, 1.0))
        self.buttons = []
        # persistent briefing button, top-right corner of the bar; a
        # rounded-square 'i' icon that opens the selected unit's briefing
        self.info_btn = DirectButton(
            parent=self.frame,
            image=get_icon_path('info_button', 'dark'),
            image_scale=0.05, relief=None,
            frameColor=(0, 0, 0, 0),
            frameSize=(-0.05, 0.05, -0.05, 0.05),
            pos=(1.28, 0, 0.285), command=None)
        self.info_btn.setTransparency(True)
        crisp_image(self.info_btn)
        add_tooltip(self.info_btn, "UNIT BRIEFING", font=base.hud_font)
        self.info_btn.hide()
        # red CAPTURE button: appears on an enemy city's menu when the
        # infantry garrison on it suffices to annex
        # red EXIT key, right end of the bar: stored units walk out
        self.exit_btn = pill_button(
            self.frame, "EXIT AIRFIELD", None, pos=(0.95, 0, 0.293),
            hw=0.17, hh=0.036, text_scale=0.032,
            text_fg=(0.97, 0.90, 0.80, 1.0), font=base.hud_font,
            kind='red')
        self.exit_btn.hide()
        self.capture_btn = pill_button(
            self.frame, "++ CAPTURE ++", None, pos=(0.95, 0, 0.293),
            hw=0.20, hh=0.038, text_scale=0.038,
            text_fg=(0.97, 0.90, 0.80, 1.0), font=base.hud_font,
            kind='red')
        self.capture_btn.hide()
        # red SCRAMBLE button floating ABOVE the bar: launches every
        # selected squadron whose sortie plan is on the plotting board
        self.scramble_btn = pill_button(
            self.frame, "SCRAMBLE", None, pos=(0, 0, 0.465),
            hw=0.24, hh=0.052, text_scale=0.036,
            text_fg=(0.97, 0.90, 0.80, 1.0), font=base.hud_font,
            kind='red')
        self.scramble_btn.hide()
        self._fit_to_screen()
        # Panda names this event aspectRatioChanged -- the
        # hyphenated spelling never fired, so neither bar
        # refitted and the bar drifted off the facsimile
        base.accept('aspectRatioChanged',
                    self._fit_to_screen)

    def _fit_to_screen(self):
        """The bar's LEFT edge lands exactly on the facsimile
        machine's border, whatever the window aspect; the title
        column rides that edge."""
        if not self.frame or self.frame.isEmpty():
            return
        try:
            ar = self.base.getAspectRatio()
        except Exception:
            ar = 4.0 / 3.0
        # machine right edge (incl. its border) in this frame's space
        left = min(-1.35, 1.35 + FaxPanel.MACH_X1
                   + FaxPanel.BORDER - 2.0 * ar)
        self.frame['frameSize'] = (left, 1.35, 0.0, 0.35)
        x = left + 0.05
        self._title_np.setX(x)
        self._info_np.setX(x)
        self._signal_np.setX(x)
        self._hint_np.setX(x)
        # SCRAMBLE floats centred over the VISIBLE bar: anchored at
        # x=0 it drifted right when the facsimile claimed the bar's
        # left edge
        self.scramble_btn.setX((left + 1.35) / 2.0)

    def show_info(self, command, args):
        self.info_btn['command'] = command
        self.info_btn['extraArgs'] = list(args)
        self.info_btn.show()

    def hide_info(self):
        self.info_btn.hide()

    def show_exit(self, command, args=()):
        self.exit_btn['command'] = command
        self.exit_btn['extraArgs'] = list(args)
        self.exit_btn.show()

    def hide_exit(self):
        self.exit_btn.hide()

    def show_capture(self, command, args):
        self.capture_btn['command'] = command
        self.capture_btn['extraArgs'] = list(args)
        self.capture_btn.show()

    def hide_capture(self):
        self.capture_btn.hide()

    def show_scramble(self, command, args=()):
        self.scramble_btn['command'] = command
        self.scramble_btn['extraArgs'] = list(args)
        self.scramble_btn.show()

    def hide_scramble(self):
        self.scramble_btn.hide()

    def set_title(self, text):
        self.title_tn.setText(text)

    def set_info(self, text):
        self.info_tn.setText(text)

    def set_signal(self, text):
        self.signal_tn.setText(text)

    def set_hint(self, text):
        self.hint_tn.setText(text)

    def clear_buttons(self):
        for b in self.buttons:
            b.destroy()
        self.buttons = []

    def add_buttons(self, entries, actions=(), big=False):
        """entries: (label, command, extraArgs[, icon_path[, selected
        [, tip[, dim]]]]).  Every control is a SQUARE console key
        bearing an icon; the full name rides a hover tooltip and a
        short label (an hp readout, a cost) prints as a caption under
        the icon.  A truthy 'selected' draws a white halo.  A truthy
        'dim' greys the whole key out -- not ready (no crew, still on
        the ways); the tooltip still explains why.
        ORDERS AND ROSTER NEVER MIX: 'actions' keys stand from the
        LEFT edge, 'entries' (the units) muster from the RIGHT.
        big=True (base and transport menus) wears keys 30% larger."""
        self.clear_buttons()
        self.set_hint('')
        # EVERY key on the bar wears the LARGE size now (big= kept
        # for the callers' sake; it no longer shrinks anything)
        per_row = 12
        side = 0.065
        pitch = 0.146
        placed = []
        for i, entry in enumerate(tuple(actions)[:per_row]):
            placed.append((i, 0, entry))
        n_act = len(placed)
        ents = list(entries)[:32]
        idx, row_i = 0, 0
        while idx < len(ents) and row_i < 2:
            room = per_row - (n_act if row_i == 0 else 0)
            take = min(room, len(ents) - idx)
            start_col = per_row - take
            for k in range(take):
                placed.append((start_col + k, row_i, ents[idx + k]))
            idx += take
            row_i += 1
        for col, row, entry in placed:
            label, command, args = entry[0], entry[1], entry[2]
            icon = entry[3] if len(entry) > 3 else None
            selected = entry[4] if len(entry) > 4 else False
            tip = entry[5] if len(entry) > 5 else label
            dim = entry[6] if len(entry) > 6 else False
            x = -1.19 + col * pitch
            y = 0.166 - row * pitch
            if selected:
                # white halo behind the key = selected indicator
                border = DirectFrame(parent=self.frame,
                                     frameColor=(1, 1, 1, 1),
                                     frameSize=(-side - 0.007, side + 0.007,
                                                -side - 0.007, side + 0.007),
                                     relief=DGG.FLAT, pos=(x, 0, y))
                self.buttons.append(border)
            btn = pill_button(self.frame, '', command,
                              extraArgs=args, pos=(x, 0, y),
                              hw=side, hh=side, corner=0.30,
                              font=self.base.hud_font)
            if icon:
                # a captioned key rides its icon high to clear the
                # chip; a bare key wears the icon dead centre. A
                # a FIELD SPRITE rides like a map counter: turned
                # 45 degrees and blown up to fill the key (a UI
                # pictogram -- unload, strike, anchor -- does not)
                sprite = '/units/' in str(icon).replace('\\\\', '/')
                pic_z = 0.012 if (label and len(label) <= 8) else 0.0
                pic = OnscreenImage(image=icon, parent=btn,
                                    scale=(side * 0.92 if sprite
                                           else 0.044 * side / 0.050),
                                    pos=(0, 0, pic_z))
                if sprite:
                    pic.setR(45)
                pic.setTransparency(True)
                crisp_image(pic)
                if label and len(label) <= 8:
                    # short caption (hp, cost) on a paper chip at the
                    # key's foot, so it stays legible over the larger
                    # pictogram
                    chw = 0.31 * 0.016 * len(label) + 0.005
                    chip = DirectFrame(parent=btn,
                                       frameColor=(0.80, 0.75, 0.60,
                                                   0.96),
                                       frameSize=(-chw, chw,
                                                  -0.011, 0.0135),
                                       relief=DGG.FLAT,
                                       pos=(0, 0, -0.0335))
                    cap = TextNode('cap')
                    cap.setAlign(TextNode.ACenter)
                    if self.base.hud_font:
                        cap.setFont(self.base.hud_font)
                    cap.setTextColor(*INK)
                    cap.setText(label)
                    np_ = chip.attachNewNode(cap)
                    np_.setScale(0.016)
                    np_.setPos(0, 0, -0.005)
            else:
                # no icon supplied: the label itself sits on the key
                fit = (2.0 * side * 0.92) / (0.62 * max(1, len(label)))
                btn['text'] = label
                btn['text_scale'] = min(0.030, fit)
                btn['text_pos'] = (0, -0.010)
            if dim:
                # greyed key: the works aren't ready (no crew, still
                # building) -- clicks fall through to the command,
                # which explains itself over the wire
                btn.setColorScale(0.55, 0.55, 0.55, 1.0)
            if tip:
                # the slip clears the key's top edge, riding over the
                # info line rather than the bar title
                add_tooltip(btn, tip, font=self.base.hud_font, dy=0.082)
            self.buttons.append(btn)

    def destroy(self):
        self.clear_buttons()
        self.frame.destroy()


NEWSPRINT = (0.89, 0.87, 0.80, 0.99)


_WIRE_LEAD = (
    "Reports reaching this desk", "Despatches from the frontier",
    "A communique issued at dawn", "Travellers arriving by rail",
    "The wireless from the coast", "Officials speaking last night",
    "A correspondent at the front", "Sources close to the ministry")
_WIRE_BODY = (
    "speak of columns on the move before first light",
    "describe heavy traffic on every road to the east",
    "confirm that reserves have been called to the colours",
    "tell of bridges watched and crossings counted",
    "report the harbours working under blackout",
    "note long trains of lorries moving under tarpaulin",
    "insist the situation remains fluid but contained",
    "count fresh batteries dug in along the ridge")
_WIRE_TAIL = (
    "No further detail was available at press time.",
    "The ministry declined to comment.",
    "Censors passed this despatch without amendment.",
    "Confirmation is awaited from the capital.",
    "The public is asked to remain calm.",
    "More in the late edition.")


def _wire_filler(seed, n_sent):
    """Column filler in the house style: plausible wire-copy nonsense
    so the sheet reads like a REAL broadsheet, deterministic per
    edition so the paper doesn't rewrite itself on a glance."""
    import random as _random
    rng = _random.Random(seed)
    out = []
    for _ in range(n_sent):
        out.append("%s %s. %s" % (rng.choice(_WIRE_LEAD),
                                  rng.choice(_WIRE_BODY),
                                  rng.choice(_WIRE_TAIL)))
    return "  ".join(out)


class Newspaper:
    """A broadsheet on the stand: masthead, dateline, banner headline
    and the deck beneath, in the manner of the wire-service extras.
    Click anywhere on the sheet (or the corner key) to file it away.
    The FINAL edition -- victory or capitulation -- carries the full
    statistical record of the war and stays up until dismissed."""

    MAST = "THE WORLD CHRONICLE"

    def __init__(self, base, headline, deck, dateline, on_dismiss,
                 final=None, stats=()):
        self.base = base
        self.on_dismiss = on_dismiss
        tall = 0.48 if final is None else 0.86
        self.frame = DirectFrame(parent=base.aspect2d,
                                 frameColor=(1, 1, 1, 1),
                                 frameTexture=sheet_tex('newsprint'),
                                 frameSize=(-0.98, 0.98, -tall, tall),
                                 state=DGG.NORMAL, pos=(0, 0, 0.06))
        self.frame.setTransparency(True)
        edge = DirectFrame(parent=self.frame, frameColor=PAPER_EDGE,
                           frameSize=(-0.99, 0.99, -tall - 0.012,
                                      -tall))
        y = tall - 0.11

        def text(t, ty, scale, color=INK, align=TextNode.ACenter,
                 wordwrap=None):
            tn = TextNode('news')
            tn.setAlign(align)
            if base.hud_font:
                tn.setFont(base.hud_font)
            tn.setTextColor(*color)
            if wordwrap:
                tn.setWordwrap(wordwrap)
            tn.setText(t)
            np_ = self.frame.attachNewNode(tn)
            np_.setPos(0 if align == TextNode.ACenter else -0.88,
                       0, ty)
            np_.setScale(scale)
            return tn, np_

        text(self.MAST, y, 0.085)
        y -= 0.055
        text("%s  *  LATE WAR EXTRA  *  ONE PENNY" % dateline,
             y, 0.026, INK_FAINT)
        y -= 0.045
        for ry in (y + 0.012, y + 0.002):
            rule = DirectFrame(parent=self.frame, frameColor=INK,
                               frameSize=(-0.90, 0.90, ry, ry + 0.004))
        y -= 0.10
        # the banner headline wraps and shrinks to fit the broadsheet
        size = 0.075 if len(headline) < 38 else 0.058
        tn, _ = text(headline, y, size, wordwrap=24.0)
        y -= 0.075 * (1 + headline.count(' ') // 12)
        y -= 0.075
        text(deck, y, 0.034, wordwrap=46.0)
        if final is None:
            # below the fold the sheet reads like a REAL broadsheet:
            # a rule, then three columns of wire copy behind thin
            # column rules (filler, deterministic per edition)
            ry = y - 0.055
            DirectFrame(parent=self.frame, frameColor=INK,
                        frameSize=(-0.90, 0.90, ry, ry + 0.003))
            col_w, gap = 0.56, 0.05
            x_left = -0.90
            seed = hash((headline, deck)) & 0xffffffff
            for ci in range(3):
                cx = x_left + ci * (col_w + gap)
                tn = TextNode('wire')
                tn.setAlign(TextNode.ALeft)
                if base.hud_font:
                    tn.setFont(base.hud_font)
                tn.setTextColor(0.32, 0.28, 0.23, 1.0)
                tn.setWordwrap(col_w / 0.021)
                tn.setText(_wire_filler(seed + ci, 2))
                np_ = self.frame.attachNewNode(tn)
                np_.setPos(cx, 0, ry - 0.045)
                np_.setScale(0.021)
                if ci:
                    DirectFrame(parent=self.frame,
                                frameColor=(0.55, 0.51, 0.44, 1.0),
                                frameSize=(cx - gap / 2 - 0.0012,
                                           cx - gap / 2 + 0.0012,
                                           -tall + 0.13, ry - 0.02))
        if final is not None:
            y -= 0.30
            text("++ %s ++" % ("TOTAL VICTORY" if final == 'victory'
                               else "CAPITULATION"), y, 0.045)
            y -= 0.075
            for label, value in stats:
                text("%-28s %s" % (label, value), y, 0.030,
                     align=TextNode.ALeft)
                y -= 0.055
        self.frame.bind(DGG.B1PRESS, lambda e: self.dismiss())
        pill_button(self.frame, "FILE AWAY",
                    lambda: self.dismiss(),
                    pos=(0.76, 0, -tall + 0.075), hw=0.15, hh=0.038,
                    font=base.hud_font)
        snd = getattr(base, 'fax_snd', None)
        if snd is not None:
            snd.play()

    def dismiss(self):
        cb = self.on_dismiss
        self.on_dismiss = None
        self.destroy()
        if cb:
            cb()

    def destroy(self):
        self.frame.destroy()


class DiplomacyLedger:
    """The Foreign Office ledger: every nation of the world on one
    sheet -- stance, standing, and the keys that move the bags.
    Declarations and offers go out AS FAXES and are answered by
    return courier; only breaking one's own pact is instant."""

    def __init__(self, game, on_close):
        from config import COUNTRIES, PLAYABLE
        self.game = game
        self.base = game
        self.on_close = on_close
        self._COUNTRIES = COUNTRIES
        self._PLAYABLE = PLAYABLE
        # no security stamp: the WARS RAGING board keeps that corner
        self.sheet = FormSheet(game, "THE DIPLOMATIC LEDGER",
                               half_w=1.42, half_h=0.86, stamp=None)
        self.frame = self.sheet.frame
        self.widgets = []
        self._static()
        self.rebuild()

    def _text(self, t, pos, scale=0.032, color=INK,
              align=TextNode.ALeft, keep=False):
        tn = TextNode('diplo')
        tn.setAlign(align)
        if self.base.hud_font:
            tn.setFont(self.base.hud_font)
        tn.setTextColor(*color)
        tn.setText(t)
        np_ = self.frame.attachNewNode(tn)
        np_.setPos(pos[0], 0, pos[1])
        np_.setScale(scale)
        if not keep:
            self.widgets.append(np_)
        return np_

    def _static(self):
        self.sheet.keys([
            ("CLOSE  [ESC]", lambda: self.on_close(), (), 1.08,
             'red', KEY_LIGHT, 0.18),
        ])

    def _page_key(self, label, cmd, args=()):
        """One page-specific key beside the standing CLOSE, TRACKED
        so it dies with the page (sheet.keys would redraw the rule
        and the end tag and leak a button on every rebuild)."""
        b = pill_button(self.frame, label, cmd, extraArgs=list(args),
                        pos=(-1.08, 0, -0.86 + 0.118), hw=0.28,
                        hh=0.055, text_scale=0.038,
                        font=self.base.hud_font, text_fg=INK)
        self.widgets.append(b)
        return b

    def rebuild(self):
        """Two pages, one sheet. The ROSTER: every nation as a big
        flag card, plus the wars raging -- that is all. Click a card
        for the DOSSIER: that nation's standing, wars, pacts, and
        the player's diplomatic keys, writ large."""
        g = self.game
        for w in self.widgets:
            w.destroy() if hasattr(w, 'destroy') else w.removeNode()
        self.widgets = []
        view = getattr(self, 'view', None)
        if view is not None and (view in g.eliminated
                                 or view == g.player_country):
            view = self.view = None
        if view == '_commitments':
            self.table = None
            self._build_commitments()
        elif view is None:
            self.table = None
            self._build_roster()
        elif getattr(self, 'table', None) == view:
            self._build_table(view)
        else:
            self._build_dossier(view)

    def _open_dossier(self, nat):
        self.view = nat
        self.table = None
        self.rebuild()

    def _open_commitments(self):
        self.view = '_commitments'
        self.table = None
        self.rebuild()

    def _build_commitments(self):
        """THE STATE OF OUR OBLIGATIONS: every power this office has
        anything standing with -- a war, a pact, a right, a cargo --
        on one sheet, so the commander need not open twenty dossiers
        to remember what he has signed."""
        g = self.game
        from config import short_name
        me = g.player_country
        self._text("++ OUR COMMITMENTS ++", (0, 0.61), 0.044,
                   color=RED_INK, align=TextNode.ACenter)
        self._text("EVERY POWER WITH WHICH SOMETHING STANDS -- "
                   "CLICK A STANDARD FOR ITS DOSSIER",
                   (0, 0.555), 0.024, color=INK_FAINT,
                   align=TextNode.ACenter)
        self._rule(-1.30, 1.30, 0.525)
        rows = []
        for nat in self._COUNTRIES:
            if nat in (me, 'neutral') or nat in g.eliminated:
                continue
            at_war = g.at_war(me, nat)
            allied = g.allied(me, nat)
            lines = self._agreement_lines(nat)
            if at_war or allied or lines:
                rows.append((nat, at_war, allied, lines))
        # the bloodiest business first, then the friends, then trade
        rows.sort(key=lambda r: (not r[1], not r[2],
                                 short_name(r[0])))
        if not rows:
            self._text("NOTHING STANDS WITH ANY POWER. THE OFFICE "
                       "HAS SIGNED NOTHING AND FIGHTS NO ONE.",
                       (0, 0.28), 0.030, color=INK_FAINT,
                       align=TextNode.ACenter)
        n_war = sum(1 for r in rows if r[1])
        n_ally = sum(1 for r in rows if r[2])
        n_paper = sum(len(r[3]) for r in rows)
        y = 0.445
        for nat, at_war, allied, lines in rows[:8]:
            self._card(nat, -1.19, y - 0.010)
            self._text(short_name(nat).upper(), (-1.10, y + 0.008),
                       0.031)
            if at_war or allied:
                self._stamp(-0.60, y + 0.012,
                            "AT WAR" if at_war else "ALLY",
                            (0.62, 0.14, 0.10, 1.0) if at_war
                            else (0.16, 0.38, 0.14, 1.0),
                            scale=0.021, center=True)
            if lines:
                for k, (label, note) in enumerate(lines[:3]):
                    ly = y + 0.016 - k * 0.032
                    self._text(label, (-0.44, ly), 0.023)
                    self._text(note, (0.86, ly), 0.021,
                               color=INK_FAINT)
                if len(lines) > 3:
                    self._text("AND %d MORE INSTRUMENT(S) ON FILE"
                               % (len(lines) - 3),
                               (-0.44, y + 0.016 - 3 * 0.032), 0.021,
                               color=INK_FAINT)
            elif not (at_war or allied):
                self._text("--", (-0.44, y + 0.012), 0.023,
                           color=INK_FAINT)
            self._rule(-1.26, 1.30, y - 0.078, w=0.0012)
            y -= 0.125
        if len(rows) > 8:
            self._text("AND %d FURTHER POWER(S) ON FILE -- OPEN "
                       "THEIR DOSSIERS FROM THE ROSTER"
                       % (len(rows) - 8), (0, y + 0.010), 0.024,
                       color=INK_FAINT, align=TextNode.ACenter)
        self._text("IN SUM: %d WAR(S), %d ALLIANCE(S), %d "
                   "INSTRUMENT(S) STANDING"
                   % (n_war, n_ally, n_paper),
                   (0, -0.63), 0.028, color=INK,
                   align=TextNode.ACenter)
        self._page_key("THE ROSTER", self._open_dossier, (None,))

    def _card(self, nat, x, y, big=False):
        from icons import flag_texture
        from config import short_name
        g = self.game
        fw = 0.075 if big else 0.056
        chip = DirectButton(parent=self.frame, relief=None,
                            frameColor=(0, 0, 0, 0),
                            image=flag_texture(nat),
                            image_scale=(fw, 1, fw * 2 / 3),
                            frameSize=(-fw, fw, -fw * 2 / 3,
                                       fw * 2 / 3),
                            pos=(x, 0, y),
                            command=self._open_dossier,
                            extraArgs=[nat])
        chip.setTransparency(True)
        crisp_image(chip)
        self.widgets.append(chip)
        return chip

    def _open_table(self, nat):
        self.view = nat
        self.table = nat
        self.offer = {}
        self.ask = {}
        self.rebuild()

    def _table_adjust(self, side, key, delta, step):
        book = self.offer if side == 'offer' else self.ask
        book[key] = max(0, book.get(key, 0) + delta * step)
        if book[key] == 0:
            book.pop(key, None)
        self.rebuild()

    def _clear_sheet(self):
        self.offer = {}
        self.ask = {}
        self.rebuild()

    TOKEN_TIP = {
        'passage': "OUR LAND COLUMNS MAY CROSS THEIR COUNTRY "
                   "WITHOUT A DECLARATION OF WAR",
        'supply': "OUR COLUMNS MAY WATER AND RESUPPLY AT THEIR "
                  "TOWNS AND QUAYS",
        'comms': "THEIR WIRELESS NET AND LAND LINES KEEP OUR "
                 "COLUMNS IN CONTACT ON THEIR GROUND",
        'nonaggression': "NEITHER POWER MAY DECLARE WAR ON THE "
                         "OTHER WHILE IT STANDS",
        'alliance': "THEIR WARS BECOME OURS AND OURS THEIRS -- "
                    "AND THEIR VOLUNTEERS MAY BE ASKED FOR",
        'peace': "THE GUNS FALL SILENT BETWEEN US",
        'funds_once': "A SINGLE PAYMENT FROM THE TREASURY",
        'funds_ftn': "A STANDING SUBSIDY, PAID EVERY FORTNIGHT",
        'res_ftn': "CARGO SHIPPED EVERY FORTNIGHT UNTIL CANCELLED",
        'res_once': "A SINGLE CARGO, LANDED THE MOMENT IT IS SIGNED",
    }

    def _table_toggle(self, side, key):
        book = self.offer if side == 'offer' else self.ask
        if key in book:
            book.pop(key)
        else:
            book[key] = 1
        self.rebuild()

    def _tokens(self, book):
        """The book of counters as a list of deal tokens."""
        out = []
        for key, n in book.items():
            if n <= 0:
                continue
            if key == 'funds_once':
                out.append({'kind': 'funds_once', 'amount': n})
            elif key == 'funds_ftn':
                out.append({'kind': 'funds_ftn', 'amount': n})
            elif key.startswith('res_ftn:'):
                out.append({'kind': 'res_ftn',
                            'res': key.split(':')[1], 'amount': n})
            elif key.startswith('res_once:'):
                out.append({'kind': 'res_once',
                            'res': key.split(':')[1], 'amount': n})
            else:
                out.append({'kind': key})
        return out

    def _dispatch_envoy(self, nat):
        g = self.game
        g.propose_deal(nat, self._tokens(self.offer),
                       self._tokens(self.ask))
        self.offer = {}
        self.ask = {}
        self.rebuild()

    def _build_table(self, nat):
        """THE NEGOTIATING TABLE: every concession is a counter laid
        on one side of the sheet or the other."""
        import deals as _d
        g = self.game
        from config import short_name, RESOURCES
        me = g.player_country
        f = self.base.hud_font
        b = pill_button(self.frame, "<< THE DOSSIER",
                        self._open_dossier, extraArgs=[nat],
                        pos=(-1.10, 0, -0.742), hw=0.19, hh=0.048,
                        font=f)
        self.widgets.append(b)
        st = g.standing(nat)
        word, mult = _d.standing_word(st)
        col = ((0.16, 0.38, 0.14, 1.0) if st >= 30 else
               (0.62, 0.14, 0.10, 1.0) if st < -10 else
               (0.40, 0.36, 0.30, 1.0))
        self._card(nat, -1.14, 0.60)
        self._text("THE ENVOY'S SHEET -- %s" % short_name(nat).upper(),
                   (-1.02, 0.615), 0.044)
        self._text("THEIR FOREIGN OFFICE STANDS %s -- THEY PRICE "
                   "OUR ASKS AT %d%% OF WORTH" % (word, int(mult * 100)),
                   (-1.02, 0.556), 0.025, color=INK_FAINT)
        # the standing gauge: where this office sits on the ladder
        self._text("STANDING", (0.58, 0.612), 0.022, color=INK_FAINT)
        self._meter(0.58, 0.573, 0.42, (st + 100) / 200.0, col)
        self._stamp(1.04, 0.612, word, col, scale=0.024)
        self._rule(-1.30, 1.30, 0.505)

        gates = g.deal_gates(nat)
        cols = {'name': -1.28, 'offer': -0.30, 'ask': 0.62}
        self._text("ON THE TABLE", (cols['name'], 0.455), 0.024,
                   color=INK_FAINT)
        self._text("WE OFFER", (cols['offer'] + 0.09, 0.455), 0.024,
                   color=INK_FAINT, align=TextNode.ACenter)
        self._text("WE ASK", (cols['ask'] + 0.09, 0.455), 0.024,
                   color=INK_FAINT, align=TextNode.ACenter)

        rows = [('funds_once', 'FUNDS (ONE PAYMENT)', 100),
                ('funds_ftn', 'FUNDS EACH FORTNIGHT', 50)]
        # ONE SHIPMENT, landed at once, and the standing treaty
        # that ships every fortnight -- a nation short of steel this
        # week wants the cargo now, not a fortnight hence
        for res in RESOURCES:
            rows.append(('res_once:%s' % res,
                         '%s (ONE SHIPMENT)' % res.upper(), 20))
        for res in RESOURCES:
            rows.append(('res_ftn:%s' % res,
                         '%s EACH FORTNIGHT' % res.upper(), 10))
        rows += [('passage', 'RIGHT OF PASSAGE', 0),
                 ('supply', 'USE OF THE SUPPLY NET', 0),
                 ('comms', 'USE OF THE WIRELESS NET', 0),
                 ('nonaggression', 'PACT OF NON-AGGRESSION', 0),
                 ('alliance', 'PACT OF ALLIANCE', 0)]
        if g.at_war(me, nat):
            rows.append(('peace', 'AN END TO THE WAR', 0))

        y = 0.405
        for key, label, step in rows:
            kind = key.split(':')[0]
            lab = self._text(label, (cols['name'], y), 0.027)
            tip = self.TOKEN_TIP.get(kind)
            if tip:
                # an inert hover plate explains what the counter buys
                hov = DirectButton(parent=self.frame, relief=None,
                                   frameColor=(0, 0, 0, 0),
                                   frameSize=(0, 0.62, -0.016,
                                              0.028),
                                   pos=(cols['name'], 0, y),
                                   state=DGG.NORMAL)
                add_tooltip(hov, tip, font=f, dy=0.055)
                self.widgets.append(hov)
            for side in ('offer', 'ask'):
                x = cols[side]
                book = self.offer if side == 'offer' else self.ask
                mutual = kind in _d.GIVE_ONLY_MUTUAL
                # a pact binds BOTH sides: it is asked for, never
                # "offered" as a one-way concession
                if mutual and side == 'offer':
                    self._text("--", (x + 0.09, y), 0.024,
                               color=INK_FAINT,
                               align=TextNode.ACenter)
                    continue
                if side == 'ask' and gates.get(kind, True) is False:
                    self._text("NOT ON OFFER", (x + 0.09, y), 0.021,
                               color=INK_FAINT,
                               align=TextNode.ACenter)
                    continue
                if step == 0:
                    # a right already signed is never sold twice --
                    # and the sheet says which WAY it runs, so a
                    # frontier we opened to them reads WE GRANTED
                    if kind in ('passage', 'supply', 'comms',
                                'nonaggression'):
                        to_us, to_them = g.right_between(nat, kind)
                        held = to_us if side == 'ask' else to_them
                        if held:
                            self._stamp(
                                x + 0.09, y + 0.004,
                                "IN FORCE" if kind == 'nonaggression'
                                else ("THEY GRANTED" if side == 'ask'
                                      else "WE GRANTED"),
                                (0.16, 0.38, 0.14, 1.0),
                                scale=0.018, center=True)
                            continue
                    if kind == 'alliance' and g.allied(me, nat):
                        self._stamp(x + 0.09, y + 0.004, "IN FORCE",
                                    (0.16, 0.38, 0.14, 1.0),
                                    scale=0.018, center=True)
                        continue
                    on = key in book
                    bt = pill_button(
                        self.frame, "PLEDGED" if on else "--",
                        self._table_toggle, extraArgs=[side, key],
                        pos=(x + 0.09, 0, y + 0.008), hw=0.10,
                        hh=0.030, text_scale=0.021, font=f,
                        latched=on)
                    self.widgets.append(bt)
                else:
                    bt = pill_button(
                        self.frame, "-", self._table_adjust,
                        extraArgs=[side, key, -1, step],
                        pos=(x - 0.02, 0, y + 0.008), hw=0.028,
                        hh=0.028, text_scale=0.030, font=f)
                    self.widgets.append(bt)
                    self._text("%d" % book.get(key, 0),
                               (x + 0.09, y), 0.028,
                               align=TextNode.ACenter)
                    bt = pill_button(
                        self.frame, "+", self._table_adjust,
                        extraArgs=[side, key, +1, step],
                        pos=(x + 0.20, 0, y + 0.008), hw=0.028,
                        hh=0.028, text_scale=0.030, font=f)
                    self.widgets.append(bt)
            y -= 0.054
            self._rule(-1.34, 1.34, y + 0.030,
                       color=(0.45, 0.40, 0.33, 0.28), w=0.0014)

        # ---- THE SHEET AS IT STANDS: both baskets in words, what
        # is already signed, and the envoy's reading -- three ruled
        # columns above the key row
        offer, ask = self._tokens(self.offer), self._tokens(self.ask)
        verdict, vword, _reply, gain = _d.evaluate(
            offer, ask, st, gates)
        y -= 0.030
        self._rule(-1.34, 1.34, y + 0.02)
        y -= 0.048
        for label, toks, cx in (("WE GIVE", offer, -1.34),
                                ("WE RECEIVE", ask, -0.55)):
            self._text(label, (cx, y), 0.024,
                       color=(0.52, 0.10, 0.06, 1.0))
            if not toks:
                self._text("nothing", (cx, y - 0.042), 0.025,
                           color=INK_FAINT)
            else:
                for i, tok in enumerate(toks[:4]):
                    self._text(_d.token_text(tok),
                               (cx, y - 0.042 - i * 0.038), 0.024)
        standing_lines = ["%s (%s)" % (what, how)
                          for what, how in
                          self._agreement_lines(nat)]
        self._text("ALREADY SIGNED", (0.24, y), 0.024,
                   color=(0.52, 0.10, 0.06, 1.0))
        if not standing_lines:
            self._text("no instrument stands between us",
                       (0.24, y - 0.042), 0.025, color=INK_FAINT)
        else:
            for i, line in enumerate(standing_lines[:4]):
                self._text(line, (0.24, y - 0.042 - i * 0.038),
                           0.023, color=(0.16, 0.38, 0.14, 1.0))
        if not offer and not ask:
            hint = ("Lay counters on the sheet -- what we give on "
                    "the left, what we want on the right.")
            hcol = INK_FAINT
        elif verdict == 'ungated':
            hint = "They will not treat for that at all -- not yet."
            hcol = (0.62, 0.14, 0.10, 1.0)
        else:
            hint = _d.shortfall_hint(gain)
            hcol = ((0.16, 0.38, 0.14, 1.0) if gain >= 0
                    else (0.62, 0.14, 0.10, 1.0))
        self._text("THE ENVOY'S READING", (0.24, y - 0.185), 0.024,
                   color=INK_FAINT)
        tn = TextNode('reading')
        tn.setWordwrap(46)
        tn.setAlign(TextNode.ALeft)
        if f:
            tn.setFont(f)
        tn.setTextColor(*hcol)
        tn.setText(hint)
        np_ = self.frame.attachNewNode(tn)
        np_.setPos(0.24, 0, y - 0.222)
        np_.setScale(0.023)
        self.widgets.append(np_)
        bt = pill_button(self.frame, "CLEAR THE SHEET",
                         self._clear_sheet, extraArgs=[],
                         pos=(-0.48, 0, -0.742), hw=0.21, hh=0.048,
                         text_scale=0.028, font=f)
        self.widgets.append(bt)
        bt = pill_button(self.frame, "++ DISPATCH THE ENVOY ++",
                         self._dispatch_envoy, extraArgs=[nat],
                         pos=(0.28, 0, -0.742), hw=0.34, hh=0.050,
                         text_scale=0.032, font=f, kind='red',
                         text_fg=KEY_LIGHT)
        self.widgets.append(bt)

    def _build_roster(self):
        g = self.game
        from config import short_name
        from icons import flag_texture
        me = g.player_country
        nations = [c for c in self._COUNTRIES
                   if c not in (me, 'neutral')
                   and c not in g.eliminated]
        nations.sort(key=lambda c: (c not in self._PLAYABLE,
                                    short_name(c)))
        # the roster: 5 columns of flag cards, names beneath, the
        # stance toward YOU printed only when it matters
        per_row = 5
        for i, nat in enumerate(nations[:25]):
            row, col = divmod(i, per_row)
            x = -1.08 + col * 0.44
            y = 0.49 - row * 0.24
            self._card(nat, x, y)
            at_war = g.at_war(me, nat)
            allied = g.allied(me, nat)
            self._text(short_name(nat).upper(), (x, y - 0.100),
                       0.032, align=TextNode.ACenter)
            if at_war or allied:
                self._stamp(x, y - 0.152,
                            "AT WAR" if at_war else "ALLY",
                            (0.62, 0.14, 0.10, 1.0) if at_war
                            else (0.16, 0.38, 0.14, 1.0),
                            scale=0.020, center=True)
        # THE WARS RAGING: the right edge is a battle-board -- each
        # war a pair of standards crossed by the swords
        wx = 1.18
        box = DirectFrame(parent=self.frame, relief=DGG.FLAT,
                          frameColor=(0.45, 0.40, 0.33, 0.55),
                          frameSize=(-0.222, 0.222, -1.175, 0.075),
                          pos=(wx, 0, 0.545), state=DGG.DISABLED)
        inner = DirectFrame(parent=box, relief=DGG.FLAT,
                            frameColor=PAPER[:3] + (1.0,),
                            frameSize=(-0.218, 0.218, -1.171,
                                       0.071), state=DGG.DISABLED)
        self.widgets.append(box)
        self._text("++ WARS RAGING ++", (wx, 0.555), 0.038,
                   color=(0.62, 0.14, 0.10, 1),
                   align=TextNode.ACenter)
        wars = sorted({tuple(sorted(w)) for w in g.wars})
        if not wars:
            self._text("ALL QUIET ON EVERY FRONT", (wx, 0.42),
                       0.026, color=INK_FAINT,
                       align=TextNode.ACenter)
        # the battle-board SCROLLS once the fronts outgrow it: every
        # war is on file, not the first seven and a count of shame
        from direct.gui.DirectScrolledFrame import DirectScrolledFrame
        row_h = 0.155
        view_h = 1.115
        need_h = max(view_h, len(wars) * row_h + 0.04)
        board = DirectScrolledFrame(
            parent=self.frame, relief=None,
            frameColor=(0, 0, 0, 0),
            frameSize=(-0.218, 0.218, -view_h, 0.0),
            canvasSize=(-0.19, 0.16, -need_h, 0.0),
            pos=(wx, 0, 0.505), state=DGG.NORMAL,
            autoHideScrollBars=True,
            scrollBarWidth=0.026,
            verticalScroll_relief=DGG.FLAT,
            verticalScroll_frameColor=(0.45, 0.40, 0.33, 0.35),
            verticalScroll_thumb_relief=DGG.FLAT,
            verticalScroll_thumb_frameColor=(0.45, 0.40, 0.33, 0.9),
            verticalScroll_incButton_relief=None,
            verticalScroll_decButton_relief=None,
            horizontalScroll_relief=None)
        board.horizontalScroll.hide()
        self.widgets.append(board)
        canvas = board.getCanvas()
        for i, (a, b) in enumerate(wars):
            wy = -0.085 - i * row_h
            for nat, dx in ((a, -0.115), (b, 0.115)):
                chip = DirectFrame(parent=canvas, relief=None,
                                   frameColor=(0, 0, 0, 0),
                                   image=flag_texture(nat),
                                   image_scale=(0.050, 1, 0.0333),
                                   frameSize=(-0.05, 0.05,
                                              -0.034, 0.034),
                                   pos=(dx, 0, wy),
                                   state=DGG.DISABLED)
                chip.setTransparency(True)
                crisp_image(chip)
            swords = DirectFrame(parent=canvas, relief=None,
                                 frameColor=(0, 0, 0, 0),
                                 image=get_icon_path('crossed_swords',
                                                     'dark'),
                                 image_scale=0.036,
                                 frameSize=(-0.04, 0.04,
                                            -0.04, 0.04),
                                 pos=(0, 0, wy),
                                 state=DGG.DISABLED)
            swords.setTransparency(True)
            crisp_image(swords)
            tn = TextNode('war_row')
            tn.setText("%s v %s" % (short_name(a).upper(),
                                    short_name(b).upper()))
            tn.setAlign(TextNode.ACenter)
            if g.hud_font:
                tn.setFont(g.hud_font)
            tn.setTextColor(*INK_FAINT)
            np_ = canvas.attachNewNode(tn)
            np_.setScale(0.021)
            np_.setPos(0, 0, wy - 0.070)
        self._text("CLICK A NATION FOR ITS DOSSIER -- WAR, PACTS "
                   "AND TERMS ARE OFFERED THERE",
                   (-0.12, -0.628), 0.024, color=INK_FAINT,
                   align=TextNode.ACenter)
        self._page_key("OUR COMMITMENTS", self._open_commitments)

    def _rule(self, x0, x1, y, color=None, w=0.0022):
        r = DirectFrame(parent=self.frame,
                        frameColor=color or (0.45, 0.40, 0.33, 0.8),
                        frameSize=(x0, x1, y - w / 2, y + w / 2),
                        relief=DGG.FLAT, state=DGG.DISABLED)
        self.widgets.append(r)
        return r

    def _meter(self, x, y, w, frac, color):
        """A ruled gauge: an empty trough with an inked fill."""
        trough = DirectFrame(parent=self.frame, relief=DGG.FLAT,
                             frameColor=(0.45, 0.40, 0.33, 0.5),
                             frameSize=(0, w, -0.012, 0.012),
                             pos=(x, 0, y), state=DGG.DISABLED)
        inner = DirectFrame(parent=trough, relief=DGG.FLAT,
                            frameColor=PAPER[:3] + (1.0,),
                            frameSize=(0.002, w - 0.002,
                                       -0.010, 0.010),
                            state=DGG.DISABLED)
        fill = max(0.0, min(1.0, frac))
        if fill > 0.001:
            DirectFrame(parent=inner, relief=DGG.FLAT,
                        frameColor=color,
                        frameSize=(0.002, 0.002 + (w - 0.004) * fill,
                                   -0.010, 0.010),
                        state=DGG.DISABLED)
        self.widgets.append(trough)
        return trough

    def _panel_head(self, x0, x1, y, title):
        self._text(title, (x0, y), 0.026, color=INK_FAINT)
        self._rule(x0, x1, y - 0.018)

    def _stamp(self, x, y, text, color, scale=0.030,
               center=False):
        """A rubber-stamped chip: bordered, inked, a hair off true."""
        w = 0.31 * scale * len(text) + scale
        hh = scale + 0.002
        box = DirectFrame(parent=self.frame, relief=DGG.FLAT,
                          frameColor=(0, 0, 0, 0),
                          frameSize=(-w, w, -hh, hh),
                          pos=(x if center else x + w, 0, y),
                          state=DGG.DISABLED)
        for inset, a in ((0.0, 0.9), (0.006, 0.0)):
            edge = DirectFrame(parent=box, relief=DGG.FLAT,
                              frameColor=color[:3] + (a,),
                              frameSize=(-w + inset, w - inset,
                                         -hh + inset, hh - inset),
                              state=DGG.DISABLED)
            if a == 0.0:
                edge['frameColor'] = PAPER[:3] + (1.0,)
        tn = TextNode('stamp')
        tn.setAlign(TextNode.ACenter)
        if self.base.hud_font:
            tn.setFont(self.base.hud_font)
        tn.setTextColor(*color)
        tn.setText(text)
        np_ = box.attachNewNode(tn)
        np_.setScale(scale)
        np_.setPos(0, 0, -scale * 0.34)
        box.setR(-2.5)
        self.widgets.append(box)
        return box

    def _agreement_lines(self, nat):
        """Every instrument standing between us, in plain words."""
        import deals as _d
        g = self.game
        out = []
        for kind in ('passage', 'supply', 'comms',
                     'nonaggression'):
            to_us, to_them = g.right_between(nat, kind)
            label = _d.KIND_LABEL[kind]
            if kind == 'nonaggression':
                if to_us:
                    out.append((label, 'BINDS BOTH'))
                continue
            if to_us:
                out.append((label, 'GRANTED TO US'))
            if to_them:
                out.append((label, 'GRANTED TO THEM'))
        for t in g.trade_deals:
            if t['with'] != nat:
                continue
            if t['res'] == 'funds':
                out.append(("SUBSIDY $%d EACH FORTNIGHT" % t['price'],
                            'WE PAY' if t['dir'] == 'out'
                            else 'THEY PAY'))
            else:
                out.append(("%d %s EACH FORTNIGHT"
                            % (t['amount'], t['res'].upper()),
                            'WE SHIP' if t['dir'] == 'out'
                            else 'WE RECEIVE'))
        return out

    def _build_dossier(self, nat):
        """The nation's file: what they are, what stands between us,
        and the UNILATERAL acts open to us. Everything that must be
        NEGOTIATED lives at the table."""
        g = self.game
        from config import short_name
        me = g.player_country
        f = self.base.hud_font
        b = pill_button(self.frame, "<< THE WORLD",
                        self._open_dossier, extraArgs=[None],
                        pos=(-1.10, 0, -0.742), hw=0.19, hh=0.048,
                        font=f)
        self.widgets.append(b)

        # ---- header band
        self._card(nat, -1.10, 0.56, big=True)
        self._text(short_name(nat).upper(), (-0.90, 0.560), 0.068)
        self._text(self._COUNTRIES[nat]['name'].upper(),
                   (-0.90, 0.478), 0.026, color=INK_FAINT)
        at_war = g.at_war(me, nat)
        allied = g.allied(me, nat)
        st = g.standing(nat)
        import deals as _d
        word, _m = _d.standing_word(st)
        col = ((0.16, 0.38, 0.14, 1.0) if st >= 30 else
               (0.62, 0.14, 0.10, 1.0) if st < -10 else
               (0.40, 0.36, 0.30, 1.0))
        self._stamp(0.55, 0.565,
                    "AT WAR" if at_war else
                    "ALLIED" if allied else "AT PEACE",
                    (0.62, 0.14, 0.10, 1.0) if at_war else
                    (0.16, 0.38, 0.14, 1.0) if allied else
                    (0.40, 0.36, 0.30, 1.0))
        self._text("THEIR FOREIGN OFFICE", (0.98, 0.596), 0.021,
                   color=INK_FAINT)
        self._meter(0.98, 0.556, 0.30, (st + 100) / 200.0, col)
        self._text(word, (0.98, 0.512), 0.024, color=col)
        self._rule(-1.30, 1.30, 0.415)

        # ---- their standing in the world
        all_nats = [c for c in self._COUNTRIES if c != 'neutral']
        wars = [short_name(o).upper() for o in all_nats
                if o != nat and g.at_war(nat, o)]
        pacts = [short_name(o).upper()
                 for o in sorted(g.alliances.get(nat, ()))
                 if o != nat]
        self._panel_head(-1.30, 1.30, 0.355, "THEIR STANDING IN "
                                             "THE WORLD")
        self._text("AT WAR WITH", (-1.30, 0.285), 0.026,
                   color=INK_FAINT)
        self._text(", ".join(wars) if wars else "NOBODY",
                   (-0.86, 0.285), 0.028,
                   color=((0.62, 0.14, 0.10, 1.0) if wars
                          else INK_FAINT))
        self._text("BOUND TO", (-1.30, 0.225), 0.026,
                   color=INK_FAINT)
        self._text(", ".join(pacts) if pacts else "NOBODY",
                   (-0.86, 0.225), 0.028,
                   color=((0.16, 0.38, 0.14, 1.0) if pacts
                          else INK_FAINT))

        # ---- what is already signed between the two of us
        self._panel_head(-1.30, 1.30, 0.145,
                         "WHAT STANDS BETWEEN US")
        lines = self._agreement_lines(nat)
        if not lines:
            self._text("No instrument stands between us -- open the "
                       "table to treat.", (-1.30, 0.078), 0.026,
                       color=INK_FAINT)
        else:
            for i, (what, how) in enumerate(lines[:6]):
                cx = -1.30 + (i % 2) * 1.28
                cy = 0.078 - (i // 2) * 0.050
                self._text(what, (cx, cy), 0.025)
                self._text(how, (cx + 0.86, cy), 0.022,
                           color=(0.16, 0.38, 0.14, 1.0))

        # ---- the table: every negotiated act lives there
        bt = pill_button(self.frame, "++ OPEN THE NEGOTIATING "
                                     "TABLE ++",
                         self._open_table, extraArgs=[nat],
                         pos=(0.0, 0, -0.28), hw=0.46, hh=0.058,
                         text_scale=0.036, font=f)
        self.widgets.append(bt)
        self._text("TRADE, PASSAGE, SUPPLY RIGHTS, PACTS AND PEACE "
                   "ARE ALL TREATED FOR AT THE TABLE",
                   (0, -0.365), 0.024, color=INK_FAINT,
                   align=TextNode.ACenter)

        # ---- acts that need no other man's signature
        self._panel_head(-1.30, 1.30, -0.46,
                         "ACTS REQUIRING NO NEGOTIATION")
        kx, keys = -0.62, []
        if not at_war:
            keys.append(("DECLARE WAR", g._diplo_action,
                         ['war', nat], 'red'))
        if allied:
            price = g.volunteer_price(nat)
            keys.append(("REQUEST VOLUNTEERS%s"
                         % (" ($%d)" % price if price else " (FREE)"),
                         g._diplo_action, ['volunteers', nat],
                         'panel'))
            keys.append(("BREAK THE PACT", g._diplo_break, [nat],
                         'red'))
        if not keys:
            self._text("The war leaves nothing to do here but "
                       "treat for its end.", (-1.30, -0.545), 0.026,
                       color=INK_FAINT)
        for i, (label, cmd, args, kind) in enumerate(keys[:3]):
            bt = pill_button(
                self.frame, label, cmd, extraArgs=args,
                pos=(kx + i * 0.64, 0, -0.555), hw=0.29, hh=0.048,
                text_scale=0.028, font=f, kind=kind,
                text_fg=((0.97, 0.90, 0.80, 1.0) if kind == 'red'
                         else INK))
            self.widgets.append(bt)
        self._text("DISPATCHES TRAVEL BY COURIER AND ARE ANSWERED "
                   "IN KIND", (0, -0.80), 0.024, color=INK_FAINT,
                   align=TextNode.ACenter)

    def destroy(self):
        self.frame.destroy()


class _Toast:
    """One incoming signal: a sheet of paper that RISES OUT OF THE
    FACSIMILE MACHINE'S SLIT (clipped below the slit line while it
    prints), stands in the delivery rack, holds, and files itself
    away to the left."""

    EMERGE_TIME = 0.85          # the machine prints the sheet
    HOLD_TIME = 11.0
    SLIDE_TIME = 0.22
    WIDTH = 0.46
    HEIGHT = 0.46 * 11.0 / 8.5  # letter proportions

    def __init__(self, panel, subject, body_lines, sender, stamp):
        self.panel = panel
        panel.toasts.append(self)
        base = panel.base
        self.width = self.WIDTH
        self.height = self.HEIGHT
        self.age = 0.0
        self.leaving = False
        self.leave_age = 0.0
        self.y = panel.SLIT_Y - self.height

        self.frame = DirectFrame(parent=base.a2dBottomLeft,
                                 frameColor=(1, 1, 1, 1),
                                 frameTexture=sheet_tex('paper'),
                                 frameSize=(0, self.width, 0,
                                            self.height),
                                 state=DGG.NORMAL)
        DirectFrame(parent=self.frame, frameColor=PAPER_EDGE,
                    frameSize=(0, self.width, self.height - 0.012,
                               self.height))
        head, head_np = _make_text(self.frame, base.hud_font,
                                   (0.035, self.height - 0.070),
                                   0.030, INK)
        head.setText(subject)
        # a long subject shrinks to the sheet instead of spilling
        w = head.getWidth() * 0.030
        if w > self.width - 0.07:
            head_np.setScale(0.030 * (self.width - 0.07) / w)
        rule, _ = _make_text(self.frame, base.hud_font,
                             (0.035, self.height - 0.108), 0.026,
                             INK_FAINT)
        rule.setText("-" * 24)
        body, _ = _make_text(self.frame, base.hud_font,
                             (0.035, self.height - 0.155), 0.0325,
                             (0.05, 0.04, 0.03, 1.0))
        body.setText('\n'.join(body_lines))
        foot, _ = _make_text(self.frame, base.hud_font,
                             (self.width / 2, 0.028), 0.021,
                             INK_FAINT, TextNode.ACenter)
        foot.setText("%s\n%s" % (sender, stamp))
        self.frame.setTransparency(True)
        self.frame.bind(DGG.B1PRESS, self._click)
        # while printing, nothing of the sheet shows below the slit
        self.frame.setClipPlane(panel.clip_np)
        self._clipped = True
        self.frame.setPos(panel.PAPER_X, 0, self.y)

    def _slot_y(self):
        """The delivery rack: the NEWEST sheet stands on the slit,
        older sheets are pushed up above it."""
        idx = self.panel.toasts.index(self)
        above = self.panel.toasts[idx + 1:]
        return self.panel.SLIT_Y + sum(t.height + 0.014
                                       for t in above)

    def update(self, dt):
        """Returns False when the toast is finished."""
        self.age += dt
        if self.leaving:
            self.leave_age += dt
            k = self.leave_age / self.SLIDE_TIME
            if k >= 1.0:
                self.frame.destroy()
                return False
            self.frame.setX(self.panel.PAPER_X
                            - k * (self.width + 0.1))
            self.frame.setAlphaScale(1.0 - k)
            return True
        if self.age <= self.EMERGE_TIME:
            # printing: the sheet climbs out of the slit
            k = self.age / self.EMERGE_TIME
            self.y = self.panel.SLIT_Y - self.height * (1.0 - k)
            self.frame.setZ(self.y)
        else:
            if self._clipped:
                self.frame.clearClipPlane()
                self._clipped = False
            # torn off: the sheet eases to its rack slot (older
            # sheets are pushed up as new ones print beneath them)
            target = self._slot_y()
            self.y += (target - self.y) * min(1.0, dt * 9.0)
            self.frame.setZ(self.y)
        if self.age > self.EMERGE_TIME + self.HOLD_TIME:
            self.leaving = True
        return True

    def _click(self, event=None):
        self.leaving = True

    def destroy(self):
        self.frame.destroy()


class FacsimileArchive:
    """THE MESSAGE FILE: every signal the machine has ever printed,
    newest first, paged like a clip of flimsies on a spike."""

    PER_PAGE = 4

    def __init__(self, base, records, on_close):
        self.base = base
        self.records = list(reversed(records))   # newest first
        self.on_close = on_close
        self.page = 0
        f = base.hud_font
        self.frame = DirectFrame(parent=base.aspect2d,
                                 frameColor=(1, 1, 1, 1),
                                 frameTexture=sheet_tex('paper'),
                                 frameSize=(-1.05, 1.05, -0.88, 0.88),
                                 state=DGG.NORMAL)
        DirectFrame(parent=self.frame, frameColor=PAPER_EDGE,
                    frameSize=(-1.05, 1.05, 0.855, 0.88))
        self._dyn = []
        self._build()

    def _text(self, t, pos, scale=0.03, color=INK,
              align=TextNode.ALeft):
        tn, np_ = _make_text(self.frame, self.base.hud_font, pos,
                             scale, color, align)
        tn.setText(t)
        self._dyn.append(np_)
        return tn

    def _build(self):
        f = self.base.hud_font
        for w in self._dyn:
            w.destroy() if hasattr(w, 'destroy') else w.removeNode()
        self._dyn = []
        self._text("*** FACSIMILE FILE -- EVERY SIGNAL RECEIVED ***",
                   (0, 0.78), 0.044, INK, TextNode.ACenter)
        pages = max(1, (len(self.records) + self.PER_PAGE - 1)
                    // self.PER_PAGE)
        self.page = max(0, min(self.page, pages - 1))
        self._text("%d SIGNAL(S) ON FILE -- SHEET %d OF %d"
                   % (len(self.records), self.page + 1, pages),
                   (0, 0.71), 0.027, INK_FAINT, TextNode.ACenter)
        y = 0.62
        rows = self.records[self.page * self.PER_PAGE:
                            (self.page + 1) * self.PER_PAGE]
        if not rows:
            self._text("NOTHING ON FILE -- THE WIRE IS QUIET",
                       (0, 0.2), 0.034, INK_FAINT, TextNode.ACenter)
        for subject, lines, sender, stamp in rows:
            self._text("-" * 78, (0, y + 0.020), 0.024, INK_FAINT,
                       TextNode.ACenter)
            self._text(subject, (-0.97, y - 0.030), 0.030, INK)
            self._text("%s   %s" % (sender, stamp),
                       (0.97, y - 0.030), 0.023, INK_FAINT,
                       TextNode.ARight)
            body = "  ".join(lines)[:150]
            self._text(body, (-0.97, y - 0.078), 0.024,
                       (0.22, 0.19, 0.15, 1.0))
            y -= 0.315
        if self.page > 0:
            b = pill_button(self.frame, "< NEWER", self._flip,
                            extraArgs=[-1], pos=(-0.62, 0, -0.79),
                            hw=0.14, hh=0.040, text_scale=0.030,
                            font=f)
            self._dyn.append(b)
        if self.page < pages - 1:
            b = pill_button(self.frame, "OLDER >", self._flip,
                            extraArgs=[+1], pos=(0.62, 0, -0.79),
                            hw=0.14, hh=0.040, text_scale=0.030,
                            font=f)
            self._dyn.append(b)
        b = pill_button(self.frame, "++ CLOSE THE FILE ++",
                        self.on_close, pos=(0, 0, -0.79),
                        hw=0.26, hh=0.044, text_scale=0.036, font=f)
        self._dyn.append(b)

    def _flip(self, d):
        self.page += d
        self._build()

    def destroy(self):
        self.frame.destroy()


class FaxPanel:
    """THE FACSIMILE MACHINE: a console in the bottom-left corner.
    Incoming signals print UP OUT OF ITS SLIT, stand in the rack,
    and file themselves away; a counter shows the traffic still in
    queue and the MESSAGE FILE key opens the complete archive."""

    MAX_VISIBLE = 2
    WRAP = 22
    ARCHIVE_CAP = 300

    # machine geometry, in a2dBottomLeft space
    MACH_X0, MACH_X1 = 0.0, 0.53
    MACH_TOP = 0.295
    SLIT_Y = 0.283
    PAPER_X = 0.035
    BORDER = 0.010              # the ink border all the way around

    def __init__(self, base):
        self.base = base
        self.queue = []
        self.toasts = []
        self.archive = []
        self.archive_fax = None
        self._shown_count = None
        # the slit line: nothing of a printing sheet shows below it
        pn = PlaneNode('facsimile_slit')
        pn.setPlane(Plane(Vec3(0, 0, 1), Point3(0, 0, self.SLIT_Y)))
        self.clip_np = base.a2dBottomLeft.attachNewNode(pn)
        self._build_console()

    def _build_console(self):
        base = self.base
        f = base.hud_font
        x0, x1, top = self.MACH_X0, self.MACH_X1, self.MACH_TOP
        bd = self.BORDER
        # the BORDER: a dark ink frame all the way around, standing
        # the machine apart from the bar beside it
        self.border = DirectFrame(
            parent=base.a2dBottomLeft,
            frameColor=(0.13, 0.11, 0.09, 1.0),
            frameSize=(x0, x1 + bd, 0.0, top + bd),
            state=DGG.NORMAL)
        self.console = DirectFrame(
            parent=base.a2dBottomLeft,
            frameColor=(1, 1, 1, 0.96),
            frameTexture=sheet_tex('bar'),
            frameSize=(x0 + bd, x1, bd, top),
            state=DGG.NORMAL)
        self.console.setTransparency(True)
        # the slit housing and the slit itself
        DirectFrame(parent=self.console,
                    frameColor=(0.16, 0.14, 0.11, 1.0),
                    frameSize=(x0, x1, top - 0.034, top))
        DirectFrame(parent=self.console,
                    frameColor=(0.04, 0.035, 0.03, 1.0),
                    frameSize=(x0 + 0.030, x1 - 0.030,
                               top - 0.026, top - 0.012))
        tn, _ = _make_text(self.console, f, (x0 + 0.035, 0.205),
                           0.036, (0.95, 0.82, 0.48, 1.0))
        tn.setText("FACSIMILE")
        tn, _ = _make_text(self.console, f, (x0 + 0.035, 0.168),
                           0.020, (0.62, 0.60, 0.52, 1.0))
        tn.setText("SIGNALS DESK -- INCOMING TRAFFIC")
        # the traffic counter: a dark window with amber digits
        DirectFrame(parent=self.console,
                    frameColor=(0.07, 0.06, 0.05, 1.0),
                    frameSize=(x0 + 0.035, x0 + 0.135,
                               0.058, 0.135))
        self.count_tn, _ = _make_text(
            self.console, f, (x0 + 0.085, 0.076), 0.048,
            (0.95, 0.72, 0.28, 1.0), TextNode.ACenter)
        self.count_tn.setText("--")
        tn, _ = _make_text(self.console, f, (x0 + 0.085, 0.028),
                           0.018, (0.62, 0.60, 0.52, 1.0),
                           TextNode.ACenter)
        tn.setText("IN QUEUE")
        self.file_btn = pill_button(
            self.console, "MESSAGE FILE", self._open_archive,
            pos=((x0 + 0.155 + x1 - 0.035) / 2, 0, 0.096),
            hw=(x1 - 0.035 - x0 - 0.155) / 2, hh=0.040,
            text_scale=0.027, font=f)
        add_tooltip(self.file_btn,
                    "EVERY SIGNAL RECEIVED -- THE COMPLETE FILE",
                    font=f)

    def post(self, subject, body, sender="SUPREME HQ"):
        snd = getattr(self.base, 'fax_snd', None)
        if snd is not None:
            snd.play()
        stamp = self.base.campaign_clock_text()             if hasattr(self.base, 'campaign_clock_text') else ''
        lines = []
        for para in body.split('\n'):
            lines.extend(_wrap_markup(para.upper(), self.WRAP))
        rec = ("++ %s ++" % subject.upper(), lines[:7],
               sender.upper(), stamp)
        self.queue.append(rec)
        self.archive.append(rec)
        if len(self.archive) > self.ARCHIVE_CAP:
            self.archive.pop(0)

    def update(self, dt):
        for t in list(self.toasts):
            if not t.update(dt):
                self.toasts.remove(t)
        # one sheet prints at a time; the rack holds two
        printing = any(t.age <= t.EMERGE_TIME and not t.leaving
                       for t in self.toasts)
        if (self.queue and not printing
                and len(self.toasts) < self.MAX_VISIBLE):
            subject, lines, sender, stamp = self.queue.pop(0)
            _Toast(self, subject, lines, sender, stamp)
        n = len(self.queue)
        if n != self._shown_count:
            self._shown_count = n
            self.count_tn.setText("%02d" % n if n else "--")

    def _open_archive(self):
        if self.archive_fax is not None:
            return
        self.archive_fax = FacsimileArchive(
            self.base, self.archive, self._close_archive)

    def _close_archive(self):
        if self.archive_fax is not None:
            self.archive_fax.destroy()
            self.archive_fax = None

    def dismiss(self):
        for t in self.toasts:
            t.leaving = True

    def destroy(self):
        for t in self.toasts:
            t.destroy()
        self.toasts = []
        self.queue = []
        self._close_archive()
        self.console.destroy()
        self.border.destroy()
        self.clip_np.removeNode()


def _wrap_markup(text, width):
    """textwrap that ignores \1b\1 ... \2 markup when measuring."""
    words = text.split()
    lines, cur, cur_len = [], [], 0
    for w in words:
        vis = len(w.replace('\1b\1', '').replace('\2', ''))
        add = vis + (1 if cur else 0)
        if cur_len + add > width and cur:
            lines.append(' '.join(cur))
            cur, cur_len = [w], vis
        else:
            cur.append(w)
            cur_len += add
    if cur:
        lines.append(' '.join(cur))
    return lines or ['']


RED_INK = (0.52, 0.10, 0.06, 1.0)       # dispatch red, section heads
STAMP_RED = (0.60, 0.12, 0.08, 0.92)    # the security stamp
GREEN_INK = (0.16, 0.38, 0.14, 1.0)
KEY_LIGHT = (0.95, 0.92, 0.86, 1.0)     # text on a red key


class FormSheet:
    """THE WAR OFFICE FORM -- the shared chrome of every facsimile
    page, in the manner of the Quick Match sheet: fax leader bands,
    corner tags, a mastheaded title over double rules, a FROM/RE
    block with a rotated security stamp, ruled sections with
    dispatch-red headers, and a bottom key row above the END OF
    TRANSMISSION tag. Pages draw their body between self.body_top
    and self.body_bot."""

    def __init__(self, base, title, half_w=1.30, half_h=0.92,
                 from_line=None, re_line=None, date_line=None,
                 stamp='MOST SECRET', sheet_tag="SHEET 1 OF 1"):
        self.base = base
        self.f = base.hud_font
        W, H = half_w, half_h
        self.W, self.H = W, H
        self.frame = DirectFrame(parent=base.aspect2d,
                                 frameColor=(1, 1, 1, 1),
                                 frameTexture=sheet_tex('paper'),
                                 frameSize=(-W, W, -H, H),
                                 state=DGG.NORMAL)
        for z0, z1 in ((H - 0.025, H), (-H, -H + 0.025)):
            DirectFrame(parent=self.frame, frameColor=PAPER_EDGE,
                        frameSize=(-W, W, z0, z1))
        self.text("FACSIMILE TRANSMISSION", (-W + 0.08, H - 0.068),
                  0.026, INK_FAINT)
        self.text(sheet_tag, (W - 0.08, H - 0.068), 0.026, INK_FAINT,
                  TextNode.ARight)
        self.text(title, (0, H - 0.150), 0.054, INK, TextNode.ACenter)
        self.rule(-W + 0.08, W - 0.08, H - 0.196, 0.005)
        self.rule(-W + 0.08, W - 0.08, H - 0.210, 0.0022)
        y = H - 0.262
        for tag, line in (('FROM', from_line), ('DATE', date_line),
                          ('RE', re_line)):
            if not line:
                continue
            self.text("%-4s : %s" % (tag, line), (-W + 0.08, y),
                      0.030)
            y -= 0.050
        if from_line or re_line or date_line:
            self.rule(-W + 0.08, W - 0.08, y - 0.008, 0.0022)
            self.body_top = y - 0.055
        else:
            self.body_top = H - 0.240
        if stamp:
            node = self.frame.attachNewNode('stamp')
            node.setPos(W - 0.40, 0, H - 0.290)
            node.setR(-7)
            sw = 0.044 * 0.31 * len(stamp) + 0.10
            sw = max(0.20, min(0.30, sw))
            sh = 0.052
            for x0, x1, z0, z1 in ((-sw, sw, sh - 0.006, sh),
                                   (-sw, sw, -sh, -sh + 0.006),
                                   (-sw, -sw + 0.006, -sh, sh),
                                   (sw - 0.006, sw, -sh, sh)):
                DirectFrame(parent=node, frameColor=STAMP_RED,
                            frameSize=(x0, x1, z0, z1))
            tn = TextNode('stamp_text')
            tn.setAlign(TextNode.ACenter)
            if self.f:
                tn.setFont(self.f)
            tn.setTextColor(*STAMP_RED)
            tn.setText(stamp)
            np_ = node.attachNewNode(tn)
            np_.setScale(0.044)
            np_.setPos(0, 0, -0.015)
        self.body_bot = -H + 0.240

    # ------------------------------------------------------ fittings
    def text(self, t, pos, scale=0.030, color=INK,
             align=TextNode.ALeft, wrap=None):
        tn = TextNode('form_text')
        tn.setAlign(align)
        if wrap:
            tn.setWordwrap(wrap)
        if self.f:
            tn.setFont(self.f)
        tn.setTextColor(*color)
        tn.setText(t)
        np_ = self.frame.attachNewNode(tn)
        np_.setPos(pos[0], 0, pos[1])
        np_.setScale(scale)
        return tn, np_

    def rule(self, x0, x1, z, thick=0.0022, color=INK):
        return DirectFrame(parent=self.frame, frameColor=color,
                           frameSize=(x0, x1, z - thick / 2.0,
                                      z + thick / 2.0))

    def vrule(self, x, z0, z1, thick=0.0022, color=INK):
        return DirectFrame(parent=self.frame, frameColor=color,
                           frameSize=(x - thick / 2.0,
                                      x + thick / 2.0, z0, z1))

    def header(self, t, pos, scale=0.032):
        """A dispatch-red section head, as the Quick Match sheet
        prints STRENGTHS and SERVICE ASSESSMENT."""
        return self.text(t, pos, scale, RED_INK)

    def flag(self, country, pos, hw=0.075):
        fr = DirectFrame(parent=self.frame, frameColor=(1, 1, 1, 1),
                         frameTexture=flag_tex(country),
                         frameSize=(-hw, hw, -hw * 2 / 3.0,
                                    hw * 2 / 3.0), pos=pos)
        return fr

    def keys(self, specs, end_tag=True):
        """The bottom key row: a rule, the keys, the transmission
        tag. specs = (label, command, extraArgs, x, kind, text_fg,
        half_width)."""
        W, H = self.W, self.H
        self.rule(-W + 0.08, W - 0.08, -H + 0.205, 0.0022)
        out = []
        for (label, cmd, args, x, kind, fg, hw) in specs:
            b = pill_button(self.frame, label, cmd,
                            extraArgs=list(args),
                            pos=(x, 0, -H + 0.118), hw=hw, hh=0.055,
                            text_scale=0.038, font=self.f, kind=kind,
                            text_fg=fg)
            out.append(b)
        if end_tag:
            self.text("++ END OF TRANSMISSION ++", (0, -H + 0.040),
                      0.023, INK_FAINT, TextNode.ACenter)
        return out

    def destroy(self):
        self.frame.destroy()


class BudgetFax:
    """The fortnight budget manifest — a large FAX form on which the
    commander allocates the appropriation across unit types, then
    TRANSMITs (locking the budget for two weeks) or DISCARDs."""

    def __init__(self, base, game, funds, unit_types, has_harbor,
                 on_transmit, on_discard, initial=None, subtitle=None,
                 mat_costs=None, stock=None):
        self.base = base
        self.game = game
        self.funds = int(funds)
        self.mat_costs = mat_costs or {}
        self.stock = stock or {}
        self.unit_types = unit_types
        self.has_harbor = has_harbor
        self.on_transmit = on_transmit
        self.on_discard = on_discard
        self.counts = {ut: 0 for ut in unit_types}
        if initial:                     # seed with the standing budget
            for ut, n in initial.items():
                if ut in self.counts:
                    self.counts[ut] = int(n)
        self.qty_tns = {}

        f = base.hud_font
        sheet = FormSheet(
            base, "BUDGET MANIFEST", half_w=1.30, half_h=0.92,
            from_line="THE EXCHEQUER, WAR APPROPRIATIONS",
            re_line="FORTNIGHT APPROPRIATION -- COMMIT BY RETURN "
                    "FACSIMILE")
        self.sheet = sheet
        self.frame = sheet.frame
        sheet.text(subtitle if subtitle else
                   "APPROPRIATION AVAILABLE: $%d   --   ONCE "
                   "TRANSMITTED THE BUDGET STANDS FOR TWO WEEKS."
                   % self.funds, (0, sheet.body_top), 0.028,
                   INK_FAINT, TextNode.ACenter)

        # two ruled columns of rows, a faint divider between them
        col_x = (-1.22, 0.06)
        row_y0 = sheet.body_top - 0.070
        rows = self._build_rows()
        per_col = (len(rows) + 1) // 2
        row_h = (row_y0 - (-0.615)) / max(1, per_col)
        sheet.vrule(-0.065, -0.640, row_y0 + 0.045, 0.0022,
                    INK_FAINT)
        for i, row in enumerate(rows):
            col = i // per_col
            y = row_y0 - (i % per_col) * row_h
            x = col_x[col]
            if row[0] == 'header':
                sheet.header(row[1], (x, y))
                sheet.rule(x, x + 1.16, y - 0.016, 0.0022, INK_FAINT)
                continue
            ut, stats, available = row[1], row[2], row[3]
            ipath = unit_ui_icon(ut)
            sprite = '/units/' in str(ipath).replace('\\\\', '/')
            ic = DirectButton(parent=self.frame, relief=None,
                              frameColor=(0, 0, 0, 0),
                              image=ipath,
                              image_scale=0.036,
                              frameSize=(-0.038, 0.038,
                                         -0.038, 0.038),
                              pos=(x + 0.028, 0, y + 0.009),
                              command=self.game.open_unit_briefing,
                              extraArgs=[ut])
            if sprite:
                ic['image_hpr'] = (0, 0, 45)
            ic.setTransparency(True)
            crisp_image(ic)
            add_tooltip(ic, "%s -- CLICK FOR THE SERVICE BRIEFING"
                        % stats['label'].upper(),
                        font=self.base.hud_font)
            sheet.text(stats['label'][:24], (x + 0.075, y), 0.028)
            mat = self.mat_costs.get(ut, {})
            cost_s = "$%d" % stats['cost']
            if mat.get('steel'):
                cost_s += " %dS" % mat['steel']
            sheet.text(cost_s, (x + 0.60, y), 0.024, INK_FAINT)
            if not available:
                sheet.text("NO HARBOR", (x + 0.84, y), 0.026,
                           INK_FAINT)
                continue
            pill_button(self.frame, "-", self._adjust,
                        extraArgs=[ut, -1],
                        pos=(x + 0.865, 0, y + 0.007),
                        hw=0.030, hh=0.030, text_scale=0.040, font=f,
                        kind='key')
            tn, _ = _make_text(self.frame, f, (x + 0.935, y), 0.032,
                               INK, TextNode.ACenter)
            tn.setText(str(self.counts.get(ut, 0)))
            self.qty_tns[ut] = tn
            pill_button(self.frame, "+", self._adjust,
                        extraArgs=[ut, +1],
                        pos=(x + 1.005, 0, y + 0.007),
                        hw=0.030, hh=0.030, text_scale=0.040, font=f,
                        kind='key')

        self.total_tn, _ = sheet.text("", (0, -0.672), 0.032, INK,
                                      TextNode.ACenter)
        self._refresh_totals()
        sheet.keys([
            ("++ TRANSMIT ++", self._transmit, (), -0.42, 'red',
             KEY_LIGHT, 0.30),
            ("-- DISCARD --", self._discard, (), 0.42, 'panel',
             (0.45, 0.12, 0.08, 1), 0.30),
        ])

    def _build_rows(self):
        rows = [('header', 'ARMY')]
        for ut, s in self.unit_types.items():
            if s['domain'] == 'land':
                rows.append(('unit', ut, s, True))
        rows.append(('header', 'NAVY'))
        for ut, s in self.unit_types.items():
            if s['domain'] == 'sea':
                rows.append(('unit', ut, s, self.has_harbor))
        rows.append(('header', 'AIR FORCE'))
        for ut, s in self.unit_types.items():
            if s['domain'] == 'air':
                rows.append(('unit', ut, s, True))
        return rows

    def _allocated(self):
        return sum(self.unit_types[ut]['cost'] * n
                   for ut, n in self.counts.items())

    def _mat_alloc(self, res):
        return sum(self.mat_costs.get(ut, {}).get(res, 0) * n
                   for ut, n in self.counts.items())

    def _adjust(self, ut, delta):
        cost = self.unit_types[ut]['cost']
        if delta > 0 and self._allocated() + cost > self.funds:
            return
        if delta > 0:
            mat = self.mat_costs.get(ut, {})
            for res in ('steel',):
                if (mat.get(res) and self.stock
                        and self._mat_alloc(res) + mat[res]
                        > self.stock.get(res, 0)):
                    return          # the yards lack the material
        self.counts[ut] = max(0, self.counts[ut] + delta)
        self.qty_tns[ut].setText(str(self.counts[ut]))
        self._refresh_totals()

    def _refresh_totals(self):
        alloc = self._allocated()
        self.total_tn.setText(
            "ALLOCATED $%d   OF   $%d   (REMAINDER $%d CARRIES FORWARD)"
            % (alloc, self.funds, self.funds - alloc))

    def _transmit(self):
        self.on_transmit(dict(self.counts))

    def _discard(self):
        self.on_discard()

    def destroy(self):
        self.frame.destroy()


class BriefingFax:
    """A read-only field-service briefing sheet — a large FAX the
    commander files after reading.  Body is a list of text lines."""

    # a sheet of letter paper (8.5 x 11), portrait
    HALF_H = 0.82
    HALF_W = HALF_H * 8.5 / 11.0
    MARGIN_X = 0.06

    def __init__(self, base, title, lines, on_close, icon_ut=None):
        self.base = base
        self.on_close = on_close
        f = base.hud_font
        W, H = self.HALF_W, self.HALF_H
        self.frame = DirectFrame(parent=base.aspect2d, frameColor=(1, 1, 1, 1),
                                 frameTexture=sheet_tex('paper'),
                                 frameSize=(-W, W, -H, H),
                                 state=DGG.NORMAL)
        DirectFrame(parent=self.frame, frameColor=PAPER_EDGE,
                    frameSize=(-W, W, H - 0.02, H))
        if icon_ut:
            # THE SUBJECT'S OWN MARK, large, on the sheet's shoulder
            ipath = unit_ui_icon(icon_ut)
            sprite = '/units/' in str(ipath).replace('\\\\', '/')
            ic = DirectFrame(parent=self.frame, relief=None,
                             frameColor=(0, 0, 0, 0),
                             image=ipath, image_scale=0.155,
                             frameSize=(-0.16, 0.16, -0.16, 0.16),
                             pos=(W - 0.24, 0, H - 0.30),
                             state=DGG.DISABLED)
            if sprite:
                ic['image_hpr'] = (0, 0, 45)
            ic.setTransparency(True)
            crisp_image(ic)

        def measure(txt):
            tn = TextNode('m')
            if f:
                tn.setFont(f)
            tn.setText(txt)
            return tn.getWidth()

        # size the text so the widest line fills most of the page width
        text_w = 2.0 * W - 2.0 * self.MARGIN_X
        widest = max((measure(ln[1:] if ln.startswith('#') else ln)
                      for ln in lines if ln), default=1.0)
        body_scale = min(0.046, text_w / max(widest, 1e-3))
        title_scale = min(body_scale * 1.2,
                          text_w / max(measure(title), 1e-3))

        top = H - 0.075
        head, _ = _make_text(self.frame, f, (0, top - title_scale),
                             title_scale, INK, TextNode.ACenter)
        head.setText(title)
        rule_y = top - title_scale * 2.2
        dash_w = measure("-") * body_scale
        rule, _ = _make_text(self.frame, f, (0, rule_y), body_scale,
                             INK_FAINT, TextNode.ACenter)
        rule.setText("-" * int(text_w / max(dash_w, 1e-3)))

        # leading spreads the lines to fill the height (within reason)
        btn_top = -H + 0.13
        body_top = rule_y - body_scale * 1.8
        avail = body_top - btn_top
        weight = sum(1.0 if ln else 0.5 for ln in lines) or 1.0
        leading = max(body_scale * 1.35,
                      min(body_scale * 2.1, avail / weight))

        x0 = -W + self.MARGIN_X
        y = body_top
        for ln in lines:
            color = INK
            if ln.startswith('#'):        # sub-heading
                ln = ln[1:]
                color = (0.42, 0.10, 0.06, 1.0)
            tn, _ = _make_text(self.frame, f, (x0, y), body_scale, color)
            tn.setText(ln)
            y -= leading if ln else leading * 0.55

        pill_button(self.frame, "++ FILE AND ACKNOWLEDGE ++",
                    self._close, pos=(0, 0, -H + 0.064),
                    hw=W - 0.06, hh=0.049, text_scale=0.038,
                    text_fg=(0.1, 0.25, 0.1, 1), font=f)

    def _close(self):
        self.on_close()

    def destroy(self):
        self.frame.destroy()


class TaxFax:
    """Tax decree form for one city: set the rate 0-100%%, see the
    projected fortnight remittance and industry drift. Binds from the
    NEXT fortnight."""

    def __init__(self, base, city, on_transmit, on_discard):
        from config import TAX_EQUILIBRIUM
        self.base = base
        self.city = city
        self.on_transmit = on_transmit
        self.on_discard = on_discard
        self.rate = (city.pending_tax if city.pending_tax is not None
                     else city.tax_rate)

        f = base.hud_font
        sheet = FormSheet(
            base, "TAX DECREE -- %s" % city.name.upper(),
            half_w=1.00, half_h=0.78,
            from_line="THE EXCHEQUER, REVENUE BRANCH",
            re_line="RATE OF TAXATION UPON THE MUNICIPALITY")
        self.sheet = sheet
        self.frame = sheet.frame

        # LEFT: the municipal record, as a ruled table
        lx0, lx1 = -0.92, -0.12
        sheet.header("THE MUNICIPAL RECORD", (lx0, sheet.body_top))
        rows = [("POPULATION", "{:,}".format(city.population)),
                ("INDUSTRY HEALTH", "%.0f%%" % city.industry),
                ("PRESENT RATE", "%d%%" % city.tax_rate)]
        ry = sheet.body_top - 0.070
        for label, val in rows:
            sheet.text(label, (lx0, ry), 0.030)
            sheet.text(val, (lx1, ry), 0.030, INK,
                       TextNode.ARight)
            sheet.rule(lx0, lx1, ry - 0.022, 0.0016, INK_FAINT)
            ry -= 0.078
        sheet.text("AT %d%% THE INDUSTRY HOLDS;\nBELOW IT HEALS; "
                   "ABOVE IT DECAYS." % TAX_EQUILIBRIUM,
                   (lx0, ry - 0.015), 0.026, INK_FAINT)
        sheet.vrule(0.0, -0.38, sheet.body_top + 0.03, 0.0022,
                    INK_FAINT)

        # RIGHT: the rate, set by key
        rx = 0.50
        sheet.header("RATE OF TAXATION", (0.12, sheet.body_top))
        pill_button(self.frame, "-", self._adjust, extraArgs=[-5],
                    pos=(rx - 0.28, 0, sheet.body_top - 0.155),
                    hw=0.045, hh=0.043, text_scale=0.052, font=f,
                    kind='key')
        self.rate_tn, _ = sheet.text(
            "", (rx, sheet.body_top - 0.175), 0.080, INK,
            TextNode.ACenter)
        pill_button(self.frame, "+", self._adjust, extraArgs=[+5],
                    pos=(rx + 0.28, 0, sheet.body_top - 0.155),
                    hw=0.045, hh=0.043, text_scale=0.052, font=f,
                    kind='key')
        self.proj_tn, _ = sheet.text("", (0.12, -0.235), 0.028, INK)
        self.drift_tn, _ = sheet.text("", (0.12, -0.290), 0.028, INK)
        self._refresh()

        sheet.text("THE DECREE BINDS FROM THE NEXT FORTNIGHT.",
                   (0, -0.415), 0.026, INK_FAINT, TextNode.ACenter)
        sheet.keys([
            ("++ TRANSMIT ++", self._transmit, (), -0.34, 'red',
             KEY_LIGHT, 0.27),
            ("-- DISCARD --", self._discard, (), 0.34, 'panel',
             (0.45, 0.12, 0.08, 1), 0.27),
        ])

    def _adjust(self, delta):
        self.rate = max(0, min(100, self.rate + delta))
        self._refresh()

    def _refresh(self):
        self.rate_tn.setText("%d%%" % self.rate)
        self.proj_tn.setText(
            "PROJECTED FORTNIGHT REMITTANCE: $%d"
            % self.city.fortnight_revenue(self.rate))
        drift = self.city.industry_drift(self.rate)
        self.drift_tn.setText(
            "EXPECTED INDUSTRY DRIFT: %+.1f%% PER FORTNIGHT" % drift)

    def _transmit(self):
        self.on_transmit(self.city, self.rate)

    def _discard(self):
        self.on_discard()

    def destroy(self):
        self.frame.destroy()


class DraftFax:
    """The CIVILIAN DRAFT for one city: pick a number of sections
    and they muster AT ONCE. The rolls are free; every man beyond
    them is conscription and the town's industry pays a head, all
    the way down to nought. The rolls refill at the fortnight."""

    def __init__(self, base, city, on_transmit, on_discard):
        from config import DRAFT_INDUSTRY_GRIND
        self.base = base
        self.city = city
        self.on_transmit = on_transmit
        self.on_discard = on_discard
        self.grind = DRAFT_INDUSTRY_GRIND
        self.ceiling = base.draft_ceiling(city)
        self.n = min(city.draft_pool, self.ceiling)

        f = base.hud_font
        sheet = FormSheet(
            base, "CIVILIAN DRAFT -- %s" % city.name.upper(),
            half_w=1.00, half_h=0.78,
            from_line="THE RECRUITING OFFICE",
            re_line="IMMEDIATE MUSTER OF THE MUNICIPALITY")
        self.sheet = sheet
        self.frame = sheet.frame

        # LEFT: the recruiting record, as a ruled table
        lx0, lx1 = -0.92, -0.12
        sheet.header("THE RECRUITING RECORD", (lx0, sheet.body_top))
        rows = [("POPULATION", "{:,}".format(city.population)),
                ("ON THE ROLLS, FREE", "%d SECTION(S)"
                 % city.draft_pool),
                ("INDUSTRY HEALTH", "%.0f%%" % city.industry)]
        ry = sheet.body_top - 0.070
        for label, val in rows:
            sheet.text(label, (lx0, ry), 0.030)
            sheet.text(val, (lx1, ry), 0.030, INK, TextNode.ARight)
            sheet.rule(lx0, lx1, ry - 0.022, 0.0016, INK_FAINT)
            ry -= 0.078
        sheet.text("THE ROLLS REFILL AT THE FORTNIGHT.  BEYOND "
                   "THEM\nIS CONSCRIPTION: -%.1f%% INDUSTRY A "
                   "SECTION,\nDOWN TO NOUGHT." % self.grind,
                   (lx0, ry - 0.015), 0.026, INK_FAINT)
        sheet.vrule(0.0, -0.38, sheet.body_top + 0.03, 0.0022,
                    INK_FAINT)

        # RIGHT: the muster, set by key
        rx = 0.50
        sheet.header("SECTIONS TO MUSTER AT ONCE",
                     (0.12, sheet.body_top))
        for dx, d, lbl in ((-0.38, -5, "-5"), (-0.24, -1, "-"),
                           (0.24, +1, "+"), (0.38, +5, "+5")):
            pill_button(self.frame, lbl, self._adjust, extraArgs=[d],
                        pos=(rx + dx, 0, sheet.body_top - 0.155),
                        hw=0.052, hh=0.043, text_scale=0.042, font=f,
                        kind='key')
        self.n_tn, _ = sheet.text(
            "", (rx, sheet.body_top - 0.185), 0.085, INK,
            TextNode.ACenter)
        self.cost_tn, _ = sheet.text("", (0.12, -0.225), 0.022, INK,
                                     wrap=36)
        self.cap_tn, _ = sheet.text("", (0.12, -0.305), 0.022,
                                    INK_FAINT, wrap=36)
        self._refresh()

        sheet.text("EVERY MUSTER STILL WANTS ITS RATIONS -- 4 TONS "
                   "OF FOOD THE SECTION.", (0, -0.415), 0.026,
                   INK_FAINT, TextNode.ACenter)
        sheet.keys([
            ("++ MUSTER ++", self._transmit, (), -0.34, 'red',
             KEY_LIGHT, 0.27),
            ("-- DISCARD --", self._discard, (), 0.34, 'panel',
             (0.45, 0.12, 0.08, 1), 0.27),
        ])

    def _adjust(self, d):
        self.n = max(0, min(self.ceiling, self.n + d))
        self._refresh()

    def _refresh(self):
        self.n_tn.setText("%d" % self.n)
        free = min(self.n, self.city.draft_pool)
        cons = self.n - free
        if cons > 0:
            after = max(0.0, self.city.industry - cons * self.grind)
            self.cost_tn.setText(
                "%d FROM THE ROLLS (FREE)  +  %d CONSCRIPTED  "
                "--  INDUSTRY %.0f%% -> %.0f%%"
                % (free, cons, self.city.industry, after))
        else:
            self.cost_tn.setText(
                "%d FROM THE ROLLS -- FREE, INDUSTRY UNTOUCHED"
                % free)
        self.cap_tn.setText(
            "THE TOWN CAN RAISE AT MOST %d SECTION(S) BEFORE "
            "INDUSTRY STANDS AT NOUGHT" % self.ceiling)

    def _transmit(self):
        self.on_transmit(self.city, self.n)

    def _discard(self):
        self.on_discard()

    def destroy(self):
        self.frame.destroy()


class CityFocusFax:
    """THE CITY LEDGER: the town's three permanent tracks with
    their level pips, its food balance, and the one directive it
    works at this fortnight -- picked here."""

    def __init__(self, base, city, on_transmit, on_discard):
        from config import (FOCUS_FINANCE_HEAL, TRACK_MAX_LEVEL,
                            AGRI_FOOD_CUM, WORKS_SPEED_MULT,
                            LAB_YIELD_MULT, CIVIL_RATION,
                            OCCUPIED_RATION, BUDGET_PERIOD_DAYS,
                            FOCUS_RESEARCH_RP_PER_M,
                            FOCUS_RESEARCH_RP_MIN, BASE_COSTS)
        self.base = base
        self.city = city
        self.on_transmit = on_transmit
        self.on_discard = on_discard
        self.choice = city.focus
        g = base
        f = base.hud_font

        rp = max(FOCUS_RESEARCH_RP_MIN,
                 city.population / 1e6 * FOCUS_RESEARCH_RP_PER_M) \
            * LAB_YIELD_MULT[city.labs_level]
        heal_rev = int(city.gross_product() * FOCUS_FINANCE_HEAL
                       / 100.0 * city.tax_rate / 100.0)

        def track_note(track, table, unit_word):
            lvl = g.city_track_level(city, track)
            cost = g.track_upgrade_cost(city, track)
            if cost is None:
                return "AT THE TOP -- LEVEL %d" % lvl, False
            return ("NEXT: %s -- $%d, ONE FORTNIGHT"
                    % (g._track_gain_word(city, track), cost)), True

        agri_note, agri_ok = track_note('agriculture', AGRI_FOOD_CUM,
                                        'T FOOD')
        works_note, works_ok = track_note('works', WORKS_SPEED_MULT,
                                          '')
        labs_note, labs_ok = track_note('laboratories',
                                        LAB_YIELD_MULT, '')
        rows = [
            ('finance', "INVEST IN FINANCE",
             "+%.0f INDUSTRY -- REVENUE RISES ~$%d/FTN"
             % (FOCUS_FINANCE_HEAL, heal_rev), True, None),
            ('agriculture', "WORK THE LAND", agri_note, agri_ok,
             city.agri_level),
            ('works', "EXPAND THE WORKS", works_note, works_ok,
             city.works_level),
            ('laboratories', "BUILD THE LABORATORIES", labs_note,
             labs_ok, city.labs_level),
            ('research', "RUN THE LABORATORIES",
             "+%.0f RESEARCH POINTS EACH FORTNIGHT (x%.1f LABS)"
             % (rp, LAB_YIELD_MULT[city.labs_level]), True, None),
        ]
        for kind, label in (('army', "RAISE AN ARMY BASE"),
                            ('air', "RAISE AN AIRFORCE BASE"),
                            ('naval', "RAISE A NAVAL BASE")):
            cost, steel = BASE_COSTS[kind]
            have = g.base_of_city(city, kind) is not None
            possible = not have and (kind != 'naval' or city.harbor)
            note = ("ALREADY STANDS" if have else
                    "WANTS OPEN WATER -- NOT A PORT TOWN"
                    if kind == 'naval' and not city.harbor else
                    "$%d + %d STEEL -- ONE FORTNIGHT, ONCE ONLY"
                    % (cost, steel))
            rows.append(('base_%s' % kind, label, note, possible,
                         None))
        self.rows = rows

        sheet = FormSheet(
            base, "CITY LEDGER -- %s" % city.name.upper(),
            half_w=1.30, half_h=0.92,
            from_line="THE TOWN CLERK, %s" % city.name.upper(),
            re_line="THE TOWN WORKS AT ONE DIRECTIVE A FORTNIGHT")
        self.sheet = sheet
        self.frame = sheet.frame

        # THE FOOD BALANCE: what this town grows against what it eats
        grows = g.city_food_output(city)
        ration = OCCUPIED_RATION if city.annexing else CIVIL_RATION
        eats = (city.population / 1e6) * ration * BUDGET_PERIOD_DAYS
        bal = grows - eats
        sheet.text(
            "THE TOWN GROWS %d T OF FOOD A FORTNIGHT AND ITS "
            "MOUTHS EAT %d -- NET %+d T"
            % (grows, int(round(eats)), int(round(bal))),
            (0, sheet.body_top + 0.006), 0.026,
            (GREEN_INK if bal >= 0 else (0.62, 0.14, 0.10, 1.0)),
            TextNode.ACenter)

        # the directive table: DIRECTIVE | LEVEL | EFFECT | STATUS
        cx_d, cx_p, cx_e, cx_s = -1.22, -0.34, 0.02, 1.02
        top = sheet.body_top - 0.052
        sheet.header("DIRECTIVE", (cx_d, top))
        sheet.header("LEVEL", (cx_p, top))
        sheet.header("EFFECT AT THIS TOWN", (cx_e, top))
        sheet.header("STATUS", (cx_s + 0.08, top), 0.032)
        sheet.rule(cx_d, 1.22, top - 0.022, 0.0022)
        table_bot = top - 0.062 - 8 * 0.0705 + 0.028
        sheet.vrule(-0.38, table_bot, top - 0.022, 0.0016, INK_FAINT)
        sheet.vrule(-0.02, table_bot, top - 0.022, 0.0016, INK_FAINT)
        sheet.vrule(0.96, table_bot, top - 0.022, 0.0016, INK_FAINT)

        self.marks = {}
        y = top - 0.062
        row_h = 0.0705
        for key, label, note, possible, level in rows:
            if possible:
                pill_button(self.frame, label, self._pick,
                            extraArgs=[key],
                            pos=(-0.81, 0, y), hw=0.39, hh=0.030,
                            text_scale=0.026, font=f)
            else:
                sheet.text(label, (-0.81, y - 0.010), 0.026,
                           INK_FAINT, TextNode.ACenter)
            if level is not None:
                from config import TRACK_MAX_LEVEL as _TM
                for k in range(_TM):
                    filled = (k < level)
                    sq = DirectFrame(
                        parent=self.frame,
                        frameColor=(INK if filled else
                                    (INK[0], INK[1], INK[2], 0.15)),
                        frameSize=(-0.012, 0.012, -0.012, 0.012),
                        pos=(cx_p + 0.02 + k * 0.055, 0, y))
            sheet.text(note, (cx_e, y - 0.010), 0.023, INK_FAINT)
            mk, _ = sheet.text("", (cx_s + 0.09, y - 0.010), 0.026,
                               GREEN_INK, TextNode.ACenter)
            self.marks[key] = mk
            y -= row_h
            sheet.rule(cx_d, 1.22, y + row_h - 0.042, 0.0012,
                       (INK[0], INK[1], INK[2], 0.25))

        self._refresh()
        sheet.keys([
            ("++ SET THE FOCUS ++", self._transmit, (), -0.44,
             'red', KEY_LIGHT, 0.32),
            ("-- LEAVE AS IT STANDS --", self._discard, (), 0.44,
             'panel', (0.45, 0.12, 0.08, 1), 0.32),
        ])

    def _pick(self, key):
        self.choice = key
        self._refresh()

    def _refresh(self):
        for key, mk in self.marks.items():
            mk.setText("<< CHOSEN" if key == self.choice else
                       ("(STANDING)" if key == self.city.focus
                        and key != self.choice else ""))

    def _transmit(self):
        self.on_transmit(self.city, self.choice)

    def _discard(self):
        self.on_discard()

    def destroy(self):
        self.frame.destroy()


class EnvoyFax:
    """A FOREIGN ENVOY IN THE ANTEROOM. He has laid a sheet on the
    table: what his nation offers, what it asks in return. Nothing
    binds us until the pen moves -- ACCEPT or SEND HIM AWAY."""

    def __init__(self, base, nat, gives, wants, on_accept, on_decline):
        import deals as _d
        from config import short_name, COUNTRIES
        self.base = base
        self.on_accept = on_accept
        self.on_decline = on_decline
        sheet = FormSheet(
            base, "AN ENVOY OF %s CALLS" % short_name(nat).upper(),
            half_w=1.00, half_h=0.78,
            from_line="THE FOREIGN OFFICE OF %s"
                      % COUNTRIES[nat]['name'].upper(),
            re_line="TERMS LAID BEFORE US -- NOTHING BINDS UNTIL "
                    "WE SIGN")
        self.sheet = sheet
        self.frame = sheet.frame
        sheet.flag(nat, (-0.83, 0, sheet.H - 0.155), hw=0.062)

        # the terms, two ruled columns: what they give, what they ask
        def side(title, tokens, x0):
            sheet.header(title, (x0, sheet.body_top))
            y = sheet.body_top - 0.062
            if not tokens:
                sheet.text("NOTHING", (x0 + 0.02, y), 0.028,
                           INK_FAINT)
                return
            for tok in tokens[:6]:
                sheet.text("+ %s" % _d.token_text(tok).upper(),
                           (x0 + 0.02, y), 0.027, INK)
                y -= 0.052

        side("THEY OFFER", gives, -0.92)
        side("THEY ASK IN RETURN", wants, 0.10)
        sheet.vrule(0.0, -0.28, sheet.body_top + 0.03, 0.0022,
                    INK_FAINT)
        sheet.rule(-0.92, 0.92, -0.32, 0.0022, INK_FAINT)

        worth = _d.basket_value(gives) - _d.basket_value(wants)
        if worth >= 0:
            note = ("OUR OWN VALUERS MAKE THIS SHEET FAVOURABLE "
                    "TO US.")
            col = GREEN_INK
        else:
            note = "OUR OWN VALUERS MAKE THIS SHEET COSTLY TO US."
            col = (0.62, 0.14, 0.10, 1.0)
        sheet.text(note, (0, -0.385), 0.028, col, TextNode.ACenter)
        sheet.keys([
            ("++ ACCEPT THE TERMS ++", on_accept, (), -0.34, 'red',
             KEY_LIGHT, 0.29),
            ("-- SEND HIM AWAY --", on_decline, (), 0.34, 'panel',
             (0.45, 0.12, 0.08, 1), 0.29),
        ])

    def destroy(self):
        self.frame.destroy()


class ProductionFax:
    """War-industries state, LIVE: grouped ARMY / AIR FORCE / NAVY,
    one row per unit type in this fortnight's order with a
    delivered/ordered tally and a progress bar for the item of that
    type nearest to delivery. The figures refresh while the page is
    open -- the manifest is a wire to the factory floor, not a
    photograph of it."""

    BAR_W = 0.40

    def __init__(self, base, sections, on_close, bottlenecks=()):
        self.base = base
        self.on_close = on_close
        self.bottlenecks = list(bottlenecks)
        self.f = base.hud_font
        sheet = FormSheet(
            base, "WAR INDUSTRIES -- PRODUCTION STATE",
            half_w=1.30, half_h=0.92,
            from_line="THE MINISTRY OF SUPPLY",
            re_line="THE FORTNIGHT ORDER, LIVE FROM THE FACTORY "
                    "FLOOR")
        self.sheet = sheet
        self.frame = sheet.frame
        self.head_tn, _ = sheet.text("", (0, sheet.body_top), 0.030,
                                     INK_FAINT, TextNode.ACenter)
        # BOTTLENECKS lead the page: halted lines are the news
        self._bneck_drop = 0.0
        if self.bottlenecks:
            by = sheet.body_top - 0.062
            sheet.header("BOTTLENECKS -- LINES HALTED FOR "
                         "MATERIALS", (-1.22, by))
            shown = self.bottlenecks[:3]
            for i, line in enumerate(shown):
                sheet.text(line + (
                    "   (+%d MORE)" % (len(self.bottlenecks) - 3)
                    if i == len(shown) - 1
                    and len(self.bottlenecks) > 3 else ""),
                    (-1.20, by - 0.048 - i * 0.042), 0.027,
                    INK_FAINT)
            self._bneck_drop = 0.062 + 0.048 + len(shown) * 0.042
        sheet.keys([
            ("++ FILE AND ACKNOWLEDGE ++", self._close, (), 0,
             'panel', INK, 0.42),
        ])
        self._grid = []             # destroyable widgets of the grid
        self._widgets = {}          # label -> (tally_tn, fill, pct_tn)
        self._keys = None
        self.update(sections)

    # ------------------------------------------------------------ live
    def update(self, sections):
        """Refresh the figures in place; rebuild the grid only when the
        set of lines itself changes (a new fortnight order)."""
        done_all = sum(r[2] for _s, rows in sections for r in rows)
        total_all = sum(r[3] for _s, rows in sections for r in rows)
        self.head_tn.setText("FORTNIGHT ORDER: %d OF %d ITEMS DELIVERED"
                             % (done_all, total_all))
        keys = tuple((s, r[0]) for s, rows in sections for r in rows)
        if keys != self._keys:
            self._keys = keys
            self._build_grid(sections)
            return
        for _sec, rows in sections:
            for (label, _icon, done, total, prog) in rows:
                if label not in self._widgets:
                    continue        # overflowed the sheet
                tally, fill, pct = self._widgets[label]
                tally.setText("%d/%d" % (done, total))
                w = max(0.0, min(1.0, prog)) * self.BAR_W
                if w > 0.003:
                    fill.show()
                    fill['frameSize'] = (0, w, -0.009, 0.009)
                else:
                    fill.hide()
                pct.setText("%d%%" % int(prog * 100))

    def _build_grid(self, sections):
        for w in self._grid:
            w.destroy() if hasattr(w, 'destroy') else w.removeNode()
        self._grid = []
        self._widgets = {}

        def text(t, pos, scale=0.032, color=INK, align=TextNode.ALeft):
            tn, np_ = self.sheet.text(t, pos, scale, color, align)
            self._grid.append(np_)
            return tn

        # flatten sections into grid slots: a branch header, then rows
        slots = []
        for sec_label, rows in sections:
            if rows:
                slots.append(('H', sec_label))
                slots.extend(('R',) + r for r in rows)
        if not slots:
            text("ALL PRODUCTION LINES IDLE.", (0, 0.20), 0.04, INK,
                 TextNode.ACenter)
            text("THE NEXT FORTNIGHT APPROPRIATION WILL SET THEM "
                 "TURNING AGAIN.", (0, 0.12), 0.030, INK_FAINT,
                 TextNode.ACenter)
            return

        col_x = (-1.22, 0.06)
        row_y0 = (self.sheet.body_top - 0.075
                  - getattr(self, '_bneck_drop', 0.0))
        row_h = (row_y0 + 0.60) / 11.0
        per_col = 11
        div = DirectFrame(parent=self.frame,
                          frameColor=(INK[0], INK[1], INK[2], 0.35),
                          frameSize=(-0.0011, 0.0011, -0.640,
                                     row_y0 + 0.050))
        div.setPos(-0.065, 0, 0)
        self._grid.append(div)
        for i, slot in enumerate(slots[:22]):
            col = i // per_col
            x = col_x[col]
            y = row_y0 - (i % per_col) * row_h
            if slot[0] == 'H':
                text("%s" % slot[1], (x, y), 0.030,
                     (0.52, 0.10, 0.06, 1.0))
                r = DirectFrame(parent=self.frame,
                                frameColor=(INK[0], INK[1], INK[2],
                                            0.35),
                                frameSize=(x, x + 1.16, y - 0.017,
                                           y - 0.0148))
                self._grid.append(r)
                continue
            _tag, label, icon, done, total, prog = slot
            ic = DirectFrame(parent=self.frame, relief=None,
                             frameColor=(0, 0, 0, 0), image=icon,
                             image_scale=0.036,
                             frameSize=(-0.04, 0.04, -0.04, 0.04),
                             pos=(x + 0.035, 0, y - 0.012))
            crisp_image(ic)
            ic.setTransparency(True)
            self._grid.append(ic)
            text(label[:24], (x + 0.085, y), 0.028)
            tally = text("%d/%d" % (done, total), (x + 1.14, y),
                         0.030, INK, TextNode.ARight)
            bx = x + 0.085
            back = DirectFrame(parent=self.frame,
                               frameColor=(0.72, 0.68, 0.56, 1.0),
                               frameSize=(0, self.BAR_W, -0.009, 0.009),
                               pos=(bx, 0, y - 0.045))
            self._grid.append(back)
            fill = DirectFrame(parent=self.frame,
                               frameColor=(0.35, 0.28, 0.16, 1.0),
                               frameSize=(0, max(0.004,
                                                 min(1.0, prog)
                                                 * self.BAR_W),
                                          -0.009, 0.009),
                               pos=(bx, 0, y - 0.045))
            self._grid.append(fill)
            if prog <= 0.008:
                fill.hide()
            pct = text("%d%%" % int(prog * 100),
                       (bx + self.BAR_W + 0.03, y - 0.056), 0.024,
                       INK_FAINT)
            self._widgets[label] = (tally, fill, pct)

    def _close(self):
        self.on_close()

    def destroy(self):
        self.frame.destroy()


class ResourcesFax:
    """The quartermaster's ledger: what the nation holds, where it
    comes from, what the fortnight has drunk so far -- and the plain
    statement of how stores and oil relate."""

    def __init__(self, base, data, on_close):
        self.base = base
        self.on_close = on_close
        sheet = FormSheet(
            base, "STRATEGIC RESOURCES", half_w=1.30, half_h=0.92,
            from_line="THE QUARTERMASTER GENERAL",
            re_line="STOCKS ON HAND, THE FORTNIGHT'S TAKE, AND THE "
                    "PUMPS")
        self.sheet = sheet
        self.frame = sheet.frame
        text = sheet.text

        top = sheet.body_top
        net_top = -0.245
        cols = {'oil': -0.86, 'steel': 0.0, 'food': 0.86}
        for vx in (-0.43, 0.43):
            sheet.vrule(vx, net_top + 0.035, top + 0.035, 0.0022,
                        INK_FAINT)
        for res, cx in cols.items():
            d = data[res]
            sheet.header(res.upper(), (cx, top), 0.042)
            text("%d TONS IN STOCK" % d['stock'], (cx, top - 0.065),
                 0.034, INK, TextNode.ACenter)
            sheet.rule(cx - 0.33, cx + 0.33, top - 0.095, 0.0016,
                       INK_FAINT)
            y = top - 0.140
            text("THE TAKE (PER FORTNIGHT, PAID DAILY):",
                 (cx - 0.36, y), 0.025, INK_FAINT)
            y -= 0.046
            for name, n in d['income'][:6]:
                text("%s +%d" % (name, n), (cx - 0.32, y), 0.026)
                y -= 0.042
            if d['more_income']:
                text("+%d MORE SITES" % d['more_income'],
                     (cx - 0.32, y), 0.024, INK_FAINT)
                y -= 0.042
            text("SPENT SO FAR THIS FORTNIGHT: %d" % d['spent'],
                 (cx - 0.36, y - 0.010), 0.025,
                 (0.62, 0.14, 0.10, 1.0))
            y -= 0.066
            if d['foreign']:
                text("FOREIGN SOURCES OF NOTE:", (cx - 0.36, y),
                     0.024, INK_FAINT)
                y -= 0.042
                for name, owner, n in d['foreign'][:3]:
                    text("%s +%d  (%s)" % (name, n, owner),
                         (cx - 0.32, y), 0.023, INK_FAINT)
                    y -= 0.038
        # THE SUPPLY NET: the plain statement of the relationship
        ry = net_top
        sheet.rule(-1.22, 1.22, ry, 0.0022)
        sheet.header("THE SUPPLY NET", (-1.22, ry - 0.052))
        text("%s LBS OF STORES IN TOWN AND STATION STOCKS   //   "
             "%s LBS ABOARD THE COLUMNS AND FLEETS"
             % ("{:,}".format(data['net_stocks']),
                "{:,}".format(data['unit_stores'])),
             (0, ry - 0.110), 0.027, INK_FAINT, TextNode.ACenter)
        text("THE PUMPS: %s LBS ISSUED TO MACHINES SO FAR THIS "
             "FORTNIGHT DREW %d TONS OF OIL"
             % ("{:,}".format(int(data['pump_lbs'])),
                int(data['pump_oil'])),
             (0, ry - 0.158), 0.027, INK_FAINT, TextNode.ACenter)
        text("ONE TON OF OIL MOVES 1,250 LBS OF STORES INTO A "
             "MACHINE -- MEN AND THE RAILWAYS DRAW NONE",
             (0, ry - 0.206), 0.027, INK, TextNode.ACenter)
        if data.get('ration'):
            text(data['ration'], (0, ry - 0.250), 0.027, INK,
                 TextNode.ACenter)
        if data.get('trade'):
            sheet.header("IMPORTS & EXPORTS BY TREATY",
                         (-1.22, ry - 0.302), 0.028)
            for i, line in enumerate(data['trade'][:4]):
                text(line, (-1.18 + (i % 2) * 1.20,
                            ry - 0.350 - (i // 2) * 0.045),
                     0.025, INK_FAINT)
        sheet.keys([
            ("++ FILE AND ACKNOWLEDGE ++", self._close, (), 0,
             'panel', INK, 0.42),
        ])
        snd = getattr(base, 'fax_snd', None)
        if snd is not None:
            snd.play()

    def _close(self):
        cb = self.on_close
        self.on_close = None
        if cb:
            cb()

    def destroy(self):
        self.frame.destroy()


class TechFax:
    """THE RESEARCH CHART: the nation's programmes as a branching
    tree -- three columns (ARMY / AIR / NAVY), nodes wired to their
    prerequisites, states plainly stamped: DELIVERED, a RESEARCH
    key when the points stand, or the prerequisite that still bars
    the way. The funding row sets the fortnight tithe."""

    CARD_W = 0.20               # half-width of a node card
    CARD_TOP = 0.042
    CARD_BOT = 0.150

    # chart placement: node -> (dx within its column, visual row)
    POS = {
        'artillery': (0.0, 0), 'heavy_armour': (-0.21, 1),
        'detection': (0.21, 1),
        'medium_bombers': (0.0, 0), 'air_logistics': (-0.21, 1),
        'strategic_bombing': (0.21, 1), 'jet_propulsion': (0.21, 2),
        'naval_gunnery': (0.0, 0), 'submarines': (-0.21, 1),
        'capital_gunnery': (0.21, 1), 'naval_aviation': (0.21, 2),
    }
    COL_X = {'land': -0.84, 'air': 0.0, 'sea': 0.84}
    ROW_Y = (0.175, -0.135, -0.445)

    def __init__(self, base, game, on_close):
        self.base = base
        self.game = game
        self.on_close = on_close
        self.sheet = FormSheet(
            base, "THE RESEARCH CHART", half_w=1.30, half_h=0.95,
            from_line="THE DIRECTORATE OF SCIENTIFIC RESEARCH",
            re_line="THE NATION'S PROGRAMMES AND THE POINTS IN "
                    "HAND")
        self.frame = self.sheet.frame
        self._dyn = []
        self._build()
        self.sheet.keys([
            ("++ FILE AND ACKNOWLEDGE ++", self.on_close, (), 0,
             'panel', INK, 0.42),
        ])

    def _text(self, t, pos, scale=0.032, color=INK,
              align=TextNode.ALeft):
        tn, np_ = _make_text(self.frame, self.base.hud_font, pos,
                             scale, color, align)
        tn.setText(t)
        self._dyn.append(np_)
        return tn

    def _rule(self, x, y, w, h, color=(0.44, 0.41, 0.33, 0.75)):
        fr = DirectFrame(parent=self.frame, frameColor=color,
                         frameSize=(-w / 2, w / 2, -h / 2, h / 2),
                         pos=(x, 0, y))
        self._dyn.append(fr)
        return fr

    def _node_pos(self, nid):
        """Where a node's card stands. A node added to the graph
        without a place on the chart falls to the middle of its row
        rather than taking the whole page down with it."""
        from tech import NODES
        node = NODES[nid]
        dx, row = self.POS.get(nid, (0.0, node['row']))
        return (self.COL_X[node['branch']] + dx,
                self.ROW_Y[min(row, len(self.ROW_Y) - 1)])

    def _build(self):
        from tech import (NODES, available_nodes, node_name,
                          normalize)
        from config import (FOCUS_RESEARCH_RP_PER_M,
                            FOCUS_RESEARCH_RP_MIN)
        from units import stats_for
        from icons import get_icon_path
        g = self.game
        c = g.player_country
        for w in self._dyn:
            w.destroy() if hasattr(w, 'destroy') else w.removeNode()
        self._dyn = []
        g.researched[c] = normalize(g.researched[c])
        have = g.researched[c]
        frontier = set(available_nodes(have))
        rp = g.research_points[c]
        labs = [x for x in g.cities
                if x.country == c and x.focus == 'research'
                and not x.annexing]
        from config import LAB_YIELD_MULT as _LYM
        yield_rp = sum(max(FOCUS_RESEARCH_RP_MIN,
                           x.population / 1e6 * FOCUS_RESEARCH_RP_PER_M)
                       * _LYM[getattr(x, 'labs_level', 0)]
                       for x in labs)

        top = self.sheet.body_top
        self._text("POINTS ON HAND: %.0f RP" % rp, (0, top), 0.032,
                   (0.52, 0.10, 0.06, 1.0), TextNode.ACenter)
        # THE POINTS COME FROM THE TOWNS, and only from the towns:
        # a city set on the laboratories works its fortnight for
        # the chart instead of the treasury
        if labs:
            names = ", ".join(x.name.upper() for x in labs[:4])
            if len(labs) > 4:
                names += " AND %d MORE" % (len(labs) - 4)
            line = ("AT WORK FOR THE CHART: %s  --  %.0f RP A "
                    "FORTNIGHT" % (names, yield_rp))
            colour = (0.16, 0.38, 0.14, 1.0)
        else:
            line = ("NO TOWN IS WORKING FOR THE CHART -- SET A "
                    "TOWN'S FORTNIGHT FOCUS ON THE LABORATORIES")
            colour = (0.62, 0.14, 0.10, 1.0)
        self._text(line, (0, top - 0.048), 0.026, colour,
                   TextNode.ACenter)
        self._text("A PROGRAMME OPENS WHEN EVERY PROGRAMME WIRED "
                   "ABOVE IT IS DELIVERED -- CHOOSE THE PATH; THE "
                   "POINTS WILL NOT COVER EVERYTHING AT ONCE",
                   (0, top - 0.090), 0.023, INK_FAINT,
                   TextNode.ACenter)

        for branch, title in (('land', "ARMY PROGRAMMES"),
                              ('air', "AIR PROGRAMMES"),
                              ('sea', "NAVAL PROGRAMMES")):
            x = self.COL_X[branch]
            self._text(title, (x, top - 0.165), 0.032,
                       (0.52, 0.10, 0.06, 1.0), TextNode.ACenter)
            self._rule(x, top - 0.187, 0.78, 0.0030,
                       (0.44, 0.41, 0.33, 0.5))

        # the WIRING first, so cards sit over the lines
        for nid, node in NODES.items():
            cx, cy = self._node_pos(nid)
            for req in node['req']:
                px, py = self._node_pos(req)
                top = cy + self.CARD_TOP
                bot = py - self.CARD_BOT
                mid = (top + bot) / 2.0
                lit = ((0.25, 0.42, 0.22, 0.9)
                       if req in have else (0.44, 0.41, 0.33, 0.55))
                self._rule(px, (bot + mid) / 2, 0.004,
                           bot - mid, lit)
                if abs(px - cx) > 0.001:
                    self._rule((px + cx) / 2, mid,
                               abs(px - cx) + 0.004, 0.004, lit)
                self._rule(cx, (mid + top) / 2, 0.004,
                           mid - top, lit)

        for nid, node in NODES.items():
            cx, cy = self._node_pos(nid)
            done = nid in have
            avail = nid in frontier
            can = avail and rp >= node['cost']
            box = DirectFrame(
                parent=self.frame,
                frameColor=((0.79, 0.76, 0.63, 1.0) if done else
                            (0.92, 0.89, 0.76, 1.0) if avail else
                            (0.86, 0.83, 0.71, 1.0)),
                frameSize=(-self.CARD_W, self.CARD_W,
                           -self.CARD_BOT, self.CARD_TOP),
                pos=(cx, 0, cy))
            self._dyn.append(box)
            edge = DirectFrame(
                parent=self.frame,
                frameColor=((0.25, 0.42, 0.22, 0.9) if done
                            else (0.30, 0.27, 0.22, 0.8) if avail
                            else (0.44, 0.41, 0.33, 0.4)),
                frameSize=(-self.CARD_W, self.CARD_W,
                           self.CARD_TOP - 0.006, self.CARD_TOP),
                pos=(cx, 0, cy))
            self._dyn.append(edge)
            name = node_name(c, nid)
            self._text(name, (cx, cy + 0.006),
                       0.0215 if len(name) > 22 else 0.024,
                       INK if (done or avail) else INK_FAINT,
                       TextNode.ACenter)
            shown = [u for u in node['unlocks']
                     if u != 'radar_station']
            for k, u in enumerate(shown[:3]):
                ipath = unit_ui_icon(u)
                sprite = '/units/' in str(ipath).replace('\\\\', '/')
                ic = DirectButton(
                    parent=self.frame, relief=None,
                    frameColor=(0, 0, 0, 0),
                    image=ipath,
                    image_scale=0.042 if sprite else 0.036,
                    frameSize=(-0.040, 0.040, -0.040, 0.040),
                    pos=(cx - self.CARD_W + 0.052 + k * 0.084,
                         0, cy - 0.042),
                    command=self.game.open_unit_briefing,
                    extraArgs=[u])
                if sprite:
                    ic['image_hpr'] = (0, 0, 45)
                ic.setTransparency(True)
                crisp_image(ic)
                add_tooltip(ic, "%s -- CLICK FOR THE SERVICE "
                            "BRIEFING"
                            % stats_for(u, self.game.player_country
                                        )['label'].upper(),
                            font=self.base.hud_font)
                if not (done or avail):
                    ic.setColorScale(1, 1, 1, 0.35)
                self._dyn.append(ic)
            lbl = ", ".join(
                ('Radar Station (works)' if u == 'radar_station'
                 else stats_for(u, c)['label'])
                for u in node['unlocks'])
            self._text(lbl[:34], (cx, cy - 0.083), 0.020,
                       INK_FAINT, TextNode.ACenter)
            if done:
                self._text("-- DELIVERED --", (cx, cy - 0.128),
                           0.024, (0.25, 0.40, 0.22, 1.0),
                           TextNode.ACenter)
            elif avail and can:
                btn = pill_button(
                    self.frame, "RESEARCH  %d RP" % node['cost'],
                    self._research, extraArgs=[nid],
                    pos=(cx, 0, cy - 0.122), hw=0.155, hh=0.031,
                    text_scale=0.024, font=self.base.hud_font)
                self._dyn.append(btn)
            elif avail:
                self._text("WANTS %d RP -- HAVE %.0f"
                           % (node['cost'], rp),
                           (cx, cy - 0.128), 0.022,
                           (0.55, 0.28, 0.20, 1.0),
                           TextNode.ACenter)
            else:
                bar = node_name(c, node['req'][0]) \
                    if node['req'] else ""
                self._text("AFTER %s" % bar[:24],
                           (cx, cy - 0.128), 0.020, INK_FAINT,
                           TextNode.ACenter)

    def _research(self, nid):
        g = self.game
        if g.research_node(g.player_country, nid):
            self._build()

    def destroy(self):
        self.frame.destroy()
