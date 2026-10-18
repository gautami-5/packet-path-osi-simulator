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
        self.title_xl  = pygame.font.SysFont("segoeuisemibold", 30, bold=True)
        self.title_md  = pygame.font.SysFont("segoeuisemibold", 18, bold=False)
        self.btn       = pygame.font.SysFont("segoeuisemibold", 15, bold=False)
        self.mono_lg   = pygame.font.SysFont("consolas",        15, bold=True)
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
# CONTACTS  (destination dropdown options)
# ---------------------------------------------------------------------------

CONTACTS = [
    {"name": "Ahmed",  "ip": "10.42.17.83",  "colour": C["cyan"],   "avatar": "A"},
    {"name": "Dhruv",  "ip": "10.91.55.204", "colour": C["violet"], "avatar": "D"},
    {"name": "Layla",  "ip": "10.33.8.112",  "colour": C["green"],  "avatar": "L"},
    {"name": "Marcus", "ip": "10.76.44.9",   "colour": C["amber"],  "avatar": "M"},
]


# ---------------------------------------------------------------------------
# DROPDOWN WIDGET  (in-game, no tkinter)
# ---------------------------------------------------------------------------

class Dropdown:
    """Custom pygame dropdown for selecting a contact."""

    ITEM_H = 52   # height of each contact card in the open list

    def __init__(self, rect, fonts: Fonts, contacts: list):
        self.rect     = pygame.Rect(rect)
        self.fonts    = fonts
        self.contacts = contacts
        self.selected = 0        # index into contacts
        self.open     = False
        self._hover_i = -1       # hovered item index when open
        self._anim    = 0.0      # 0→1 open animation

    # ── Public API ───────────────────────────────────────────────

    @property
    def contact(self):
        return self.contacts[self.selected]

    def handle_event(self, event):
        """Returns True if selection changed."""
        changed = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.open:
                # Check if a list item was clicked
                for i, _ in enumerate(self.contacts):
                    ir = self._item_rect(i)
                    if ir.collidepoint(pos):
                        if self.selected != i:
                            self.selected = i
                            changed = True
                        self.open = False
                        return changed
                # Click outside → close without change
                self.open = False
            else:
                if self.rect.collidepoint(pos):
                    self.open = True
        if event.type == pygame.MOUSEMOTION:
            self._hover_i = -1
            if self.open:
                for i, _ in enumerate(self.contacts):
                    if self._item_rect(i).collidepoint(event.pos):
                        self._hover_i = i
                        break
        return changed

    def update(self, dt):
        target = 1.0 if self.open else 0.0
        self._anim += (target - self._anim) * min(1.0, dt * 12)

    def draw(self, surf):
        c = self.contact
        # ── Header (always visible) ──────────────────────────────
        hov_head = self.rect.collidepoint(pygame.mouse.get_pos()) and not self.open
        border_col = C["cyan"] if self.open else (C["cyan"] if hov_head else C["line"])
        draw_rect_rounded(surf, (10, 18, 32), self.rect, radius=10,
                          border=2, border_colour=border_col)

        # Avatar circle
        av_cx = self.rect.x + 28
        av_cy = self.rect.centery
        pygame.draw.circle(surf, (*c["colour"], 60), (av_cx, av_cy), 18)
        pygame.draw.circle(surf, c["colour"], (av_cx, av_cy), 18, width=2)
        av_txt = self.fonts.label_lg.render(c["avatar"], True, c["colour"])
        surf.blit(av_txt, (av_cx - av_txt.get_width() // 2,
                           av_cy - av_txt.get_height() // 2))

        # Name + IP
        name_s = self.fonts.label_lg.render(c["name"], True, C["text"])
        ip_s   = self.fonts.mono_sm.render(c["ip"],   True, C["muted"])
        surf.blit(name_s, (self.rect.x + 54, self.rect.centery - 14))
        surf.blit(ip_s,   (self.rect.x + 54, self.rect.centery + 4))

        # Chevron
        angle = self._anim * 180     # rotates 0→180 when open
        chev = "▲" if self._anim > 0.5 else "▼"
        ch_s = self.fonts.label.render(chev, True, C["muted"])
        surf.blit(ch_s, (self.rect.right - ch_s.get_width() - 14,
                         self.rect.centery - ch_s.get_height() // 2))

        # ── Drop-down list (animated height) ─────────────────────
        if self._anim > 0.01:
            visible_h = int(self._anim * len(self.contacts) * self.ITEM_H)
            list_r = pygame.Rect(self.rect.x, self.rect.bottom + 4,
                                 self.rect.w, visible_h)
            # Clip so it reveals smoothly
            clip = surf.get_clip()
            surf.set_clip(list_r)
            for i, ct in enumerate(self.contacts):
                ir = self._item_rect(i)
                is_hov = (i == self._hover_i)
                is_sel = (i == self.selected)
                bg = (22, 40, 62) if is_hov else ((16, 30, 48) if is_sel else (12, 20, 34))
                draw_rect_rounded(surf, bg, ir, radius=8,
                                  border=1,
                                  border_colour=ct["colour"] if (is_hov or is_sel) else C["line"])
                # Avatar
                cx2, cy2 = ir.x + 22, ir.centery
                pygame.draw.circle(surf, (*ct["colour"], 50), (cx2, cy2), 14)
                pygame.draw.circle(surf, ct["colour"], (cx2, cy2), 14, width=1)
                av2 = self.fonts.label.render(ct["avatar"], True, ct["colour"])
                surf.blit(av2, (cx2 - av2.get_width() // 2, cy2 - av2.get_height() // 2))
                # Name + ip
                n2 = self.fonts.label_lg.render(ct["name"], True, C["text"] if is_hov else C["muted"])
                ip2 = self.fonts.mono_sm.render(ct["ip"], True, ct["colour"] if is_sel else (80, 110, 150))
                surf.blit(n2,  (ir.x + 44, ir.centery - 12))
                surf.blit(ip2, (ir.x + 44, ir.centery + 6))
                # Tick if selected
                if is_sel:
                    tick = self.fonts.label_lg.render("✓", True, ct["colour"])
                    surf.blit(tick, (ir.right - tick.get_width() - 12, ir.centery - tick.get_height() // 2))
            surf.set_clip(clip)

    def _item_rect(self, i):
        return pygame.Rect(self.rect.x, self.rect.bottom + 4 + i * self.ITEM_H,
                           self.rect.w, self.ITEM_H - 2)


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

        # Single full-width panel
        lp_x = self.pad
        lp_y = self.header_h + self.pad
        lp_w = W - self.pad * 2
        lp_h = H - self.header_h - self.footer_h - self.pad * 2
        self.left_panel = pygame.Rect(lp_x, lp_y, lp_w, lp_h)

        # Inner padding reference
        in_x = lp_x + 32
        in_w = lp_w - 64

        # ── Destination dropdown (top area) ──────────────────────
        # Sits just below the section title + divider
        dd_y = lp_y + 80
        dd_w = 340
        self.dropdown = Dropdown(
            pygame.Rect(in_x, dd_y, dd_w, 58),
            fonts, CONTACTS
        )

        # ── Source info field (to the right of dropdown) ─────────
        self._src_x = in_x + dd_w + 24
        self._src_y = dd_y

        # ── Message input ─────────────────────────────────────────
        in_y = dd_y + 80
        in_h = 140
        self.input = TextInput(pygame.Rect(in_x, in_y, in_w, in_h), fonts)

        # ── Buttons ──────────────────────────────────────────────
        btn_y = in_y + in_h + 20
        self.btn_send  = Button(pygame.Rect(in_x + in_w - 210, btn_y, 210, 48),
                                "↗  SEND TO OS", fonts, primary=True)
        self.btn_clear = Button(pygame.Rect(in_x, btn_y, 120, 48),
                                "✕  Clear", fonts, primary=False)

        # Particles
        import random
        self.particles = [Particle() for _ in range(35)]

        # Animation state
        self.time_elapsed = 0.0
        self.panel_slide  = 0.0     # 0→1 panels slide in
        self.result_msg   = None    # set when done

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
        self.dropdown.handle_event(event)
        self.btn_send.handle_event(event)

        if self.btn_clear.handle_event(event):
            self.input.text = ""

        if self.btn_send.handle_event(event):
            self._try_send()

        # Ctrl+Enter shortcut
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if pygame.key.get_mods() & pygame.KMOD_CTRL:
                self._try_send()

    def _try_send(self):
        if not self.input.value:
            self.toast.show("Please type a message first!", C["amber"])
            return
        self.result_msg = self.input.value

    # ── Update ───────────────────────────────────────────────────

    def update(self, dt):
        self.time_elapsed += dt
        self.panel_slide = min(1.0, self.panel_slide + dt * 2.5)

        for p in self.particles:
            p.update()

        self.input.update(dt)
        self.dropdown.update(dt)
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

        # ── MAIN PANEL ───────────────────────────────────────────
        lp = self.left_panel.move(0, int((1 - slide_t) * 30))
        self._draw_panel_bg(surf, lp)
        self._draw_left_panel(surf, lp, t)

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

        # Title text — clean, no eyebrow or tagline
        title = self.fonts.title_lg.render("PACKET PATH", True, C["text"])
        tx = self.pad + 54
        surf.blit(title, (tx, 24))

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
        # Offset widgets to follow the panel's animated position
        ox = panel.x - self.left_panel.x
        oy = panel.y - self.left_panel.y

        px, py = panel.x + 32, panel.y + 22

        # ── Section header ───────────────────────────────────────
        h2  = self.fonts.label_lg.render("01 /  COMPOSE YOUR MESSAGE", True, C["text"])
        tag = self.fonts.mono_sm.render("LAYER 7 · APPLICATION", True, C["cyan"])
        surf.blit(h2,  (px, py))
        surf.blit(tag, (px + h2.get_width() + 16, py + 2))
        pygame.draw.line(surf, C["line"], (px, py + 22), (panel.right - 32, py + 22))

        # ── TO label ─────────────────────────────────────────────
        to_lbl = self.fonts.label.render("TO", True, C["muted"])
        surf.blit(to_lbl, (px, py + 34))

        # ── Dropdown (drawn with offset) ─────────────────────────
        old_dd = self.dropdown.rect.copy()
        self.dropdown.rect.x += ox
        self.dropdown.rect.y += oy
        self.dropdown.draw(surf)
        self.dropdown.rect = old_dd

        # ── FROM info box (right of dropdown) ────────────────────
        src_x = self._src_x + ox
        src_y = self._src_y + oy
        self._draw_info_field(surf, src_x, src_y, 260,
                              "FROM (SOURCE)", "PC-01  ·  192.168.1.10", C["cyan"])

        # Protocol pill
        proto_x = src_x + 280
        self._draw_info_field(surf, proto_x, src_y, 180,
                              "PROTOCOL", "TCP  ·  Port 443", C["violet"])

        # ── Message label + counter ──────────────────────────────
        in_dx = self.input.rect.x + ox
        in_dy = self.input.rect.y + oy
        msg_lbl_y = in_dy - 20
        lbl = self.fonts.label.render("MESSAGE PAYLOAD", True, C["muted"])
        surf.blit(lbl, (px, msg_lbl_y))
        cnt_col = C["amber"] if len(self.input.text) > 100 else C["muted"]
        cnt = self.fonts.counter.render(
            f"{len(self.input.text)}/{TextInput.MAX_LEN}", True, cnt_col)
        surf.blit(cnt, (panel.right - 32 - cnt.get_width(), msg_lbl_y))

        # ── Text input ───────────────────────────────────────────
        old_r = self.input.rect.copy()
        self.input.rect.x = in_dx
        self.input.rect.y = in_dy
        self.input.draw(surf)
        self.input.rect = old_r

        # ── Hint ─────────────────────────────────────────────────
        hint = self.fonts.body_sm.render(
            "Ctrl + Enter  to send   ·   Max 120 characters", True, C["muted"])
        surf.blit(hint, (px, in_dy + self.input.rect.h + 8))

        # ── Buttons ──────────────────────────────────────────────
        btn_dy = in_dy + self.input.rect.h + 26
        old_s = self.btn_send.rect.copy()
        old_c = self.btn_clear.rect.copy()
        self.btn_send.rect.x  = in_dx + self.input.rect.w - 210
        self.btn_send.rect.y  = btn_dy
        self.btn_clear.rect.x = in_dx
        self.btn_clear.rect.y = btn_dy
        self.btn_send.draw(surf)
        self.btn_clear.draw(surf)
        self.btn_send.rect  = old_s
        self.btn_clear.rect = old_c

        # ── Callout box ──────────────────────────────────────────
        box_y = btn_dy + 66
        box_r = pygame.Rect(px, box_y, panel.w - 64, 80)
        draw_rect_rounded(surf, (10, 22, 38), box_r, radius=10,
                          border=1, border_colour=(40, 60, 85))
        icon  = self.fonts.label_lg.render("💡", True, C["amber"])
        surf.blit(icon, (box_r.x + 14, box_r.y + 12))
        ctitle = self.fonts.label.render("WHAT HAPPENS NEXT?", True, C["amber"])
        cb1 = self.fonts.body_sm.render(
            "Your message is handed to the Operating System, which passes it", True, C["muted"])
        cb2 = self.fonts.body_sm.render(
            "down through each OSI layer — adding headers at every step.", True, C["muted"])
        surf.blit(ctitle, (box_r.x + 42, box_r.y + 12))
        surf.blit(cb1,    (box_r.x + 14, box_r.y + 34))
        surf.blit(cb2,    (box_r.x + 14, box_r.y + 54))

    def _draw_info_field(self, surf, x, y, w, label, value, val_col):
        lbl = self.fonts.label.render(label, True, C["muted"])
        val = self.fonts.mono.render(value, True, val_col)
        r = pygame.Rect(x, y, w, 46)
        draw_rect_rounded(surf, (10, 18, 32), r, radius=8,
                          border=1, border_colour=C["line"])
        surf.blit(lbl, (x + 10, y + 6))
        surf.blit(val, (x + 10, y + 24))

    # _draw_right_panel removed — OSI stack panel replaced by full-width compose layout

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
# SCENE: LEVEL 2 — MESSAGE MOVES TO OS (PORTS MULTIPLEXER)
# ---------------------------------------------------------------------------

class LevelOSPorts:
    """
    Scene: Message moves from Application to OS.
    The OS has multiple ports connected to it.
    The message travels from one assigned port (mentioning the port number explicitly).
    """

    def __init__(self, screen, fonts: Fonts, message: str, contact: dict):
        self.screen   = screen
        self.fonts    = fonts
        self.message  = message
        self.contact  = contact
        self.source_port = 52143   # Allocated outbound port

        self.time_elapsed = 0.0
        self.packet_progress = 0.0
        self.packet_arrived = False
        self.proceed = False

        # Defined OS ports connected to the network stack
        self.ports = [
            {"num": 49152, "label": "PORT 49152", "sub": "Ephemeral Socket · Idle",     "active": False, "col": C["line"]},
            {"num": 50418, "label": "PORT 50418", "sub": "Ephemeral Socket · Idle",     "active": False, "col": C["line"]},
            {"num": 52143, "label": "PORT 52143", "sub": "★ ALLOCATED CLIENT SOCKET",    "active": True,  "col": C["cyan"]},
            {"num": 54890, "label": "PORT 54890", "sub": "Ephemeral Socket · Idle",     "active": False, "col": C["line"]},
            {"num": 59102, "label": "PORT 59102", "sub": "Ephemeral Socket · Idle",     "active": False, "col": C["line"]},
        ]

        # Buttons
        self.btn_proceed = Button(pygame.Rect(910, 662, 250, 48), "PROCEED INSIDE OS ➜", fonts, primary=True)
        self.btn_fast    = Button(pygame.Rect(750, 662, 140, 48), "⏩ Fast Track",       fonts, primary=False)

        # Background ambience & animation
        self.particles = [Particle() for _ in range(25)]
        self.sparks = []
        self._scan_surf = self._make_scanlines(1200, 750)

    def _make_scanlines(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(0, h, 4):
            pygame.draw.line(s, (0, 0, 0, 16), (0, y), (w, y))
        return s

    def handle_event(self, event):
        if self.btn_proceed.handle_event(event):
            self.proceed = True

        if self.btn_fast.handle_event(event):
            self.time_elapsed = 3.0
            self.packet_progress = 1.0
            self.packet_arrived = True

        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.proceed = True

    def update(self, dt):
        self.time_elapsed += dt

        for p in self.particles:
            p.update()

        # Update traveling packet (takes 2.2 seconds to reach the port)
        duration = 2.2
        if not self.packet_arrived:
            self.packet_progress = min(1.0, self.time_elapsed / duration)
            if self.packet_progress >= 1.0:
                self.packet_arrived = True
                # Spawn celebratory arrival sparks at Port 52143
                for _ in range(24):
                    self.sparks.append({
                        "x": 860.0, "y": 380.0,
                        "vx": (__import__('random').random() - 0.5) * 120.0,
                        "vy": (__import__('random').random() - 0.5) * 120.0,
                        "life": 1.0, "colour": C["cyan"]
                    })

        # Update sparks
        for sp in self.sparks[:]:
            sp["x"] += sp["vx"] * dt
            sp["y"] += sp["vy"] * dt
            sp["life"] -= dt * 1.5
            if sp["life"] <= 0:
                self.sparks.remove(sp)

        self.btn_proceed.update(dt)
        self.btn_fast.update(dt)

    def draw(self):
        surf = self.screen
        W, H = surf.get_width(), surf.get_height()
        t = self.time_elapsed

        # Background
        surf.fill(C["bg"])

        # Glow ambient blobs
        for (cx, cy, col, rad) in [
            (int(W * 0.15), int(H * 0.15), C["blue"],   280),
            (int(W * 0.85), int(H * 0.40), C["cyan"],   320),
            (int(W * 0.50), int(H * 0.85), C["violet"], 240),
        ]:
            g = glow_surface(rad, col, alpha=16)
            surf.blit(g, (cx - rad, cy - rad))

        for p in self.particles:
            p.draw(surf)

        surf.blit(self._scan_surf, (0, 0))

        # ── Header Bar ───────────────────────────────────────────
        header = pygame.Rect(0, 0, W, 70)
        draw_gradient_rect(surf, header, (12, 20, 38), (8, 13, 24))
        pygame.draw.line(surf, C["line"], (0, 69), (W, 69))

        # Logo icon
        logo_r = pygame.Rect(32, 13, 44, 44)
        pulse = 0.5 + 0.5 * math.sin(t * 2.5)
        logo_col = tuple(int(C["cyan"][i] + (C["violet"][i] - C["cyan"][i]) * pulse) for i in range(3))
        pygame.draw.rect(surf, logo_col, logo_r, border_radius=12)
        sym = self.fonts.hero.render("↯", True, C["black"])
        surf.blit(sym, (logo_r.centerx - sym.get_width() // 2,
                        logo_r.centery - sym.get_height() // 2))

        # Header Titles
        title = self.fonts.title_lg.render("PACKET PATH", True, C["text"])
        surf.blit(title, (88, 22))

        badge_r = pygame.Rect(W - 320, 14, 288, 42)
        draw_rect_rounded(surf, (16, 28, 48), badge_r, radius=10, border=1, border_colour=C["line"])
        lvl_lbl = self.fonts.label.render("CURRENT STAGE", True, C["muted"])
        lvl_txt = self.fonts.label_lg.render("02 / OS PORT DISPATCH", True, C["cyan"])
        surf.blit(lvl_lbl, (badge_r.x + 14, badge_r.y + 6))
        surf.blit(lvl_txt, (badge_r.x + 14, badge_r.y + 22))

        # ── Subheader Title ──────────────────────────────────────
        sub_title = self.fonts.title_md.render("MESSAGE TRANSFER TO OPERATING SYSTEM", True, C["text"])
        sub_desc  = self.fonts.body_sm.render(
            "The application hands over the buffer to the OS Kernel socket layer, which allocates an outbound port.",
            True, C["muted"]
        )
        surf.blit(sub_title, (40, 84))
        surf.blit(sub_desc,  (40, 110))

        # ── Left Card: APPLICATION SPACE ─────────────────────────
        app_rect = pygame.Rect(40, 140, 330, 480)
        draw_rect_rounded(surf, C["panel"], app_rect, radius=14, border=1, border_colour=C["line"])

        # Tag
        app_tag_r = pygame.Rect(app_rect.x + 20, app_rect.y + 16, 175, 24)
        draw_rect_rounded(surf, (18, 32, 54), app_tag_r, radius=6)
        app_tag = self.fonts.mono_sm.render("APPLICATION SPACE (L7)", True, C["cyan"])
        surf.blit(app_tag, (app_tag_r.x + 8, app_tag_r.y + 4))

        # Process info
        p_name = self.fonts.label_lg.render("ChatClient.exe", True, C["text"])
        p_pid  = self.fonts.mono_sm.render("Process PID: 4892 · Active Socket", True, C["muted"])
        surf.blit(p_name, (app_rect.x + 20, app_rect.y + 50))
        surf.blit(p_pid,  (app_rect.x + 20, app_rect.y + 70))

        # Divider
        pygame.draw.line(surf, C["line"], (app_rect.x + 20, app_rect.y + 95), (app_rect.right - 20, app_rect.y + 95))

        # Target recipient field
        c_lbl = self.fonts.label.render("DESTINATION CONTACT", True, C["muted"])
        c_val = self.fonts.label_lg.render(f"{self.contact['name']}", True, self.contact['colour'])
        c_ip  = self.fonts.mono_sm.render(f"Target IP: {self.contact['ip']}", True, C["text"])
        surf.blit(c_lbl, (app_rect.x + 20, app_rect.y + 110))
        surf.blit(c_val, (app_rect.x + 20, app_rect.y + 128))
        surf.blit(c_ip,  (app_rect.x + 20, app_rect.y + 148))

        # Message Preview Box
        msg_lbl = self.fonts.label.render("OUTGOING MESSAGE BUFFER", True, C["muted"])
        surf.blit(msg_lbl, (app_rect.x + 20, app_rect.y + 185))

        msg_box = pygame.Rect(app_rect.x + 20, app_rect.y + 205, app_rect.w - 40, 140)
        draw_rect_rounded(surf, (10, 16, 28), msg_box, radius=10, border=1, border_colour=C["cyan_dim"])

        # Truncate text nicely
        disp_text = self.message if len(self.message) <= 90 else self.message[:87] + "…"
        lines = []
        cur = ""
        for word in disp_text.split(" "):
            if len(cur + " " + word) < 26:
                cur = (cur + " " + word).strip()
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)

        for i, l in enumerate(lines[:4]):
            rendered_line = self.fonts.body.render(l, True, C["text"])
            surf.blit(rendered_line, (msg_box.x + 14, msg_box.y + 14 + i * 24))

        # Socket call status
        status_box = pygame.Rect(app_rect.x + 20, app_rect.y + 365, app_rect.w - 40, 85)
        draw_rect_rounded(surf, (12, 22, 38), status_box, radius=8, border=1, border_colour=C["line"])
        st_title = self.fonts.label.render("KERNEL SYSTEM CALL", True, C["amber"])
        st_call  = self.fonts.mono.render("sys_sendto(fd, buf)", True, C["cyan"])
        st_note  = self.fonts.body_sm.render("Passing buffer to kernel...", True, C["muted"])
        surf.blit(st_title, (status_box.x + 12, status_box.y + 10))
        surf.blit(st_call,  (status_box.x + 12, status_box.y + 32))
        surf.blit(st_note,  (status_box.x + 12, status_box.y + 54))

        # ── Center: CONDUIT / SYSTEM BUS ─────────────────────────
        bus_y = 380
        bus_start_x = app_rect.right
        bus_end_x = 750

        # Neon bus conduit lines
        pygame.draw.line(surf, (25, 45, 70), (bus_start_x, bus_y), (bus_end_x, bus_y), 4)

        # Animated bus pulses
        for i in range(5):
            pulse_x = bus_start_x + int(((t * 140 + i * 70) % (bus_end_x - bus_start_x)))
            pygame.draw.circle(surf, C["cyan"], (pulse_x, bus_y), 3)

        arrow_lbl = self.fonts.mono_sm.render("SYSTEM BUS  ════▶", True, C["cyan_dim"])
        surf.blit(arrow_lbl, (bus_start_x + 50, bus_y - 20))

        # ── Right Card: OPERATING SYSTEM KERNEL (PORTS) ──────────
        os_rect = pygame.Rect(750, 140, 410, 480)
        draw_rect_rounded(surf, C["panel"], os_rect, radius=14, border=1, border_colour=C["line"])

        os_tag_r = pygame.Rect(os_rect.x + 20, os_rect.y + 16, 250, 24)
        draw_rect_rounded(surf, (18, 32, 54), os_tag_r, radius=6)
        os_tag = self.fonts.mono_sm.render("OS KERNEL · SOCKET MULTIPLEXER", True, C["cyan"])
        surf.blit(os_tag, (os_tag_r.x + 8, os_tag_r.y + 4))

        p_desc = self.fonts.body_sm.render("Multiple socket ports connected to OS network stack:", True, C["muted"])
        surf.blit(p_desc, (os_rect.x + 20, os_rect.y + 48))

        # Ports list rendering
        start_py = os_rect.y + 75
        port_spacing = 72

        for i, pt in enumerate(self.ports):
            pr = pygame.Rect(os_rect.x + 20, start_py + i * port_spacing, os_rect.w - 40, 62)
            is_active = pt["active"]

            # Highlight allocated port
            if is_active:
                port_pulse = 0.5 + 0.5 * math.sin(t * 6)
                bg_col = (18, 38, 58)
                bdr_col = tuple(int(C["cyan"][c] * (0.6 + 0.4 * port_pulse)) for c in range(3))
                glow = glow_surface(pr.w // 2 + 10, C["cyan"], alpha=int(25 * port_pulse))
                surf.blit(glow, (pr.centerx - pr.w // 2 - 10, pr.centery - pr.w // 2 - 10))
            else:
                bg_col = (11, 18, 30)
                bdr_col = (30, 44, 62)

            draw_rect_rounded(surf, bg_col, pr, radius=10, border=2 if is_active else 1, border_colour=bdr_col)

            # Port status LED indicator
            led_col = C["cyan"] if is_active else (60, 80, 105)
            pygame.draw.circle(surf, led_col, (pr.x + 20, pr.centery), 7)
            if is_active:
                pygame.draw.circle(surf, C["white"], (pr.x + 20, pr.centery), 3)

            # Port Number and Description
            p_title = self.fonts.mono_lg.render(pt["label"], True, C["cyan"] if is_active else C["muted"])
            p_sub   = self.fonts.body_sm.render(pt["sub"],   True, C["green"] if is_active else (90, 115, 145))
            surf.blit(p_title, (pr.x + 38, pr.y + 12))
            surf.blit(p_sub,   (pr.x + 38, pr.y + 34))

            # Allocated Badge
            if is_active:
                badge = self.fonts.mono_sm.render("SELECTED OUTBOUND", True, C["black"])
                bw, bh = badge.get_width() + 14, 22
                bx = pr.right - bw - 12
                by = pr.centery - bh // 2
                draw_rect_rounded(surf, C["cyan"], pygame.Rect(bx, by, bw, bh), radius=6)
                surf.blit(badge, (bx + 7, by + 4))

        # ── Traveling Packet Animation ───────────────────────────
        # Target port is index 2 (Port 52143)
        target_port_y = start_py + 2 * port_spacing + 31
        target_port_x = os_rect.x + 20

        # Bezier / Interpolated position
        prog = self.packet_progress
        if prog < 0.6:
            # Traveling along horizontal bus
            pt_prog = prog / 0.6
            pkt_x = bus_start_x + (bus_end_x - bus_start_x) * pt_prog
            pkt_y = bus_y
        else:
            # Routing into Port 52143
            pt_prog = (prog - 0.6) / 0.4
            pkt_x = bus_end_x + (target_port_x - bus_end_x) * pt_prog
            pkt_y = bus_y + (target_port_y - bus_y) * pt_prog

        # Render moving packet capsule
        pkt_w, pkt_h = 130, 40
        pkt_r = pygame.Rect(int(pkt_x - pkt_w // 2), int(pkt_y - pkt_h // 2), pkt_w, pkt_h)

        # Packet glow
        pkt_glow = glow_surface(40, C["cyan"], alpha=60)
        surf.blit(pkt_glow, (pkt_r.centerx - 40, pkt_r.centery - 40))

        draw_rect_rounded(surf, (15, 30, 50), pkt_r, radius=10, border=2, border_colour=C["cyan"])
        pkt_txt = self.fonts.mono_sm.render("DATA BUFFER", True, C["text"])
        surf.blit(pkt_txt, (pkt_r.centerx - pkt_txt.get_width() // 2,
                            pkt_r.centery - pkt_txt.get_height() // 2))

        # Sparks draw
        for sp in self.sparks:
            r = int(max(1, sp["life"] * 4))
            pygame.draw.circle(surf, sp["colour"], (int(sp["x"]), int(sp["y"])), r)

        # ── Bottom Callout Banner (Mentions Port 52143 explicitly) ─────────
        banner_r = pygame.Rect(40, 642, 690, 80)
        draw_rect_rounded(surf, (10, 24, 42), banner_r, radius=12, border=1, border_colour=C["cyan_dim"])

        b_icon = self.fonts.title_lg.render("⚡", True, C["cyan"])
        surf.blit(b_icon, (banner_r.x + 16, banner_r.y + 12))

        b_title = self.fonts.label_lg.render(
            f"OUTBOUND PORT ASSIGNED: {self.source_port}", True, C["cyan"])
        b_text1 = self.fonts.body_sm.render(
            f"The OS connects through Port {self.source_port}. The message exits from this specific port.", True, C["text"])
        b_text2 = self.fonts.body_sm.render(
            f"NOTE: In the next scene, set your Transport Header's Source Port to {self.source_port}!", True, C["amber"])

        surf.blit(b_title, (banner_r.x + 50, banner_r.y + 10))
        surf.blit(b_text1, (banner_r.x + 50, banner_r.y + 32))
        surf.blit(b_text2, (banner_r.x + 50, banner_r.y + 52))

        # Draw Buttons
        self.btn_proceed.draw(surf)
        if not self.packet_arrived:
            self.btn_fast.draw(surf)


# ---------------------------------------------------------------------------
# SCENE: LEVEL 2 — INSIDE OS (TRANSPORT HEADER ATTACHMENT & ENVELOPE)
# ---------------------------------------------------------------------------

class LevelInsideOS:
    """
    Heading: INSIDE OS
    User attaches Transport Header containing:
      - Source Port (same as the port it came from: 52143)
      - Destination Port: 443 (as HTTPS is default)
      - Checksum: header called Checksum
    After this, the user drags the whole packet and puts it in an envelope!
    """

    def __init__(self, screen, fonts: Fonts, message: str, contact: dict, source_port: int = 52143):
        self.screen      = screen
        self.fonts       = fonts
        self.message     = message
        self.contact     = contact
        self.source_port = source_port

        self.time_elapsed = 0.0
        self.all_attached = False

        # 3 Required Transport Header Chips
        self.chips = [
            {
                "id": "src_port",
                "label": "Source Port",
                "val": f"{self.source_port}",
                "desc": f"Port {self.source_port} (OS Socket)",
                "col": C["cyan"],
                "attached": False,
                "slot_idx": 0,
                "home_rect": pygame.Rect(40, 200, 230, 68),
                "rect":      pygame.Rect(40, 200, 230, 68),
            },
            {
                "id": "dst_port",
                "label": "Dest Port",
                "val": "443",
                "desc": "Port 443 (Default HTTPS)",
                "col": C["violet"],
                "attached": False,
                "slot_idx": 1,
                "home_rect": pygame.Rect(40, 280, 230, 68),
                "rect":      pygame.Rect(40, 280, 230, 68),
            },
            {
                "id": "checksum",
                "label": "Checksum",
                "val": "0x7E4B",
                "desc": "Integrity Checksum Header",
                "col": C["green"],
                "attached": False,
                "slot_idx": 2,
                "home_rect": pygame.Rect(40, 360, 230, 68),
                "rect":      pygame.Rect(40, 360, 230, 68),
            },
        ]

        # Packet dimensions & layout on Workbench
        self.packet_base_x = 310
        self.packet_base_y = 195
        self.packet_w = 840
        self.packet_h = 135

        self.packet_x = float(self.packet_base_x)
        self.packet_y = float(self.packet_base_y)

        # Dragging state
        self.drag_chip_idx = None
        self.drag_chip_offset = (0, 0)
        self.dragging_packet = False
        self.drag_packet_offset = (0, 0)

        # Encapsulation Envelope
        self.envelope_rect = pygame.Rect(530, 440, 400, 185)
        self.encapsulated  = False
        self.encapsulate_t = 0.0

        # Completion buttons
        self.btn_replay  = Button(pygame.Rect(440, 640, 150, 48), "↺ Replay", fonts, primary=False)
        self.btn_compose = Button(pygame.Rect(610, 640, 220, 48), "↗ New Message", fonts, primary=True)
        self.action_replay = False
        self.action_compose = False

        self.particles = [Particle() for _ in range(25)]
        self.celebrate_sparks = []
        self._scan_surf = self._make_scanlines(1200, 750)

    def _make_scanlines(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(0, h, 4):
            pygame.draw.line(s, (0, 0, 0, 16), (0, y), (w, y))
        return s

    def _get_packet_rect(self):
        return pygame.Rect(int(self.packet_x), int(self.packet_y), self.packet_w, self.packet_h)

    def _get_slot_rect(self, slot_idx):
        # 3 slots inside Transport Header area
        # Transport Header width is 450
        slot_w = 136
        slot_h = 74
        slot_start_x = int(self.packet_x) + 16 + slot_idx * (slot_w + 12)
        slot_y = int(self.packet_y) + 46
        return pygame.Rect(slot_start_x, slot_y, slot_w, slot_h)

    def handle_event(self, event):
        if self.encapsulated:
            if self.btn_replay.handle_event(event):
                self.action_replay = True
            if self.btn_compose.handle_event(event):
                self.action_compose = True
            return

        pos = getattr(event, "pos", pygame.mouse.get_pos())

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # 1. Check if clicking on an unattached chip to drag or click-to-attach
            for i, chip in enumerate(self.chips):
                if not chip["attached"] and chip["rect"].collidepoint(pos):
                    self.drag_chip_idx = i
                    self.drag_chip_offset = (pos[0] - chip["rect"].x, pos[1] - chip["rect"].y)
                    return

            # 2. If all attached, check if clicking on the whole packet to drag it!
            if self.all_attached:
                if self._get_packet_rect().collidepoint(pos):
                    self.dragging_packet = True
                    self.drag_packet_offset = (pos[0] - self.packet_x, pos[1] - self.packet_y)
                    return

        elif event.type == pygame.MOUSEMOTION:
            if self.drag_chip_idx is not None:
                chip = self.chips[self.drag_chip_idx]
                chip["rect"].x = pos[0] - self.drag_chip_offset[0]
                chip["rect"].y = pos[1] - self.drag_chip_offset[1]

            if self.dragging_packet:
                self.packet_x = pos[0] - self.drag_packet_offset[0]
                self.packet_y = pos[1] - self.drag_packet_offset[1]

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            # Release dragged chip
            if self.drag_chip_idx is not None:
                chip = self.chips[self.drag_chip_idx]
                target_slot = self._get_slot_rect(chip["slot_idx"])
                header_rect = pygame.Rect(int(self.packet_x), int(self.packet_y), 480, self.packet_h)

                # If dropped on slot or header, OR if clicked (released close to start)
                click_threshold = 20
                is_click = (abs(chip["rect"].x - chip["home_rect"].x) < click_threshold and
                            abs(chip["rect"].y - chip["home_rect"].y) < click_threshold)

                if is_click or chip["rect"].colliderect(target_slot) or chip["rect"].colliderect(header_rect) or chip["rect"].colliderect(self._get_packet_rect()):
                    chip["attached"] = True
                    chip["rect"] = target_slot.copy()
                else:
                    chip["rect"] = chip["home_rect"].copy()

                self.drag_chip_idx = None

            # Release dragged packet
            if self.dragging_packet:
                self.dragging_packet = False
                pkt_r = self._get_packet_rect()

                # Check if dropped onto the Envelope!
                if pkt_r.colliderect(self.envelope_rect):
                    self.encapsulated = True
                    self.packet_x = self.envelope_rect.centerx - self.packet_w // 2
                    self.packet_y = self.envelope_rect.centery - self.packet_h // 2
                    # Trigger celebration explosion
                    for _ in range(40):
                        angle = __import__('random').random() * math.tau
                        speed = __import__('random').random() * 220.0 + 80.0
                        self.celebrate_sparks.append({
                            "x": float(self.envelope_rect.centerx),
                            "y": float(self.envelope_rect.centery),
                            "vx": math.cos(angle) * speed,
                            "vy": math.sin(angle) * speed,
                            "life": 1.2,
                            "colour": __import__('random').choice([C["cyan"], C["amber"], C["green"], C["white"]])
                        })
                else:
                    # Return packet to workbench base
                    self.packet_x = float(self.packet_base_x)
                    self.packet_y = float(self.packet_base_y)

    def update(self, dt):
        self.time_elapsed += dt

        for p in self.particles:
            p.update()

        # Check if all chips attached
        was_all = self.all_attached
        self.all_attached = all(c["attached"] for c in self.chips)

        # Update attached chip positions to follow packet
        if not self.encapsulated:
            for chip in self.chips:
                if chip["attached"]:
                    chip["rect"] = self._get_slot_rect(chip["slot_idx"])

        # Update celebration sparks
        for sp in self.celebrate_sparks[:]:
            sp["x"] += sp["vx"] * dt
            sp["y"] += sp["vy"] * dt
            sp["life"] -= dt * 1.2
            if sp["life"] <= 0:
                self.celebrate_sparks.remove(sp)

        if self.encapsulated:
            self.encapsulate_t = min(1.0, self.encapsulate_t + dt * 2.0)
            self.btn_replay.update(dt)
            self.btn_compose.update(dt)

    def draw(self):
        surf = self.screen
        W, H = surf.get_width(), surf.get_height()
        t = self.time_elapsed

        # Background
        surf.fill(C["bg"])

        # Glow ambient blobs
        for (cx, cy, col, rad) in [
            (int(W * 0.20), int(H * 0.15), C["blue"],   260),
            (int(W * 0.80), int(H * 0.25), C["violet"], 280),
            (int(W * 0.50), int(H * 0.75), C["cyan"],   320),
        ]:
            g = glow_surface(rad, col, alpha=16)
            surf.blit(g, (cx - rad, cy - rad))

        for p in self.particles:
            p.draw(surf)

        surf.blit(self._scan_surf, (0, 0))

        # ── Header Bar ───────────────────────────────────────────
        header = pygame.Rect(0, 0, W, 70)
        draw_gradient_rect(surf, header, (12, 20, 38), (8, 13, 24))
        pygame.draw.line(surf, C["line"], (0, 69), (W, 69))

        logo_r = pygame.Rect(32, 13, 44, 44)
        pygame.draw.rect(surf, C["cyan"], logo_r, border_radius=12)
        sym = self.fonts.hero.render("↯", True, C["black"])
        surf.blit(sym, (logo_r.centerx - sym.get_width() // 2,
                        logo_r.centery - sym.get_height() // 2))

        title = self.fonts.title_lg.render("PACKET PATH", True, C["text"])
        surf.blit(title, (88, 22))

        badge_r = pygame.Rect(W - 350, 14, 318, 42)
        draw_rect_rounded(surf, (16, 28, 48), badge_r, radius=10, border=1, border_colour=C["line"])
        lvl_lbl = self.fonts.label.render("CURRENT LAYER", True, C["muted"])
        lvl_txt = self.fonts.label_lg.render("LAYER 4 · TRANSPORT ENCAPSULATION", True, C["cyan"])
        surf.blit(lvl_lbl, (badge_r.x + 14, badge_r.y + 6))
        surf.blit(lvl_txt, (badge_r.x + 14, badge_r.y + 22))

        # ── Main Heading: "INSIDE OS" ─────────────────────────────
        head_text = self.fonts.title_xl.render("INSIDE OS", True, C["text"])
        surf.blit(head_text, (40, 80))

        # Subtitle instructions
        if not self.all_attached:
            guide = "STEP 1: Attach Transport Header fields (Source Port, Dest Port 443, Checksum) to the payload."
            g_col = C["cyan"]
        elif not self.encapsulated:
            guide = "★ STEP 2: Drag the assembled Transport Packet into the Envelope below to Encapsulate!"
            g_col = C["amber"]
        else:
            guide = "✓ PACKET ENCAPSULATED: Transport Layer segment sealed inside Network Envelope!"
            g_col = C["green"]

        sub_guide = self.fonts.label_lg.render(guide, True, g_col)
        surf.blit(sub_guide, (40, 120))

        # ── Left Tray: AVAILABLE TRANSPORT HEADERS ────────────────
        tray_rect = pygame.Rect(30, 150, 250, 480)
        draw_rect_rounded(surf, C["panel"], tray_rect, radius=14, border=1, border_colour=C["line"])

        tray_tag_r = pygame.Rect(tray_rect.x + 16, tray_rect.y + 14, 218, 22)
        draw_rect_rounded(surf, (18, 32, 54), tray_tag_r, radius=6)
        tray_tag = self.fonts.mono_sm.render("TRANSPORT HEADER TRAY", True, C["cyan"])
        surf.blit(tray_tag, (tray_tag_r.x + 8, tray_tag_r.y + 4))

        tray_hint = self.fonts.body_sm.render("Click or Drag to attach:", True, C["muted"])
        surf.blit(tray_hint, (tray_rect.x + 16, tray_rect.y + 42))

        # Draw unattached chips in the tray
        for chip in self.chips:
            if not chip["attached"] and self.drag_chip_idx != self.chips.index(chip):
                self._draw_chip(surf, chip, is_dragging=False)

        # ── Right Area: PACKET ASSEMBLY WORKBENCH ─────────────────
        bench_r = pygame.Rect(295, 150, 875, 480)
        draw_rect_rounded(surf, (11, 18, 30), bench_r, radius=14, border=1, border_colour=C["line"])

        bench_lbl = self.fonts.mono_sm.render("PACKET ASSEMBLY WORKBENCH", True, (65, 90, 120))
        surf.blit(bench_lbl, (bench_r.x + 18, bench_r.y + 12))

        # ── Draw Envelope Dropzone ────────────────────────────────
        self._draw_envelope(surf)

        # ── Draw Packet (Transport Header + Data Payload) ─────────
        if not self.encapsulated or self.encapsulate_t < 0.95:
            self._draw_packet(surf)

        # Draw actively dragged chip on top of everything
        if self.drag_chip_idx is not None:
            chip = self.chips[self.drag_chip_idx]
            self._draw_chip(surf, chip, is_dragging=True)

        # Draw Sparks
        for sp in self.celebrate_sparks:
            r = int(max(2, sp["life"] * 5))
            pygame.draw.circle(surf, sp["colour"], (int(sp["x"]), int(sp["y"])), r)

        # ── Completion Dialog / Modal Overlay ────────────────────
        if self.encapsulated and self.encapsulate_t > 0.4:
            self._draw_completion_modal(surf)

    def _draw_chip(self, surf, chip, is_dragging=False):
        r = chip["rect"]
        col = chip["col"]

        # Lift & Glow when dragging
        if is_dragging:
            glow = glow_surface(50, col, alpha=70)
            surf.blit(glow, (r.centerx - 50, r.centery - 50))
            bg_col = (24, 45, 72)
            bdr_col = col
        else:
            bg_col = (16, 28, 46)
            bdr_col = (40, 65, 95)

        draw_rect_rounded(surf, bg_col, r, radius=10, border=2 if is_dragging else 1, border_colour=bdr_col)

        # Chip label and value
        lbl = self.fonts.label.render(chip["label"].upper(), True, col)
        val = self.fonts.mono_lg.render(chip["val"], True, C["text"])
        sub = self.fonts.mono_sm.render(chip["desc"], True, C["muted"])

        surf.blit(lbl, (r.x + 12, r.y + 8))
        surf.blit(val, (r.x + 12, r.y + 26))
        surf.blit(sub, (r.x + 12, r.y + 48))

    def _draw_packet(self, surf):
        pkt_r = self._get_packet_rect()
        t = self.time_elapsed

        # Scaling during encapsulation animation
        if self.encapsulated:
            scale = 1.0 - self.encapsulate_t * 0.7
            draw_w = int(pkt_r.w * scale)
            draw_h = int(pkt_r.h * scale)
            draw_x = pkt_r.centerx - draw_w // 2
            draw_y = pkt_r.centery - draw_h // 2
            r = pygame.Rect(draw_x, draw_y, draw_w, draw_h)
        else:
            r = pkt_r

        # Glow when dragging or ready to drag
        if self.all_attached:
            pulse = 0.5 + 0.5 * math.sin(t * 5)
            glow_col = C["amber"] if self.dragging_packet else C["cyan"]
            glow = glow_surface(r.w // 2 + 15, glow_col, alpha=int(30 * pulse) if not self.dragging_packet else 50)
            surf.blit(glow, (r.centerx - r.w // 2 - 15, r.centery - r.w // 2 - 15))

        # Main Packet Frame
        draw_rect_rounded(surf, (14, 24, 40), r, radius=12,
                          border=2 if self.all_attached else 1,
                          border_colour=C["cyan"] if self.all_attached else C["line"])

        # ── 1. Left Part: TRANSPORT HEADER SECTION ───────────────
        th_w = 460
        th_r = pygame.Rect(r.x, r.y, th_w, r.h)
        draw_rect_rounded(surf, (18, 30, 50), th_r, radius=12, border=1, border_colour=C["cyan_dim"])

        th_tag = self.fonts.mono_sm.render("TRANSPORT HEADER (LAYER 4)", True, C["cyan"])
        surf.blit(th_tag, (th_r.x + 16, th_r.y + 14))

        # 3 Slots inside Transport Header
        for i, chip in enumerate(self.chips):
            sr = self._get_slot_rect(i)

            if chip["attached"]:
                # Draw attached chip inside slot
                self._draw_chip(surf, chip, is_dragging=False)
                # Checkmark badge
                check = self.fonts.label.render("✓", True, C["green"])
                surf.blit(check, (sr.right - 18, sr.y + 8))
            else:
                # Empty slot outline with prompt
                draw_rect_rounded(surf, (12, 20, 34), sr, radius=8, border=1, border_colour=(45, 65, 90))
                slot_lbl = self.fonts.label.render(f"[ + {chip['label']} ]", True, (75, 105, 140))
                surf.blit(slot_lbl, (sr.centerx - slot_lbl.get_width() // 2,
                                     sr.centery - slot_lbl.get_height() // 2))

        # ── 2. Right Part: DATA PAYLOAD SECTION ──────────────────
        dp_x = r.x + th_w
        dp_w = r.w - th_w
        dp_r = pygame.Rect(dp_x, r.y, dp_w, r.h)
        draw_rect_rounded(surf, (12, 20, 36), dp_r, radius=12, border=1, border_colour=C["line"])

        dp_tag = self.fonts.mono_sm.render("DATA PAYLOAD (L7 BUFFER)", True, C["muted"])
        surf.blit(dp_tag, (dp_r.x + 18, dp_r.y + 14))

        # Destination info
        dest_txt = self.fonts.body_sm.render(f"To: {self.contact['name']} ({self.contact['ip']})", True, self.contact['colour'])
        surf.blit(dest_txt, (dp_r.x + 18, dp_r.y + 36))

        # Message Preview
        p_msg = f'"{self.message}"'
        if len(p_msg) > 36:
            p_msg = p_msg[:33] + "…"
        msg_s = self.fonts.body.render(p_msg, True, C["text"])
        surf.blit(msg_s, (dp_r.x + 18, dp_r.y + 64))

        bytes_txt = self.fonts.mono_sm.render(f"Size: {len(self.message)} bytes · Encoding: UTF-8", True, (80, 110, 145))
        surf.blit(bytes_txt, (dp_r.x + 18, dp_r.y + 96))

    def _draw_envelope(self, surf):
        r = self.envelope_rect
        is_hovered = self.dragging_packet and self._get_packet_rect().colliderect(r)
        t = self.time_elapsed

        # Glow on dropzone
        pulse = 0.5 + 0.5 * math.sin(t * 6)
        if is_hovered:
            glow = glow_surface(r.w // 2 + 20, C["green"], alpha=60)
            surf.blit(glow, (r.centerx - r.w // 2 - 20, r.centery - r.w // 2 - 20))
            env_bg = (20, 42, 35)
            env_bdr = C["green"]
        elif self.encapsulated:
            env_bg = (16, 28, 44)
            env_bdr = C["cyan"]
        else:
            env_bg = (14, 22, 36)
            env_bdr = C["line"]

        # Envelope Body
        flap_h = 35
        body_r = pygame.Rect(r.x, r.y + flap_h, r.w, r.h - flap_h)
        draw_rect_rounded(surf, env_bg, body_r, radius=12, border=2, border_colour=env_bdr)

        # Flap Triangle
        if self.encapsulated:
            # Flap closed downwards
            flap_points = [
                (r.x, r.y + flap_h),
                (r.centerx, r.y + flap_h + 55),
                (r.right, r.y + flap_h)
            ]
            pygame.draw.polygon(surf, (22, 36, 56), flap_points)
            pygame.draw.lines(surf, env_bdr, False, flap_points, 2)

            # Gold Cyber Seal Stamp
            seal_cx = r.centerx
            seal_cy = r.y + flap_h + 55
            pygame.draw.circle(surf, C["amber"], (seal_cx, seal_cy), 22)
            pygame.draw.circle(surf, C["white"], (seal_cx, seal_cy), 22, width=2)
            seal_txt = self.fonts.label.render("✓ L4", True, C["black"])
            surf.blit(seal_txt, (seal_cx - seal_txt.get_width() // 2,
                                 seal_cy - seal_txt.get_height() // 2))

            sealed_lbl = self.fonts.mono_sm.render("ENCAPSULATED & SEALED", True, C["amber"])
            surf.blit(sealed_lbl, (r.centerx - sealed_lbl.get_width() // 2, r.bottom - 26))
        else:
            # Flap open upwards
            flap_points = [
                (r.x, r.y + flap_h),
                (r.centerx, r.y),
                (r.right, r.y + flap_h)
            ]
            pygame.draw.polygon(surf, (18, 30, 48), flap_points)
            pygame.draw.lines(surf, env_bdr, False, flap_points, 2)

            # Dropzone prompt
            if is_hovered:
                p_text = "RELEASE MOUSE TO ENCAPSULATE!"
                p_col = C["green"]
            elif self.all_attached:
                p_text = "▼ DROP PACKET HERE TO ENCAPSULATE ▼"
                p_col = C["amber"]
            else:
                p_text = "ENCAPSULATION ENVELOPE (NETWORK LAYER)"
                p_col = C["muted"]

            prompt = self.fonts.label_lg.render(p_text, True, p_col)
            surf.blit(prompt, (r.centerx - prompt.get_width() // 2, r.centery + 10))

            sub = self.fonts.mono_sm.render("Encloses Transport Segment for Layer 3 Routing", True, (70, 95, 130))
            surf.blit(sub, (r.centerx - sub.get_width() // 2, r.centery + 34))

    def _draw_completion_modal(self, surf):
        W, H = surf.get_width(), surf.get_height()

        # Dim overlay
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surf.blit(overlay, (0, 0))

        # Modal Dialog Card
        mw, mh = 620, 360
        mx = (W - mw) // 2
        my = (H - mh) // 2 - 20
        modal_r = pygame.Rect(mx, my, mw, mh)

        draw_rect_rounded(surf, (14, 25, 42), modal_r, radius=16, border=2, border_colour=C["cyan"])

        # Glow halo around card
        glow = glow_surface(mw // 2 + 20, C["cyan"], alpha=35)
        surf.blit(glow, (modal_r.centerx - mw // 2 - 20, modal_r.centery - mw // 2 - 20))

        # Header Badge
        m_title = self.fonts.title_lg.render("PACKET SUCCESSFULLY ENCAPSULATED!", True, C["text"])
        surf.blit(m_title, (modal_r.centerx - m_title.get_width() // 2, my + 24))

        m_sub = self.fonts.body_sm.render(
            "The message payload has been encapsulated with the Layer 4 Transport Header.",
            True, C["muted"]
        )
        surf.blit(m_sub, (modal_r.centerx - m_sub.get_width() // 2, my + 60))

        # Summary Checklist Card
        chk_r = pygame.Rect(mx + 30, my + 95, mw - 60, 145)
        draw_rect_rounded(surf, (10, 18, 30), chk_r, radius=10, border=1, border_colour=C["line"])

        items = [
            ("✓ Source Port:", f"{self.source_port} (Allocated from OS socket)", C["cyan"]),
            ("✓ Destination Port:", "443 (Default HTTPS)", C["violet"]),
            ("✓ Checksum Header:", "0x7E4B (Packet Integrity Verified)", C["green"]),
            ("✓ L4 Datagram:", "Sealed inside Network Envelope", C["amber"]),
        ]

        for i, (label, val, col) in enumerate(items):
            ly = chk_r.y + 14 + i * 30
            lbl_s = self.fonts.label_lg.render(label, True, col)
            val_s = self.fonts.body.render(val, True, C["text"])
            surf.blit(lbl_s, (chk_r.x + 18, ly))
            surf.blit(val_s, (chk_r.x + 200, ly))

        # Score Award Banner
        score_lbl = self.fonts.label_lg.render("SCORE EARNED: +200 PTS", True, C["green"])
        surf.blit(score_lbl, (modal_r.centerx - score_lbl.get_width() // 2, my + 255))

        # Buttons
        self.btn_replay.rect.x = mx + 130
        self.btn_replay.rect.y = my + 290
        self.btn_compose.rect.x = mx + 310
        self.btn_compose.rect.y = my + 290

        self.btn_replay.draw(surf)
        self.btn_compose.draw(surf)


# ---------------------------------------------------------------------------
# MAIN GAME  — state machine
# ---------------------------------------------------------------------------

class Game:
    STATE_COMPOSE    = "compose"
    STATE_OS_PORTS   = "os_ports"
    STATE_INSIDE_OS  = "inside_os"

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        flags = pygame.DOUBLEBUF | pygame.HWSURFACE
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), flags)
        self.clock  = pygame.time.Clock()
        self.fonts  = Fonts()

        # Game state
        self.state   = self.STATE_COMPOSE
        self.message = ""
        self.contact = None

        # Scenes
        self.compose   = Level1Compose(self.screen, self.fonts, self.clock)
        self.os_ports  = None
        self.inside_os = None

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
        elif self.state == self.STATE_OS_PORTS:
            if self.os_ports:
                self.os_ports.handle_event(event)
        elif self.state == self.STATE_INSIDE_OS:
            if self.inside_os:
                self.inside_os.handle_event(event)

    def _update(self, dt):
        if self.state == self.STATE_COMPOSE:
            self.compose.update(dt)
            # When player clicks SEND
            if self.compose.result_msg:
                self.message = self.compose.result_msg
                self.contact = self.compose.dropdown.contact
                self.os_ports = LevelOSPorts(self.screen, self.fonts, self.message, self.contact)
                self.state = self.STATE_OS_PORTS

        elif self.state == self.STATE_OS_PORTS:
            self.os_ports.update(dt)
            # Transition to Inside OS
            if self.os_ports.proceed:
                self.inside_os = LevelInsideOS(
                    self.screen, self.fonts,
                    self.message, self.contact,
                    self.os_ports.source_port
                )
                self.state = self.STATE_INSIDE_OS

        elif self.state == self.STATE_INSIDE_OS:
            self.inside_os.update(dt)
            # Replay Level
            if self.inside_os.action_replay:
                self.inside_os = LevelInsideOS(
                    self.screen, self.fonts,
                    self.message, self.contact,
                    self.os_ports.source_port
                )
            # Compose new message
            elif self.inside_os.action_compose:
                self.compose.result_msg = None
                self.compose.input.text = ""
                self.state = self.STATE_COMPOSE

    def _draw(self):
        if self.state == self.STATE_COMPOSE:
            self.compose.draw()
        elif self.state == self.STATE_OS_PORTS:
            if self.os_ports:
                self.os_ports.draw()
        elif self.state == self.STATE_INSIDE_OS:
            if self.inside_os:
                self.inside_os.draw()

    def _quit(self):
        pygame.quit()
        sys.exit()


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    Game().run()

