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
from ui import PAPER, PAPER_EDGE, INK, INK_FAINT

TITLE_COLOR = (0.92, 0.87, 0.70, 1.0)
SUB_COLOR = (0.70, 0.66, 0.55, 1.0)
BTN_COLORS = ((0.16, 0.15, 0.12, 0.92), (0.30, 0.27, 0.18, 0.96),
              (0.10, 0.09, 0.07, 0.92), (0.3, 0.3, 0.3, 0.5))

COUNTRY_BLURBS = {
    'britain': "The Royal Navy rules the waves. Hold the home\n"
               "isles and strike back by sea and air.",
    'germany': "Panzers and a dense road net. Command the continent\n"
               "with rapid armoured thrusts.",
    'usa':     "The arsenal of democracy. Vast industry and two\n"
               "oceans between you and the enemy.",
    'japan':   "An island empire. Carriers and transports project\n"
               "power across the Pacific.",
    'soviet':  "The Rodina's endless manpower. Absorb the blow, then\n"
               "grind the invader down across the steppe.",
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
        for key in ('n', 'h', 'q', 'b', 's', 'escape',
                    '1', '2', '3', '4', '5', '6'):
            self.base.ignore(key)

    # --------------------------------------------------------------- pages
    def show_main(self):
        self._clear()
        self._text("SCHATTENFRONT", (0, 0.62), 0.15, TITLE_COLOR)
        self._text("A WORLD AT WAR  *  1939 - 1945", (0, 0.50), 0.05,
                   SUB_COLOR)
        self._button("[N]  NEW GAME", (0, 0.18), self.show_country_select,
                     ['new'])
        # multiplayer is not in this build: the key sits dark and dead
        mp = self._button("MULTIPLAYER  (COMING SOON)", (0, 0.02), None)
        mp['state'] = DGG.DISABLED
        mp.setColorScale(0.55, 0.55, 0.55, 0.75)
        self._button("[S]  SETTINGS", (0, -0.14), self.show_settings)
        self._button("[Q]  QUIT", (0, -0.30), self._quit)
        from config import GAME_VERSION
        self._text("ALPHA %s" % GAME_VERSION,
                   (0, -0.85), 0.035, SUB_COLOR)
        self.base.accept('n', self.show_country_select, ['new'])
        self.base.accept('s', self.show_settings)
        self.base.accept('q', self._quit)

    def show_country_select(self, mode='new'):
        self._clear()
        frame = DirectFrame(parent=self.root, frameColor=PAPER,
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
        paper_text("FROM : WAR OFFICE, MOBILIZATION BRANCH", (-0.85, 0.60),
                   0.037, INK, TextNode.ALeft)
        paper_text("RE   : ORDER 1939/1 -- ASSIGNMENT OF COMMAND",
                   (-0.85, 0.545), 0.037, INK, TextNode.ALeft)
        paper_text("-" * 52, (0, 0.50), 0.04)
        paper_text("YOU ARE HEREBY DIRECTED TO ASSUME SUPREME COMMAND",
                   (0, 0.445), 0.037)
        paper_text("OF THE ARMED FORCES OF ONE OF THE POWERS BELOW.",
                   (0, 0.395), 0.037)
        if mode == 'host':
            paper_text("(FIELD TELEPHONE NETWORK UNDER CONSTRUCTION --",
                       (0, 0.34), 0.032, INK_FAINT)
            paper_text("HOSTED WAR GAME WILL PROCEED UNDER LOCAL COMMAND)",
                       (0, 0.30), 0.032, INK_FAINT)

        # space the nation rows to fill the sheet regardless of how many
        # powers there are
        n_countries = len(COUNTRIES) - 1   # neutral is not picked
        y = 0.22
        row_step = 0.60 / max(1, n_countries - 1)
        playable = [(k, v) for k, v in COUNTRIES.items()
                    if k != 'neutral']
        for i, (key, info) in enumerate(playable):
            c = info['color']
            chip = DirectFrame(parent=frame,
                               frameColor=(c[0], c[1], c[2], 1),
                               frameSize=(-0.03, 0.03, -0.03, 0.03),
                               pos=(-0.78, 0, y + 0.01))
            self.widgets.append(chip)
            btn = DirectButton(
                parent=frame, text="[%d]  %s" % (i + 1, info['name'].upper()),
                text_scale=0.045, text_fg=INK, text_align=TextNode.ALeft,
                text_font=self.base.hud_font,
                frameColor=((0.86, 0.82, 0.68, 0.0),
                            (0.80, 0.74, 0.55, 1.0),
                            (0.70, 0.66, 0.54, 0.9), (0.5, 0.5, 0.5, 0.3)),
                frameSize=(-0.05, 1.45, -0.05, 0.07), relief=DGG.FLAT,
                command=self._pick, extraArgs=[key],
                pos=(-0.68, 0, y))
            self.widgets.append(btn)
            blurb = COUNTRY_BLURBS[key].replace('\n', ' ')
            paper_text(blurb, (-0.68, y - 0.055), 0.028, INK_FAINT,
                       TextNode.ALeft)
            self.base.accept(str(i + 1), self._pick, [key])
            y -= row_step

        paper_text("REPLY BY RETURN FAX INDICATING NATION.  TIME IS",
                   (0, -0.62), 0.035)
        paper_text("OF THE ESSENCE.  ++ MESSAGE ENDS ++", (0, -0.67), 0.035)
        self._button("[B]  BACK", (0, -0.92), self.show_main, width=0.3,
                     scale=0.04)
        self.base.accept('b', self.show_main)
        self.base.accept('escape', self.show_main)

    def show_settings(self):
        self._clear()
        frame = DirectFrame(parent=self.root, frameColor=PAPER,
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
