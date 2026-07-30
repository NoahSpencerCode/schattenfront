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
from panda3d.core import SamplerState, TextNode

from icons import get_icon_path, sheet_texture


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
        tex.setAnisotropicDegree(4)
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
                    frameTexture=sheet_texture('plate'),
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
        ('RUBBER', -0.69, TextNode.ALeft),
        ('FORCES', -0.47, TextNode.ALeft),
        ('CITIES', -0.29, TextNode.ALeft),
        ('TIME', 0.10, TextNode.ACenter),
        ('[OUT OF CONTACT]', 0.54, TextNode.ACenter),
        ('KILLS', 0.84, TextNode.ACenter),
        ('LOSSES', 1.02, TextNode.ACenter),
        ('SPEED', 1.20, TextNode.ACenter),
    ]

    RESOURCE_COLS = ('OIL', 'STEEL', 'RUBBER')

    def __init__(self, base, on_budget, on_factory=None,
                 on_resources=None):
        self.base = base
        self.frame = DirectFrame(parent=base.a2dTopCenter,
                                 frameColor=(1, 1, 1, 0.92),
                                 frameTexture=sheet_texture('bar'),
                                 frameSize=(-2.0, 2.0, -0.155, 0.0),
                                 state=DGG.NORMAL)
        self.frame.setTransparency(True)
        self.values = {}
        for (title, x, align) in self.COLUMNS:
            head, _ = _make_text(self.frame, base.hud_font,
                                 (x, -0.048), 0.024,
                                 (0.55, 0.53, 0.45, 1.0), align)
            head.setText(title)
            color = (ALERT if title == '[OUT OF CONTACT]'
                     else (ACCENT if title == 'TIME' else BAR_TEXT))
            val, _ = _make_text(self.frame, base.hud_font,
                                (x, -0.118), 0.040, color, align)
            self.values[title] = val
        self.budget_btn = pill_button(
            self.frame, "BUDGET", on_budget, pos=(1.44, 0, -0.068),
            hw=0.155, hh=0.037, text_scale=0.034, font=base.hud_font)
        # war-industries report, beside the budget: a proper console
        # key, not a bare pictogram floating on the panel
        self.factory_btn = pill_button(
            self.frame, '', on_factory, pos=(1.645, 0, -0.062),
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
            self.frame, '', on_resources, pos=(1.755, 0, -0.062),
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
        # fourteen dots: the days of the running fortnight
        self.day_dots = []
        for i in range(14):
            x = 1.44 - 0.169 + i * 0.026
            dot = DirectFrame(parent=self.frame,
                              frameColor=(0.32, 0.30, 0.26, 1.0),
                              frameSize=(-0.008, 0.008, -0.008, 0.008),
                              pos=(x, 0, -0.132))
            self.day_dots.append(dot)
        self._fortnight_day = 0
        # the RESOURCE STRIP explains itself on hover: each column
        # carries an invisible plate whose tooltip itemizes the flow
        self.res_tips = {}
        for res, x, _a in self.COLUMNS:
            if res not in self.RESOURCE_COLS:
                continue
            hov = DirectButton(parent=self.frame, relief=None,
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
        self.frame = DirectFrame(parent=base.a2dBottomCenter,
                                 frameColor=(1, 1, 1, 0.92),
                                 frameTexture=sheet_texture('bar'),
                                 frameSize=(-1.35, 1.35, 0.0, 0.35),
                                 state=DGG.NORMAL)
        self.frame.setTransparency(True)
        self.title_tn, _ = _make_text(self.frame, base.hud_font,
                                      (-1.30, 0.290), 0.05, ACCENT)
        self.info_tn, _ = _make_text(self.frame, base.hud_font,
                                     (-1.30, 0.225), 0.036, BAR_TEXT)
        self.info_tn.setText('')
        # the SIGNALS line rides above the bar: short despatches
        # ("REPORTING FOR DUTY", refused orders) print here and fade,
        # never touching the selection's own info line
        self.signal_tn, _ = _make_text(self.frame, base.hud_font,
                                       (-1.30, 0.360), 0.034,
                                       (0.95, 0.82, 0.48, 1.0))
        self.signal_tn.setText('')
        self.hint_tn, _ = _make_text(self.frame, base.hud_font,
                                     (-1.30, 0.035), 0.033,
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

    def add_buttons(self, entries):
        """entries: (label, command, extraArgs[, icon_path[, selected
        [, tip[, dim]]]]).  Every control is a SQUARE console key
        bearing an icon; the full name rides a hover tooltip and a
        short label (an hp readout, a cost) prints as a caption under
        the icon.  A truthy 'selected' draws a white halo.  A truthy
        'dim' greys the whole key out -- not ready (no crew, still on
        the ways); the tooltip still explains why. Two rows of 16."""
        self.clear_buttons()
        self.set_hint('')
        per_row = 16
        side = 0.050
        for i, entry in enumerate(entries[:32]):
            label, command, args = entry[0], entry[1], entry[2]
            icon = entry[3] if len(entry) > 3 else None
            selected = entry[4] if len(entry) > 4 else False
            tip = entry[5] if len(entry) > 5 else label
            dim = entry[6] if len(entry) > 6 else False
            row, col = divmod(i, per_row)
            x = -1.19 + col * 0.112
            y = 0.166 - row * 0.112
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
                # chip; a bare key wears the icon dead centre
                pic_z = 0.012 if (label and len(label) <= 8) else 0.0
                pic = OnscreenImage(image=icon, parent=btn,
                                    scale=0.044, pos=(0, 0, pic_z))
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
                                 frameTexture=sheet_texture('newsprint'),
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
        self.frame = DirectFrame(parent=game.aspect2d,
                                 frameColor=(1, 1, 1, 1),
                                 frameTexture=sheet_texture('paper'),
                                 frameSize=(-1.42, 1.42, -0.86, 0.86),
                                 state=DGG.NORMAL)
        DirectFrame(parent=self.frame, frameColor=PAPER_EDGE,
                    frameSize=(-1.42, 1.42, 0.835, 0.86))
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
        self._text("++ DIPLOMATIC LEDGER ++", (0, 0.76), 0.05,
                   align=TextNode.ACenter, keep=True)
        self._text("FOREIGN OFFICE -- MOST SECRET", (0, 0.70), 0.026,
                   color=INK_FAINT, align=TextNode.ACenter, keep=True)
        pill_button(self.frame, "CLOSE [ESC]",
                    lambda: self.on_close(), pos=(1.16, 0, 0.775),
                    hw=0.17, hh=0.040, font=self.base.hud_font,
                    kind='red')

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
        if view is None:
            self._build_roster()
        else:
            self._build_dossier(view)

    def _open_dossier(self, nat):
        self.view = nat
        self.rebuild()

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
            y = 0.55 - row * 0.27
            self._card(nat, x, y)
            at_war = g.at_war(me, nat)
            allied = g.allied(me, nat)
            self._text(short_name(nat).upper(), (x, y - 0.100),
                       0.032, align=TextNode.ACenter)
            if at_war or allied:
                self._text("AT WAR" if at_war else "ALLY",
                           (x, y - 0.140), 0.026,
                           color=((0.62, 0.14, 0.10, 1) if at_war
                                  else (0.16, 0.35, 0.14, 1)),
                           align=TextNode.ACenter)
        # THE WARS RAGING: the right edge is a battle-board -- each
        # war a pair of standards crossed by the swords
        wx = 1.18
        self._text("++ WARS RAGING ++", (wx, 0.63), 0.040,
                   color=(0.62, 0.14, 0.10, 1),
                   align=TextNode.ACenter)
        wars = sorted({tuple(sorted(w)) for w in g.wars})
        if not wars:
            self._text("ALL QUIET ON EVERY FRONT", (wx, 0.50),
                       0.026, color=INK_FAINT,
                       align=TextNode.ACenter)
        for i, (a, b) in enumerate(wars[:8]):
            wy = 0.49 - i * 0.165
            for nat, dx in ((a, -0.115), (b, 0.115)):
                chip = DirectFrame(parent=self.frame, relief=None,
                                   frameColor=(0, 0, 0, 0),
                                   image=flag_texture(nat),
                                   image_scale=(0.050, 1, 0.0333),
                                   frameSize=(-0.05, 0.05,
                                              -0.034, 0.034),
                                   pos=(wx + dx, 0, wy))
                chip.setTransparency(True)
                crisp_image(chip)
                self.widgets.append(chip)
            swords = DirectFrame(parent=self.frame, relief=None,
                                 frameColor=(0, 0, 0, 0),
                                 image=get_icon_path('crossed_swords',
                                                     'dark'),
                                 image_scale=0.036,
                                 frameSize=(-0.04, 0.04,
                                            -0.04, 0.04),
                                 pos=(wx, 0, wy))
            swords.setTransparency(True)
            crisp_image(swords)
            self.widgets.append(swords)
            self._text("%s v %s" % (short_name(a).upper(),
                                    short_name(b).upper()),
                       (wx, wy - 0.070), 0.021,
                       color=INK_FAINT, align=TextNode.ACenter)
        if len(wars) > 8:
            self._text("AND %d MORE FRONTS AFLAME"
                       % (len(wars) - 8),
                       (wx, 0.49 - 8 * 0.165), 0.023,
                       color=(0.62, 0.14, 0.10, 1),
                       align=TextNode.ACenter)
        self._text("CLICK A NATION FOR ITS DOSSIER -- WAR, PACTS "
                   "AND TERMS ARE OFFERED THERE",
                   (-0.10, -0.80), 0.026, color=INK_FAINT,
                   align=TextNode.ACenter)

    def _build_dossier(self, nat):
        g = self.game
        from config import short_name
        me = g.player_country
        b = pill_button(self.frame, "<< THE WORLD",
                        self._open_dossier, extraArgs=[None],
                        pos=(-1.16, 0, 0.775), hw=0.17, hh=0.040,
                        font=self.base.hud_font)
        self.widgets.append(b)
        # the nation, writ large
        self._card(nat, -0.98, 0.42, big=True)
        self._text(short_name(nat).upper(), (-0.72, 0.46), 0.075)
        self._text(self._COUNTRIES[nat]['name'].upper(),
                   (-0.72, 0.36), 0.028, color=INK_FAINT)
        at_war = g.at_war(me, nat)
        allied = g.allied(me, nat)
        stance = ("AT WAR WITH US" if at_war else
                  "OUR ALLY" if allied else "AT PEACE WITH US")
        self._text(stance, (-0.72, 0.28), 0.040,
                   color=((0.62, 0.14, 0.10, 1) if at_war else
                          (0.16, 0.35, 0.14, 1) if allied
                          else INK_FAINT))
        # their wars and their pacts, in full
        all_nats = [c for c in self._COUNTRIES if c != 'neutral']
        wars = [o for o in all_nats
                if o != nat and g.at_war(nat, o)]
        pacts = [o for o in sorted(g.alliances.get(nat, ()))
                 if o != nat]
        self._text("AT WAR WITH:", (-1.10, 0.10), 0.032)
        if wars:
            for i, o in enumerate(wars[:8]):
                self._text(short_name(o).upper(),
                           (-0.78, 0.10 - i * 0.055), 0.030,
                           color=(0.62, 0.14, 0.10, 1))
        else:
            self._text("NOBODY", (-0.78, 0.10), 0.030,
                       color=INK_FAINT)
        py0 = 0.10 - max(1, min(len(wars), 8)) * 0.055 - 0.06
        self._text("BOUND TO:", (-1.10, py0), 0.032)
        if pacts:
            for i, o in enumerate(pacts[:6]):
                self._text(short_name(o).upper(),
                           (-0.78, py0 - i * 0.055), 0.030,
                           color=(0.16, 0.35, 0.14, 1))
        else:
            self._text("NOBODY", (-0.78, py0), 0.030,
                       color=INK_FAINT)
        # the keys, big and few, on the right half
        kx, f = 0.62, self.base.hud_font
        if g.pouch_pending(nat) is not None:
            self._text("COURIER EN ROUTE -- THE ANSWER COMES BY "
                       "RETURN POUCH", (kx, 0.10), 0.030,
                       color=INK_FAINT, align=TextNode.ACenter)
        elif allied:
            price = g.volunteer_price(nat)
            b = pill_button(self.frame,
                            "REQUEST VOLUNTEERS%s" %
                            (" ($%d)" % price if price else " (FREE)"),
                            g._diplo_action,
                            extraArgs=['volunteers', nat],
                            pos=(kx, 0, 0.16), hw=0.42, hh=0.062,
                            text_scale=0.036, font=f)
            self.widgets.append(b)
            b = pill_button(self.frame, "BREAK THE PACT",
                            g._diplo_break, extraArgs=[nat],
                            pos=(kx, 0, 0.00), hw=0.42, hh=0.062,
                            text_scale=0.036, font=f, kind='red',
                            text_fg=(0.97, 0.90, 0.80, 1.0))
            self.widgets.append(b)
        elif at_war:
            b = pill_button(self.frame, "OFFER PEACE",
                            g._diplo_action,
                            extraArgs=['peace', nat],
                            pos=(kx, 0, 0.10), hw=0.42, hh=0.070,
                            text_scale=0.042, font=f)
            self.widgets.append(b)
        else:
            b = pill_button(self.frame, "PROPOSE ALLIANCE",
                            g._diplo_action,
                            extraArgs=['alliance', nat],
                            pos=(kx, 0, 0.16), hw=0.42, hh=0.062,
                            text_scale=0.038, font=f)
            self.widgets.append(b)
            b = pill_button(self.frame, "DECLARE WAR",
                            g._diplo_action,
                            extraArgs=['war', nat],
                            pos=(kx, 0, 0.00), hw=0.42, hh=0.062,
                            text_scale=0.038, font=f, kind='red',
                            text_fg=(0.97, 0.90, 0.80, 1.0))
            self.widgets.append(b)
        # THE TRADE LEDGER: buy their surplus, sell them yours;
        # every standing line printed with its cancel key
        from config import TRADE_STEPS
        if not at_war:
            ty = -0.24
            self._text("++ TRADE ++", (kx, ty), 0.036,
                       align=TextNode.ACenter)
            ty -= 0.062
            for res in ('oil', 'steel', 'rubber'):
                cap = g.seller_capacity(nat, res)
                self._text("%s:" % res.upper(), (kx - 0.42, ty),
                           0.028)
                if cap > 0:
                    for j, amt in enumerate(TRADE_STEPS):
                        if amt > cap:
                            continue
                        price = int(amt * g.trade_price(nat, res,
                                                        'in'))
                        b = pill_button(
                            self.frame, "BUY %d ($%d)" % (amt, price),
                            g.propose_trade,
                            extraArgs=[nat, res, amt, 'in'],
                            pos=(kx - 0.10 + j * 0.30, 0, ty + 0.008),
                            hw=0.135, hh=0.036, text_scale=0.022,
                            font=f)
                        self.widgets.append(b)
                else:
                    self._text("NONE TO SELL", (kx - 0.10, ty),
                               0.024, color=INK_FAINT)
                if nat in self._PLAYABLE:
                    price = int(TRADE_STEPS[0]
                                * g.trade_price(nat, res, 'out'))
                    b = pill_button(
                        self.frame, "SELL %d ($%d)"
                        % (TRADE_STEPS[0], price),
                        g.propose_trade,
                        extraArgs=[nat, res, TRADE_STEPS[0], 'out'],
                        pos=(kx + 0.44, 0, ty + 0.008),
                        hw=0.135, hh=0.036, text_scale=0.022, font=f)
                    self.widgets.append(b)
                ty -= 0.075
            deals = [t for t in g.trade_deals if t['with'] == nat]
            for deal in deals[:3]:
                word = ("IMPORTING %d %s ($%d/FTN)"
                        if deal['dir'] == 'in' else
                        "EXPORTING %d %s (+$%d/FTN)") % (
                    deal['amount'], deal['res'].upper(),
                    deal['price'])
                self._text(word, (kx - 0.42, ty), 0.025,
                           color=(0.16, 0.35, 0.14, 1.0))
                b = pill_button(self.frame, "CANCEL",
                                g.cancel_trade, extraArgs=[deal],
                                pos=(kx + 0.34, 0, ty + 0.008),
                                hw=0.085, hh=0.030,
                                text_scale=0.022, font=f,
                                kind='red',
                                text_fg=(0.97, 0.90, 0.80, 1.0))
                self.widgets.append(b)
                ty -= 0.062
        self._text("DISPATCHES TRAVEL BY COURIER AND ARE ANSWERED "
                   "IN KIND -- TRADE IS SETTLED EACH FORTNIGHT",
                   (0, -0.80), 0.026, color=INK_FAINT,
                   align=TextNode.ACenter)

    def destroy(self):
        self.frame.destroy()


class _Toast:
    """One field signal: a small sheet of paper that slides up, holds,
    and files itself away."""

    SLIDE_TIME = 0.22
    HOLD_TIME = 11.0
    # letter-paper proportions (8.5 x 11), trimmed so two stacked
    # sheets still clear both bars now the bottom bar sits taller
    WIDTH = 0.54
    HEIGHT = 0.54 * 11.0 / 8.5

    def __init__(self, panel, subject, body_lines, sender, stamp):
        self.panel = panel
        panel.toasts.append(self)       # register before first placement
        base = panel.base
        self.width = self.WIDTH
        self.height = self.HEIGHT
        self.age = 0.0
        self.leaving = False
        self.leave_age = 0.0

        self.frame = DirectFrame(parent=base.a2dBottomLeft,
                                 frameColor=(1, 1, 1, 1),
                                 frameTexture=sheet_texture('paper'),
                                 frameSize=(0, self.width, 0, self.height),
                                 state=DGG.NORMAL)
        DirectFrame(parent=self.frame, frameColor=PAPER_EDGE,
                    frameSize=(0, self.width, self.height - 0.012,
                               self.height))
        head, _ = _make_text(self.frame, base.hud_font,
                             (0.04, self.height - 0.075), 0.032, INK)
        head.setText(subject)
        rule, _ = _make_text(self.frame, base.hud_font,
                             (0.04, self.height - 0.115), 0.028, INK_FAINT)
        rule.setText("-" * 24)
        body, _ = _make_text(self.frame, base.hud_font,
                             (0.04, self.height - 0.165), 0.0345,
                             (0.05, 0.04, 0.03, 1.0))
        body.setText('\n'.join(body_lines))
        foot, _ = _make_text(self.frame, base.hud_font,
                             (self.width / 2, 0.030), 0.022, INK_FAINT,
                             TextNode.ACenter)
        foot.setText("%s\n%s" % (sender, stamp))
        self.frame.setTransparency(True)
        self.frame.bind(DGG.B1PRESS, self._click)
        self._place(0.0)

    def _slot_y(self):
        # stacked above the bottom bar, lowest slot first
        return 0.40 + sum(t.height + 0.012 for t in
                          self.panel.toasts[:self.panel.toasts.index(self)])

    def _place(self, rise):
        y = self._slot_y()
        self.frame.setPos(0.06, 0, y - (1.0 - rise) * (self.height + 0.12))

    def _click(self, event=None):
        self.leaving = True

    def update(self, dt):
        """Returns False when the toast is finished."""
        self.age += dt
        if not self.leaving:
            rise = min(1.0, self.age / self.SLIDE_TIME)
            self._place(rise)
            self.frame.setAlphaScale(min(1.0, rise * 1.5))
            if self.age > self.SLIDE_TIME + self.HOLD_TIME:
                self.leaving = True
            return True
        self.leave_age += dt
        k = self.leave_age / self.SLIDE_TIME
        if k >= 1.0:
            self.frame.destroy()
            return False
        self._place(1.0)
        self.frame.setX(0.06 - k * (self.width + 0.1))
        self.frame.setAlphaScale(1.0 - k)
        return True

    def destroy(self):
        self.frame.destroy()


class FaxPanel:
    """Field signals: brief FAX slips that slide up from the bottom-left
    corner, hold a few seconds, and file themselves away.  Use ui.B()
    to bold the words that matter."""

    MAX_VISIBLE = 2
    WRAP = 26

    def __init__(self, base):
        self.base = base
        self.queue = []
        self.toasts = []

    def post(self, subject, body, sender="SUPREME HQ"):
        snd = getattr(self.base, 'fax_snd', None)
        if snd is not None:
            snd.play()
        stamp = self.base.campaign_clock_text() \
            if hasattr(self.base, 'campaign_clock_text') else ''
        lines = []
        for para in body.split('\n'):
            # wrap on the visible length (markup chars are zero-width)
            lines.extend(_wrap_markup(para.upper(), self.WRAP))
        self.queue.append(("++ %s ++" % subject.upper(), lines[:7],
                           sender.upper(), stamp))

    def update(self, dt):
        for t in list(self.toasts):
            if not t.update(dt):
                self.toasts.remove(t)
        while self.queue and len(self.toasts) < self.MAX_VISIBLE:
            subject, lines, sender, stamp = self.queue.pop(0)
            _Toast(self, subject, lines, sender, stamp)

    def dismiss(self):
        for t in self.toasts:
            t.leaving = True

    def destroy(self):
        for t in self.toasts:
            t.destroy()
        self.toasts = []
        self.queue = []


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
        self.frame = DirectFrame(parent=base.aspect2d, frameColor=(1, 1, 1, 1),
                                 frameTexture=sheet_texture('paper'),
                                 frameSize=(-1.18, 1.18, -0.92, 0.92),
                                 state=DGG.NORMAL)
        DirectFrame(parent=self.frame, frameColor=PAPER_EDGE,
                    frameSize=(-1.18, 1.18, 0.895, 0.92))

        def text(t, pos, scale=0.034, color=INK, align=TextNode.ALeft):
            tn, _ = _make_text(self.frame, f, pos, scale, color, align)
            tn.setText(t)
            return tn

        text("*** BUDGET MANIFEST -- FORTNIGHT APPROPRIATION ***",
             (0, 0.83), 0.045, INK, TextNode.ACenter)
        text("FROM : THE EXCHEQUER, WAR APPROPRIATIONS", (-1.10, 0.76))
        text("RE   : ALLOCATION OF FUNDS -- COMMIT BY RETURN FAX",
             (-1.10, 0.71))
        text(subtitle if subtitle else
             "APPROPRIATION AVAILABLE: $%d   ONCE TRANSMITTED THE BUDGET "
             "STANDS FOR TWO WEEKS." % self.funds, (-1.10, 0.66), 0.030,
             INK_FAINT)
        text("-" * 78, (0, 0.62), 0.034, INK, TextNode.ACenter)

        # two columns of rows
        col_x = (-1.10, 0.10)
        row_y0 = 0.545
        row_h = 0.077
        rows = self._build_rows()
        per_col = (len(rows) + 1) // 2
        for i, row in enumerate(rows):
            col = i // per_col
            y = row_y0 - (i % per_col) * row_h
            x = col_x[col]
            if row[0] == 'header':
                text(row[1], (x, y), 0.036, INK_FAINT)
                continue
            ut, stats, available = row[1], row[2], row[3]
            ic = DirectFrame(parent=self.frame, relief=None,
                             frameColor=(0, 0, 0, 0),
                             image=get_icon_path(ut, 'dark'),
                             image_scale=0.026,
                             frameSize=(-0.027, 0.027, -0.027, 0.027),
                             pos=(x + 0.024, 0, y + 0.009))
            ic.setTransparency(True)
            crisp_image(ic)
            text(stats['label'][:24], (x + 0.06, y), 0.030)
            mat = self.mat_costs.get(ut, {})
            cost_s = "$%d" % stats['cost']
            if mat.get('steel'):
                cost_s += " %dS" % mat['steel']
            if mat.get('rubber'):
                cost_s += " %dR" % mat['rubber']
            text(cost_s, (x + 0.56, y), 0.024, INK_FAINT)
            if not available:
                text("NO HARBOR", (x + 0.80, y), 0.028, INK_FAINT)
                continue
            pill_button(self.frame, "-", self._adjust,
                        extraArgs=[ut, -1], pos=(x + 0.815, 0, y + 0.007),
                        hw=0.030, hh=0.030, text_scale=0.040, font=f,
                        kind='key')
            tn, _ = _make_text(self.frame, f, (x + 0.885, y), 0.032, INK,
                               TextNode.ACenter)
            tn.setText(str(self.counts.get(ut, 0)))
            self.qty_tns[ut] = tn
            pill_button(self.frame, "+", self._adjust,
                        extraArgs=[ut, +1], pos=(x + 0.955, 0, y + 0.007),
                        hw=0.030, hh=0.030, text_scale=0.040, font=f,
                        kind='key')

        text("-" * 78, (0, -0.70), 0.034, INK, TextNode.ACenter)
        self.total_tn, _ = _make_text(self.frame, f, (0, -0.755), 0.036,
                                      INK, TextNode.ACenter)
        self._refresh_totals()

        pill_button(self.frame, "++ TRANSMIT ++", self._transmit,
                    pos=(-0.40, 0, -0.842), hw=0.30, hh=0.047,
                    text_scale=0.042, text_fg=(0.10, 0.25, 0.10, 1),
                    font=f)
        pill_button(self.frame, "-- DISCARD --", self._discard,
                    pos=(0.40, 0, -0.842), hw=0.30, hh=0.047,
                    text_scale=0.042, text_fg=(0.45, 0.12, 0.08, 1),
                    font=f)

    def _build_rows(self):
        rows = [('header', '--- ARMY ---')]
        for ut, s in self.unit_types.items():
            if s['domain'] == 'land':
                rows.append(('unit', ut, s, True))
        rows.append(('header', '--- NAVY ---'))
        for ut, s in self.unit_types.items():
            if s['domain'] == 'sea':
                rows.append(('unit', ut, s, self.has_harbor))
        rows.append(('header', '--- AIR FORCE ---'))
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
            for res in ('steel', 'rubber'):
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

    def __init__(self, base, title, lines, on_close):
        self.base = base
        self.on_close = on_close
        f = base.hud_font
        W, H = self.HALF_W, self.HALF_H
        self.frame = DirectFrame(parent=base.aspect2d, frameColor=(1, 1, 1, 1),
                                 frameTexture=sheet_texture('paper'),
                                 frameSize=(-W, W, -H, H),
                                 state=DGG.NORMAL)
        DirectFrame(parent=self.frame, frameColor=PAPER_EDGE,
                    frameSize=(-W, W, H - 0.02, H))

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
        self.frame = DirectFrame(parent=base.aspect2d, frameColor=(1, 1, 1, 1),
                                 frameTexture=sheet_texture('paper'),
                                 frameSize=(-0.85, 0.85, -0.62, 0.62),
                                 state=DGG.NORMAL)
        DirectFrame(parent=self.frame, frameColor=PAPER_EDGE,
                    frameSize=(-0.85, 0.85, 0.595, 0.62))

        def text(t, pos, scale=0.036, color=INK, align=TextNode.ALeft):
            tn, _ = _make_text(self.frame, f, pos, scale, color, align)
            tn.setText(t)
            return tn

        text("*** TAX DECREE -- %s ***" % city.name.upper(),
             (0, 0.52), 0.048, INK, TextNode.ACenter)
        text("FROM : THE EXCHEQUER, REVENUE BRANCH", (-0.78, 0.44))
        text("RE   : RATE OF TAXATION UPON THE MUNICIPALITY",
             (-0.78, 0.39))
        text("-" * 56, (0, 0.345), 0.036, INK, TextNode.ACenter)
        text("POPULATION ......... %s" % "{:,}".format(city.population),
             (-0.78, 0.28))
        text("INDUSTRY HEALTH .... %.0f%%" % city.industry, (-0.78, 0.22))
        text("PRESENT RATE ....... %d%%" % city.tax_rate, (-0.78, 0.16))
        text("AT %d%% THE INDUSTRY HOLDS; BELOW IT HEALS; ABOVE IT "
             "DECAYS." % TAX_EQUILIBRIUM, (-0.78, 0.10), 0.028, INK_FAINT)

        pill_button(self.frame, "-", self._adjust, extraArgs=[-5],
                    pos=(-0.30, 0, -0.041), hw=0.045, hh=0.043,
                    text_scale=0.052, font=f, kind='key')
        self.rate_tn, _ = _make_text(self.frame, f, (0, -0.055), 0.075,
                                     INK, TextNode.ACenter)
        pill_button(self.frame, "+", self._adjust, extraArgs=[+5],
                    pos=(0.30, 0, -0.041), hw=0.045, hh=0.043,
                    text_scale=0.052, font=f, kind='key')

        self.proj_tn, _ = _make_text(self.frame, f, (0, -0.20), 0.034,
                                     INK, TextNode.ACenter)
        self.drift_tn, _ = _make_text(self.frame, f, (0, -0.26), 0.034,
                                      INK, TextNode.ACenter)
        text("THE DECREE BINDS FROM THE NEXT FORTNIGHT.", (0, -0.34),
             0.030, INK_FAINT, TextNode.ACenter)
        self._refresh()

        pill_button(self.frame, "++ TRANSMIT ++", self._transmit,
                    pos=(-0.32, 0, -0.492), hw=0.26, hh=0.044,
                    text_scale=0.040, text_fg=(0.1, 0.25, 0.1, 1),
                    font=f)
        pill_button(self.frame, "-- DISCARD --", self._discard,
                    pos=(0.32, 0, -0.492), hw=0.26, hh=0.044,
                    text_scale=0.040, text_fg=(0.45, 0.12, 0.08, 1),
                    font=f)

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
        self.frame = DirectFrame(parent=base.aspect2d, frameColor=(1, 1, 1, 1),
                                 frameTexture=sheet_texture('paper'),
                                 frameSize=(-1.12, 1.12, -0.88, 0.88),
                                 state=DGG.NORMAL)
        DirectFrame(parent=self.frame, frameColor=PAPER_EDGE,
                    frameSize=(-1.12, 1.12, 0.855, 0.88))
        tn, _ = _make_text(self.frame, self.f, (0, 0.78), 0.045, INK,
                           TextNode.ACenter)
        tn.setText("*** WAR INDUSTRIES -- PRODUCTION STATE ***")
        self.head_tn, _ = _make_text(self.frame, self.f, (0, 0.70),
                                     0.032, INK_FAINT, TextNode.ACenter)
        tn, _ = _make_text(self.frame, self.f, (0, 0.655), 0.032, INK,
                           TextNode.ACenter)
        tn.setText("-" * 74)
        # BOTTLENECKS lead the page: halted lines are the news
        self._bneck_drop = 0.0
        if self.bottlenecks:
            by = 0.595
            tn, _ = _make_text(self.frame, self.f, (-1.04, by), 0.032,
                               (0.62, 0.14, 0.10, 1.0))
            tn.setText("++ BOTTLENECKS -- LINES HALTED FOR "
                       "MATERIALS ++")
            shown = self.bottlenecks[:3]
            for i, line in enumerate(shown):
                tn, _ = _make_text(self.frame, self.f,
                                   (-1.04, by - 0.048 - i * 0.042),
                                   0.027, INK_FAINT)
                tn.setText(line + (
                    "   (+%d MORE)" % (len(self.bottlenecks) - 3)
                    if i == len(shown) - 1
                    and len(self.bottlenecks) > 3 else ""))
            self._bneck_drop = 0.048 + len(shown) * 0.042 + 0.03
        pill_button(self.frame, "++ FILE AND ACKNOWLEDGE ++",
                    self._close, pos=(0, 0, -0.772), hw=0.42, hh=0.046,
                    text_scale=0.040, font=self.f)
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
            tn, np_ = _make_text(self.frame, self.f, pos, scale, color,
                                 align)
            tn.setText(t)
            self._grid.append(np_)
            return tn

        # flatten sections into grid slots: a branch header, then rows
        slots = []
        for sec_label, rows in sections:
            if rows:
                slots.append(('H', sec_label))
                slots.extend(('R',) + r for r in rows)
        if not slots:
            text("ALL PRODUCTION LINES IDLE.", (0, 0.30), 0.04, INK,
                 TextNode.ACenter)
            text("THE NEXT FORTNIGHT APPROPRIATION WILL SET THEM "
                 "TURNING AGAIN.", (0, 0.22), 0.030, INK_FAINT,
                 TextNode.ACenter)
            return

        col_x = (-1.02, 0.10)
        row_y0 = 0.56 - getattr(self, '_bneck_drop', 0.0)
        row_h = 0.111
        per_col = 11
        for i, slot in enumerate(slots[:22]):
            col = i // per_col
            x = col_x[col]
            y = row_y0 - (i % per_col) * row_h
            if slot[0] == 'H':
                text("++ %s ++" % slot[1], (x + 0.035, y), 0.030,
                     (0.52, 0.10, 0.06, 1.0))
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
            tally = text("%d/%d" % (done, total), (x + 0.92, y), 0.030,
                         INK, TextNode.ARight)
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
        f = base.hud_font
        self.frame = DirectFrame(parent=base.aspect2d,
                                 frameColor=(1, 1, 1, 1),
                                 frameTexture=sheet_texture('paper'),
                                 frameSize=(-1.18, 1.18, -0.92, 0.92),
                                 state=DGG.NORMAL)
        DirectFrame(parent=self.frame, frameColor=PAPER_EDGE,
                    frameSize=(-1.18, 1.18, 0.895, 0.92))

        def text(t, pos, scale=0.030, color=INK,
                 align=TextNode.ALeft):
            tn, _ = _make_text(self.frame, f, pos, scale, color, align)
            tn.setText(t)
            return tn

        text("*** STRATEGIC RESOURCES -- THE QUARTERMASTER'S "
             "LEDGER ***", (0, 0.82), 0.043, INK, TextNode.ACenter)
        text("STOCKS ON HAND, THE FORTNIGHT'S TAKE, AND THE PUMPS",
             (0, 0.755), 0.027, INK_FAINT, TextNode.ACenter)
        cols = {'oil': -0.78, 'steel': 0.0, 'rubber': 0.78}
        for res, cx in cols.items():
            d = data[res]
            text(res.upper(), (cx, 0.66), 0.045, INK,
                 TextNode.ACenter)
            text("%d TONS IN STOCK" % d['stock'], (cx, 0.585),
                 0.036, INK, TextNode.ACenter)
            y = 0.505
            text("THE TAKE, EACH FORTNIGHT:", (cx - 0.33, y),
                 0.026, INK_FAINT)
            y -= 0.048
            for name, n in d['income'][:6]:
                text("%s +%d" % (name, n), (cx - 0.29, y), 0.027)
                y -= 0.044
            if d['more_income']:
                text("+%d MORE SITES" % d['more_income'],
                     (cx - 0.29, y), 0.025, INK_FAINT)
                y -= 0.044
            text("SPENT SO FAR THIS FORTNIGHT: %d" % d['spent'],
                 (cx - 0.33, y - 0.010), 0.026,
                 (0.62, 0.14, 0.10, 1.0))
            y -= 0.070
            if d['foreign']:
                text("FOREIGN SOURCES OF NOTE:", (cx - 0.33, y),
                     0.025, INK_FAINT)
                y -= 0.044
                for name, owner, n in d['foreign'][:3]:
                    text("%s +%d  (%s)" % (name, n, owner),
                         (cx - 0.29, y), 0.024, INK_FAINT)
                    y -= 0.040
        # THE SUPPLY NET: the plain statement of the relationship
        ry = -0.42
        tn, _ = _make_text(self.frame, f, (0, ry), 0.032, INK,
                           TextNode.ACenter)
        tn.setText("-" * 74)
        text("THE SUPPLY NET", (0, ry - 0.055), 0.034, INK,
             TextNode.ACenter)
        text("%s LBS OF STORES IN TOWN AND STATION STOCKS   //   "
             "%s LBS ABOARD THE COLUMNS AND FLEETS"
             % ("{:,}".format(data['net_stocks']),
                "{:,}".format(data['unit_stores'])),
             (0, ry - 0.105), 0.027, INK_FAINT, TextNode.ACenter)
        text("THE PUMPS: %s LBS ISSUED TO MACHINES SO FAR THIS "
             "FORTNIGHT DREW %d TONS OF OIL"
             % ("{:,}".format(int(data['pump_lbs'])),
                int(data['pump_oil'])),
             (0, ry - 0.155), 0.027, INK_FAINT, TextNode.ACenter)
        text("ONE TON OF OIL MOVES 250 LBS OF STORES INTO A "
             "MACHINE -- MEN AND THE RAILWAYS DRAW NONE",
             (0, ry - 0.205), 0.027, INK, TextNode.ACenter)
        if data.get('trade'):
            text("IMPORTS & EXPORTS BY TREATY:", (-1.04, ry - 0.265),
                 0.028, INK)
            for i, line in enumerate(data['trade'][:4]):
                text(line, (-1.00 + (i % 2) * 1.10,
                            ry - 0.310 - (i // 2) * 0.045),
                     0.025, INK_FAINT)
        pill_button(self.frame, "++ FILE AND ACKNOWLEDGE ++",
                    self._close, pos=(0, 0, -0.79), hw=0.42,
                    hh=0.046, text_scale=0.040, font=f)
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
    """The DIRECTORATE OF RESEARCH page: three programme columns
    (LAND / AIR / SEA), each a chain of tiers researched in order.
    The header shows points on hand and the fortnight tithe; a tier
    with its price met shows a RESEARCH button. The funding row sets
    what share of each tax fortnight the laboratories receive."""

    def __init__(self, base, game, on_close):
        from tech import (TECH_TREES, RESEARCH_PCT_CHOICES,
                          RESEARCH_DOLLARS_PER_POINT)
        self.base = base
        self.game = game
        self.on_close = on_close
        f = base.hud_font
        self.frame = DirectFrame(parent=base.aspect2d, frameColor=(1, 1, 1, 1),
                                 frameTexture=sheet_texture('paper'),
                                 frameSize=(-1.24, 1.24, -0.92, 0.92),
                                 state=DGG.NORMAL)
        DirectFrame(parent=self.frame, frameColor=PAPER_EDGE,
                    frameSize=(-1.24, 1.24, 0.895, 0.92))
        self._dyn = []
        self._build()

    def _text(self, t, pos, scale=0.032, color=INK,
              align=TextNode.ALeft, dyn=True):
        tn, np_ = _make_text(self.frame, self.base.hud_font, pos, scale,
                             color, align)
        tn.setText(t)
        if dyn:
            self._dyn.append(np_)
        return tn

    def _build(self):
        from tech import TECH_TREES, RESEARCH_PCT_CHOICES
        from units import stats_for
        from icons import get_icon_path
        g = self.game
        c = g.player_country
        for w in self._dyn:
            w.destroy() if hasattr(w, 'destroy') else w.removeNode()
        self._dyn = []
        rp = g.research_points[c]
        pct = g.research_pct[c]
        tithe = int(g.projected_revenue(c) * pct / 100.0)
        self._text("*** DIRECTORATE OF RESEARCH -- PROGRAMMES ***",
                   (0, 0.83), 0.045, INK, TextNode.ACenter)
        self._text("POINTS ON HAND: %.0f RP      FORTNIGHT TITHE: %d%% "
                   "OF TAXES (= $%d = %.1f RP)"
                   % (rp, pct, tithe, tithe / 300.0),
                   (0, 0.76), 0.032, (0.52, 0.10, 0.06, 1.0),
                   TextNode.ACenter)
        # funding row
        self._text("RESEARCH FUNDING:", (-1.10, 0.69), 0.032)
        for i, p in enumerate(RESEARCH_PCT_CHOICES):
            active = (p == pct)
            btn = pill_button(
                self.frame, "%d%%" % p, self._set_pct, extraArgs=[p],
                pos=(-0.55 + i * 0.19, 0, 0.709), hw=0.075, hh=0.038,
                text_scale=0.032, font=self.base.hud_font,
                latched=active)
            self._dyn.append(btn)
        self._text("(THE TITHE IS SKIMMED FROM EACH FORTNIGHT'S TAXES "
                   "BEFORE THE TREASURY -- $300 BUYS 1 RP)",
                   (-1.10, 0.63), 0.026, INK_FAINT)

        cols = {'land': (-0.82, "ARMY PROGRAMMES"),
                'air': (0.0, "AIR PROGRAMMES"),
                'sea': (0.82, "NAVAL PROGRAMMES")}
        for branch, (x, title) in cols.items():
            self._text("++ %s ++" % title, (x, 0.54), 0.034,
                       (0.52, 0.10, 0.06, 1.0), TextNode.ACenter)
            tiers = TECH_TREES[c][branch]
            y = 0.44
            unlocked_prev = True
            for i, (name, cost, unlocks) in enumerate(tiers):
                done = (branch, i) in g.researched[c]
                avail = unlocked_prev and not done
                unlocked_prev = done
                box = DirectFrame(
                    parent=self.frame,
                    frameColor=((0.80, 0.77, 0.64, 1.0) if done else
                                (0.90, 0.87, 0.74, 1.0)),
                    frameSize=(-0.36, 0.36, -0.155, 0.045),
                    pos=(x, 0, y))
                self._dyn.append(box)
                self._text(name, (x, y + 0.005), 0.028, INK,
                           TextNode.ACenter)
                units_lbl = ", ".join(
                    (stats_for(u, c)['label'] if u != 'radar_station'
                     else 'Radar Station (works)') for u in unlocks)
                self._text(units_lbl[:44], (x, y - 0.045), 0.023,
                           INK_FAINT, TextNode.ACenter)
                for k, u in enumerate([u for u in unlocks
                                       if u != 'radar_station'][:3]):
                    ic = DirectFrame(
                        parent=self.frame, relief=None,
                        frameColor=(0, 0, 0, 0),
                        image=get_icon_path(u, 'dark'),
                        image_scale=0.030,
                        frameSize=(-0.03, 0.03, -0.03, 0.03),
                        pos=(x - 0.30 + k * 0.075, 0, y - 0.095))
                    ic.setTransparency(True)
                    crisp_image(ic)
                    self._dyn.append(ic)
                if done:
                    self._text("RESEARCHED", (x + 0.20, y - 0.100),
                               0.026, (0.25, 0.40, 0.22, 1.0),
                               TextNode.ACenter)
                elif avail:
                    can = g.research_points[c] >= cost
                    btn = pill_button(
                        self.frame, "RESEARCH  (%d RP)" % cost,
                        self._research, extraArgs=[branch],
                        pos=(x + 0.14, 0, y - 0.097),
                        hw=0.17, hh=0.036, text_scale=0.026,
                        text_fg=(INK if can
                                 else (0.55, 0.5, 0.42, 1)),
                        font=self.base.hud_font)
                    self._dyn.append(btn)
                else:
                    self._text("LOCKED -- %d RP" % cost,
                               (x + 0.17, y - 0.100), 0.024, INK_FAINT,
                               TextNode.ACenter)
                y -= 0.27
        btn = pill_button(self.frame, "++ FILE AND ACKNOWLEDGE ++",
                          self.on_close, pos=(0, 0, -0.832),
                          hw=0.42, hh=0.046, text_scale=0.040,
                          font=self.base.hud_font)
        self._dyn.append(btn)

    def _set_pct(self, p):
        self.game.research_pct[self.game.player_country] = p
        self._build()

    def _research(self, branch):
        g = self.game
        if g.research_tier(g.player_country, branch):
            self._build()

    def destroy(self):
        self.frame.destroy()
