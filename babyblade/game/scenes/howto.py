"""How to play: finishes, actions and counters, controls, AI."""

from __future__ import annotations

import pygame

from babyblade.game import assets as A
from babyblade.game import inputs, ui
from babyblade.game.app import Scene

ACTIONS = [
    ("CHARGE", "Charge", "0 spin", "+20 spin (Stamina +25), drifts to the centre. Takes 25% extra damage."),
    ("ATTACK", "Attack", "8 spin", "Dash at the rival. 12 damage x power. Beats Charge."),
    ("GUARD", "Guard", "4 spin", "+5 stability (Defender +10). Halves hits; attacker takes 3 recoil."),
    ("DODGE", "Dodge", "8 spin", "Side-step that evades Attack and Special. Fails near the edge."),
    ("SPECIAL", "Special Spin", "35 spin", "25 damage, big push, 10 self-recoil, 3 s cooldown. Breaks Guard."),
]
FINISHES = [
    ("RING OUT", A.GOLD, "Push the rival past the stadium edge."),
    ("BURST", A.RED, "Break the rival's stability to zero."),
    ("SPIN FINISH", A.CYAN, "Outlast the rival until its spin runs out."),
    ("POINTS", A.GREEN, "After 40 rounds: 40% spin, 40% stability, 20% centre position."),
]
CONTROLS = [
    ("Actions", "1 Charge · 2 Attack · 3 Guard · 4 Special · SPACE Dodge · gamepad X A Y RB B"),
    ("Steer", "move freely: WASD / arrows · left stick · on-screen joystick"),
    ("Pause", "P / Esc · Start · pause button"),
    ("Launch", "Space / tap / A in the green zone"),
    ("Guide", "H in battle explains every number and gauge on the screen"),
    ("Mute", "M"),
]


class HowToScene(Scene):
    def __init__(self) -> None:
        self.page = 0
        self.back = ui.Button((A.W - 60 - 180, A.H - 76, 180, 52), "Back", self._back, accent=A.MUTED)
        self.menu = ui.Menu([self.back])

    def _back(self) -> None:
        self.app.pop()

    def event(self, e: pygame.event.Event) -> None:
        cmd = inputs.nav(e)
        if cmd == "back":
            self._back()
        elif cmd in ("left", "right"):
            self.page = (self.page + (1 if cmd == "right" else -1)) % 3
        elif cmd == "confirm":
            self.menu.nav("confirm")
        self.menu.handle(e)
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and e.pos[1] < 110:
            self.page = (self.page + 1) % 3

    def update(self, dt: float) -> None:
        self.menu.update(dt)

    def draw(self, screen: pygame.Surface) -> None:
        screen.blit(A.stage_background(), (0, 0))
        A.glow_text(screen, "HOW TO PLAY", 50, A.WHITE, A.PURPLE, (60, 30), anchor="topleft")
        tabs = ["Finishes & rounds", "Actions & counters", "Controls & AI"]
        for i, t in enumerate(tabs):
            r = pygame.Rect(520 + i * 230, 40, 220, 44)
            pygame.draw.rect(screen, A.PANEL_HI if i == self.page else A.PANEL, r, border_radius=10)
            pygame.draw.rect(screen, A.PURPLE if i == self.page else A.LINE, r, 2, border_radius=10)
            A.text(screen, t.upper(), 16, A.WHITE if i == self.page else A.MUTED, r.center, weight="bold")
        A.text(screen, "LEFT / RIGHT to switch pages", 14, A.DIM, (A.W - 60, 100), anchor="topright")
        body = pygame.Rect(60, 126, A.W - 120, 500)
        ui.panel(screen, body, alpha=190)
        if self.page == 0:
            y = body.y + 34
            A.text(screen, "40 rounds of 3 seconds (120 s). Each round both blades lock in one action at the same time.", 19, A.WHITE, (body.x + 30, y), anchor="topleft")
            A.text(screen, "Physics runs continuously: blades orbit the bowl, dash, collide and get knocked back.", 19, A.MUTED, (body.x + 30, y + 30), anchor="topleft")
            A.text(screen, "The stadium shrinks by 1 every 6 rounds (10 → 6). Outside the line you are out.", 19, A.MUTED, (body.x + 30, y + 60), anchor="topleft")
            y += 120
            for name, col, desc in FINISHES:
                A.glow_text(screen, name, 30, col, col, (body.x + 30, y), anchor="midleft", strength=2)
                A.text(screen, desc, 19, A.WHITE, (body.x + 270, y), anchor="midleft")
                y += 70
            A.text(screen, "Both eliminated in the same moment = DRAW.", 17, A.MUTED, (body.x + 30, y), anchor="midleft")
        elif self.page == 1:
            y = body.y + 40
            for icon, name, cost, desc in ACTIONS:
                A.draw_icon(screen, icon, (body.x + 50, y), 34, A.GOLD)
                A.text(screen, name.upper(), 24, A.WHITE, (body.x + 90, y), anchor="midleft", weight="bold")
                A.text(screen, cost, 16, A.MUTED, (body.x + 290, y), anchor="midleft", weight="bold")
                A.text(screen, desc, 18, A.WHITE, (body.x + 390, y), anchor="midleft")
                y += 70
            A.text(screen, "Counters: Attack > Charge · Guard > Attack · Special breaks Guard · Dodge avoids Attack & Special",
                   18, A.GOLD, (body.centerx, body.bottom - 60), weight="bold")
            A.text(screen, "If both attack, both hits land. Nobody gets priority.", 16, A.MUTED, (body.centerx, body.bottom - 30))
        else:
            y = body.y + 36
            for k, v in CONTROLS:
                A.text(screen, k.upper(), 20, A.GOLD, (body.x + 30, y), anchor="midleft", weight="bold")
                A.text(screen, v, 19, A.WHITE, (body.x + 180, y), anchor="midleft")
                y += 42
            y += 14
            lines = [
                ("IRONCLAD", A.RED, "Minimax search with MAX/MIN values, alpha-beta pruning and iterative deepening."),
                ("CYCLONE", A.PURPLE, "Monte Carlo Tree Search: selection (UCB1), expansion, simulation, backpropagation."),
                ("DANGER", A.GREEN, "Mamdani fuzzy logic: edge distance + spin energy → Low / Medium / High."),
            ]
            for name, col, desc in lines:
                A.text(screen, name, 20, col, (body.x + 30, y), anchor="midleft", weight="bold")
                A.text(screen, desc, 18, A.WHITE, (body.x + 180, y), anchor="midleft")
                y += 44
        self.menu.draw(screen)
