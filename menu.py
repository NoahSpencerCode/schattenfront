"""
Main menu and nation selection, framed as War Office paperwork.

If media/menu_background.mp4 exists it plays fullscreen behind the menu
(see README for placement instructions); otherwise a plain dark backdrop
is used.
"""

import glob
import os

from direct.gui.DirectGui import DirectButton, DirectFrame, DGG
from panda3d.core import CardMaker, MovieTexture, TextNode, TextureStage

from config import COUNTRIES, MEDIA_PATH, MENU_VIDEO_PATH
from ui import PAPER, PAPER_EDGE, INK, INK_FAINT, sheet_tex, flag_tex

TITLE_COLOR = (0.92, 0.87, 0.70, 1.0)
SUB_COLOR = (0.70, 0.66, 0.55, 1.0)
BTN_COLORS = ((0.16, 0.15, 0.12, 0.92), (0.30, 0.27, 0.18, 0.96),
              (0.10, 0.09, 0.07, 0.92), (0.3, 0.3, 0.3, 0.5))

RED_INK = (0.52, 0.10, 0.06, 1.0)          # dispatch red, as the FAX uses
STAMP_RED = (0.60, 0.12, 0.08, 0.92)

# The General Staff appreciation of each power: epithet on the roster,
# headquarters line, three strengths, three weaknesses and a service
# assessment -- all grounded in the NATION_UNITS stat modifiers.
COUNTRY_DOSSIERS = {
    'britain': {
        'epithet': "MISTRESS OF THE SEAS",
        'hq': "THE WAR CABINET, WHITEHALL, LONDON",
        'strengths': ["THE ROYAL NAVY RULES THE WAVES",
                      "ARMOURED CARRIERS SHRUG OFF BOMBS",
                      "RADAR: THE WIDEST EYES IN THE WAR"],
        'weaknesses': ["TANKS ARE SLOW AND PONDEROUS",
                       "AN EMPIRE OF STRETCHED SEA LANES",
                       "THE HOME ISLES STAND EXPOSED"],
        'ratings': (('ARMY', 3), ('NAVY', 5), ('AIR FORCE', 4),
                    ('INDUSTRY', 3)),
    },
    'germany': {
        'epithet': "THE CONTINENTAL BLITZ",
        'hq': "OBERKOMMANDO DER WEHRMACHT, BERLIN",
        'strengths': ["EXPERTEN FIGHTER WINGS RULE THE AIR",
                      "TIGER ARMOUR BREAKS ANY LINE",
                      "CHEAP U-BOATS; THE DENSEST RAILS"],
        'weaknesses': ["HEAVY EQUIPMENT IS PRICED DEAR",
                       "TOO FEW HULLS ON THE SURFACE",
                       "ENEMIES ON EVERY LANDWARD FRONT"],
        'ratings': (('ARMY', 5), ('NAVY', 2), ('AIR FORCE', 4),
                    ('INDUSTRY', 3)),
    },
    'usa': {
        'epithet': "THE ARSENAL OF DEMOCRACY",
        'hq': "WAR DEPARTMENT, WASHINGTON D.C.",
        'strengths': ["INDUSTRY: EVERYTHING COSTS LESS",
                      "LIBERTY SHIPS FASTER THAN SINKINGS",
                      "THE BEST-EQUIPPED RIFLEMEN AFIELD"],
        'weaknesses': ["TWO OCEANS FROM EVERY FRONT",
                       "LONG CONVOY RUNS TO KEEP SUPPLIED",
                       "NO EARLY EDGE IN ARMOUR QUALITY"],
        'ratings': (('ARMY', 4), ('NAVY', 4), ('AIR FORCE', 4),
                    ('INDUSTRY', 5)),
    },
    'japan': {
        'epithet': "EMPIRE OF THE PACIFIC",
        'hq': "IMPERIAL GENERAL HEADQUARTERS, TOKYO",
        'strengths': ["UNMATCHED AIRCRAFT RANGE",
                      "THE KIDO BUTAI CARRIER FORCE",
                      "LONG LANCE NIGHT DESTROYERS"],
        'weaknesses': ["PAPER-THIN ARMOUR, MEN AND MACHINES",
                       "A THIN HOME INDUSTRY",
                       "A PERIMETER FED BY SLOW MARUS"],
        'ratings': (('ARMY', 2), ('NAVY', 5), ('AIR FORCE', 4),
                    ('INDUSTRY', 2)),
    },
    'soviet': {
        'epithet': "THE UNBREAKABLE EAST",
        'hq': "STAVKA OF THE SUPREME HIGH COMMAND, MOSCOW",
        'strengths': ["ENDLESS, CHEAPEST INFANTRY MASSES",
                      "T-34S AND MASSED ARTILLERY",
                      "THE ARMOURED IL-2 FLYING TANK"],
        'weaknesses': ["A COASTAL NAVY, NOTHING MORE",
                       "SHORT-LEGGED FIGHTER COVER",
                       "VAST FRONTIERS TO HOLD"],
        'ratings': (('ARMY', 5), ('NAVY', 1), ('AIR FORCE', 3),
                    ('INDUSTRY', 4)),
    },
}


class MenuScreen:
    def __init__(self, base, on_start_game):
        self.base = base
        self.on_start_game = on_start_game
        self.root = base.aspect2d.attachNewNode('menu_root')
        self.video_card = None
        self.video_tex = None
        self.widgets = []
        self._make_background()
        self.show_main()

    # ---------------------------------------------------------- background
    @staticmethod
    def _find_menu_video():
        """menu_background.mp4 if present, else any .mp4 in media/."""
        if os.path.exists(MENU_VIDEO_PATH):
            return MENU_VIDEO_PATH
        candidates = sorted(glob.glob(os.path.join(MEDIA_PATH, '*.mp4')))
        return candidates[0] if candidates else None

    def _make_background(self):
        played = False
        video_path = self._find_menu_video()
        if video_path:
            try:
                tex = MovieTexture('menu_background')
                if tex.read(video_path):
                    tex.setLoop(True)
                    tex.play()
                    # drop the needle somewhere new each time so the
                    # reel opens on a different scene
                    length = tex.getVideoLength()
                    if length and length > 8.0:
                        import random as _random
                        tex.setTime(_random.uniform(0.0, length - 5.0))
                    cm = CardMaker('menu_bg')
                    cm.setFrameFullscreenQuad()
                    cm.setUvRange(tex)
                    self.video_card = self.base.render2d.attachNewNode(
                        cm.generate())
                    self.video_card.setTexture(tex)
                    self.video_card.setBin('background', 0)
                    self.video_tex = tex
                    self._fit_video()   # scale to the window, no stretch
                    # re-fit if the window is resized (own task, so we
                    # never clobber ShowBase's window-event handler)
                    self._last_win_size = (self.base.win.getXSize(),
                                           self.base.win.getYSize())
                    self.base.taskMgr.add(self._watch_resize,
                                          'menu_reel_fit')
                    played = True
            except Exception as exc:
                print("Menu video could not be played:", exc)
        if not played:
            cm = CardMaker('menu_bg')
            cm.setFrameFullscreenQuad()
            self.video_card = self.base.render2d.attachNewNode(cm.generate())
            self.video_card.setColor(0.07, 0.08, 0.10, 1.0)
            self.video_card.setBin('background', 0)

    def _fit_video(self):
        """Scale the reel to cover the window without distorting it: the
        video fills the screen, the overflowing dimension is cropped
        (some side/top clipping), and the aspect ratio is preserved."""
        if not self.video_tex or not self.video_card:
            return
        vw = self.video_tex.getVideoWidth()
        vh = self.video_tex.getVideoHeight()
        win = self.base.win
        if not (vw and vh and win):
            return
        ww, wh = win.getXSize(), win.getYSize()
        if not (ww and wh):
            return
        win_aspect = ww / float(wh)
        vid_aspect = vw / float(vh)
        ts = TextureStage.getDefault()
        if vid_aspect >= win_aspect:
            # video is wider than the window: keep full height, crop the
            # left/right edges
            keep = win_aspect / vid_aspect
            self.video_card.setTexScale(ts, keep, 1.0)
            self.video_card.setTexOffset(ts, (1.0 - keep) / 2.0, 0.0)
        else:
            # video is taller/narrower: keep full width, crop top/bottom
            keep = vid_aspect / win_aspect
            self.video_card.setTexScale(ts, 1.0, keep)
            self.video_card.setTexOffset(ts, 0.0, (1.0 - keep) / 2.0)

    def _watch_resize(self, task):
        win = self.base.win
        if win is not None:
            size = (win.getXSize(), win.getYSize())
            if size != self._last_win_size:
                self._last_win_size = size
                self._fit_video()
        return task.cont

    # ------------------------------------------------------------- helpers
    def _text(self, text, pos, scale, color, align=TextNode.ACenter):
        tn = TextNode('menu_text')
        tn.setText(text)
        tn.setAlign(align)
        if self.base.hud_font:
            tn.setFont(self.base.hud_font)
        tn.setTextColor(*color)
        tn.setShadow(0.04, 0.04)
        tn.setShadowColor(0, 0, 0, 0.7)
        np_ = self.root.attachNewNode(tn)
        np_.setPos(pos[0], 0, pos[1])
        np_.setScale(scale)
        self.widgets.append(np_)
        return np_

    def _button(self, text, pos, command, args=(), width=0.42, scale=0.05):
        from ui import pill_button
        btn = pill_button(self.root, text, command, extraArgs=args,
                          pos=(pos[0], 0, pos[1] + 0.012), hw=width,
                          hh=0.058, text_scale=scale,
                          font=self.base.hud_font)
        self.widgets.append(btn)
        return btn

    def _clear(self):
        for w in self.widgets:
            w.destroy() if hasattr(w, 'destroy') else w.removeNode()
        self.widgets = []
        for key in ('n', 'h', 'l', 'q', 'b', 's', 'w', 'escape',
                    'enter', '1', '2', '3', '4', '5', '6'):
            self.base.ignore(key)
        if getattr(self, 'wiki', None) is not None:
            self.wiki.destroy()
            self.wiki = None

    # --------------------------------------------------------------- pages
    def show_main(self):
        self._clear()
        self._text("GLOBAL OPERATIONS", (0, 0.62), 0.145,
                   TITLE_COLOR)
        self._text("* 1939 EDITION *  --  A WORLD AT WAR", (0, 0.50),
                   0.05, SUB_COLOR)
        # new game and load game live together behind one key: the
        # selection page carries LOAD GAME in its bottom-left corner
        self._button("[N]  QUICK MATCH", (0, 0.30),
                     self.show_country_select, ['new'])
        # the campaign and multiplayer are not in this build: their
        # keys sit dark and dead
        for label, y in (("CAMPAIGN  (COMING SOON)", 0.14),
                         ("MULTIPLAYER  (COMING SOON)", -0.02)):
            dead = self._button(label, (0, y), None)
            dead['state'] = DGG.DISABLED
            dead.setColorScale(0.55, 0.55, 0.55, 0.75)
        self._button("[W]  WIKI", (0, -0.18), self.show_wiki)
        self._button("[S]  SETTINGS", (0, -0.34), self.show_settings)
        self._button("[Q]  QUIT", (0, -0.50), self._quit)
        from config import GAME_VERSION
        self._text("ALPHA %s" % GAME_VERSION,
                   (0, -0.85), 0.035, SUB_COLOR)
        self.base.accept('n', self.show_country_select, ['new'])
        self.base.accept('enter', self.show_country_select, ['new'])
        self.base.accept('w', self.show_wiki)
        self.base.accept('s', self.show_settings)
        self.base.accept('q', self._quit)

    def show_load_page(self, back_to='main'):
        """Filed campaigns, newest first, as a records-office fax.
        back_to='select' returns to the Quick Match sheet, whence the
        page is reached."""
        import saveload
        self._clear()
        go_back = (self.show_country_select if back_to == 'select'
                   else self.show_main)
        frame = DirectFrame(parent=self.root, frameColor=(1, 1, 1, 1),
                                 frameTexture=sheet_tex('paper'),
                            frameSize=(-0.95, 0.95, -0.78, 0.78),
                            state=DGG.NORMAL)
        self.widgets.append(frame)
        top = DirectFrame(parent=frame, frameColor=PAPER_EDGE,
                          frameSize=(-0.95, 0.95, 0.755, 0.78))
        self.widgets.append(top)

        def paper_text(text, pos, scale, color=INK,
                       align=TextNode.ACenter):
            tn = TextNode('paper_text')
            tn.setText(text)
            tn.setAlign(align)
            if self.base.hud_font:
                tn.setFont(self.base.hud_font)
            tn.setTextColor(*color)
            np_ = frame.attachNewNode(tn)
            np_.setPos(pos[0], 0, pos[1])
            np_.setScale(scale)
            self.widgets.append(np_)

        paper_text("*** INCOMING FAX ***", (0, 0.68), 0.045)
        paper_text("FROM : WAR OFFICE, RECORDS SECTION",
                   (-0.85, 0.60), 0.037, INK, TextNode.ALeft)
        paper_text("RE   : FILED CAMPAIGNS -- RESUMPTION OF COMMAND",
                   (-0.85, 0.545), 0.037, INK, TextNode.ALeft)
        paper_text("-" * 52, (0, 0.50), 0.04)
        saves = saveload.list_saves()[:8]
        if not saves:
            paper_text("THE ARCHIVE DRAWER IS EMPTY.  SAVE FROM THE",
                       (0, 0.30), 0.037)
            paper_text("FIELD ORDERS MENU (ESC) DURING A CAMPAIGN.",
                       (0, 0.25), 0.037)
        y = 0.40
        from config import COUNTRIES as _C
        import time as _t
        for meta in saves:
            nation = _C.get(meta.get('nation', ''), {}).get(
                'name', meta.get('nation', '?'))
            stamp = _t.strftime('%d %b %Y %H:%M',
                                _t.localtime(meta.get('saved_at', 0)))
            label = "%s  --  %s  (%d CITIES, %d UNITS)" % (
                nation.upper(), meta.get('campaign_date', '?'),
                meta.get('cities', 0), meta.get('forces', 0))
            btn = DirectButton(
                parent=frame, text=label,
                text_scale=0.036, text_fg=INK,
                text_align=TextNode.ALeft,
                text_font=self.base.hud_font,
                frameColor=((0.86, 0.82, 0.68, 0.0),
                            (0.80, 0.74, 0.55, 1.0),
                            (0.70, 0.66, 0.54, 0.9),
                            (0.5, 0.5, 0.5, 0.3)),
                frameSize=(-0.06, 1.60, -0.035, 0.055),
                relief=DGG.FLAT,
                command=self.base.load_game,
                extraArgs=[meta['path']],
                pos=(-0.80, 0, y))
            self.widgets.append(btn)
            paper_text("FILED %s" % stamp.upper(),
                       (-0.78, y - 0.042), 0.026, INK_FAINT,
                       TextNode.ALeft)
            y -= 0.13
        paper_text("++ MESSAGE ENDS ++", (0, -0.67), 0.035)
        self._button("[B]  BACK", (0, -0.92), go_back, width=0.3,
                     scale=0.04)
        self.base.accept('b', go_back)
        self.base.accept('escape', go_back)

    def show_country_select(self, mode='new'):
        """One wide FAX form: the roster of powers down the left with
        their standards, the General Staff appreciation of the chosen
        power on the right, LOAD GAME bottom-left, START GAME
        bottom-right. Clicking a power re-prints the sheet."""
        from config import PLAYABLE
        self._clear()
        self._mode = mode
        if getattr(self, 'sel_country', None) not in PLAYABLE:
            self.sel_country = PLAYABLE[0]
        sel = self.sel_country
        doss = COUNTRY_DOSSIERS[sel]

        X0, X1, Z0, Z1 = -1.30, 1.30, -0.92, 0.92
        frame = DirectFrame(parent=self.root, frameColor=(1, 1, 1, 1),
                            frameTexture=sheet_tex('paper'),
                            frameSize=(X0, X1, Z0, Z1), state=DGG.NORMAL)
        self.widgets.append(frame)
        # fax leader bands top and bottom
        for z0, z1 in ((Z1 - 0.025, Z1), (Z0, Z0 + 0.025)):
            band = DirectFrame(parent=frame, frameColor=PAPER_EDGE,
                               frameSize=(X0, X1, z0, z1))
            self.widgets.append(band)

        def paper_text(text, pos, scale, color=INK,
                       align=TextNode.ACenter, parent=None, wrap=None):
            tn = TextNode('paper_text')
            tn.setText(text)
            tn.setAlign(align)
            if wrap:
                tn.setWordwrap(wrap)
            if self.base.hud_font:
                tn.setFont(self.base.hud_font)
            tn.setTextColor(*color)
            np_ = (parent or frame).attachNewNode(tn)
            np_.setPos(pos[0], 0, pos[1])
            np_.setScale(scale)
            self.widgets.append(np_)
            return np_

        def rule(x0, x1, z, thick=0.004, color=INK):
            r = DirectFrame(parent=frame, frameColor=color,
                            frameSize=(x0, x1, z - thick / 2.0,
                                       z + thick / 2.0))
            self.widgets.append(r)
            return r

        def vrule(x, z0, z1, thick=0.004, color=INK):
            r = DirectFrame(parent=frame, frameColor=color,
                            frameSize=(x - thick / 2.0, x + thick / 2.0,
                                       z0, z1))
            self.widgets.append(r)
            return r

        def flag(key, pos, hw, hh):
            f = DirectFrame(parent=frame, frameColor=(1, 1, 1, 1),
                            frameTexture=flag_tex(key),
                            frameSize=(-hw, hw, -hh, hh), pos=pos)
            self.widgets.append(f)
            return f

        # ------------------------------------------------- masthead
        paper_text("FACSIMILE TRANSMISSION", (X0 + 0.08, 0.845), 0.028,
                   INK_FAINT, TextNode.ALeft)
        paper_text("SHEET 1 OF 1", (X1 - 0.08, 0.845), 0.028,
                   INK_FAINT, TextNode.ARight)
        paper_text("ASSIGNMENT OF SUPREME COMMAND", (0, 0.755), 0.060)
        rule(X0 + 0.08, X1 - 0.08, 0.715, 0.006)
        rule(X0 + 0.08, X1 - 0.08, 0.700, 0.0025)

        # form block, left; MOST SECRET stamp, right
        paper_text("FROM : WAR OFFICE, MOBILIZATION BRANCH",
                   (X0 + 0.08, 0.645), 0.032, INK, TextNode.ALeft)
        paper_text("DATE : 1 SEPTEMBER 1939",
                   (X0 + 0.08, 0.592), 0.032, INK, TextNode.ALeft)
        paper_text("RE   : ORDER 1939/1 -- SELECTION OF A POWER "
                   "FOR COMMAND",
                   (X0 + 0.08, 0.539), 0.032, INK, TextNode.ALeft)
        stamp = frame.attachNewNode('stamp')
        stamp.setPos(0.94, 0, 0.60)
        stamp.setR(-7)
        self.widgets.append(stamp)
        sw, sh = 0.275, 0.062
        for x0, x1, z0, z1 in ((-sw, sw, sh - 0.007, sh),
                               (-sw, sw, -sh, -sh + 0.007),
                               (-sw, -sw + 0.007, -sh, sh),
                               (sw - 0.007, sw, -sh, sh)):
            e = DirectFrame(parent=stamp, frameColor=STAMP_RED,
                            frameSize=(x0, x1, z0, z1))
            self.widgets.append(e)
        paper_text("MOST SECRET", (0, -0.017), 0.052, STAMP_RED,
                   parent=stamp)
        if mode == 'host':
            paper_text("(FIELD TELEPHONE NET UNDER CONSTRUCTION -- "
                       "WAR GAME PROCEEDS UNDER LOCAL COMMAND)",
                       (0, 0.487), 0.026, INK_FAINT)

        rule(X0 + 0.08, X1 - 0.08, 0.470, 0.0025)

        # ------------------------------------- roster of the powers
        RX1 = -0.44                     # roster right edge
        DX0 = -0.36                     # dossier left edge
        paper_text("POWERS AWAITING ORDERS", (X0 + 0.08, 0.415), 0.028,
                   INK_FAINT, TextNode.ALeft)
        paper_text("GENERAL STAFF APPRECIATION", (DX0 + 0.02, 0.415),
                   0.028, INK_FAINT, TextNode.ALeft)
        vrule(-0.40, -0.660, 0.455, 0.0025, INK_FAINT)

        playable = [(k, COUNTRIES[k]) for k in PLAYABLE]
        y = 0.290
        for i, (key, info) in enumerate(playable):
            selected = (key == sel)
            row_fill = ((0.22, 0.19, 0.14, 1.0) if selected else
                        (0.86, 0.82, 0.68, 0.0))
            btn = DirectButton(
                parent=frame, text='',
                frameColor=(row_fill,
                            row_fill if selected else
                            (0.80, 0.74, 0.55, 0.55),
                            row_fill if selected else
                            (0.70, 0.66, 0.54, 0.65),
                            (0.5, 0.5, 0.5, 0.3)),
                frameSize=(0.0, RX1 - X0 - 0.05, -0.085, 0.105),
                relief=DGG.FLAT, command=self._select, extraArgs=[key],
                pos=(X0 + 0.05, 0, y))
            self.widgets.append(btn)
            flag(key, (X0 + 0.155, 0, y + 0.012), 0.078, 0.052)
            name_col = ((0.93, 0.90, 0.80, 1.0) if selected else INK)
            sub_col = ((0.75, 0.71, 0.60, 1.0) if selected else
                       INK_FAINT)
            paper_text("[%d]  %s" % (i + 1, info['name'].upper()),
                       (X0 + 0.27, y + 0.030), 0.040, name_col,
                       TextNode.ALeft)
            paper_text(COUNTRY_DOSSIERS[key]['epithet'],
                       (X0 + 0.27, y - 0.032), 0.024, sub_col,
                       TextNode.ALeft)
            if selected:
                paper_text("YOUR COMMAND", (RX1 - 0.030, y - 0.058),
                           0.023, (0.86, 0.44, 0.36, 1.0),
                           TextNode.ARight)
            if i < len(playable) - 1:
                rule(X0 + 0.05, RX1, y - 0.090, 0.002, INK_FAINT)
            self.base.accept(str(i + 1), self._select, [key])
            y -= 0.200

        # ------------------------------- the appreciation (dossier)
        DX1 = X1 - 0.08
        box_top, box_bot = 0.370, -0.660
        rule(DX0, DX1, box_top)
        rule(DX0, DX1, box_bot)
        vrule(DX0, box_bot, box_top)
        vrule(DX1, box_bot, box_top)

        flag(sel, (DX0 + 0.26, 0, box_top - 0.175), 0.195, 0.130)
        info = COUNTRIES[sel]
        paper_text(info['name'].upper(), (DX0 + 0.52, box_top - 0.135),
                   0.054, INK, TextNode.ALeft)
        paper_text(doss['hq'], (DX0 + 0.52, box_top - 0.205), 0.026,
                   INK_FAINT, TextNode.ALeft)
        c = info['color']
        chipy = box_top - 0.275
        chip = DirectFrame(parent=frame, frameColor=(c[0], c[1], c[2], 1),
                           frameSize=(-0.022, 0.022, -0.022, 0.022),
                           pos=(DX0 + 0.545, 0, chipy))
        self.widgets.append(chip)
        paper_text("COLOUR OF ARMS ON THE MAP", (DX0 + 0.60, chipy - 0.010),
                   0.024, INK_FAINT, TextNode.ALeft)

        rule(DX0 + 0.04, DX1 - 0.04, 0.020, 0.0025)
        col_s, col_w = DX0 + 0.06, DX0 + 0.85
        paper_text("STRENGTHS", (col_s, -0.045), 0.032, RED_INK,
                   TextNode.ALeft)
        paper_text("WEAKNESSES", (col_w, -0.045), 0.032, RED_INK,
                   TextNode.ALeft)
        for j, line in enumerate(doss['strengths']):
            paper_text("+ %s" % line, (col_s, -0.105 - j * 0.055),
                       0.0265, INK, TextNode.ALeft)
        for j, line in enumerate(doss['weaknesses']):
            paper_text("- %s" % line, (col_w, -0.105 - j * 0.055),
                       0.0265, INK, TextNode.ALeft)

        rule(DX0 + 0.04, DX1 - 0.04, -0.290, 0.0025)
        paper_text("SERVICE ASSESSMENT", (col_s, -0.340), 0.032,
                   RED_INK, TextNode.ALeft)
        ty = -0.408
        for label, score in doss['ratings']:
            paper_text(label, (col_s, ty - 0.012), 0.028, INK,
                       TextNode.ALeft)
            for k in range(5):
                filled = (k < score)
                sq = DirectFrame(
                    parent=frame,
                    frameColor=(INK if filled else
                                (INK[0], INK[1], INK[2], 0.14)),
                    frameSize=(-0.017, 0.017, -0.017, 0.017),
                    pos=(DX0 + 0.44 + k * 0.062, 0, ty))
                self.widgets.append(sq)
            ty -= 0.062
        vrule(DX0 + 0.38, ty + 0.030, -0.375, 0.002, INK_FAINT)
        paper_text("ASSESSMENT PREPARED BY THE GENERAL\n"
                   "STAFF.  FOR PLANNING PURPOSES ONLY.\n"
                   "COMMANDERS PROCEED AT THEIR OWN\n"
                   "DISCRETION.",
                   (DX0 + 0.90, -0.405), 0.0235, INK_FAINT,
                   TextNode.ALeft)

        # ------------------------------------------ bottom controls
        rule(X0 + 0.08, X1 - 0.08, -0.705, 0.0025)
        from ui import pill_button
        load_b = pill_button(frame, "[L]  LOAD GAME", self.show_load_page,
                             extraArgs=['select'],
                             pos=(X0 + 0.35, 0, -0.795), hw=0.26,
                             hh=0.058, text_scale=0.040,
                             font=self.base.hud_font)
        self.widgets.append(load_b)
        back_b = pill_button(frame, "[B]  BACK", self.show_main,
                             pos=(0, 0, -0.795), hw=0.17, hh=0.052,
                             text_scale=0.036, font=self.base.hud_font)
        self.widgets.append(back_b)
        start_b = pill_button(frame, "START GAME  >>", self._start,
                              pos=(X1 - 0.35, 0, -0.795), hw=0.26,
                              hh=0.058, text_scale=0.040,
                              font=self.base.hud_font, kind='red',
                              text_fg=(0.95, 0.92, 0.86, 1.0))
        self.widgets.append(start_b)
        paper_text("++ END OF TRANSMISSION ++", (0, -0.885), 0.024,
                   INK_FAINT)
        self.base.accept('l', self.show_load_page, ['select'])
        self.base.accept('enter', self._start)
        self.base.accept('b', self.show_main)
        self.base.accept('escape', self.show_main)

    def _select(self, country):
        """Mark a power on the roster and re-print the sheet."""
        self.sel_country = country
        self.show_country_select(getattr(self, '_mode', 'new'))

    def _start(self):
        self._pick(self.sel_country)

    def show_settings(self):
        self._clear()
        frame = DirectFrame(parent=self.root, frameColor=(1, 1, 1, 1),
                                 frameTexture=sheet_tex('paper'),
                            frameSize=(-0.95, 0.95, -0.78, 0.78),
                            state=DGG.NORMAL)
        self.widgets.append(frame)
        top = DirectFrame(parent=frame, frameColor=PAPER_EDGE,
                          frameSize=(-0.95, 0.95, 0.755, 0.78))
        self.widgets.append(top)

        def paper_text(text, pos, scale, color=INK,
                       align=TextNode.ACenter):
            tn = TextNode('paper_text')
            tn.setText(text)
            tn.setAlign(align)
            if self.base.hud_font:
                tn.setFont(self.base.hud_font)
            tn.setTextColor(*color)
            np_ = frame.attachNewNode(tn)
            np_.setPos(pos[0], 0, pos[1])
            np_.setScale(scale)
            self.widgets.append(np_)

        paper_text("*** INCOMING FAX ***", (0, 0.68), 0.045)
        paper_text("FROM : WAR OFFICE, SIGNALS AND OPTICS SECTION",
                   (-0.85, 0.60), 0.037, INK, TextNode.ALeft)
        paper_text("RE   : TECHNICAL ORDER -- PROJECTION EQUIPMENT",
                   (-0.85, 0.545), 0.037, INK, TextNode.ALeft)
        paper_text("-" * 52, (0, 0.50), 0.04)
        paper_text("ANTI-ALIASING SMOOTHS THE DRAWN LINES AND EDGES",
                   (0, 0.42), 0.037)
        paper_text("OF THE MAP.  SELECT A GRADE OF OPTICS BELOW.",
                   (0, 0.37), 0.037)

        current = int(getattr(self.base, 'aa_samples', 0))
        choices = ((0, 'OFF'), (2, 'MSAA 2X'), (4, 'MSAA 4X'),
                   (8, 'MSAA 8X'))
        xs = (-0.66, -0.22, 0.22, 0.66)
        for i, ((val, label), x) in enumerate(zip(choices, xs)):
            active = (val == current)
            from ui import pill_button
            btn = pill_button(
                frame, "[%d] %s" % (i + 1, label),
                self._set_antialias, extraArgs=[val],
                pos=(x, 0, 0.173), hw=0.20, hh=0.055,
                text_scale=0.04, font=self.base.hud_font,
                latched=active)
            self.widgets.append(btn)
            self.base.accept(str(i + 1), self._set_antialias, [val])
        stamp = next(lbl for v, lbl in choices if v == current)
        paper_text("IN EFFECT: %s" % stamp, (0, 0.02), 0.037,
                   (0.52, 0.10, 0.06, 1.0))
        paper_text("(THE PROJECTOR FLICKERS ONCE WHILE THE OPTICS",
                   (0, -0.12), 0.032, INK_FAINT)
        paper_text("ARE EXCHANGED.  THE SETTING IS KEPT ON FILE.)",
                   (0, -0.16), 0.032, INK_FAINT)
        paper_text("++ MESSAGE ENDS ++", (0, -0.62), 0.035)
        self._button("[B]  BACK", (0, -0.92), self.show_main, width=0.3,
                     scale=0.04)
        self.base.accept('b', self.show_main)
        self.base.accept('escape', self.show_main)

    def show_wiki(self):
        """THE FIELD MANUAL: the tabbed wiki of every mechanic."""
        from wiki import WikiFax
        self._clear()
        self.wiki = WikiFax(self.base, self.show_main)
        self.base.accept('escape', self.show_main)
        self.base.accept('b', self.show_main)

    def _set_antialias(self, samples):
        if hasattr(self.base, 'set_antialias'):
            self.base.set_antialias(samples)
        self.show_settings()            # refresh the IN EFFECT stamp

    def _pick(self, country):
        self.on_start_game(country)

    def _quit(self):
        self.base.userExit()

    def destroy(self):
        self._clear()
        self.base.taskMgr.remove('menu_reel_fit')
        if self.video_tex:
            try:
                self.video_tex.stop()
            except Exception:
                pass
        if self.video_card:
            self.video_card.removeNode()
            self.video_card = None
        self.root.removeNode()
