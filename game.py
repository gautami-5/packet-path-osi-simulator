"""
PACKET PATH — OSI Transmission Lab
===================================
A Python/Pygame educational networking game.

Part 1: Message Composition Screen
  - Player types a message on a simulated PC desktop
  - Animated neon dark UI with blinking cursor
  - Character counter, source/destination info
  - "SEND TO OS" button triggers encapsulation journey
"""

import pygame
import sys
import math
import time

# ---------------------------------------------------------------------------
# CONSTANTS & COLOUR PALETTE
# ---------------------------------------------------------------------------

SCREEN_W, SCREEN_H = 1200, 750
FPS = 60
TITLE = "PACKET PATH — OSI Transmission Lab"

# Colour palette (mirrors the HTML/CSS design)
C = {
    "bg":        (8,   13,  24),    # deep navy
    "panel":     (16,  24,  39),    # slightly lighter panel
    "panel2":    (13,  20,  34),
    "line":      (38,  53,  74),    # border colour
    "text":      (237, 245, 255),   # near-white
    "muted":     (145, 164, 191),   # grey-blue
    "cyan":      (85,  230, 255),   # neon cyan
    "cyan_dim":  (40,  110, 130),
    "blue":      (109, 140, 255),
    "violet":    (178, 140, 255),
    "green":     (98,  237, 178),
    "amber":     (255, 200, 107),
    "red":       (255, 107, 130),
    "white":     (255, 255, 255),
    "black":     (0,   0,   0),
}

# ---------------------------------------------------------------------------
# HELPER: Rounded Rectangle
# ---------------------------------------------------------------------------

def draw_rect_rounded(surf, colour, rect, radius=12, border=0, border_colour=None):
    """Draw a filled (and optionally bordered) rounded rectangle."""
    if border and border_colour:
        pygame.draw.rect(surf, border_colour, rect, border_radius=radius)
        inner = pygame.Rect(rect.x + border, rect.y + border,
                            rect.w - border * 2, rect.h - border * 2)
        pygame.draw.rect(surf, colour, inner, border_radius=max(0, radius - border))
    else:
        pygame.draw.rect(surf, colour, rect, border_radius=radius)


def draw_gradient_rect(surf, rect, col_top, col_bot, radius=0):
    """Vertical gradient fill inside rect."""
    for y in range(rect.h):
        t = y / max(rect.h - 1, 1)
        r = int(col_top[0] + (col_bot[0] - col_top[0]) * t)
        g = int(col_top[1] + (col_bot[1] - col_top[1]) * t)
        b = int(col_top[2] + (col_bot[2] - col_top[2]) * t)
        pygame.draw.line(surf, (r, g, b), (rect.x, rect.y + y), (rect.x + rect.w - 1, rect.y + y))


def glow_surface(radius, colour, alpha=80):
    """Create a circular glow surface."""
    size = radius * 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    for r in range(radius, 0, -1):
        a = int(alpha * (1 - r / radius) ** 1.5)
        pygame.draw.circle(surf, (*colour, a), (radius, radius), r)
    return surf


# ---------------------------------------------------------------------------
# FONT LOADER
# ---------------------------------------------------------------------------

class Fonts:
    def __init__(self):
        pygame.font.init()
        # Use system fonts that we confirmed exist
        self.title_lg  = pygame.font.SysFont("segoeuisemibold", 26, bold=False)
        self.title_sm  = pygame.font.SysFont("segoeui",         13, bold=False)
        self.label     = pygame.font.SysFont("segoeuisemibold", 11, bold=False)
        self.label_lg  = pygame.font.SysFont("segoeuisemibold", 14, bold=False)
        self.body      = pygame.font.SysFont("segoeui",         14, bold=False)
        self.body_sm   = pygame.font.SysFont("segoeui",         12, bold=False)
        self.mono      = pygame.font.SysFont("consolas",        13, bold=False)
        self.mono_sm   = pygame.font.SysFont("consolas",        11, bold=False)
        self.hero      = pygame.font.SysFont("segoeuisemibold", 38, bold=False)
        self.btn       = pygame.font.SysFont("segoeuisemibold", 15, bold=False)
        self.counter   = pygame.font.SysFont("consolas",        12, bold=False)


# ---------------------------------------------------------------------------
# PARTICLE SYSTEM (background ambience)
# ---------------------------------------------------------------------------

class Particle:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = float(pygame.display.get_surface().get_width()) * \
                 (0.1 + 0.8 * __import__('random').random())
        self.y = float(pygame.display.get_surface().get_height()) + 10
        self.vy = -(__import__('random').random() * 0.4 + 0.1)
        self.vx = (__import__('random').random() - 0.5) * 0.2
        self.alpha = int(__import__('random').random() * 80 + 20)
        self.radius = __import__('random').random() * 1.5 + 0.5
        c = __import__('random').choice([C["cyan"], C["violet"], C["blue"]])
        self.colour = c

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.y < -10:
            self.reset()
            self.y = float(pygame.display.get_surface().get_height()) + 10

    def draw(self, surf):
        if self.radius < 1:
            return
        s = pygame.Surface((int(self.radius * 2 + 1), int(self.radius * 2 + 1)), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.colour, self.alpha),
                           (int(self.radius), int(self.radius)), int(self.radius))
        surf.blit(s, (int(self.x - self.radius), int(self.y - self.radius)))


# ---------------------------------------------------------------------------
# TOAST NOTIFICATION
# ---------------------------------------------------------------------------

class Toast:
    def __init__(self, fonts: Fonts):
        self.fonts = fonts
        self.message = ""
        self.alpha = 0
        self.timer = 0
        self.colour = C["cyan"]

    def show(self, msg, colour=None):
        self.message = msg
        self.alpha = 255
        self.timer = 2.5          # seconds
        self.colour = colour or C["cyan"]

    def update(self, dt):
        if self.timer > 0:
            self.timer -= dt
            if self.timer <= 0.5:
                self.alpha = int(255 * (self.timer / 0.5))
            else:
                self.alpha = 255

    def draw(self, surf):
        if self.timer <= 0 or not self.message:
            return
        text_surf = self.fonts.body.render(self.message, True, self.colour)
        pad_x, pad_y = 20, 10
        w = text_surf.get_width() + pad_x * 2
        h = text_surf.get_height() + pad_y * 2
        x = (surf.get_width() - w) // 2
        y = surf.get_height() - h - 24

        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.set_alpha(self.alpha)
        pygame.draw.rect(panel, (20, 35, 55, 220), pygame.Rect(0, 0, w, h), border_radius=10)
        pygame.draw.rect(panel, (*self.colour, 180), pygame.Rect(0, 0, w, h),
                         border_radius=10, width=1)
        panel.blit(text_surf, (pad_x, pad_y))
        surf.blit(panel, (x, y))


# ---------------------------------------------------------------------------
# ANIMATED BUTTON
# ---------------------------------------------------------------------------

class Button:
    def __init__(self, rect, label, fonts: Fonts, primary=True):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.fonts = fonts
        self.primary = primary
        self.hover = False
        self.press_time = 0
        self._anim_t = 0.0         # 0→1 hover animation

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.press_time = time.time()
                return True
        return False

    def update(self, dt):
        target = 1.0 if self.hover else 0.0
        self.hover = self.rect.collidepoint(pygame.mouse.get_pos())
        self._anim_t += (target - self._anim_t) * min(1.0, dt * 10)

    def draw(self, surf):
        t = self._anim_t
        # Lift effect
        lift = int(t * 3)
        r = self.rect.move(0, -lift)

        if self.primary:
            # Gradient: cyan → violet
            col_l = tuple(int(C["cyan"][i] + (C["blue"][i] - C["cyan"][i]) * t) for i in range(3))
            col_r = tuple(int(C["blue"][i] + (C["violet"][i] - C["blue"][i]) * t) for i in range(3))
            draw_gradient_rect(surf, r, col_l, col_r, radius=12)
            pygame.draw.rect(surf, col_l, r, border_radius=12, width=0)
            # Glow on hover
            if t > 0.1:
                glow = pygame.Surface((r.w + 40, r.h + 40), pygame.SRCALPHA)
                pygame.draw.rect(glow, (*C["cyan"], int(30 * t)),
                                 pygame.Rect(20, 20, r.w, r.h), border_radius=12)
                surf.blit(glow, (r.x - 20, r.y - 20))
            text_col = C["black"]
        else:
            border_col = tuple(int(C["line"][i] + (C["cyan"][i] - C["line"][i]) * t) for i in range(3))
            draw_rect_rounded(surf, C["panel"], r, radius=12,
                              border=1, border_colour=border_col)
            text_col = C["text"]

        label_surf = self.fonts.btn.render(self.label, True, text_col)
        surf.blit(label_surf, (r.centerx - label_surf.get_width() // 2,
                                r.centery - label_surf.get_height() // 2))


# ---------------------------------------------------------------------------
# TEXT INPUT WIDGET
# ---------------------------------------------------------------------------

class TextInput:
    MAX_LEN = 120

    def __init__(self, rect, fonts: Fonts, placeholder="Type your message here…"):
        self.rect = pygame.Rect(rect)
        self.fonts = fonts
        self.placeholder = placeholder
        self.text = ""
        self.cursor_visible = True
        self.cursor_timer = 0.0
        self.focused = True
        self._focus_anim = 0.0    # 0→1 for border glow

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.focused = self.rect.collidepoint(event.pos)

        if self.focused and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                pass  # handled upstream
            elif event.unicode and len(self.text) < self.MAX_LEN:
                self.text += event.unicode

    def update(self, dt):
        self.cursor_timer += dt
        if self.cursor_timer >= 0.5:
            self.cursor_timer = 0.0
            self.cursor_visible = not self.cursor_visible

        target = 1.0 if self.focused else 0.0
        self.focused = self.focused  # keep state
        self._focus_anim += (target - self._focus_anim) * min(1.0, dt * 8)

    def draw(self, surf):
        t = self._focus_anim
        border_col = tuple(int(C["line"][i] + (C["cyan"][i] - C["line"][i]) * t) for i in range(3))

        # Glow halo
        if t > 0.05:
            glow = pygame.Surface((self.rect.w + 20, self.rect.h + 20), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*C["cyan"], int(18 * t)),
                             pygame.Rect(10, 10, self.rect.w, self.rect.h), border_radius=12)
            surf.blit(glow, (self.rect.x - 10, self.rect.y - 10))

        draw_rect_rounded(surf, (10, 18, 32), self.rect, radius=12,
                          border=2, border_colour=border_col)

        # Determine display text
        display = self.text if self.text else self.placeholder
        col = C["text"] if self.text else C["muted"]

        # Word-wrap / clip
        inner_x = self.rect.x + 16
        inner_y = self.rect.y + 14
        inner_w = self.rect.w - 32
        inner_h = self.rect.h - 28

        # Simple multi-line wrapping
        words = display.split(" ")
        lines, current = [], ""
        for w in words:
            test = (current + " " + w).strip()
            if self.fonts.body.size(test)[0] <= inner_w:
                current = test
            else:
                if current:
                    lines.append(current)
                current = w
        if current:
            lines.append(current)

        # Draw lines (max 4 visible)
        line_h = self.fonts.body.get_linesize() + 2
        clip = surf.get_clip()
        surf.set_clip(pygame.Rect(inner_x, inner_y, inner_w, inner_h))
        for i, ln in enumerate(lines[:4]):
            ls = self.fonts.body.render(ln, True, col)
            surf.blit(ls, (inner_x, inner_y + i * line_h))

        # Blinking cursor on last line
        if self.focused and self.cursor_visible and self.text:
            last_line = lines[-1] if lines else ""
            cx = inner_x + self.fonts.body.size(last_line)[0] + 2
            cy = inner_y + (len(lines) - 1) * line_h
            pygame.draw.line(surf, C["cyan"], (cx, cy + 2), (cx, cy + line_h - 2), 2)

        surf.set_clip(clip)

    @property
    def value(self):
        return self.text.strip()


# ---------------------------------------------------------------------------
# OSI LAYER INFO CARDS (right panel)
# ---------------------------------------------------------------------------

OSI_LAYERS = [
    {"n": 7, "name": "Application",  "pdu": "Data",    "colour": C["cyan"],   "info": "HTTP, DNS — provides services to apps"},
    {"n": 6, "name": "Presentation", "pdu": "Data",    "colour": C["blue"],   "info": "Encoding, encryption, formatting"},
    {"n": 5, "name": "Session",      "pdu": "Data",    "colour": C["violet"], "info": "Session management & dialogue control"},
    {"n": 4, "name": "Transport",    "pdu": "Segment", "colour": C["green"],  "info": "Port numbers, reliability (TCP/UDP)"},
    {"n": 3, "name": "Network",      "pdu": "Packet",  "colour": C["amber"],  "info": "IP addressing & routing decisions"},
    {"n": 2, "name": "Data Link",    "pdu": "Frame",   "colour": C["red"],    "info": "MAC addresses, hop-to-hop delivery"},
    {"n": 1, "name": "Physical",     "pdu": "Bits",    "colour": C["muted"],  "info": "Raw bitstream over cable/radio"},
]


# ---------------------------------------------------------------------------
# SCENE: LEVEL 1 — COMPOSE MESSAGE
# ---------------------------------------------------------------------------

class Level1Compose:
    """
    The first screen of the game.
    Player types a message; clicking SEND TO OS returns the text
    and triggers the transition to the next part.
    """

    def __init__(self, screen: pygame.Surface, fonts: Fonts, clock: pygame.time.Clock):
        self.screen = screen
        self.fonts = fonts
        self.clock = clock
        self.toast = Toast(fonts)

        W, H = screen.get_width(), screen.get_height()

        # ── Layout geometry ──────────────────────────────────────
        self.header_h   = 70
        self.footer_h   = 36
        self.pad        = 28
        self.left_w     = int(W * 0.58)
        self.right_w    = W - self.left_w - self.pad * 3

        # Left panel (compose area)
        lp_x = self.pad
        lp_y = self.header_h + self.pad
        lp_w = self.left_w
        lp_h = H - self.header_h - self.footer_h - self.pad * 2
        self.left_panel = pygame.Rect(lp_x, lp_y, lp_w, lp_h)

        # Input box inside left panel
        in_x = lp_x + 24
        in_y = lp_y + 120
        in_w = lp_w - 48
        in_h = 130
        self.input = TextInput(pygame.Rect(in_x, in_y, in_w, in_h), fonts)

        # Buttons
        btn_y = in_y + in_h + 22
        self.btn_send = Button(pygame.Rect(in_x + in_w - 200, btn_y, 200, 46), "↗  SEND TO OS", fonts, primary=True)
        self.btn_clear = Button(pygame.Rect(in_x, btn_y, 110, 46), "✕  Clear", fonts, primary=False)

        # Info row below buttons
        self.info_y = btn_y + 66

        # Right panel (OSI layer stack preview)
        rp_x = lp_x + lp_w + self.pad
        rp_y = lp_y
        rp_w = self.right_w
        rp_h = lp_h
        self.right_panel = pygame.Rect(rp_x, rp_y, rp_w, rp_h)
        self.rp_x = rp_x
        self.rp_y = rp_y
        self.rp_w = rp_w

        # Particles
        import random
        self.particles = [Particle() for _ in range(35)]

        # Animation state
        self.time_elapsed = 0.0
        self.panel_slide  = 0.0     # 0→1 panels slide in
        self.result_msg   = None    # set when done

        # OSI layer hover
        self.hovered_layer = -1

        # Scanline overlay (pre-rendered)
        self._scan_surf = self._make_scanlines(W, H)

    def _make_scanlines(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(0, h, 4):
            pygame.draw.line(s, (0, 0, 0, 18), (0, y), (w, y))
        return s

    # ── Input relay ──────────────────────────────────────────────

    def handle_event(self, event):
        self.input.handle_event(event)
        self.btn_send.handle_event(event)

        if self.btn_clear.handle_event(event):
            self.input.text = ""

        if self.btn_send.handle_event(event):
            self._try_send()

        # Enter key shortcut
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if pygame.key.get_mods() & pygame.KMOD_CTRL:
                self._try_send()

        # OSI layer hover (right panel)
        if event.type == pygame.MOUSEMOTION:
            self.hovered_layer = self._layer_at(event.pos)

    def _try_send(self):
        if not self.input.value:
            self.toast.show("Please type a message first!", C["amber"])
            return
        self.result_msg = self.input.value

    def _layer_at(self, pos):
        card_h = 44
        gap    = 6
        start_y = self.rp_y + 52
        for i, _ in enumerate(OSI_LAYERS):
            r = pygame.Rect(self.rp_x + 12, start_y + i * (card_h + gap),
                            self.rp_w - 24, card_h)
            if r.collidepoint(pos):
                return i
        return -1

    # ── Update ───────────────────────────────────────────────────

    def update(self, dt):
        self.time_elapsed += dt
        self.panel_slide = min(1.0, self.panel_slide + dt * 2.5)

        for p in self.particles:
            p.update()

        self.input.update(dt)
        self.btn_send.update(dt)
        self.btn_clear.update(dt)
        self.toast.update(dt)

    # ── Draw ─────────────────────────────────────────────────────

    def draw(self):
        surf = self.screen
        W, H = surf.get_width(), surf.get_height()
        t = self.time_elapsed

        # Background
        surf.fill(C["bg"])

        # Radial glow blobs (ambient)
        for (cx, cy, col, rad) in [
            (int(W * 0.12), int(H * 0.02), C["blue"],   320),
            (int(W * 0.88), int(H * 0.08), C["violet"], 260),
            (int(W * 0.50), int(H * 0.95), C["cyan"],   200),
        ]:
            g = glow_surface(rad, col, alpha=18)
            surf.blit(g, (cx - rad, cy - rad))

        # Particles
        for p in self.particles:
            p.draw(surf)

        # Scanlines
        surf.blit(self._scan_surf, (0, 0))

        # ── HEADER ───────────────────────────────────────────────
        self._draw_header(surf, W, t)

        # ── SLIDE-IN ANIMATION ───────────────────────────────────
        slide_t = self._ease_out(self.panel_slide)
        offset = int((1 - slide_t) * 60)

        # ── LEFT PANEL ───────────────────────────────────────────
        lp = self.left_panel.move(-offset, 0)
        self._draw_panel_bg(surf, lp)
        self._draw_left_panel(surf, lp, t)

        # ── RIGHT PANEL ──────────────────────────────────────────
        rp = self.right_panel.move(offset, 0)
        self._draw_panel_bg(surf, rp)
        self._draw_right_panel(surf, rp, t)

        # ── TOAST ────────────────────────────────────────────────
        self.toast.draw(surf)

        # ── FOOTER ───────────────────────────────────────────────
        self._draw_footer(surf, W, H)

    def _draw_header(self, surf, W, t):
        # Header bar with gradient
        header = pygame.Rect(0, 0, W, self.header_h)
        draw_gradient_rect(surf, header, (12, 20, 38), (8, 13, 24))

        # Bottom border
        pygame.draw.line(surf, C["line"], (0, self.header_h - 1), (W, self.header_h - 1))

        # Logo circle
        logo_r = pygame.Rect(self.pad, 13, 44, 44)
        pulse = 0.5 + 0.5 * math.sin(t * 2.2)
        logo_col = tuple(int(C["cyan"][i] + (C["violet"][i] - C["cyan"][i]) * pulse) for i in range(3))
        pygame.draw.rect(surf, logo_col, logo_r, border_radius=13)
        sym = self.fonts.hero.render("↯", True, C["black"])
        surf.blit(sym, (logo_r.centerx - sym.get_width() // 2,
                        logo_r.centery - sym.get_height() // 2))

        # Title text
        title = self.fonts.title_lg.render("PACKET PATH", True, C["text"])
        sub   = self.fonts.title_sm.render("From message to delivery  ·  Interactive OSI Simulator", True, C["muted"])
        eyeb  = self.fonts.label.render("NETWORK TRANSMISSION LAB", True, C["cyan"])
        tx = self.pad + 54
        surf.blit(eyeb,  (tx, 16))
        surf.blit(title, (tx, 28))
        surf.blit(sub,   (tx, 50))

        # Level badge (right side)
        badge_x = W - 280
        badge_y = 14
        badge_r = pygame.Rect(badge_x, badge_y, 250, 42)
        draw_rect_rounded(surf, (16, 28, 48), badge_r, radius=10,
                          border=1, border_colour=C["line"])

        lvl_lbl = self.fonts.label.render("CURRENT LEVEL", True, C["muted"])
        lvl_txt = self.fonts.label_lg.render("01 / COMPOSE MESSAGE", True, C["cyan"])
        surf.blit(lvl_lbl, (badge_x + 12, badge_y + 6))
        surf.blit(lvl_txt, (badge_x + 12, badge_y + 22))

        # Score placeholder
        sc_x = W - 30 - 110
        sc_r = pygame.Rect(sc_x, 14, 110, 42)
        # (not drawn here; shown once scoring starts)

    def _draw_panel_bg(self, surf, rect):
        """Draw the dark glassmorphism panel."""
        draw_rect_rounded(surf, C["panel"], rect, radius=16,
                          border=1, border_colour=C["line"])

    def _draw_left_panel(self, surf, panel, t):
        px, py = panel.x + 24, panel.y + 20

        # Section title
        h2 = self.fonts.label_lg.render("01 /  COMPOSE YOUR MESSAGE", True, C["text"])
        tag = self.fonts.mono_sm.render("LAYER 7 · APPLICATION", True, C["cyan"])
        surf.blit(h2,  (px, py))
        surf.blit(tag, (px + h2.get_width() + 16, py + 2))

        # Divider
        pygame.draw.line(surf, C["line"], (px, py + 22), (panel.right - 24, py + 22))

        # Source / Destination row
        iy = py + 36
        self._draw_info_field(surf, px,                    iy, 220, "SOURCE DEVICE",
                              "PC-01  ·  192.168.1.10", C["cyan"])
        self._draw_info_field(surf, px + 240,              iy, 220, "DESTINATION",
                              "Server-01  ·  10.0.0.20", C["green"])
        self._draw_info_field(surf, panel.right - 24 - 170, iy, 170, "PROTOCOL",
                              "TCP  ·  Port 443", C["violet"])

        # "TYPE YOUR MESSAGE" label
        lbl_y = iy + 58
        label = self.fonts.label.render("MESSAGE PAYLOAD", True, C["muted"])
        surf.blit(label, (px, lbl_y))

        # Character counter
        char_cnt = self.fonts.counter.render(
            f"{len(self.input.text)}/{TextInput.MAX_LEN}", True,
            C["amber"] if len(self.input.text) > 100 else C["muted"])
        surf.blit(char_cnt, (panel.right - 24 - char_cnt.get_width(), lbl_y))

        # Draw input field (positioned relative to panel offset)
        dx = self.input.rect.x - self.left_panel.x + panel.x
        dy = self.input.rect.y - self.left_panel.y + panel.y
        old_rect = self.input.rect.copy()
        self.input.rect.x = dx
        self.input.rect.y = dy
        self.input.draw(surf)
        self.input.rect = old_rect

        # ── Hint row beneath input ───────────────────────────────
        hint_y = dy + self.input.rect.h + 10
        hint = self.fonts.body_sm.render(
            "Press  Ctrl + Enter  to send   ·   Max 120 characters", True, C["muted"])
        surf.blit(hint, (px, hint_y))

        # Draw buttons
        dbx = self.input.rect.x - self.left_panel.x + panel.x
        dby = self.input.rect.y - self.left_panel.y + panel.y + self.input.rect.h + 28

        old_s = self.btn_send.rect.copy()
        old_c = self.btn_clear.rect.copy()

        self.btn_send.rect.x  = dbx + (self.input.rect.w - 200)
        self.btn_send.rect.y  = dby
        self.btn_clear.rect.x = dbx
        self.btn_clear.rect.y = dby

        self.btn_send.draw(surf)
        self.btn_clear.draw(surf)

        self.btn_send.rect  = old_s
        self.btn_clear.rect = old_c

        # ── Concept callout box ──────────────────────────────────
        box_y = dby + 62
        box_r = pygame.Rect(px, box_y, panel.w - 48, 76)
        draw_rect_rounded(surf, (10, 22, 38), box_r, radius=10,
                          border=1, border_colour=(40, 60, 85))

        icon = self.fonts.label_lg.render("💡", True, C["amber"])
        surf.blit(icon, (box_r.x + 12, box_r.y + 10))

        concept_title = self.fonts.label.render("WHAT HAPPENS NEXT?", True, C["amber"])
        concept_body  = self.fonts.body_sm.render(
            "Your message will be handed to the Operating System, which passes it", True, C["muted"])
        concept_body2 = self.fonts.body_sm.render(
            "down through each OSI layer — adding headers at every step.", True, C["muted"])
        surf.blit(concept_title, (box_r.x + 38, box_r.y + 10))
        surf.blit(concept_body,  (box_r.x + 12, box_r.y + 32))
        surf.blit(concept_body2, (box_r.x + 12, box_r.y + 50))

    def _draw_info_field(self, surf, x, y, w, label, value, val_col):
        lbl = self.fonts.label.render(label, True, C["muted"])
        val = self.fonts.mono.render(value, True, val_col)
        r = pygame.Rect(x, y, w, 46)
        draw_rect_rounded(surf, (10, 18, 32), r, radius=8,
                          border=1, border_colour=C["line"])
        surf.blit(lbl, (x + 10, y + 6))
        surf.blit(val, (x + 10, y + 24))

    def _draw_right_panel(self, surf, panel, t):
        px, py = panel.x + 16, panel.y + 18

        h2  = self.fonts.label_lg.render("OSI LAYER STACK", True, C["text"])
        sub = self.fonts.body_sm.render("Click any layer to learn more", True, C["muted"])
        surf.blit(h2,  (px, py))
        surf.blit(sub, (px, py + 20))

        pygame.draw.line(surf, C["line"], (px, py + 38), (panel.right - 16, py + 38))

        card_h = 44
        gap    = 6
        start_y = py + 50

        mx, my = pygame.mouse.get_pos()

        for i, layer in enumerate(OSI_LAYERS):
            cy = start_y + i * (card_h + gap)
            cr = pygame.Rect(panel.x + 12, cy, panel.w - 24, card_h)
            is_hov = cr.collidepoint(mx, my)

            # Slide-in stagger
            slide_t = self._ease_out(min(1.0, (self.panel_slide - i * 0.05) * 3))
            ox = int((1 - slide_t) * 40)
            cr_draw = cr.move(ox, 0)

            # Background
            bg_col = (18, 32, 52) if is_hov else (13, 22, 36)
            draw_rect_rounded(surf, bg_col, cr_draw, radius=8,
                              border=1, border_colour=layer["colour"] if is_hov else C["line"])

            # Left colour strip
            strip = pygame.Rect(cr_draw.x + 1, cr_draw.y + 4, 4, cr_draw.h - 8)
            pygame.draw.rect(surf, layer["colour"], strip, border_radius=3)

            # Layer number
            num = self.fonts.mono_sm.render(f"L{layer['n']}", True, layer["colour"])
            surf.blit(num, (cr_draw.x + 14, cr_draw.y + 7))

            # Layer name
            name_col = C["text"] if is_hov else C["muted"]
            name = self.fonts.label.render(layer["name"].upper(), True, name_col)
            surf.blit(name, (cr_draw.x + 40, cr_draw.y + 7))

            # PDU badge
            pdu = self.fonts.mono_sm.render(layer["pdu"], True, layer["colour"])
            surf.blit(pdu, (cr_draw.right - pdu.get_width() - 10, cr_draw.y + 7))

            # Info text (on hover)
            if is_hov:
                info = self.fonts.body_sm.render(layer["info"], True, C["muted"])
                surf.blit(info, (cr_draw.x + 14, cr_draw.y + 26))
            else:
                info = self.fonts.body_sm.render(layer["info"], True, (60, 80, 110))
                surf.blit(info, (cr_draw.x + 14, cr_draw.y + 26))

        # Bottom note
        note_y = start_y + len(OSI_LAYERS) * (card_h + gap) + 10
        note = self.fonts.body_sm.render(
            "Next level: drag your message into each layer →", True, C["muted"])
        surf.blit(note, (px, note_y))

    def _draw_footer(self, surf, W, H):
        pygame.draw.line(surf, C["line"], (0, H - self.footer_h), (W, H - self.footer_h))
        text = self.fonts.mono_sm.render(
            "PACKET PATH  ·  Educational simulation  ·  No real packets transmitted  ·  Protocol fields are illustrative",
            True, (70, 95, 130))
        surf.blit(text, (W // 2 - text.get_width() // 2, H - self.footer_h + 10))

    @staticmethod
    def _ease_out(t):
        t = max(0.0, min(1.0, t))
        return 1 - (1 - t) ** 3


# ---------------------------------------------------------------------------
# TRANSITION SCREEN  (flash → slide between levels)
# ---------------------------------------------------------------------------

class TransitionScreen:
    def __init__(self, screen, fonts, message="Sending to OS…"):
        self.screen = screen
        self.fonts  = fonts
        self.message = message
        self.alpha  = 0.0
        self.done   = False
        self._t     = 0.0

    def update(self, dt):
        self._t += dt
        # Fade in → hold → fade out
        if self._t < 0.4:
            self.alpha = self._t / 0.4
        elif self._t < 1.0:
            self.alpha = 1.0
        elif self._t < 1.4:
            self.alpha = 1.0 - (self._t - 1.0) / 0.4
        else:
            self.done = True

    def draw(self):
        surf = self.screen
        W, H = surf.get_width(), surf.get_height()
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((*C["bg"], int(self.alpha * 240)))
        surf.blit(overlay, (0, 0))

        if self.alpha > 0.3:
            # Glowing packet icon
            cx, cy = W // 2, H // 2 - 30
            pulse = 0.6 + 0.4 * math.sin(self._t * 8)
            r = int(36 * pulse)
            g = glow_surface(r + 20, C["cyan"], alpha=60)
            surf.blit(g, (cx - r - 20, cy - r - 20))
            pygame.draw.circle(surf, C["panel"], (cx, cy), r)
            pygame.draw.circle(surf, C["cyan"], (cx, cy), r, width=2)

            icon = self.fonts.hero.render("↯", True, C["cyan"])
            surf.blit(icon, (cx - icon.get_width() // 2, cy - icon.get_height() // 2))

            msg = self.fonts.label_lg.render(self.message, True, C["text"])
            sub = self.fonts.body_sm.render("Passing to Operating System…", True, C["muted"])
            surf.blit(msg, (W // 2 - msg.get_width() // 2, cy + r + 20))
            surf.blit(sub, (W // 2 - sub.get_width() // 2, cy + r + 44))


# ---------------------------------------------------------------------------
# MAIN GAME  — state machine
# ---------------------------------------------------------------------------

class Game:
    STATE_COMPOSE    = "compose"
    STATE_TRANSITION = "transition"
    STATE_DONE       = "done"     # placeholder for Level 2 (future)

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        flags = pygame.DOUBLEBUF | pygame.HWSURFACE
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), flags)
        self.clock  = pygame.time.Clock()
        self.fonts  = Fonts()

        # Game state
        self.state   = self.STATE_COMPOSE
        self.message = ""            # filled after Level 1

        # Scenes
        self.compose    = Level1Compose(self.screen, self.fonts, self.clock)
        self.transition = None

    # ── Main loop ────────────────────────────────────────────────

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._quit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self._quit()
                self._handle_event(event)

            self._update(dt)
            self._draw()
            pygame.display.flip()

    def _handle_event(self, event):
        if self.state == self.STATE_COMPOSE:
            self.compose.handle_event(event)

    def _update(self, dt):
        if self.state == self.STATE_COMPOSE:
            self.compose.update(dt)
            # Check if player clicked SEND
            if self.compose.result_msg:
                self.message = self.compose.result_msg
                self.state   = self.STATE_TRANSITION
                self.transition = TransitionScreen(
                    self.screen, self.fonts,
                    f'Sending  "{self.message[:40]}{"…" if len(self.message) > 40 else ""}"')

        elif self.state == self.STATE_TRANSITION:
            self.transition.update(dt)
            if self.transition.done:
                # TODO: load Level 2 here; for now show a "coming soon" toast
                self.state = self.STATE_DONE
                self.compose.result_msg = None
                self.compose.toast.show(
                    f'Message "{self.message[:30]}…" queued!  Level 2 (Encapsulation) coming soon.',
                    C["green"])
                self.state = self.STATE_COMPOSE

    def _draw(self):
        if self.state in (self.STATE_COMPOSE, self.STATE_DONE):
            self.compose.draw()
        elif self.state == self.STATE_TRANSITION:
            self.compose.draw()           # background still visible
            self.transition.draw()        # overlay on top

    def _quit(self):
        pygame.quit()
        sys.exit()


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    Game().run()
