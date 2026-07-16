"""
In-game UI, WW2 field-headquarters style.

A top bar with the main stats (including units out of W/T contact and
the BUDGET button), a bottom bar with controls and information on the
current selection, and the left and right sides of the screen kept
clear.  Anything that asks the player a question or reports an event
arrives as a FAX from HQ — including the fortnight budget manifest.
"""

import textwrap

from direct.gui.DirectGui import DirectButton, DirectFrame, DGG
from panda3d.core import TextNode

from icons import get_icon_path

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


class TopBar:
    """Main stats strip: each stat is a titled column, value beneath."""

    COLUMNS = [
        ('NATION', -1.42, TextNode.ALeft),
        ('TREASURY', -1.06, TextNode.ALeft),
        ('FORCES', -0.72, TextNode.ALeft),
        ('CITIES', -0.48, TextNode.ALeft),
        ('TIME', -0.02, TextNode.ACenter),
        ('[OUT OF CONTACT]', 0.52, TextNode.ACenter),
        ('KILLS', 0.82, TextNode.ACenter),
        ('LOSSES', 1.00, TextNode.ACenter),
        ('SPEED', 1.18, TextNode.ACenter),
    ]

    def __init__(self, base, on_budget):
        self.base = base
        self.frame = DirectFrame(parent=base.a2dTopCenter,
                                 frameColor=BAR_BG,
                                 frameSize=(-2.0, 2.0, -0.155, 0.0),
                                 state=DGG.NORMAL)
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
        self.budget_btn = DirectButton(
            parent=self.frame, text="BUDGET",
            text_scale=0.036, text_fg=INK,
            text_font=base.hud_font,
            frameColor=BTN_PAPER,
            frameSize=(-0.22, 0.22, -0.030, 0.044),
            relief=DGG.FLAT, command=on_budget,
            pos=(1.52, 0, -0.090))

    def set_stats(self, stats):
        """stats: dict keyed by column title."""
        for title, value in stats.items():
            if title in self.values:
                self.values[title].setText(str(value))

    def set_budget_label(self, label):
        self.budget_btn['text'] = label

    def destroy(self):
        self.frame.destroy()


class BottomBar:
    """Controls and information on the current selection."""

    def __init__(self, base):
        self.base = base
        self.frame = DirectFrame(parent=base.a2dBottomCenter,
                                 frameColor=BAR_BG,
                                 frameSize=(-1.35, 1.35, 0.0, 0.30),
                                 state=DGG.NORMAL)
        self.title_tn, _ = _make_text(self.frame, base.hud_font,
                                      (-1.30, 0.240), 0.05, ACCENT)
        self.info_tn, _ = _make_text(self.frame, base.hud_font,
                                     (-1.30, 0.175), 0.036, BAR_TEXT)
        self.info_tn.setText('')
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
            pos=(1.28, 0, 0.235), command=None)
        self.info_btn.setTransparency(True)
        self.info_btn.hide()

    def show_info(self, command, args):
        self.info_btn['command'] = command
        self.info_btn['extraArgs'] = list(args)
        self.info_btn.show()

    def hide_info(self):
        self.info_btn.hide()

    def set_title(self, text):
        self.title_tn.setText(text)

    def set_info(self, text):
        self.info_tn.setText(text)

    def set_hint(self, text):
        self.hint_tn.setText(text)

    def clear_buttons(self):
        for b in self.buttons:
            b.destroy()
        self.buttons = []

    def add_buttons(self, entries):
        """entries: (label, command, extraArgs[, icon_path[, selected]]).
        With an icon the button shows the unit pictogram beside the
        label; a truthy 'selected' draws a white border. Two rows of 9."""
        self.clear_buttons()
        self.set_hint('')
        per_row = 9
        for i, entry in enumerate(entries[:18]):
            label, command, args = entry[0], entry[1], entry[2]
            icon = entry[3] if len(entry) > 3 else None
            selected = entry[4] if len(entry) > 4 else False
            row, col = divmod(i, per_row)
            x = -1.30 + 0.145 + col * 0.295
            y = 0.105 - row * 0.075
            if selected:
                # white halo behind the button = selected indicator
                border = DirectFrame(parent=self.frame,
                                     frameColor=(1, 1, 1, 1),
                                     frameSize=(-0.152, 0.152,
                                                -0.036, 0.050),
                                     relief=DGG.FLAT, pos=(x, 0, y))
                self.buttons.append(border)
            kwargs = dict(parent=self.frame, text=label,
                          text_scale=0.030, text_fg=INK,
                          text_font=self.base.hud_font,
                          frameColor=BTN_PAPER,
                          frameSize=(-0.14, 0.14, -0.026, 0.040),
                          relief=DGG.FLAT,
                          command=command, extraArgs=args,
                          pos=(x, 0, y))
            if icon:
                kwargs.update(image=icon, image_scale=0.024,
                              image_pos=(-0.105, 0, 0.007),
                              text_scale=0.026,
                              text_pos=(-0.075, -0.002),
                              text_align=TextNode.ALeft)
            btn = DirectButton(**kwargs)
            if icon:
                btn.setTransparency(True)
            self.buttons.append(btn)

    def destroy(self):
        self.clear_buttons()
        self.frame.destroy()


class _Toast:
    """One field signal: a small sheet of paper that slides up, holds,
    and files itself away."""

    SLIDE_TIME = 0.22
    HOLD_TIME = 11.0
    # letter-paper proportions (8.5 x 11)
    WIDTH = 0.56
    HEIGHT = 0.56 * 11.0 / 8.5

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
                                 frameColor=PAPER,
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
        return 0.36 + sum(t.height + 0.03 for t in
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
                 on_transmit, on_discard):
        self.base = base
        self.game = game
        self.funds = int(funds)
        self.unit_types = unit_types
        self.has_harbor = has_harbor
        self.on_transmit = on_transmit
        self.on_discard = on_discard
        self.counts = {ut: 0 for ut in unit_types}
        self.qty_tns = {}

        f = base.hud_font
        self.frame = DirectFrame(parent=base.aspect2d, frameColor=PAPER,
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
        text("APPROPRIATION AVAILABLE: $%d   ONCE TRANSMITTED THE BUDGET "
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
            label = "%s %s" % (stats['icon'].ljust(4), stats['label'][:20])
            text(label, (x, y), 0.030)
            text("$%d" % stats['cost'], (x + 0.62, y), 0.030, INK_FAINT)
            if not available:
                text("NO HARBOR", (x + 0.80, y), 0.028, INK_FAINT)
                continue
            DirectButton(parent=self.frame, text="-", text_scale=0.040,
                         text_fg=INK, text_font=f, frameColor=BTN_PAPER,
                         frameSize=(-0.030, 0.030, -0.026, 0.040),
                         relief=DGG.FLAT, command=self._adjust,
                         extraArgs=[ut, -1], pos=(x + 0.815, 0, y))
            tn, _ = _make_text(self.frame, f, (x + 0.885, y), 0.032, INK,
                               TextNode.ACenter)
            tn.setText("0")
            self.qty_tns[ut] = tn
            DirectButton(parent=self.frame, text="+", text_scale=0.040,
                         text_fg=INK, text_font=f, frameColor=BTN_PAPER,
                         frameSize=(-0.030, 0.030, -0.026, 0.040),
                         relief=DGG.FLAT, command=self._adjust,
                         extraArgs=[ut, +1], pos=(x + 0.955, 0, y))

        text("-" * 78, (0, -0.70), 0.034, INK, TextNode.ACenter)
        self.total_tn, _ = _make_text(self.frame, f, (0, -0.755), 0.036,
                                      INK, TextNode.ACenter)
        self._refresh_totals()

        DirectButton(parent=self.frame, text="++ TRANSMIT ++",
                     text_scale=0.042, text_fg=(0.1, 0.25, 0.1, 1),
                     text_font=f, frameColor=BTN_PAPER,
                     frameSize=(-0.30, 0.30, -0.038, 0.056),
                     relief=DGG.FLAT, command=self._transmit,
                     pos=(-0.40, 0, -0.85))
        DirectButton(parent=self.frame, text="-- DISCARD --",
                     text_scale=0.042, text_fg=(0.45, 0.12, 0.08, 1),
                     text_font=f, frameColor=BTN_PAPER,
                     frameSize=(-0.30, 0.30, -0.038, 0.056),
                     relief=DGG.FLAT, command=self._discard,
                     pos=(0.40, 0, -0.85))

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

    def _adjust(self, ut, delta):
        cost = self.unit_types[ut]['cost']
        if delta > 0 and self._allocated() + cost > self.funds:
            return
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
        self.frame = DirectFrame(parent=base.aspect2d, frameColor=PAPER,
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

        DirectButton(parent=self.frame, text="++ FILE AND ACKNOWLEDGE ++",
                     text_scale=0.038, text_fg=(0.1, 0.25, 0.1, 1),
                     text_font=f, frameColor=BTN_PAPER,
                     frameSize=(-W + 0.06, W - 0.06, -0.042, 0.060),
                     relief=DGG.FLAT, command=self._close,
                     pos=(0, 0, -H + 0.055))

    def _close(self):
        self.on_close()

    def destroy(self):
        self.frame.destroy()
