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
import zlib

# ---------------------------------------------------------------------------
# CONSTANTS & COLOUR PALETTE
# ---------------------------------------------------------------------------

SCREEN_W, SCREEN_H = 1200, 750
FPS = 60
TITLE = "PACKET PATH — OSI Transmission Lab"

# ---------------------------------------------------------------------------
# NETWORK MTU — packets larger than this (in bytes) will be fragmented.
# 576 bytes is the RFC 791 mandated minimum reassembly buffer size, chosen
# here as a realistic but clearly visible teaching threshold.
# ---------------------------------------------------------------------------
NETWORK_MTU       = 576          # bytes
IP_HEADER_BYTES   = 20           # fixed IPv4 header overhead per fragment
PAYLOAD_UNIT      = 8            # IPv4 fragment payloads must be multiples of 8

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
            if event.key == pygame.K_v and (event.mod & pygame.KMOD_CTRL):
                try:
                    pasted = pygame.scrap.get_text()
                    if pasted:
                        clean = "".join(c for c in pasted if c.isprintable() or c == " ")
                        self.text += clean
                except Exception:
                    pass
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                pass  # handled upstream
            elif event.unicode and event.unicode.isprintable():
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

        # Multi-line wrapping with long-word splitting
        words = display.split(" ")
        lines, current = [], ""
        for w in words:
            while w and self.fonts.body.size(w)[0] > inner_w:
                k = 1
                while k <= len(w) and self.fonts.body.size(w[:k])[0] <= inner_w:
                    k += 1
                cut = max(1, k - 1)
                chunk = w[:cut]
                if current:
                    lines.append(current)
                    current = ""
                lines.append(chunk)
                w = w[cut:]

            test = (current + " " + w).strip() if current else w
            if self.fonts.body.size(test)[0] <= inner_w:
                current = test
            else:
                if current:
                    lines.append(current)
                current = w
        if current:
            lines.append(current)

        # Draw lines (auto-scroll to always show the bottom lines / active typing)
        line_h = self.fonts.body.get_linesize() + 2
        max_visible = max(1, inner_h // line_h)
        visible_lines = lines[-max_visible:] if len(lines) > max_visible else lines

        clip = surf.get_clip()
        surf.set_clip(pygame.Rect(inner_x, inner_y, inner_w, inner_h))
        for i, ln in enumerate(visible_lines):
            ls = self.fonts.body.render(ln, True, col)
            surf.blit(ls, (inner_x, inner_y + i * line_h))

        # Blinking cursor on last line
        if self.focused and self.cursor_visible and self.text:
            last_line = visible_lines[-1] if visible_lines else ""
            cx = inner_x + self.fonts.body.size(last_line)[0] + 2
            cy = inner_y + (len(visible_lines) - 1) * line_h
            pygame.draw.line(surf, C["cyan"], (cx, cy + 2), (cx, cy + line_h - 2), 2)

        surf.set_clip(clip)

    @property
    def value(self):
        return self.text.strip()


# ---------------------------------------------------------------------------
# CONTACTS  (destination dropdown options)
# ---------------------------------------------------------------------------

CONTACTS = [
    {"name": "Naman",  "ip": "10.42.17.83",  "colour": C["cyan"],   "avatar": "A"},
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
        n_chars = len(self.input.text)
        n_bytes = len(self.input.text.encode("utf-8"))
        if n_bytes > NETWORK_MTU:
            cnt_text = f"{n_chars} chars ({n_bytes} B · > {NETWORK_MTU}B MTU: will fragment!)"
            cnt_col = C["amber"]
        else:
            cnt_text = f"{n_chars} chars ({n_bytes} B)"
            cnt_col = C["muted"]
        cnt = self.fonts.counter.render(cnt_text, True, cnt_col)
        surf.blit(cnt, (panel.right - 32 - cnt.get_width(), msg_lbl_y))

        # ── Text input ───────────────────────────────────────────
        old_r = self.input.rect.copy()
        self.input.rect.x = in_dx
        self.input.rect.y = in_dy
        self.input.draw(surf)
        self.input.rect = old_r

        # ── Hint ─────────────────────────────────────────────────
        hint = self.fonts.body_sm.render(
            "Ctrl + Enter to send   ·   Paste with Ctrl + V", True, C["muted"])
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

        # ── Dropdown drawn LAST so its open list renders on top ───
        old_dd = self.dropdown.rect.copy()
        self.dropdown.rect.x += ox
        self.dropdown.rect.y += oy
        self.dropdown.draw(surf)
        self.dropdown.rect = old_dd

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

            disp_m = self.message if len(self.message) <= 60 else self.message[:57] + "…"
            msg = self.fonts.label_lg.render(disp_m, True, C["text"])
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
# SCENE: LEVEL 2b — LAYER 4 TRANSPORT PROTOCOL SELECTION & HANDSHAKE
# ---------------------------------------------------------------------------

class LevelL4Handshake:
    """
    Layer 4 Transport Protocol scene.

    The player picks TCP or UDP:
      - TCP: Animated 3-way handshake  SYN → SYN-ACK → ACK
             with live TCP header fields (Flags, Seq, Ack) shown per step.
             Connection Established banner after step 3.
      - UDP: Animated fire-and-forget single datagram arrow.
             Explains: no handshake, no guarantee, low overhead.

    Emits:
      self.action_next   (bool) → proceed to LevelInsideOS
      self.protocol      (str)  → "TCP" or "UDP" (passed downstream)
    """

    # TCP handshake step definitions
    _TCP_STEPS = [
        {
            "label":  "Step 1 · SYN",
            "dir":    "→",          # client → server
            "colour": "cyan",
            "flags":  "SYN=1  ACK=0  FIN=0  RST=0",
            "seq":    "Seq=0",
            "ack":    "Ack=—",
            "desc":   "Client initiates connection. SYN flag set, random ISN chosen.",
        },
        {
            "label":  "Step 2 · SYN-ACK",
            "dir":    "←",          # server → client
            "colour": "violet",
            "flags":  "SYN=1  ACK=1  FIN=0  RST=0",
            "seq":    "Seq=0",
            "ack":    "Ack=1",
            "desc":   "Server agrees. SYN+ACK set, acknowledges client's ISN+1.",
        },
        {
            "label":  "Step 3 · ACK",
            "dir":    "→",          # client → server
            "colour": "green",
            "flags":  "SYN=0  ACK=1  FIN=0  RST=0",
            "seq":    "Seq=1",
            "ack":    "Ack=1",
            "desc":   "Client confirms. ACK set. Full-duplex channel open.",
        },
    ]

    def __init__(self, screen, fonts: Fonts, message: str, contact: dict, source_port: int = 52143):
        self.screen      = screen
        self.fonts       = fonts
        self.message     = message
        self.contact     = contact
        self.source_port = source_port

        self.protocol    = None     # "TCP" or "UDP" — set by player choice
        self.action_next = False
        self.time_elapsed = 0.0

        # UI phase:
        #   0 = protocol selection
        #   1 = TCP handshake animation
        #   2 = TCP done (connection established banner)
        #   3 = UDP animation
        #   4 = UDP done (proceed auto-prompt)
        self.phase   = 0
        self.phase_t = 0.0

        # TCP handshake step tracker
        self.tcp_step      = 0       # 0-2 = which step is animating
        self.tcp_pkt_t     = 0.0     # 0→1 progress of flying packet
        self.tcp_steps_done = []     # list of completed step indices

        # UDP packet animation
        self.udp_pkt_t = 0.0

        # Sparks
        self.sparks = []

        # Buttons (protocol choice)
        self.btn_tcp  = Button(pygame.Rect(310, 330, 250, 68), "TCP  ·  Reliable", fonts, primary=True)
        self.btn_udp  = Button(pygame.Rect(620, 330, 250, 68), "UDP  ·  Fast",     fonts, primary=False)
        self.btn_next = Button(pygame.Rect(860, 676, 290, 46), "PROCEED ➜",        fonts, primary=True)
        self.btn_back = Button(pygame.Rect(710, 676, 130, 46), "↶ Back",           fonts, primary=False)

        self.particles  = [Particle() for _ in range(25)]
        self._scan_surf = self._make_scanlines(SCREEN_W, SCREEN_H)

        # Layout constants
        self.CLIENT_X = 160
        self.SERVER_X = 1040
        self.LANE_Y   = 380

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _make_scanlines(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(0, h, 4):
            pygame.draw.line(s, (0, 0, 0, 16), (0, y), (w, y))
        return s

    def _spawn_sparks(self, cx, cy, count=30, colours=None):
        import random, math as _m
        colours = colours or [C["cyan"], C["green"], C["white"]]
        for _ in range(count):
            angle = _m.tau * random.random()
            speed = random.random() * 240 + 60
            self.sparks.append({
                "x": float(cx), "y": float(cy),
                "vx": _m.cos(angle) * speed,
                "vy": _m.sin(angle) * speed,
                "life": random.uniform(0.5, 1.2),
                "colour": random.choice(colours),
            })

    def _pkt_pos(self, t, direction):
        """Interpolate packet position between client and server (or vice-versa)."""
        if direction == "→":
            x = self.CLIENT_X + (self.SERVER_X - self.CLIENT_X) * t
        else:
            x = self.SERVER_X + (self.CLIENT_X - self.SERVER_X) * t
        y = self.LANE_Y
        return int(x), int(y)

    # ── Event ────────────────────────────────────────────────────────────────

    def handle_event(self, event):
        # Protocol selection phase
        if self.phase == 0:
            if self.btn_tcp.handle_event(event):
                self.protocol = "TCP"
                self.phase    = 1
                self.phase_t  = 0.0
                self.tcp_step = 0
                self.tcp_pkt_t = 0.0
            if self.btn_udp.handle_event(event):
                self.protocol  = "UDP"
                self.phase     = 3
                self.phase_t   = 0.0
                self.udp_pkt_t = 0.0
            return

        # TCP done / UDP done — show Proceed button
        if self.phase in (2, 4):
            if self.btn_next.handle_event(event):
                self.action_next = True
            if self.btn_back.handle_event(event):
                self._reset()

    def _reset(self):
        self.phase          = 0
        self.phase_t        = 0.0
        self.protocol       = None
        self.tcp_step       = 0
        self.tcp_pkt_t      = 0.0
        self.tcp_steps_done = []
        self.udp_pkt_t      = 0.0
        self.sparks         = []

    # ── Update ───────────────────────────────────────────────────────────────

    def update(self, dt):
        self.time_elapsed += dt
        self.phase_t      += dt

        for p in self.particles:
            p.update()
        for sp in self.sparks[:]:
            sp["x"]   += sp["vx"] * dt
            sp["y"]   += sp["vy"] * dt
            sp["life"] -= dt * 1.0
            if sp["life"] <= 0:
                self.sparks.remove(sp)

        if self.phase == 0:
            self.btn_tcp.update(dt)
            self.btn_udp.update(dt)

        elif self.phase == 1:
            # Animate current TCP step packet
            PKT_SPEED = 1.4   # seconds for packet to cross
            self.tcp_pkt_t += dt / PKT_SPEED
            if self.tcp_pkt_t >= 1.0:
                self.tcp_pkt_t = 1.0
                # Packet arrived — add to done list
                if self.tcp_step not in self.tcp_steps_done:
                    self.tcp_steps_done.append(self.tcp_step)
                    step = self._TCP_STEPS[self.tcp_step]
                    # Spark at destination
                    dest_x = self.SERVER_X if step["dir"] == "→" else self.CLIENT_X
                    self._spawn_sparks(dest_x, self.LANE_Y, count=24,
                                       colours=[C[step["colour"]], C["white"]])
                # Brief pause then move to next step
                if self.phase_t >= 0.6:
                    if self.tcp_step < 2:
                        self.tcp_step  += 1
                        self.tcp_pkt_t  = 0.0
                        self.phase_t    = 0.0
                    else:
                        # All 3 steps done
                        self.phase   = 2
                        self.phase_t = 0.0
                        self._spawn_sparks(
                            (self.CLIENT_X + self.SERVER_X) // 2, self.LANE_Y - 20,
                            count=60, colours=[C["green"], C["cyan"], C["white"], C["amber"]]
                        )

        elif self.phase == 2:
            self.btn_next.update(dt)
            self.btn_back.update(dt)

        elif self.phase == 3:
            # UDP animation — single packet across in 1.2 s then done
            self.udp_pkt_t += dt / 1.2
            if self.udp_pkt_t >= 1.0:
                self.udp_pkt_t = 1.0
                if self.phase_t >= 0.8:
                    self.phase   = 4
                    self.phase_t = 0.0
                    self._spawn_sparks(self.SERVER_X, self.LANE_Y, count=30,
                                       colours=[C["amber"], C["white"]])

        elif self.phase == 4:
            self.btn_next.update(dt)
            self.btn_back.update(dt)

    # ── Draw ─────────────────────────────────────────────────────────────────

    def draw(self):
        surf = self.screen
        W, H = surf.get_width(), surf.get_height()
        t    = self.time_elapsed

        surf.fill(C["bg"])

        # Ambient glow
        for (cx, cy, col, rad) in [
            (int(W * 0.1),  int(H * 0.2),  C["cyan"],   280),
            (int(W * 0.9),  int(H * 0.25), C["violet"], 260),
            (int(W * 0.5),  int(H * 0.9),  C["green"],  200),
        ]:
            g = glow_surface(rad, col, alpha=15)
            surf.blit(g, (cx - rad, cy - rad))

        for p in self.particles:
            p.draw(surf)
        surf.blit(self._scan_surf, (0, 0))

        # ── Header ─────────────────────────────────────────────────────────
        hdr = pygame.Rect(0, 0, W, 70)
        draw_gradient_rect(surf, hdr, (12, 20, 38), (8, 13, 24))
        pygame.draw.line(surf, C["line"], (0, 69), (W, 69))

        logo_r = pygame.Rect(32, 13, 44, 44)
        pygame.draw.rect(surf, C["violet"], logo_r, border_radius=12)
        sym = self.fonts.hero.render("⇌", True, C["white"])
        surf.blit(sym, (logo_r.centerx - sym.get_width() // 2,
                        logo_r.centery - sym.get_height() // 2))
        surf.blit(self.fonts.title_lg.render("PACKET PATH", True, C["text"]), (88, 22))

        badge_r = pygame.Rect(W - 370, 14, 338, 42)
        draw_rect_rounded(surf, (16, 28, 48), badge_r, radius=10, border=1, border_colour=C["line"])
        surf.blit(self.fonts.label.render("CURRENT LAYER", True, C["muted"]),
                  (badge_r.x + 14, badge_r.y + 6))
        surf.blit(self.fonts.label_lg.render("LAYER 4 · TRANSPORT PROTOCOL", True, C["violet"]),
                  (badge_r.x + 14, badge_r.y + 22))

        # ── Subheader ──────────────────────────────────────────────────────
        if self.phase == 0:
            head = "SELECT TRANSPORT PROTOCOL"
            col  = C["text"]
        elif self.protocol == "TCP":
            head = "TCP · 3-WAY HANDSHAKE"
            col  = C["cyan"]
        else:
            head = "UDP · CONNECTIONLESS DATAGRAM"
            col  = C["amber"]

        hs = self.fonts.title_md.render(head, True, col)
        surf.blit(hs, (W // 2 - hs.get_width() // 2, 78))

        # ── Protocol selection phase ────────────────────────────────────────
        if self.phase == 0:
            self._draw_protocol_choice(surf)
        else:
            # Draw the network diagram (client ↔ server)
            self._draw_network_lane(surf)

            if self.phase in (1, 2):
                self._draw_tcp_handshake(surf)
            elif self.phase in (3, 4):
                self._draw_udp_flow(surf)

            if self.phase in (2, 4):
                self._draw_done_banner(surf)
                self.btn_back.draw(surf)
                self.btn_next.draw(surf)

        # Sparks
        for sp in self.sparks:
            r = max(2, int(sp["life"] * 6))
            pygame.draw.circle(surf, sp["colour"], (int(sp["x"]), int(sp["y"])), r)

    # ── Sub-draw helpers ─────────────────────────────────────────────────────

    def _draw_protocol_choice(self, surf):
        W = surf.get_width()

        # Info panel
        info_r = pygame.Rect(W // 2 - 340, 120, 680, 160)
        draw_rect_rounded(surf, (14, 22, 38), info_r, radius=12, border=1, border_colour=C["line"])
        txt = self.fonts.body_sm.render(
            "The Transport Layer (Layer 4) decides HOW data is delivered across the network.", True, C["muted"])
        surf.blit(txt, (info_r.centerx - txt.get_width() // 2, info_r.y + 16))

        # Two option cards
        cards = [
            {
                "rect":  pygame.Rect(240, 300, 300, 260),
                "title": "TCP",
                "sub":   "Transmission Control Protocol",
                "col":   C["cyan"],
                "icon":  "⇌",
                "pros":  ["✓ Reliable delivery", "✓ In-order packets", "✓ Error detection & retransmit", "✓ Flow control"],
                "cons":  ["✗ 3-way handshake overhead", "✗ Higher latency"],
                "use":   "Use for: HTTPS, SSH, FTP, Email",
            },
            {
                "rect":  pygame.Rect(590, 300, 300, 260),
                "title": "UDP",
                "sub":   "User Datagram Protocol",
                "col":   C["amber"],
                "icon":  "→",
                "pros":  ["✓ No handshake (low latency)", "✓ Minimal overhead", "✓ Broadcasts / Multicasts"],
                "cons":  ["✗ No delivery guarantee", "✗ No ordering"],
                "use":   "Use for: DNS, DHCP, VoIP, Gaming",
            },
        ]

        for card in cards:
            r   = card["rect"]
            col = card["col"]
            draw_rect_rounded(surf, (14, 22, 38), r, radius=14, border=2, border_colour=col)

            # Top colour bar
            pygame.draw.rect(surf, col, pygame.Rect(r.x, r.y, r.w, 6), border_radius=6)

            # Icon + title
            icon_s  = self.fonts.hero.render(card["icon"], True, col)
            surf.blit(icon_s, (r.centerx - icon_s.get_width() // 2, r.y + 14))
            title_s = self.fonts.title_xl.render(card["title"], True, col)
            surf.blit(title_s, (r.centerx - title_s.get_width() // 2, r.y + 56))
            sub_s   = self.fonts.mono_sm.render(card["sub"], True, C["muted"])
            surf.blit(sub_s, (r.centerx - sub_s.get_width() // 2, r.y + 90))

            # Pros/cons
            pygame.draw.line(surf, C["line"], (r.x + 12, r.y + 110), (r.right - 12, r.y + 110))
            fy = r.y + 116
            for pro in card["pros"]:
                s = self.fonts.body_sm.render(pro, True, C["green"])
                surf.blit(s, (r.x + 14, fy))
                fy += 18
            for con in card["cons"]:
                s = self.fonts.body_sm.render(con, True, C["red"])
                surf.blit(s, (r.x + 14, fy))
                fy += 18

            # Use label at bottom
            pygame.draw.line(surf, C["line"], (r.x + 12, r.bottom - 30), (r.right - 12, r.bottom - 30))
            use_s = self.fonts.mono_sm.render(card["use"], True, col)
            surf.blit(use_s, (r.centerx - use_s.get_width() // 2, r.bottom - 22))

        # Buttons
        self.btn_tcp.rect = pygame.Rect(254, 573, 272, 46)
        self.btn_udp.rect = pygame.Rect(604, 573, 272, 46)
        self.btn_tcp.draw(surf)
        self.btn_udp.draw(surf)

        prompt = self.fonts.label.render("▲ Click a protocol to begin", True, C["muted"])
        surf.blit(prompt, (W // 2 - prompt.get_width() // 2, 636))

    def _draw_network_lane(self, surf):
        """Draw client node, server node, and the connecting lane."""
        W = surf.get_width()
        lane_y = self.LANE_Y

        # Lane line
        pygame.draw.line(surf, C["line"], (self.CLIENT_X, lane_y), (self.SERVER_X, lane_y), 2)

        # Client node
        self._draw_host_node(surf, self.CLIENT_X, lane_y,
                             "CLIENT", "192.168.1.10", C["cyan"], "PC-01")
        # Server node
        self._draw_host_node(surf, self.SERVER_X, lane_y,
                             "SERVER", self.contact["ip"],
                             self.contact["colour"], self.contact["name"])

        # Port labels
        p_c = self.fonts.mono_sm.render(f":{self.source_port}", True, C["cyan"])
        surf.blit(p_c, (self.CLIENT_X - p_c.get_width() // 2, lane_y + 55))
        p_s = self.fonts.mono_sm.render(":443", True, C["violet"])
        surf.blit(p_s, (self.SERVER_X - p_s.get_width() // 2, lane_y + 55))

    def _draw_host_node(self, surf, cx, cy, role, ip, col, name):
        r = 34
        g = glow_surface(r + 20, col, alpha=50)
        surf.blit(g, (cx - r - 20, cy - r - 20))
        pygame.draw.circle(surf, C["panel"], (cx, cy), r)
        pygame.draw.circle(surf, col, (cx, cy), r, width=2)
        icon = self.fonts.title_md.render("⬡", True, col)
        surf.blit(icon, (cx - icon.get_width() // 2, cy - icon.get_height() // 2))
        role_s = self.fonts.label.render(role, True, col)
        surf.blit(role_s, (cx - role_s.get_width() // 2, cy - r - 32))
        name_s = self.fonts.mono_sm.render(name, True, C["text"])
        surf.blit(name_s, (cx - name_s.get_width() // 2, cy + r + 8))
        ip_s = self.fonts.mono_sm.render(ip, True, C["muted"])
        surf.blit(ip_s, (cx - ip_s.get_width() // 2, cy + r + 26))

    def _draw_tcp_handshake(self, surf):
        W  = surf.get_width()
        ly = self.LANE_Y

        colours_map = {"cyan": C["cyan"], "violet": C["violet"], "green": C["green"]}

        # Draw completed steps as faded arrows
        for si in self.tcp_steps_done:
            step = self._TCP_STEPS[si]
            col  = colours_map[step["colour"]]
            self._draw_step_arrow(surf, step, col, ly - 40 - si * 60, alpha=120, label=step["label"])

        # Draw current in-flight packet
        if self.phase == 1 and self.tcp_step <= 2:
            step    = self._TCP_STEPS[self.tcp_step]
            col     = colours_map[step["colour"]]
            row_y   = ly - 40 - self.tcp_step * 60

            # Ease-out interpolation for smooth travel
            et = 1 - (1 - min(1.0, self.tcp_pkt_t)) ** 2
            px, py = self._pkt_pos(et, step["dir"])

            # Draw arrow line (partial)
            if step["dir"] == "→":
                pygame.draw.line(surf, (*col, 60), (self.CLIENT_X, row_y), (px, row_y), 2)
            else:
                pygame.draw.line(surf, (*col, 60), (self.SERVER_X, row_y), (px, row_y), 2)

            # Flying packet dot
            gp = glow_surface(22, col, alpha=80)
            surf.blit(gp, (px - 22, row_y - 22))
            pygame.draw.circle(surf, C["panel"], (px, row_y), 12)
            pygame.draw.circle(surf, col, (px, row_y), 12, width=2)

            # Step info panel (live, shown while packet travels)
            self._draw_step_info_panel(surf, step, col)

        # TCP flag table header
        self._draw_flag_legend(surf)

    def _draw_step_arrow(self, surf, step, col, y, alpha, label):
        """Draw a completed handshake arrow."""
        if step["dir"] == "→":
            x1, x2 = self.CLIENT_X, self.SERVER_X
        else:
            x1, x2 = self.SERVER_X, self.CLIENT_X

        line_s = pygame.Surface((abs(x2 - x1), 2), pygame.SRCALPHA)
        line_s.fill((*col, alpha))
        surf.blit(line_s, (min(x1, x2), y))

        # Arrowhead
        tip_x = x2
        tip_y = y
        dx    = 1 if x2 > x1 else -1
        pts   = [(tip_x, tip_y), (tip_x - dx*14, tip_y - 7), (tip_x - dx*14, tip_y + 7)]
        pygame.draw.polygon(surf, (*col, alpha), pts)

        # Label
        lbl_s = self.fonts.mono_sm.render(label, True, (*col, alpha))
        mid_x = (x1 + x2) // 2
        surf.blit(lbl_s, (mid_x - lbl_s.get_width() // 2, y - 16))

    def _draw_step_info_panel(self, surf, step, col):
        """Draw current step info box at bottom left."""
        pr = pygame.Rect(40, 470, 480, 180)
        draw_rect_rounded(surf, (12, 20, 36), pr, radius=12, border=2, border_colour=col)

        title_s = self.fonts.label_lg.render(step["label"], True, col)
        surf.blit(title_s, (pr.x + 14, pr.y + 10))

        pygame.draw.line(surf, C["line"], (pr.x + 12, pr.y + 34), (pr.right - 12, pr.y + 34))

        flags_s = self.fonts.mono_sm.render("FLAGS:  " + step["flags"], True, C["text"])
        seq_s   = self.fonts.mono_sm.render(step["seq"] + "   " + step["ack"],  True, C["cyan"])
        surf.blit(flags_s, (pr.x + 14, pr.y + 42))
        surf.blit(seq_s,   (pr.x + 14, pr.y + 64))

        pygame.draw.line(surf, C["line"], (pr.x + 12, pr.y + 86), (pr.right - 12, pr.y + 86))

        desc_s  = self.fonts.body_sm.render(step["desc"], True, C["muted"])
        surf.blit(desc_s, (pr.x + 14, pr.y + 94))

        # TCP segment size note
        tcp_s = self.fonts.mono_sm.render(
            f"TCP Hdr: 20 B  |  Src: {self.source_port}  |  Dst: 443  |  Window: 65535",
            True, C["muted"])
        surf.blit(tcp_s, (pr.x + 14, pr.y + 120))

        # Step progress dots
        for i in range(3):
            dot_col = col if i <= self.tcp_step else C["line"]
            pygame.draw.circle(surf, dot_col, (pr.x + 14 + i * 22, pr.y + 156), 7)
            if i < 2:
                pygame.draw.line(surf, C["line"], (pr.x + 21 + i * 22, pr.y + 156),
                                 (pr.x + 29 + i * 22, pr.y + 156), 1)

    def _draw_flag_legend(self, surf):
        """Draw the TCP flag reference table on the right."""
        lr = pygame.Rect(690, 470, 470, 180)
        draw_rect_rounded(surf, (12, 20, 36), lr, radius=12, border=1, border_colour=C["line"])
        surf.blit(self.fonts.label_lg.render("TCP FLAG REFERENCE", True, C["muted"]),
                  (lr.x + 14, lr.y + 10))
        pygame.draw.line(surf, C["line"], (lr.x + 12, lr.y + 34), (lr.right - 12, lr.y + 34))

        flags = [
            ("SYN", "Synchronise — initiate connection",    C["cyan"]),
            ("ACK", "Acknowledge — confirm receipt",        C["green"]),
            ("FIN", "Finish — graceful close",              C["amber"]),
            ("RST", "Reset — abort connection immediately", C["red"]),
            ("PSH", "Push — send data to app immediately",  C["violet"]),
            ("URG", "Urgent — prioritise this segment",     C["muted"]),
        ]
        fy = lr.y + 42
        for flag, desc, col in flags:
            f_s = self.fonts.mono_sm.render(flag + ":", True, col)
            d_s = self.fonts.body_sm.render(desc,       True, C["muted"])
            surf.blit(f_s, (lr.x + 14,  fy))
            surf.blit(d_s, (lr.x + 60,  fy))
            fy += 20

    def _draw_udp_flow(self, surf):
        """Draw UDP single-datagram animation."""
        ly     = self.LANE_Y
        col    = C["amber"]

        # Draw partial arrow
        et = 1 - (1 - min(1.0, self.udp_pkt_t)) ** 2
        px, py = self._pkt_pos(et, "→")

        pygame.draw.line(surf, (*col, 80), (self.CLIENT_X, ly), (px, ly), 2)

        # Packet square (UDP has no connection state — show as square, not circle)
        if self.udp_pkt_t < 1.0:
            gp = glow_surface(22, col, alpha=70)
            surf.blit(gp, (px - 22, ly - 22))
            sq_r = pygame.Rect(px - 12, ly - 12, 24, 24)
            pygame.draw.rect(surf, C["panel"], sq_r, border_radius=4)
            pygame.draw.rect(surf, col, sq_r, border_radius=4, width=2)
            u_s = self.fonts.mono_sm.render("UDP", True, col)
            surf.blit(u_s, (px - u_s.get_width() // 2, ly - u_s.get_height() // 2))

        # UDP info panel
        pr = pygame.Rect(40, 470, 480, 160)
        draw_rect_rounded(surf, (12, 20, 36), pr, radius=12, border=2, border_colour=col)
        surf.blit(self.fonts.label_lg.render("UDP DATAGRAM — FIRE & FORGET", True, col),
                  (pr.x + 14, pr.y + 10))
        pygame.draw.line(surf, C["line"], (pr.x + 12, pr.y + 34), (pr.right - 12, pr.y + 34))

        lines = [
            ("HEADER:",   "Src Port | Dst Port | Length | Checksum",   C["text"]),
            ("SIZE:",     "8 bytes fixed (vs TCP 20 bytes minimum)",    C["muted"]),
            ("DELIVERY:", "Best-effort — no ACK, no retransmit",       C["amber"]),
            ("ORDER:",    "Not guaranteed — app must handle",           C["muted"]),
        ]
        fy = pr.y + 42
        for lbl, val, col2 in lines:
            l_s = self.fonts.mono_sm.render(lbl,  True, C["muted"])
            v_s = self.fonts.body_sm.render(val, True, col2)
            surf.blit(l_s, (pr.x + 14, fy))
            surf.blit(v_s, (pr.x + 90, fy))
            fy += 22

        # UDP comparison table
        lr = pygame.Rect(690, 470, 470, 160)
        draw_rect_rounded(surf, (12, 20, 36), lr, radius=12, border=1, border_colour=C["line"])
        surf.blit(self.fonts.label_lg.render("TCP vs UDP AT A GLANCE", True, C["muted"]),
                  (lr.x + 14, lr.y + 10))
        pygame.draw.line(surf, C["line"], (lr.x + 12, lr.y + 34), (lr.right - 12, lr.y + 34))

        rows = [
            ("Connection",  "3-way handshake",    "None"),
            ("Reliability", "Guaranteed",          "Best-effort"),
            ("Ordering",    "In-order",            "Out-of-order ok"),
            ("Header",      "20 B min",            "8 B fixed"),
            ("Speed",       "Slower",              "Faster"),
        ]
        # Column headers
        surf.blit(self.fonts.mono_sm.render("FEATURE",     True, C["muted"]),  (lr.x + 12,  lr.y + 40))
        surf.blit(self.fonts.mono_sm.render("TCP",         True, C["cyan"]),   (lr.x + 170, lr.y + 40))
        surf.blit(self.fonts.mono_sm.render("UDP",         True, C["amber"]),  (lr.x + 310, lr.y + 40))
        pygame.draw.line(surf, C["line"], (lr.x + 12, lr.y + 54), (lr.right - 12, lr.y + 54))

        fy = lr.y + 58
        for feat, tcp_v, udp_v in rows:
            surf.blit(self.fonts.mono_sm.render(feat,  True, C["muted"]),  (lr.x + 12,  fy))
            surf.blit(self.fonts.mono_sm.render(tcp_v, True, C["cyan"]),   (lr.x + 170, fy))
            surf.blit(self.fonts.mono_sm.render(udp_v, True, C["amber"]),  (lr.x + 310, fy))
            fy += 18

    def _draw_done_banner(self, surf):
        W = surf.get_width()
        if self.protocol == "TCP":
            col  = C["green"]
            text = "✓  TCP CONNECTION ESTABLISHED  ·  READY TO TRANSMIT"
        else:
            col  = C["amber"]
            text = "✓  UDP DATAGRAM SENT  ·  NO HANDSHAKE REQUIRED"

        banner_r = pygame.Rect(W // 2 - 370, 440, 740, 50)
        draw_rect_rounded(surf, (16, 38, 28), banner_r, radius=10, border=2, border_colour=col)
        gp = glow_surface(banner_r.w // 2, col, alpha=25)
        surf.blit(gp, (banner_r.centerx - banner_r.w // 2, banner_r.centery - banner_r.w // 2))
        txt_s = self.fonts.label_lg.render(text, True, col)
        surf.blit(txt_s, (banner_r.centerx - txt_s.get_width() // 2, banner_r.centery - txt_s.get_height() // 2))


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
        self.btn_replay = Button(pygame.Rect(440, 640, 150, 48), "↺ Replay", fonts, primary=False)
        self.btn_next   = Button(pygame.Rect(610, 640, 270, 48), "PROCEED TO IP ENCAP ➜", fonts, primary=True)
        self.action_replay = False
        self.action_next   = False

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
            if self.btn_next.handle_event(event):
                self.action_next = True
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
            self.btn_next.update(dt)

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

        # Status message (scoring will be introduced in the routing part)
        ready_lbl = self.fonts.label_lg.render("PACKET READY FOR NETWORK LAYER ROUTING", True, C["cyan"])
        surf.blit(ready_lbl, (modal_r.centerx - ready_lbl.get_width() // 2, my + 255))

        # Buttons
        self.btn_replay.rect.x = mx + 60
        self.btn_replay.rect.y = my + 290
        self.btn_next.rect.x   = mx + 240
        self.btn_next.rect.y   = my + 290

        self.btn_replay.draw(surf)
        self.btn_next.draw(surf)


# ---------------------------------------------------------------------------
# SCENE: LEVEL 3 — IPv4 HEADER ENCAPSULATION & ADDRESSING
# ---------------------------------------------------------------------------

class Level3IPEncapsulation:
    """
    Scene: The previous envelope is put in another outer envelope which has
    Source IP and Destination IP.
    Grid structure matching the IPv4 Header diagram:
      - 32-bit ruler on top (16 bits + 16 bits)
      - Row 1: VER (User input: 0100 or 0110), Header Length (4 bits), Type of Service (8 bits), Total length (16 bits)
      - Row 2: Identification (16 bits), Flags (0, DF, MF), Fragment Offset (13 bits)
      - Row 3: Time to live (8 bits), Protocol (8 bits), Header checksum (16 bits)
      - Row 4: Source IP Address (32 bits) -> 192.168.1.10
      - Row 5: Destination IP Address (32 bits) -> contact['ip']
      - Row 6: Options (0-40 bytes)
      - Row 7: Data -> Drop target for the previous L4 envelope!
    """

    def __init__(self, screen, fonts: Fonts, message: str, contact: dict, source_port: int = 52143):
        self.screen      = screen
        self.fonts       = fonts
        self.message     = message
        self.contact     = contact
        self.source_port = source_port

        self.source_ip = "192.168.1.10"
        self.dest_ip   = contact["ip"]

        self.time_elapsed = 0.0

        # Version User Input field
        self.ver_input = ""
        self.ver_focused = True
        self.cursor_visible = True
        self.cursor_t = 0.0

        # Quick version toggle buttons
        self.btn_v4 = Button(pygame.Rect(35, 275, 120, 36), "0100 (IPv4)", fonts, primary=False)
        self.btn_v6 = Button(pygame.Rect(165, 275, 120, 36), "0110 (IPv6)", fonts, primary=False)

        # Previous L4 Envelope (Draggable)
        self.l4_home_rect = pygame.Rect(35, 380, 250, 130)
        self.l4_rect      = self.l4_home_rect.copy()
        self.l4_attached  = False
        self.dragging_l4  = False
        self.drag_offset  = (0, 0)

        # Grid Geometry
        self.gx = 310
        self.gy = 120
        self.gw = 855

        # Drop target for DATA (Row 7)
        self.data_target_rect = pygame.Rect(self.gx, self.gy + 304, self.gw, 130)

        # Outer Envelope & Encapsulation state
        self.encapsulated  = False
        self.encapsulate_t = 0.0
        self.action_routing = False
        self.action_replay  = False

        self.btn_proceed = Button(pygame.Rect(870, 665, 290, 48), "PROCEED TO ROUTING MAP ➜", fonts, primary=True)
        self.btn_replay  = Button(pygame.Rect(700, 665, 150, 48), "↺ Reset IP", fonts, primary=False)

        self.particles = [Particle() for _ in range(25)]
        self.sparks = []
        self._scan_surf = self._make_scanlines(1200, 750)

    def _make_scanlines(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(0, h, 4):
            pygame.draw.line(s, (0, 0, 0, 16), (0, y), (w, y))
        return s

    def is_valid_ver(self):
        return self.ver_input in ("0100", "0110")

    def handle_event(self, event):
        pos = getattr(event, "pos", pygame.mouse.get_pos())

        if self.btn_v4.handle_event(event):
            self.ver_input = "0100"
            self._check_encap()
            return
        if self.btn_v6.handle_event(event):
            self.ver_input = "0110"
            self._check_encap()
            return

        if self.encapsulated:
            if self.btn_proceed.handle_event(event):
                self.action_routing = True
            if self.btn_replay.handle_event(event):
                self.action_replay = True
            return

        # Text input handling for VER
        if event.type == pygame.KEYDOWN and not self.encapsulated:
            if event.key == pygame.K_BACKSPACE:
                self.ver_input = self.ver_input[:-1]
                self._check_encap()
            elif event.unicode in ("0", "1") and len(self.ver_input) < 4:
                self.ver_input += event.unicode
                self._check_encap()

        # Mouse drag for previous L4 envelope
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            ver_rect = pygame.Rect(self.gx + 4, self.gy + 24, 115, 42)
            if ver_rect.collidepoint(pos):
                self.ver_focused = True

            if not self.l4_attached and self.l4_rect.collidepoint(pos):
                self.dragging_l4 = True
                self.drag_offset = (pos[0] - self.l4_rect.x, pos[1] - self.l4_rect.y)

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging_l4:
                self.l4_rect.x = pos[0] - self.drag_offset[0]
                self.l4_rect.y = pos[1] - self.drag_offset[1]

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging_l4:
                self.dragging_l4 = False
                # If dropped into Data section (Row 7)
                if self.l4_rect.colliderect(self.data_target_rect):
                    self.l4_attached = True
                    self.l4_rect.x = self.data_target_rect.centerx - self.l4_rect.w // 2
                    self.l4_rect.y = self.data_target_rect.centery - self.l4_rect.h // 2
                    self._check_encap()
                else:
                    self.l4_rect = self.l4_home_rect.copy()

    def _check_encap(self):
        if self.is_valid_ver() and self.l4_attached:
            self.encapsulated = True
            for _ in range(35):
                angle = __import__('random').random() * math.tau
                speed = __import__('random').random() * 200.0 + 60.0
                self.sparks.append({
                    "x": float(self.data_target_rect.centerx),
                    "y": float(self.data_target_rect.centery),
                    "vx": math.cos(angle) * speed,
                    "vy": math.sin(angle) * speed,
                    "life": 1.2,
                    "colour": __import__('random').choice([C["cyan"], C["green"], C["amber"], C["white"]])
                })

    def update(self, dt):
        self.time_elapsed += dt
        self.cursor_t += dt
        if self.cursor_t >= 0.5:
            self.cursor_t = 0.0
            self.cursor_visible = not self.cursor_visible

        for p in self.particles:
            p.update()

        for sp in self.sparks[:]:
            sp["x"] += sp["vx"] * dt
            sp["y"] += sp["vy"] * dt
            sp["life"] -= dt * 1.2
            if sp["life"] <= 0:
                self.sparks.remove(sp)

        self.btn_v4.update(dt)
        self.btn_v6.update(dt)

        if self.encapsulated:
            self.encapsulate_t = min(1.0, self.encapsulate_t + dt * 2.0)
            self.btn_proceed.update(dt)
            self.btn_replay.update(dt)

    def draw(self):
        surf = self.screen
        W, H = surf.get_width(), surf.get_height()
        t = self.time_elapsed

        # Background
        surf.fill(C["bg"])

        for (cx, cy, col, rad) in [
            (int(W * 0.15), int(H * 0.15), C["blue"],   260),
            (int(W * 0.85), int(H * 0.35), C["cyan"],   300),
            (int(W * 0.50), int(H * 0.85), C["violet"], 250),
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
        lvl_txt = self.fonts.label_lg.render("LAYER 3 · IPv4 DATAGRAM ENCAPSULATION", True, C["cyan"])
        surf.blit(lvl_lbl, (badge_r.x + 14, badge_r.y + 6))
        surf.blit(lvl_txt, (badge_r.x + 14, badge_r.y + 22))

        # ── Subheader ────────────────────────────────────────────
        head_s = self.fonts.title_md.render("OUTER ENVELOPE: IPv4 HEADER & ADDRESSING", True, C["text"])
        sub_s  = self.fonts.body_sm.render(
            "Input the 4-bit Version (0100 for IPv4 or 0110 for IPv6), then drag the previous L4 envelope into Data.",
            True, C["muted"]
        )
        surf.blit(head_s, (35, 78))
        surf.blit(sub_s,  (35, 100))

        # ── Left Column: Instructions & Draggable L4 Envelope ─────
        inst_r = pygame.Rect(25, 125, 265, 235)
        draw_rect_rounded(surf, C["panel"], inst_r, radius=12, border=1, border_colour=C["line"])

        t_lbl = self.fonts.mono_sm.render("TASK CHECKLIST", True, C["cyan"])
        surf.blit(t_lbl, (inst_r.x + 14, inst_r.y + 12))

        v_ok = self.is_valid_ver()
        c1 = C["green"] if v_ok else C["amber"]
        txt1 = f"1. Version: {self.ver_input if self.ver_input else '____'} " + ("✓" if v_ok else "(Type 0100)")
        s1 = self.fonts.body_sm.render(txt1, True, c1)
        surf.blit(s1, (inst_r.x + 14, inst_r.y + 36))

        c2 = C["green"] if self.l4_attached else C["amber"]
        txt2 = "2. Data Payload: " + ("✓ Envelope Attached" if self.l4_attached else "Drop Envelope below")
        s2 = self.fonts.body_sm.render(txt2, True, c2)
        surf.blit(s2, (inst_r.x + 14, inst_r.y + 60))

        surf.blit(self.fonts.label.render("QUICK SELECT VER (4 BITS):", True, C["muted"]), (inst_r.x + 14, inst_r.y + 115))
        self.btn_v4.draw(surf)
        self.btn_v6.draw(surf)

        # ── Draggable Previous L4 Envelope ────────────────────────
        if not self.l4_attached or self.dragging_l4:
            self._draw_l4_envelope_item(surf, self.l4_rect, is_dragging=self.dragging_l4)

        # ── Outer Envelope Encapsulation Banner / Frame ───────────
        self._draw_ipv4_grid(surf)

        # Draw dragged L4 envelope on top of everything if moving
        if self.dragging_l4:
            self._draw_l4_envelope_item(surf, self.l4_rect, is_dragging=True)

        # Sparks
        for sp in self.sparks:
            r = int(max(2, sp["life"] * 5))
            pygame.draw.circle(surf, sp["colour"], (int(sp["x"]), int(sp["y"])), r)

        # ── Bottom Action Controls ────────────────────────────────
        if self.encapsulated:
            self.btn_replay.draw(surf)
            self.btn_proceed.draw(surf)

    def _draw_l4_envelope_item(self, surf, rect, is_dragging=False):
        r = rect
        if is_dragging:
            glow = glow_surface(r.w // 2 + 15, C["cyan"], alpha=70)
            surf.blit(glow, (r.centerx - r.w // 2 - 15, r.centery - r.w // 2 - 15))
            bg_col = (20, 38, 62)
            bdr_col = C["cyan"]
        else:
            bg_col = (16, 28, 46)
            bdr_col = (40, 70, 100)

        draw_rect_rounded(surf, bg_col, r, radius=10, border=2 if is_dragging else 1, border_colour=bdr_col)

        # Flap Triangle
        flap = [(r.x, r.y + 24), (r.centerx, r.y + 44), (r.right, r.y + 24)]
        pygame.draw.polygon(surf, (22, 36, 56), flap)
        pygame.draw.lines(surf, bdr_col, False, flap, 1)

        # Wax seal stamp
        pygame.draw.circle(surf, C["amber"], (r.centerx, r.y + 44), 14)
        seal = self.fonts.label.render("✓L4", True, C["black"])
        surf.blit(seal, (r.centerx - seal.get_width() // 2, r.y + 44 - seal.get_height() // 2))

        # Text labels
        t1 = self.fonts.label.render("PREVIOUS L4 ENVELOPE", True, C["cyan"])
        t2 = self.fonts.mono_sm.render(f"Port {self.source_port} ➜ 443", True, C["text"])
        t3 = self.fonts.mono_sm.render("Drag into DATA field", True, C["muted"] if not is_dragging else C["green"])

        surf.blit(t1, (r.centerx - t1.get_width() // 2, r.y + 64))
        surf.blit(t2, (r.centerx - t2.get_width() // 2, r.y + 82))
        surf.blit(t3, (r.centerx - t3.get_width() // 2, r.y + 102))

    def _draw_ipv4_grid(self, surf):
        gx, gy, gw = self.gx, self.gy, self.gw

        # 32-bit ruler
        ruler_y = gy
        pygame.draw.line(surf, (40, 60, 85), (gx, ruler_y), (gx + gw, ruler_y), 2)
        r0  = self.fonts.mono_sm.render("◀ 16 bits ▶", True, C["muted"])
        r16 = self.fonts.mono_sm.render("◀ 16 bits ▶ (32 bits total)", True, C["muted"])
        surf.blit(r0,  (gx + gw // 4 - r0.get_width() // 2, ruler_y - 18))
        surf.blit(r16, (gx + 3 * gw // 4 - r16.get_width() // 2, ruler_y - 18))

        # ── Outer Envelope Frame ─────────────────────────────────
        outer_frame = pygame.Rect(gx - 8, gy + 14, gw + 16, 442)
        is_ready = self.encapsulated
        frame_bdr = C["green"] if is_ready else (C["cyan_dim"] if self.is_valid_ver() else C["line"])
        draw_rect_rounded(surf, (10, 16, 28), outer_frame, radius=12, border=2, border_colour=frame_bdr)

        # ── Row 1: VER, IHL, TOS, Total Length ───────────────────
        r1_y = gy + 20
        h1 = 46

        # Col 1: VER (User Input field)
        ver_w = 120
        ver_r = pygame.Rect(gx, r1_y, ver_w, h1)
        v_ok = self.is_valid_ver()
        ver_bg = (24, 46, 36) if v_ok else (20, 32, 50)
        ver_bdr = C["green"] if v_ok else (C["cyan"] if self.ver_focused else C["line"])
        draw_rect_rounded(surf, ver_bg, ver_r, radius=6, border=2, border_colour=ver_bdr)

        lbl_v = self.fonts.label.render("Version (4b)", True, C["cyan"] if not v_ok else C["green"])
        surf.blit(lbl_v, (ver_r.x + 8, ver_r.y + 4))

        # User input text
        cur_sym = "|" if (self.cursor_visible and not v_ok) else ""
        v_disp = (self.ver_input + cur_sym) if self.ver_input or not v_ok else "0100"
        col_v = C["text"] if self.ver_input else C["muted"]
        v_surf = self.fonts.mono_lg.render(v_disp, True, col_v)
        surf.blit(v_surf, (ver_r.x + 12, ver_r.y + 22))

        # Col 2: Header Length (IHL)
        ihl_w = 120
        ihl_r = pygame.Rect(gx + ver_w, r1_y, ihl_w, h1)
        draw_rect_rounded(surf, (14, 22, 36), ihl_r, radius=6, border=1, border_colour=C["line"])
        surf.blit(self.fonts.label.render("Header Len (4b)", True, C["muted"]), (ihl_r.x + 8, ihl_r.y + 4))
        surf.blit(self.fonts.mono_lg.render("0101 (20B)", True, C["text"]),    (ihl_r.x + 8, ihl_r.y + 22))

        # Col 3: Type of Service
        tos_w = 210
        tos_r = pygame.Rect(gx + ver_w + ihl_w, r1_y, tos_w, h1)
        draw_rect_rounded(surf, (14, 22, 36), tos_r, radius=6, border=1, border_colour=C["line"])
        surf.blit(self.fonts.label.render("Type of Service (8b)", True, C["muted"]), (tos_r.x + 8, tos_r.y + 4))
        surf.blit(self.fonts.mono.render("0x00 (Normal QoS)", True, C["text"]),     (tos_r.x + 8, tos_r.y + 24))

        # Col 4: Total length
        len_w = gw - (ver_w + ihl_w + tos_w)
        len_r = pygame.Rect(gx + ver_w + ihl_w + tos_w, r1_y, len_w, h1)
        draw_rect_rounded(surf, (14, 22, 36), len_r, radius=6, border=1, border_colour=C["line"])
        surf.blit(self.fonts.label.render("Total Length (16 bits)", True, C["muted"]), (len_r.x + 8, len_r.y + 4))
        surf.blit(self.fonts.mono.render(f"{64 + len(self.message)} Bytes", True, C["cyan"]), (len_r.x + 8, len_r.y + 24))

        # ── Row 2: Identification, 0, DF, MF, Fragment Offset ───
        r2_y = r1_y + h1 + 4
        h2 = 46

        # Identification
        id_w = gw // 2
        id_r = pygame.Rect(gx, r2_y, id_w, h2)
        draw_rect_rounded(surf, (14, 22, 36), id_r, radius=6, border=1, border_colour=C["line"])
        surf.blit(self.fonts.label.render("Identification (16 bits)", True, C["muted"]), (id_r.x + 8, id_r.y + 4))
        surf.blit(self.fonts.mono.render("0x4A1E (Packet ID)", True, C["text"]),        (id_r.x + 8, id_r.y + 24))

        # Flags: 0, DF, MF
        flg_x = gx + id_w
        f0_r  = pygame.Rect(flg_x, r2_y, 35, h2)
        fdf_r = pygame.Rect(flg_x + 35, r2_y, 40, h2)
        fmf_r = pygame.Rect(flg_x + 75, r2_y, 40, h2)

        draw_rect_rounded(surf, (14, 22, 36), f0_r, radius=4, border=1, border_colour=C["line"])
        draw_rect_rounded(surf, (14, 22, 36), fdf_r, radius=4, border=1, border_colour=C["line"])
        draw_rect_rounded(surf, (14, 22, 36), fmf_r, radius=4, border=1, border_colour=C["line"])

        surf.blit(self.fonts.label.render("0",  True, C["muted"]), (f0_r.centerx - 4, f0_r.y + 4))
        surf.blit(self.fonts.mono.render("0",   True, C["text"]),  (f0_r.centerx - 4, f0_r.y + 22))

        surf.blit(self.fonts.label.render("DF", True, C["cyan"]),  (fdf_r.centerx - 7, fdf_r.y + 4))
        surf.blit(self.fonts.mono.render("1",   True, C["green"]), (fdf_r.centerx - 4, fdf_r.y + 22))

        surf.blit(self.fonts.label.render("MF", True, C["muted"]), (fmf_r.centerx - 8, fmf_r.y + 4))
        surf.blit(self.fonts.mono.render("0",   True, C["text"]),  (fmf_r.centerx - 4, fmf_r.y + 22))

        # Fragment Offset
        fo_x = flg_x + 115
        fo_w = gw - (id_w + 115)
        fo_r = pygame.Rect(fo_x, r2_y, fo_w, h2)
        draw_rect_rounded(surf, (14, 22, 36), fo_r, radius=6, border=1, border_colour=C["line"])
        surf.blit(self.fonts.label.render("Fragment Offset (13 bits)", True, C["muted"]), (fo_r.x + 8, fo_r.y + 4))
        surf.blit(self.fonts.mono.render("0 (No Fragmentation)", True, C["text"]),        (fo_r.x + 8, fo_r.y + 24))

        # ── Row 3: TTL, Protocol, Checksum ───────────────────────
        r3_y = r2_y + h2 + 4
        h3 = 46

        ttl_w = 210
        ttl_r = pygame.Rect(gx, r3_y, ttl_w, h3)
        draw_rect_rounded(surf, (14, 22, 36), ttl_r, radius=6, border=1, border_colour=C["line"])
        surf.blit(self.fonts.label.render("Time to live (8 bits)", True, C["muted"]), (ttl_r.x + 8, ttl_r.y + 4))
        surf.blit(self.fonts.mono.render("64 (Hops limit)", True, C["text"]),        (ttl_r.x + 8, ttl_r.y + 24))

        proto_w = 210
        proto_r = pygame.Rect(gx + ttl_w, r3_y, proto_w, h3)
        draw_rect_rounded(surf, (14, 22, 36), proto_r, radius=6, border=1, border_colour=C["line"])
        surf.blit(self.fonts.label.render("Protocol (8 bits)", True, C["muted"]), (proto_r.x + 8, proto_r.y + 4))
        surf.blit(self.fonts.mono.render("6 (TCP)", True, C["violet"]),           (proto_r.x + 8, proto_r.y + 24))

        chk_w = gw - (ttl_w + proto_w)
        chk_r = pygame.Rect(gx + ttl_w + proto_w, r3_y, chk_w, h3)
        draw_rect_rounded(surf, (14, 22, 36), chk_r, radius=6, border=1, border_colour=C["line"])
        surf.blit(self.fonts.label.render("Header Checksum (16 bits)", True, C["muted"]), (chk_r.x + 8, chk_r.y + 4))
        surf.blit(self.fonts.mono.render("0x9F3B (Header Checksum)", True, C["green"]),   (chk_r.x + 8, chk_r.y + 24))

        # ── Row 4: Source IP Address (32 bits) ───────────────────
        r4_y = r3_y + h3 + 4
        h4 = 44
        src_r = pygame.Rect(gx, r4_y, gw, h4)
        draw_rect_rounded(surf, (16, 28, 48), src_r, radius=6, border=1, border_colour=C["cyan_dim"])
        surf.blit(self.fonts.label.render("Source IP Address (32 bits)", True, C["cyan"]), (src_r.x + 10, src_r.y + 4))
        surf.blit(self.fonts.mono_lg.render(f"{self.source_ip}  (Host PC-01 · Local Interface)", True, C["text"]), (src_r.x + 10, src_r.y + 20))

        # ── Row 5: Destination IP Address (32 bits) ──────────────
        r5_y = r4_y + h4 + 4
        h5 = 44
        dst_r = pygame.Rect(gx, r5_y, gw, h5)
        draw_rect_rounded(surf, (16, 28, 48), dst_r, radius=1, border=1, border_colour=self.contact["colour"])
        surf.blit(self.fonts.label.render("Destination IP Address (32 bits)", True, self.contact["colour"]), (dst_r.x + 10, dst_r.y + 4))
        surf.blit(self.fonts.mono_lg.render(f"{self.dest_ip}  ({self.contact['name']} · Target Host)", True, C["text"]), (dst_r.x + 10, dst_r.y + 20))

        # ── Row 6: Options (0 - 40 bytes) ────────────────────────
        r6_y = r5_y + h5 + 4
        h6 = 36
        opt_r = pygame.Rect(gx, r6_y, gw, h6)
        draw_rect_rounded(surf, (12, 18, 30), opt_r, radius=6, border=1, border_colour=C["line"])
        surf.blit(self.fonts.label.render("Options (0 - 40 bytes)", True, (70, 95, 125)), (opt_r.x + 10, opt_r.y + 2))
        surf.blit(self.fonts.mono_sm.render("None (Standard 20-byte base header)", True, C["muted"]), (opt_r.x + 10, opt_r.y + 18))

        # ── Row 7: DATA (Drop Target for Previous Envelope) ───────
        r7_y = r6_y + h6 + 4
        h7 = 110
        self.data_target_rect = pygame.Rect(gx, r7_y, gw, h7)

        d_bg = (18, 38, 30) if self.l4_attached else (14, 22, 34)
        d_bdr = C["green"] if self.l4_attached else C["amber"]
        draw_rect_rounded(surf, d_bg, self.data_target_rect, radius=8, border=2 if not self.l4_attached else 1, border_colour=d_bdr)

        surf.blit(self.fonts.label_lg.render("DATA (PAYLOAD)", True, d_bdr), (self.data_target_rect.x + 12, self.data_target_rect.y + 8))

        if self.l4_attached:
            # Draw nested envelope inside Data slot
            slot_card = pygame.Rect(self.data_target_rect.centerx - 180, self.data_target_rect.y + 30, 360, 68)
            draw_rect_rounded(surf, (20, 34, 52), slot_card, radius=8, border=1, border_colour=C["cyan"])
            pygame.draw.circle(surf, C["amber"], (slot_card.x + 28, slot_card.centery), 16)
            s_txt = self.fonts.label.render("✓L4", True, C["black"])
            surf.blit(s_txt, (slot_card.x + 28 - s_txt.get_width() // 2, slot_card.centery - s_txt.get_height() // 2))

            surf.blit(self.fonts.label_lg.render("L4 SEGMENT ENVELOPE SEALED INSIDE", True, C["green"]), (slot_card.x + 56, slot_card.y + 12))
            surf.blit(self.fonts.mono_sm.render(f"Port {self.source_port} ➜ 443 | Checksum: OK", True, C["text"]), (slot_card.x + 56, slot_card.y + 36))
        else:
            prompt_s = self.fonts.label_lg.render("▼ DROP PREVIOUS L4 ENVELOPE HERE INTO DATA SECTION ▼", True, C["amber"])
            sub_s = self.fonts.body_sm.render("Drag the sealed Transport envelope from the left tray into this field.", True, C["muted"])
            surf.blit(prompt_s, (self.data_target_rect.centerx - prompt_s.get_width() // 2, self.data_target_rect.y + 40))
            surf.blit(sub_s,    (self.data_target_rect.centerx - sub_s.get_width() // 2, self.data_target_rect.y + 68))

        # ── Outer Envelope Flap & Cyber Seal ──────────────────────
        if self.encapsulated:
            seal_cx = gx + gw // 2
            seal_cy = gy + 14
            pygame.draw.circle(surf, C["cyan"], (seal_cx, seal_cy), 22)
            pygame.draw.circle(surf, C["white"], (seal_cx, seal_cy), 22, width=2)
            s_lbl = self.fonts.label.render("✓L3", True, C["black"])
            surf.blit(s_lbl, (seal_cx - s_lbl.get_width() // 2, seal_cy - s_lbl.get_height() // 2))

            done_s = self.fonts.label_lg.render("★ OUTER ENVELOPE SEALED (IPv4 DATAGRAM COMPLETE) ★", True, C["green"])
            surf.blit(done_s, (gx + gw // 2 - done_s.get_width() // 2, self.data_target_rect.bottom + 10))


# ---------------------------------------------------------------------------
# SCENE: LEVEL 3b — IPv4 FRAGMENTATION
# ---------------------------------------------------------------------------

class LevelFragmentation:
    """
    Scene: Shown when the datagram payload exceeds NETWORK_MTU bytes.
    Teaches the student:
      - Why fragmentation happens (link MTU restriction)
      - How IPv4 splits the datagram (RFC 791 rules)
      - What happens to flags: MF=1 on all but last, offset per fragment
      - Reassembly at the destination host

    If payload <= MTU: show a short "no fragmentation" panel that
    auto-proceeds to routing after 2 seconds.
    """

    # Packet ID is fixed for demonstration (shown in every fragment header)
    PACKET_ID = 0x4A1E

    def __init__(self, screen, fonts: Fonts, message: str, contact: dict, source_port: int = 52143):
        self.screen      = screen
        self.fonts       = fonts
        self.message     = message
        self.contact     = contact
        self.source_port = source_port

        self.time_elapsed = 0.0
        self.action_proceed = False   # signal to Game to move to routing
        self.action_replay  = False

        # ── Fragmentation maths ──────────────────────────────────────────────
        # Total datagram = IP header + payload
        # "payload" here is the message bytes (the L4 segment already encapsulated)
        # We treat every character as 1 byte (ASCII / UTF-8 single-byte).
        self.payload_bytes  = len(message)           # raw L4 data bytes
        self.total_bytes    = IP_HEADER_BYTES + self.payload_bytes
        self.msg_bits       = self.total_bytes * 8   # total datagram bits

        # Maximum payload per fragment (must be multiple of PAYLOAD_UNIT=8)
        max_payload_per_frag = NETWORK_MTU - IP_HEADER_BYTES   # 556 bytes
        # Round down to nearest multiple of 8
        max_payload_per_frag = (max_payload_per_frag // PAYLOAD_UNIT) * PAYLOAD_UNIT

        self.needs_fragmentation = self.total_bytes > NETWORK_MTU

        # Build fragment list
        self.fragments = []   # each: {id, offset, length, payload_bytes, mf, bits}
        if self.needs_fragmentation:
            remaining = self.payload_bytes
            offset    = 0
            frag_idx  = 0
            while remaining > 0:
                chunk = min(remaining, max_payload_per_frag)
                if remaining - chunk > 0:
                    # Align to 8 bytes (chunk already aligned, remaining tail may not be)
                    chunk = (chunk // PAYLOAD_UNIT) * PAYLOAD_UNIT
                mf = 1 if remaining - chunk > 0 else 0
                self.fragments.append({
                    "idx":    frag_idx,
                    "offset": offset,          # in bytes (display as 8-byte units in header)
                    "offset_units": offset // PAYLOAD_UNIT,
                    "payload": chunk,
                    "total":  IP_HEADER_BYTES + chunk,
                    "mf":     mf,
                    "df":     0,
                    "bits":   (IP_HEADER_BYTES + chunk) * 8,
                    "label":  f"Fragment {frag_idx + 1}",
                })
                offset    += chunk
                remaining -= chunk
                frag_idx  += 1
        else:
            # Single datagram, no split needed
            self.fragments = [{
                "idx":    0,
                "offset": 0,
                "offset_units": 0,
                "payload": self.payload_bytes,
                "total":  self.total_bytes,
                "mf":     0,
                "df":     1,
                "bits":   self.msg_bits,
                "label":  "Datagram (no fragmentation)",
            }]

        # ── Animation state ──────────────────────────────────────────────────
        # Phase 0: intro burst (original datagram shown, then splits)
        # Phase 1: fragments animate outward to their grid positions
        # Phase 2: steady state — fragments displayed, "PROCEED" button appears
        # Phase 3: (only if no fragmentation) auto-proceed countdown
        self.phase      = 0
        self.phase_t    = 0.0    # time within current phase

        # Animated split: original rect shrinks left, fragments slide right
        self.split_done   = False
        self.frag_anim_t  = [0.0] * len(self.fragments)   # 0→1 per fragment

        # Sparks on split
        self.sparks = []
        self._split_sparked = False

        # Reassembly panel — shown at bottom, fades in during phase 2
        self.reassembly_alpha = 0.0

        # Buttons
        self.btn_proceed = Button(pygame.Rect(860, 678, 300, 46), "PROCEED TO DATA LINK (L2) ➜", fonts, primary=True)
        self.btn_replay  = Button(pygame.Rect(700, 678, 140, 46), "↺ Replay", fonts, primary=False)

        self.particles   = [Particle() for _ in range(25)]
        self._scan_surf  = self._make_scanlines(SCREEN_W, SCREEN_H)

        # Auto-proceed timer for no-fragmentation case
        self._auto_t = 0.0
        self._auto_delay = 2.2

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _make_scanlines(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(0, h, 4):
            pygame.draw.line(s, (0, 0, 0, 16), (0, y))
        return s

    def _make_scanlines(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(0, h, 4):
            pygame.draw.line(s, (0, 0, 0, 16), (0, y), (w, y))
        return s

    def _spawn_sparks(self, cx, cy, count=40, colours=None):
        import random, math as _m
        colours = colours or [C["cyan"], C["amber"], C["red"], C["white"]]
        for _ in range(count):
            angle = random.random() * _m.tau
            speed = random.random() * 280 + 60
            self.sparks.append({
                "x": float(cx), "y": float(cy),
                "vx": _m.cos(angle) * speed,
                "vy": _m.sin(angle) * speed,
                "life": random.uniform(0.6, 1.4),
                "colour": random.choice(colours),
            })

    # ── Fragment layout ───────────────────────────────────────────────────────

    def _frag_rects(self):
        """Return the target screen Rect for each fragment card."""
        n = len(self.fragments)
        W = SCREEN_W
        card_w = min(340, (W - 80) // max(n, 1))
        card_h = 220
        total_w = n * card_w + (n - 1) * 16
        x0 = (W - total_w) // 2
        y0 = 250
        rects = []
        for i in range(n):
            rects.append(pygame.Rect(x0 + i * (card_w + 16), y0, card_w, card_h))
        return rects

    # ── Event ────────────────────────────────────────────────────────────────

    def handle_event(self, event):
        if self.phase < 2:
            return
        if self.btn_proceed.handle_event(event):
            self.action_proceed = True
        if self.btn_replay.handle_event(event):
            self.action_replay = True

    # ── Update ───────────────────────────────────────────────────────────────

    def update(self, dt):
        self.time_elapsed += dt
        self.phase_t      += dt

        for p in self.particles:
            p.update()

        for sp in self.sparks[:]:
            sp["x"]  += sp["vx"] * dt
            sp["y"]  += sp["vy"] * dt
            sp["life"] -= dt * 1.1
            if sp["life"] <= 0:
                self.sparks.remove(sp)

        if self.phase == 0:
            # Phase 0: show original datagram for 1.2 s, then trigger split
            if self.phase_t >= 1.2 and not self._split_sparked:
                self._split_sparked = True
                # Spawn sparks at centre of original datagram rect
                self._spawn_sparks(SCREEN_W // 2, 340, count=55,
                                   colours=[C["cyan"], C["amber"], C["red"], C["violet"]])
            if self.phase_t >= 1.5:
                self.phase   = 1
                self.phase_t = 0.0

        elif self.phase == 1:
            # Phase 1: animate each fragment flying out
            stagger = 0.12
            all_done = True
            for i in range(len(self.fragments)):
                delay = i * stagger
                t = max(0.0, self.phase_t - delay) * 2.8
                self.frag_anim_t[i] = min(1.0, t)
                if self.frag_anim_t[i] < 1.0:
                    all_done = False
            if all_done and self.phase_t >= 0.4 + len(self.fragments) * stagger:
                self.phase   = 2
                self.phase_t = 0.0

        elif self.phase == 2:
            # Phase 2: steady — fade in reassembly panel & buttons
            self.reassembly_alpha = min(255, self.reassembly_alpha + dt * 300)
            self.btn_proceed.update(dt)
            self.btn_replay.update(dt)

            if not self.needs_fragmentation:
                self._auto_t += dt
                if self._auto_t >= self._auto_delay:
                    self.action_proceed = True

    # ── Draw ─────────────────────────────────────────────────────────────────

    def draw(self):
        surf = self.screen
        W, H = surf.get_width(), surf.get_height()
        t = self.time_elapsed

        # Background
        surf.fill(C["bg"])

        # Ambient glow blobs
        for (cx, cy, col, rad) in [
            (int(W * 0.1),  int(H * 0.2),  C["red"],    250),
            (int(W * 0.9),  int(H * 0.3),  C["violet"], 300),
            (int(W * 0.5),  int(H * 0.9),  C["cyan"],   200),
        ]:
            g = glow_surface(rad, col, alpha=14)
            surf.blit(g, (cx - rad, cy - rad))

        for p in self.particles:
            p.draw(surf)
        surf.blit(self._scan_surf, (0, 0))

        # ── Header Bar ─────────────────────────────────────────────────────
        header = pygame.Rect(0, 0, W, 70)
        draw_gradient_rect(surf, header, (12, 20, 38), (8, 13, 24))
        pygame.draw.line(surf, C["line"], (0, 69), (W, 69))

        logo_r = pygame.Rect(32, 13, 44, 44)
        pygame.draw.rect(surf, C["red"], logo_r, border_radius=12)
        sym = self.fonts.hero.render("⊕", True, C["white"])
        surf.blit(sym, (logo_r.centerx - sym.get_width() // 2,
                        logo_r.centery - sym.get_height() // 2))

        title_s = self.fonts.title_lg.render("PACKET PATH", True, C["text"])
        surf.blit(title_s, (88, 22))

        badge_r = pygame.Rect(W - 380, 14, 348, 42)
        draw_rect_rounded(surf, (16, 28, 48), badge_r, radius=10, border=1, border_colour=C["line"])
        lvl_lbl = self.fonts.label.render("CURRENT LAYER", True, C["muted"])
        lvl_txt = self.fonts.label_lg.render("LAYER 3 · IPv4 FRAGMENTATION & MTU", True, C["red"])
        surf.blit(lvl_lbl, (badge_r.x + 14, badge_r.y + 6))
        surf.blit(lvl_txt, (badge_r.x + 14, badge_r.y + 22))

        # ── Subheader ──────────────────────────────────────────────────────
        if self.needs_fragmentation:
            head_s = self.fonts.title_md.render("DATAGRAM TOO LARGE — IPv4 FRAGMENTATION REQUIRED", True, C["amber"])
        else:
            head_s = self.fonts.title_md.render("DATAGRAM FITS WITHIN NETWORK MTU — NO FRAGMENTATION NEEDED", True, C["green"])
        surf.blit(head_s, (W // 2 - head_s.get_width() // 2, 78))

        # MTU info bar
        info_y = 106
        mtu_s   = self.fonts.mono_sm.render(
            f"Network MTU = {NETWORK_MTU} B ({NETWORK_MTU * 8} bits)   |   "
            f"Datagram = {self.total_bytes} B ({self.msg_bits} bits)   |   "
            f"Fragments = {len(self.fragments)}",
            True, C["cyan"] if not self.needs_fragmentation else C["amber"]
        )
        surf.blit(mtu_s, (W // 2 - mtu_s.get_width() // 2, info_y))

        # ── Phase 0: Show original datagram ────────────────────────────────
        if self.phase == 0:
            alpha = min(1.0, self.phase_t / 0.4)
            self._draw_original_datagram(surf, alpha)

        # ── Phase 1 & 2: Animated fragments ────────────────────────────────
        else:
            # Original datagram shrinks away (reverse alpha)
            if self.phase == 1:
                orig_alpha = max(0.0, 1.0 - self.phase_t * 3.0)
                if orig_alpha > 0.05:
                    self._draw_original_datagram(surf, orig_alpha)

            # Draw each fragment card
            rects = self._frag_rects()
            for i, frag in enumerate(self.fragments):
                anim = self.frag_anim_t[i]
                if anim <= 0:
                    continue
                # Ease-out cubic
                a = 1 - (1 - anim) ** 3

                # Fragment slides from centre to its target rect
                cx = W // 2
                cy = 340
                tr = rects[i]
                fx = int(cx + (tr.x - cx) * a)
                fy = int(cy + (tr.y - cy) * a)
                card_alpha = int(a * 255)

                self._draw_frag_card(surf, frag, pygame.Rect(fx, fy, tr.w, tr.h), card_alpha, i)

            # Phase 2: reassembly note & buttons
            if self.phase == 2:
                self._draw_reassembly_panel(surf)
                if self.needs_fragmentation:
                    self.btn_replay.draw(surf)
                    self.btn_proceed.draw(surf)
                else:
                    # "Auto-proceeding" countdown bar
                    progress = min(1.0, self._auto_t / self._auto_delay)
                    bar_r = pygame.Rect(W // 2 - 200, H - 60, 400, 6)
                    pygame.draw.rect(surf, C["line"],  bar_r, border_radius=3)
                    pygame.draw.rect(surf, C["green"], pygame.Rect(bar_r.x, bar_r.y, int(bar_r.w * progress), bar_r.h), border_radius=3)
                    auto_s = self.fonts.body_sm.render("Auto-proceeding to routing…", True, C["muted"])
                    surf.blit(auto_s, (W // 2 - auto_s.get_width() // 2, H - 80))

        # Sparks
        for sp in self.sparks:
            r = max(2, int(sp["life"] * 5))
            pygame.draw.circle(surf, sp["colour"], (int(sp["x"]), int(sp["y"])), r)

    # ── Sub-draw helpers ─────────────────────────────────────────────────────

    def _draw_original_datagram(self, surf, alpha):
        """Draw the undivided original datagram as a glowing envelope."""
        W = surf.get_width()
        w, h = 520, 110
        r = pygame.Rect(W // 2 - w // 2, 285, w, h)

        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.set_alpha(int(alpha * 255))
        pygame.draw.rect(panel, (14, 24, 42), pygame.Rect(0, 0, w, h), border_radius=12)
        col = C["amber"] if self.needs_fragmentation else C["green"]
        pygame.draw.rect(panel, col, pygame.Rect(0, 0, w, h), border_radius=12, width=2)

        # Label
        lbl = self.fonts.label_lg.render("ORIGINAL IPv4 DATAGRAM", True, col)
        panel.blit(lbl, (w // 2 - lbl.get_width() // 2, 10))

        sz_s = self.fonts.mono.render(
            f"{self.total_bytes} bytes  ({self.msg_bits} bits)   ID=0x{self.PACKET_ID:04X}   DF=0   MF=0   Offset=0",
            True, C["text"]
        )
        panel.blit(sz_s, (w // 2 - sz_s.get_width() // 2, 38))

        payload_s = self.fonts.mono_sm.render(
            f"IP Hdr: {IP_HEADER_BYTES} B + Payload: {self.payload_bytes} B = {self.total_bytes} B total",
            True, C["muted"]
        )
        panel.blit(payload_s, (w // 2 - payload_s.get_width() // 2, 62))

        limit_s = self.fonts.mono_sm.render(
            f"Network MTU: {NETWORK_MTU} B  ←  {'EXCEEDS LIMIT !' if self.needs_fragmentation else 'Within limit ✓'}",
            True, C["red"] if self.needs_fragmentation else C["green"]
        )
        panel.blit(limit_s, (w // 2 - limit_s.get_width() // 2, 84))

        surf.blit(panel, (r.x, r.y))

        if self.needs_fragmentation and alpha > 0.7:
            # Pulsing warning ring
            pulse = 0.6 + 0.4 * math.sin(self.time_elapsed * 8)
            gw_r = int(w // 2 * pulse) + 20
            g = glow_surface(gw_r, C["red"], alpha=30)
            surf.blit(g, (r.centerx - gw_r, r.centery - gw_r))

    def _draw_frag_card(self, surf, frag, rect, alpha, idx):
        """Draw one fragment card showing its IPv4 header fields."""
        import random as _rnd
        colours_cycle = [C["cyan"], C["violet"], C["green"], C["amber"], C["blue"]]
        accent = colours_cycle[idx % len(colours_cycle)]

        panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        panel.set_alpha(alpha)

        # Background
        pygame.draw.rect(panel, (14, 22, 38), pygame.Rect(0, 0, rect.w, rect.h), border_radius=12)
        pygame.draw.rect(panel, accent,       pygame.Rect(0, 0, rect.w, rect.h), border_radius=12, width=2)

        # Top accent bar
        pygame.draw.rect(panel, accent, pygame.Rect(0, 0, rect.w, 6), border_radius=6)

        pw = rect.w
        # Fragment number badge
        badge_txt = self.fonts.label_lg.render(frag["label"].upper(), True, accent)
        panel.blit(badge_txt, (pw // 2 - badge_txt.get_width() // 2, 14))

        # Size
        sz_s = self.fonts.mono.render(f"{frag['total']} B  ({frag['bits']} bits)", True, C["text"])
        panel.blit(sz_s, (pw // 2 - sz_s.get_width() // 2, 36))

        # Fields
        fields = [
            ("ID",           f"0x{self.PACKET_ID:04X}",          C["muted"]),
            ("DF",           str(frag["df"]),                    C["cyan"]  if frag["df"] else C["muted"]),
            ("MF",           str(frag["mf"]),                    C["amber"] if frag["mf"] else C["muted"]),
            ("Frag Offset",  f"{frag['offset_units']} (×8 B)",   C["violet"]),
            ("Payload",      f"{frag['payload']} B",             C["green"]),
            ("IP Header",    f"{IP_HEADER_BYTES} B",             C["muted"]),
        ]

        fy = 62
        for name, val, col in fields:
            pygame.draw.line(panel, (30, 45, 65), (10, fy - 2), (pw - 10, fy - 2))
            n_s = self.fonts.mono_sm.render(name + ":", True, C["muted"])
            v_s = self.fonts.mono_sm.render(val,        True, col)
            panel.blit(n_s, (12, fy))
            panel.blit(v_s, (pw - v_s.get_width() - 12, fy))
            fy += 22

        # MF indicator pill
        mf_text = "MF=1  MORE FRAGS ▶" if frag["mf"] else "MF=0  LAST FRAG ✓"
        mf_col  = C["amber"]             if frag["mf"] else C["green"]
        mf_r    = pygame.Rect(8, rect.h - 36, rect.w - 16, 26)
        pygame.draw.rect(panel, (*mf_col, 40), mf_r, border_radius=6)
        pygame.draw.rect(panel, mf_col,        mf_r, border_radius=6, width=1)
        mf_s = self.fonts.label.render(mf_text, True, mf_col)
        panel.blit(mf_s, (mf_r.centerx - mf_s.get_width() // 2, mf_r.y + 7))

        surf.blit(panel, (rect.x, rect.y))

    def _draw_reassembly_panel(self, surf):
        """Draw the reassembly information panel at the bottom."""
        W = surf.get_width()
        a = int(self.reassembly_alpha)
        if a <= 0:
            return

        panel_r = pygame.Rect(40, 500, W - 80, 160)
        panel = pygame.Surface((panel_r.w, panel_r.h), pygame.SRCALPHA)
        panel.set_alpha(a)

        pygame.draw.rect(panel, (12, 22, 38), pygame.Rect(0, 0, panel_r.w, panel_r.h), border_radius=12)
        col = C["green"] if not self.needs_fragmentation else C["cyan"]
        pygame.draw.rect(panel, col, pygame.Rect(0, 0, panel_r.w, panel_r.h), border_radius=12, width=1)

        if self.needs_fragmentation:
            title_s = self.fonts.label_lg.render(
                f"★ REASSEMBLY AT DESTINATION HOST  ({len(self.fragments)} fragments → 1 datagram)", True, C["cyan"])
            panel.blit(title_s, (panel_r.w // 2 - title_s.get_width() // 2, 10))

            lines = [
                f"Each fragment carries the same ID (0x{self.PACKET_ID:04X}) so the destination can match them.",
                "Fragments are buffered and sorted by Fragment Offset.  When MF=0 fragment arrives → reassembly begins.",
                f"Reassembled datagram = {self.total_bytes} B  ({self.payload_bytes} B payload + {IP_HEADER_BYTES} B IP header).",
            ]
            for i, ln in enumerate(lines):
                s = self.fonts.body_sm.render(ln, True, C["muted"])
                panel.blit(s, (16, 38 + i * 22))

            rfc_s = self.fonts.mono_sm.render(
                "RFC 791 §3.2 · Fragment Offset in units of 8 octets · MF bit set on all but last fragment",
                True, C["line"]
            )
            panel.blit(rfc_s, (panel_r.w // 2 - rfc_s.get_width() // 2, 106))

            # Mini fragment flow arrow
            n = len(self.fragments)
            slot_w = min(80, (panel_r.w - 40) // max(n + 2, 1))
            sx = 20
            sy = 128
            for i in range(n):
                colours_cycle = [C["cyan"], C["violet"], C["green"], C["amber"], C["blue"]]
                fc = colours_cycle[i % len(colours_cycle)]
                fr = pygame.Rect(sx, sy, slot_w - 4, 22)
                pygame.draw.rect(panel, (*fc, 60), fr, border_radius=4)
                pygame.draw.rect(panel, fc, fr, border_radius=4, width=1)
                f_s = self.fonts.mono_sm.render(f"F{i+1}", True, fc)
                panel.blit(f_s, (fr.centerx - f_s.get_width() // 2, fr.y + 4))
                sx += slot_w
                if i < n - 1:
                    arr = self.fonts.mono_sm.render("→", True, C["muted"])
                    panel.blit(arr, (sx - 4, sy + 4))

            # Arrow to reassembled
            arr2 = self.fonts.label.render("⟹", True, C["green"])
            panel.blit(arr2, (sx + 2, sy + 2))
            re_r = pygame.Rect(sx + arr2.get_width() + 6, sy, 90, 22)
            pygame.draw.rect(panel, (20, 40, 28), re_r, border_radius=4)
            pygame.draw.rect(panel, C["green"], re_r, border_radius=4, width=1)
            re_s = self.fonts.mono_sm.render("DATAGRAM", True, C["green"])
            panel.blit(re_s, (re_r.centerx - re_s.get_width() // 2, re_r.y + 4))

        else:
            # No fragmentation branch
            ok_s = self.fonts.title_md.render("✓  DATAGRAM PASSES WITHOUT FRAGMENTATION", True, C["green"])
            panel.blit(ok_s, (panel_r.w // 2 - ok_s.get_width() // 2, 18))
            sub_s = self.fonts.body_sm.render(
                f"Total datagram ({self.total_bytes} B) ≤ Network MTU ({NETWORK_MTU} B).  "
                "DF=1 is set — routers must NOT fragment this packet.",
                True, C["muted"]
            )
            panel.blit(sub_s, (panel_r.w // 2 - sub_s.get_width() // 2, 56))
            sub2_s = self.fonts.mono_sm.render(
                "RFC 791 §2.3: If DF=1 and datagram > link MTU, router drops packet and sends ICMP Type 3 Code 4.",
                True, C["cyan_dim"]
            )
            panel.blit(sub2_s, (panel_r.w // 2 - sub2_s.get_width() // 2, 86))

        surf.blit(panel, (panel_r.x, panel_r.y))


# ---------------------------------------------------------------------------
# SCENE: LEVEL 4 — ROUTING PART (ISP HOP CHALLENGE)
# ---------------------------------------------------------------------------


class Level4Routing:
    """
    Scene: Routing through multiple routers to reach the ISP Gateway.
    - Multiple routers interconnected with each other and multiple ways to reach the ISP.
    - User chooses path hop-by-hop.
    - Each link has its own random weight/cost.
    - Precalculated shortest path, longest path, and their average (kept HIDDEN during path choice).
    - User path is highlighted and path cost is tracked temporarily.
    - On reaching ISP:
        Score = round(average_cost - user_path_cost)
        Difference is added to user points!
    - Benchmarks and performance debrief are revealed.
    """

    def __init__(self, screen, fonts: Fonts, message: str, contact: dict):
        self.screen   = screen
        self.fonts    = fonts
        self.message  = message
        self.contact  = contact

        self.time_elapsed = 0.0

        # Routers definition (x, y layout across network map)
        self.routers = {
            "R1":  {"name": "R1 (Home Gateway)", "pos": (130, 360), "col": C["cyan"],   "ip": "192.168.1.1"},
            "R2":  {"name": "R2 (Core-A)",       "pos": (330, 210), "col": C["blue"],   "ip": "10.0.1.1"},
            "R3":  {"name": "R3 (Core-B)",       "pos": (330, 510), "col": C["violet"], "ip": "10.0.2.1"},
            "R4":  {"name": "R4 (Metro-A)",      "pos": (580, 180), "col": C["blue"],   "ip": "10.0.3.1"},
            "R5":  {"name": "R5 (Metro-B)",      "pos": (580, 530), "col": C["violet"], "ip": "10.0.4.1"},
            "R6":  {"name": "R6 (Edge Router)",  "pos": (810, 360), "col": C["green"],  "ip": "10.0.5.1"},
            "ISP": {"name": "ISP Gateway",       "pos": (1050, 360),"col": C["amber"],  "ip": "100.64.0.1"},
        }

        # Links definition with random cost ranges
        link_pairs = [
            ("R1", "R2", (3, 7)),
            ("R1", "R3", (4, 8)),
            ("R2", "R3", (2, 5)),
            ("R2", "R4", (4, 9)),
            ("R2", "R5", (6, 11)),
            ("R3", "R5", (4, 9)),
            ("R4", "R6", (3, 7)),
            ("R4", "ISP", (9, 15)),
            ("R5", "R6", (3, 7)),
            ("R5", "ISP", (8, 14)),
            ("R6", "ISP", (3, 6)),
        ]

        # Generate link weights & build adjacency graph
        self.adj = {k: [] for k in self.routers}
        self.link_costs = {}
        for u, v, (min_w, max_w) in link_pairs:
            w = __import__('random').randint(min_w, max_w)
            self.link_costs[(u, v)] = w
            self.link_costs[(v, u)] = w
            self.adj[u].append((v, w))
            self.adj[v].append((u, w))

        # Precalculate all simple paths from R1 to ISP
        all_paths = self._find_all_simple_paths("R1", "ISP", ["R1"], 0)
        all_paths.sort(key=lambda x: x[1])

        # Store precalculated shortest, longest, and average cost (KEPT HIDDEN FROM USER)
        self.shortest_path, self.shortest_cost = all_paths[0]
        self.longest_path,  self.longest_cost  = all_paths[-1]
        self.average_cost = (self.shortest_cost + self.longest_cost) / 2.0

        # User Routing State
        self.user_path = ["R1"]
        self.user_cost = 0
        self.current_router = "R1"
        self.reached_isp = False
        self.score_points = 0

        # Animation state for packet motion
        self.packet_pos = list(self.routers["R1"]["pos"])
        self.target_pos = list(self.routers["R1"]["pos"])

        # Control Buttons
        self.btn_undo  = Button(pygame.Rect(870, 115, 130, 40), "↶ Undo Hop", fonts, primary=False)
        self.btn_reset = Button(pygame.Rect(1015, 115, 135, 40), "↺ Reset Path", fonts, primary=False)

        # Completion Modal buttons
        self.btn_replay     = Button(pygame.Rect(430, 580, 150, 48), "↺ Replay Route", fonts, primary=False)
        self.btn_next_route = Button(pygame.Rect(600, 580, 270, 48), "ROUTE TO DESTINATION ➜", fonts, primary=True)

        self.action_replay     = False
        self.action_next_route = False

        self.particles = [Particle() for _ in range(25)]
        self.celebrate_sparks = []
        self._scan_surf = self._make_scanlines(1200, 750)

    def _make_scanlines(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(0, h, 4):
            pygame.draw.line(s, (0, 0, 0, 16), (0, y), (w, y))
        return s

    def _find_all_simple_paths(self, cur, dest, visited, cost):
        if cur == dest:
            return [(visited, cost)]
        res = []
        for nxt, w in self.adj[cur]:
            if nxt not in visited:
                res.extend(self._find_all_simple_paths(nxt, dest, visited + [nxt], cost + w))
        return res

    def get_valid_neighbors(self):
        """Neighbors of current router that haven't been visited yet."""
        if self.reached_isp:
            return []
        valid = []
        for nxt, w in self.adj[self.current_router]:
            if nxt not in self.user_path:
                valid.append(nxt)
        return valid

    def handle_event(self, event):
        pos = getattr(event, "pos", pygame.mouse.get_pos())

        if self.reached_isp:
            if self.btn_replay.handle_event(event):
                self.action_replay = True
            if self.btn_next_route.handle_event(event):
                self.action_next_route = True
            return

        if self.btn_undo.handle_event(event):
            self._undo_hop()
            return

        if self.btn_reset.handle_event(event):
            self._reset_path()
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            valid_next = self.get_valid_neighbors()
            for r_key in valid_next:
                r_pos = self.routers[r_key]["pos"]
                dist = math.hypot(pos[0] - r_pos[0], pos[1] - r_pos[1])
                if dist <= 38:
                    self._hop_to(r_key)
                    break

    def _hop_to(self, next_router):
        cost = self.link_costs[(self.current_router, next_router)]
        self.user_cost += cost
        self.user_path.append(next_router)
        self.current_router = next_router
        self.target_pos = list(self.routers[next_router]["pos"])

        # Check if reached ISP
        if next_router == "ISP":
            self.reached_isp = True
            # Compute score: remainder of average cost - user path cost
            self.score_points = round(self.average_cost - self.user_cost)

            # Celebration particles at ISP
            isp_pos = self.routers["ISP"]["pos"]
            for _ in range(40):
                angle = __import__('random').random() * math.tau
                speed = __import__('random').random() * 220.0 + 70.0
                self.celebrate_sparks.append({
                    "x": float(isp_pos[0]), "y": float(isp_pos[1]),
                    "vx": math.cos(angle) * speed,
                    "vy": math.sin(angle) * speed,
                    "life": 1.4,
                    "colour": __import__('random').choice([C["cyan"], C["amber"], C["green"], C["white"]])
                })

    def _undo_hop(self):
        if len(self.user_path) > 1 and not self.reached_isp:
            removed = self.user_path.pop()
            prev = self.user_path[-1]
            cost = self.link_costs[(prev, removed)]
            self.user_cost -= cost
            self.current_router = prev
            self.packet_pos = list(self.routers[prev]["pos"])
            self.target_pos = list(self.routers[prev]["pos"])

    def _reset_path(self):
        self.user_path = ["R1"]
        self.user_cost = 0
        self.current_router = "R1"
        self.reached_isp = False
        self.packet_pos = list(self.routers["R1"]["pos"])
        self.target_pos = list(self.routers["R1"]["pos"])

    def update(self, dt):
        self.time_elapsed += dt

        for p in self.particles:
            p.update()

        # Animate packet moving towards target router
        dx = self.target_pos[0] - self.packet_pos[0]
        dy = self.target_pos[1] - self.packet_pos[1]
        dist = math.hypot(dx, dy)
        if dist > 1.0:
            speed = min(dist, dt * 600.0)
            self.packet_pos[0] += (dx / dist) * speed
            self.packet_pos[1] += (dy / dist) * speed
        else:
            self.packet_pos = list(self.target_pos)

        # Update sparks
        for sp in self.celebrate_sparks[:]:
            sp["x"] += sp["vx"] * dt
            sp["y"] += sp["vy"] * dt
            sp["life"] -= dt * 1.2
            if sp["life"] <= 0:
                self.celebrate_sparks.remove(sp)

        self.btn_undo.update(dt)
        self.btn_reset.update(dt)

        if self.reached_isp:
            self.btn_replay.update(dt)
            self.btn_next_route.update(dt)

    def draw(self):
        surf = self.screen
        W, H = surf.get_width(), surf.get_height()
        t = self.time_elapsed

        # Background
        surf.fill(C["bg"])

        for (cx, cy, col, rad) in [
            (int(W * 0.15), int(H * 0.15), C["blue"],   260),
            (int(W * 0.85), int(H * 0.35), C["amber"],  300),
            (int(W * 0.50), int(H * 0.85), C["cyan"],   250),
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
        lvl_lbl = self.fonts.label.render("CURRENT STAGE", True, C["muted"])
        lvl_txt = self.fonts.label_lg.render("04 / ROUTING TO ISP GATEWAY", True, C["cyan"])
        surf.blit(lvl_lbl, (badge_r.x + 14, badge_r.y + 6))
        surf.blit(lvl_txt, (badge_r.x + 14, badge_r.y + 22))

        # ── Top HUD Bar ──────────────────────────────────────────
        hud_r = pygame.Rect(30, 85, W - 60, 52)
        draw_rect_rounded(surf, C["panel"], hud_r, radius=10, border=1, border_colour=C["line"])

        # Path Status
        pos_str = " ➜ ".join(self.user_path)
        surf.blit(self.fonts.label.render("ACTIVE ROUTE:", True, C["muted"]), (hud_r.x + 14, hud_r.y + 8))
        surf.blit(self.fonts.mono.render(pos_str, True, C["cyan"]),           (hud_r.x + 14, hud_r.y + 26))

        # Cost Counter (temporarily tracked for user)
        c_x = hud_r.x + 420
        surf.blit(self.fonts.label.render("TOTAL PATH COST:", True, C["amber"]), (c_x, hud_r.y + 8))
        surf.blit(self.fonts.mono_lg.render(f"{self.user_cost} (Hops: {len(self.user_path)-1})", True, C["text"]), (c_x, hud_r.y + 26))

        # Destination target info
        d_x = hud_r.x + 620
        surf.blit(self.fonts.label.render("TARGET DESTINATION:", True, C["muted"]), (d_x, hud_r.y + 8))
        surf.blit(self.fonts.mono.render("ISP Gateway (100.64.0.1)", True, C["green"]), (d_x, hud_r.y + 26))

        # Controls
        if not self.reached_isp:
            self.btn_undo.draw(surf)
            self.btn_reset.draw(surf)

        # ── Graph Canvas ─────────────────────────────────────────
        # 1. Draw Links
        user_edges = set()
        for i in range(len(self.user_path) - 1):
            user_edges.add((self.user_path[i], self.user_path[i+1]))
            user_edges.add((self.user_path[i+1], self.user_path[i]))

        drawn_links = set()
        for u in self.routers:
            for v, w in self.adj[u]:
                pair = tuple(sorted((u, v)))
                if pair in drawn_links:
                    continue
                drawn_links.add(pair)

                pos_u = self.routers[u]["pos"]
                pos_v = self.routers[v]["pos"]

                is_user_edge = (u, v) in user_edges

                # Edge line
                if is_user_edge:
                    edge_col = C["cyan"]
                    edge_w   = 4
                else:
                    edge_col = (30, 48, 70)
                    edge_w   = 2

                pygame.draw.line(surf, edge_col, pos_u, pos_v, edge_w)

                # Animated pulses on user chosen path
                if is_user_edge:
                    p_t = (t * 2.5) % 1.0
                    px = pos_u[0] + (pos_v[0] - pos_u[0]) * p_t
                    py = pos_u[1] + (pos_v[1] - pos_u[1]) * p_t
                    pygame.draw.circle(surf, C["white"], (int(px), int(py)), 3)

                # Link weight badge (pill)
                mid_x = (pos_u[0] + pos_v[0]) // 2
                mid_y = (pos_u[1] + pos_v[1]) // 2

                bw, bh = 34, 22
                pill_r = pygame.Rect(mid_x - bw // 2, mid_y - bh // 2, bw, bh)
                pill_bg = (24, 45, 70) if is_user_edge else (14, 22, 36)
                draw_rect_rounded(surf, pill_bg, pill_r, radius=6, border=1, border_colour=edge_col)
                w_txt = self.fonts.mono_sm.render(str(w), True, C["text"] if not is_user_edge else C["cyan"])
                surf.blit(w_txt, (pill_r.centerx - w_txt.get_width() // 2,
                                  pill_r.centery - w_txt.get_height() // 2))

        # 2. Draw Router Nodes
        valid_next = set(self.get_valid_neighbors())
        mouse_pos = pygame.mouse.get_pos()

        for r_key, r_info in self.routers.items():
            rx, ry = r_info["pos"]
            is_cur   = (r_key == self.current_router)
            is_valid = (r_key in valid_next)
            is_hover = (is_valid and math.hypot(mouse_pos[0] - rx, mouse_pos[1] - ry) <= 38)
            in_path  = (r_key in self.user_path)

            node_radius = 34

            # Glow halo for valid next hops or current node
            if is_valid:
                pulse = 0.5 + 0.5 * math.sin(t * 6)
                g_col = C["green"] if not is_hover else C["cyan"]
                glow = glow_surface(node_radius + 18, g_col, alpha=int(40 * pulse) if not is_hover else 75)
                surf.blit(glow, (rx - node_radius - 18, ry - node_radius - 18))
            elif is_cur:
                glow = glow_surface(node_radius + 15, C["cyan"], alpha=50)
                surf.blit(glow, (rx - node_radius - 15, ry - node_radius - 15))

            # Main Router Circle
            if is_cur:
                bg_col = (20, 48, 72)
                bdr_col = C["cyan"]
            elif in_path:
                bg_col = (18, 38, 56)
                bdr_col = C["cyan"]
            elif is_valid:
                bg_col = (18, 36, 42) if not is_hover else (24, 52, 60)
                bdr_col = C["green"] if not is_hover else C["cyan"]
            else:
                bg_col = (13, 20, 34)
                bdr_col = C["line"]

            pygame.draw.circle(surf, bg_col, (rx, ry), node_radius)
            pygame.draw.circle(surf, bdr_col, (rx, ry), node_radius, width=2)

            # Node label
            name_s = self.fonts.label_lg.render(r_key, True, C["text"])
            surf.blit(name_s, (rx - name_s.get_width() // 2, ry - 14))

            sub_txt = self.fonts.mono_sm.render(r_info["ip"].split(".")[-1], True, r_info["col"])
            surf.blit(sub_txt, (rx - sub_txt.get_width() // 2, ry + 4))

            # Hover indicator tag
            if is_hover:
                tip = self.fonts.mono_sm.render("CLICK TO HOP", True, C["green"])
                surf.blit(tip, (rx - tip.get_width() // 2, ry + node_radius + 6))
            else:
                tip = self.fonts.body_sm.render(r_info["name"].split(" ")[0], True, C["muted"])
                surf.blit(tip, (rx - tip.get_width() // 2, ry + node_radius + 6))

        # 3. Draw Traveling Packet Sprite
        px, py = int(self.packet_pos[0]), int(self.packet_pos[1])
        pkt_glow = glow_surface(26, C["cyan"], alpha=90)
        surf.blit(pkt_glow, (px - 26, py - 26))
        pygame.draw.circle(surf, C["white"], (px, py), 10)
        pygame.draw.circle(surf, C["cyan"],  (px, py), 12, width=2)

        # 4. Draw celebration sparks
        for sp in self.celebrate_sparks:
            r = int(max(2, sp["life"] * 5))
            pygame.draw.circle(surf, sp["colour"], (int(sp["x"]), int(sp["y"])), r)

        # ── Completion / Results Modal ───────────────────────────
        if self.reached_isp:
            self._draw_results_modal(surf)

    def _draw_results_modal(self, surf):
        W, H = surf.get_width(), surf.get_height()

        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surf.blit(overlay, (0, 0))

        mw, mh = 680, 470
        mx = (W - mw) // 2
        my = (H - mh) // 2
        card_r = pygame.Rect(mx, my, mw, mh)

        draw_rect_rounded(surf, (14, 25, 42), card_r, radius=16, border=2, border_colour=C["cyan"])
        glow = glow_surface(mw // 2 + 20, C["cyan"], alpha=35)
        surf.blit(glow, (card_r.centerx - mw // 2 - 20, card_r.centery - mw // 2 - 20))

        # Title
        m_title = self.fonts.title_lg.render("PACKET SUCCESSFULLY REACHED ISP!", True, C["text"])
        surf.blit(m_title, (card_r.centerx - m_title.get_width() // 2, my + 24))

        m_sub = self.fonts.body_sm.render("Your routing decisions have been evaluated against network benchmarks.", True, C["muted"])
        surf.blit(m_sub, (card_r.centerx - m_sub.get_width() // 2, my + 56))

        # User's Path Box
        u_box = pygame.Rect(mx + 30, my + 88, mw - 60, 68)
        draw_rect_rounded(surf, (10, 18, 30), u_box, radius=10, border=1, border_colour=C["cyan_dim"])

        surf.blit(self.fonts.label.render("YOUR CHOSEN PATH:", True, C["muted"]), (u_box.x + 14, u_box.y + 10))
        surf.blit(self.fonts.mono_lg.render(" ➜ ".join(self.user_path), True, C["cyan"]), (u_box.x + 14, u_box.y + 26))

        u_cost_s = self.fonts.label_lg.render(f"Cost: {self.user_cost}", True, C["text"])
        surf.blit(u_cost_s, (u_box.right - u_cost_s.get_width() - 16, u_box.y + 26))

        # Revealed Benchmarks Box
        b_box = pygame.Rect(mx + 30, my + 168, mw - 60, 140)
        draw_rect_rounded(surf, (12, 20, 34), b_box, radius=10, border=1, border_colour=C["line"])

        surf.blit(self.fonts.label.render("REVEALED BENCHMARKS (PREVIOUSLY HIDDEN):", True, C["amber"]), (b_box.x + 14, b_box.y + 10))

        # Shortest (Dijkstra)
        s_lbl = self.fonts.body_sm.render(f"★ Optimal Dijkstra Path: {' ➜ '.join(self.shortest_path)}", True, C["green"])
        s_c   = self.fonts.mono.render(f"Cost: {self.shortest_cost}", True, C["green"])
        surf.blit(s_lbl, (b_box.x + 14, b_box.y + 36))
        surf.blit(s_c,   (b_box.right - s_c.get_width() - 14, b_box.y + 36))

        # Longest Path
        l_lbl = self.fonts.body_sm.render(f"• Longest Simple Path: {' ➜ '.join(self.longest_path)}", True, C["muted"])
        l_c   = self.fonts.mono.render(f"Cost: {self.longest_cost}", True, C["muted"])
        surf.blit(l_lbl, (b_box.x + 14, b_box.y + 64))
        surf.blit(l_c,   (b_box.right - l_c.get_width() - 14, b_box.y + 64))

        # Average Benchmark
        a_lbl = self.fonts.body_sm.render("• Benchmark Average Cost: (Shortest + Longest) / 2", True, C["cyan"])
        a_c   = self.fonts.mono.render(f"Avg: {self.average_cost:.1f}", True, C["cyan"])
        surf.blit(a_lbl, (b_box.x + 14, b_box.y + 92))
        surf.blit(a_c,   (b_box.right - a_c.get_width() - 14, b_box.y + 92))

        # Scoring Formula & Remainder Points
        score_box = pygame.Rect(mx + 30, my + 320, mw - 60, 68)
        score_bg = (18, 42, 32) if self.score_points >= 0 else (42, 20, 26)
        score_bdr = C["green"] if self.score_points >= 0 else C["red"]
        draw_rect_rounded(surf, score_bg, score_box, radius=10, border=1, border_colour=score_bdr)

        formula_s = self.fonts.body_sm.render(
            f"Score Formula: Average ({self.average_cost:.1f}) - User Cost ({self.user_cost})",
            True, C["muted"]
        )
        points_s = self.fonts.title_md.render(
            f"POINTS AWARDED: {self.score_points:+} PTS",
            True, score_bdr
        )
        surf.blit(formula_s, (score_box.x + 16, score_box.y + 12))
        surf.blit(points_s,  (score_box.x + 16, score_box.y + 34))

        # Evaluation verdict
        if self.user_cost == self.shortest_cost:
            verdict = "★ PERFECT ROUTE! You found the optimal Dijkstra shortest path!"
            v_col = C["green"]
        elif self.score_points > 0:
            verdict = "✓ EFFICIENT ROUTING! Beat the network average latency!"
            v_col = C["cyan"]
        else:
            verdict = "High congestion route taken. Link penalty applied."
            v_col = C["amber"]

        v_s = self.fonts.label.render(verdict, True, v_col)
        surf.blit(v_s, (card_r.centerx - v_s.get_width() // 2, my + 400))

        # Buttons
        self.btn_replay.rect.x = mx + 60
        self.btn_replay.rect.y = my + 420
        self.btn_next_route.rect.x = mx + 240
        self.btn_next_route.rect.y = my + 420

        self.btn_replay.draw(surf)
        self.btn_next_route.draw(surf)


# ---------------------------------------------------------------------------
# SCENE: LEVEL 5 — ROUTING TO DESTINATION & DYNAMIC LINK FAILURE
# ---------------------------------------------------------------------------

class Level5DestRouting:
    """
    Scene: Routing from ISP Gateway to the Destination Router.
    A random link breaks in route, requiring the user to dynamically re-route!
    """

    def __init__(self, screen, fonts: Fonts, message: str, contact: dict):
        self.screen   = screen
        self.fonts    = fonts
        self.message  = message
        self.contact  = contact

        self.time_elapsed = 0.0

        # Routers definition on the Transit Backbone
        self.routers = {
            "ISP":    {"name": "ISP Gateway",       "pos": (120, 360), "col": C["amber"],  "ip": "100.64.0.1"},
            "B1":     {"name": "B1 (Transit North)","pos": (330, 200), "col": C["blue"],   "ip": "198.51.100.1"},
            "B2":     {"name": "B2 (Transit South)","pos": (330, 520), "col": C["violet"], "ip": "198.51.100.2"},
            "B3":     {"name": "B3 (IXP Exchange A)","pos": (580, 220), "col": C["blue"],   "ip": "203.0.113.1"},
            "B4":     {"name": "B4 (IXP Exchange B)","pos": (580, 500), "col": C["violet"], "ip": "203.0.113.2"},
            "B5":     {"name": "B5 (Metro Edge 1)", "pos": (810, 210), "col": C["green"],  "ip": "172.16.1.1"},
            "B6":     {"name": "B6 (Metro Edge 2)", "pos": (810, 510), "col": C["green"],  "ip": "172.16.2.1"},
            "R_DEST": {"name": f"R_DEST ({contact['name']})", "pos": (1050, 360), "col": contact['colour'], "ip": contact['ip']},
        }

        # Links definition with latency costs (ms)
        link_pairs = [
            ("ISP", "B1", (10, 15)),
            ("ISP", "B2", (12, 17)),
            ("B1", "B2", (6, 10)),
            ("B1", "B3", (12, 18)),
            ("B1", "B4", (18, 26)),
            ("B2", "B4", (14, 20)),
            ("B2", "B3", (20, 28)),
            ("B3", "B4", (7, 12)),
            ("B3", "B5", (14, 22)),
            ("B3", "B6", (22, 30)),
            ("B4", "B6", (15, 23)),
            ("B4", "B5", (22, 30)),
            ("B5", "B6", (8, 14)),
            ("B5", "R_DEST", (9, 15)),
            ("B6", "R_DEST", (10, 16)),
        ]

        # Generate link weights
        self.adj = {k: [] for k in self.routers}
        self.link_costs = {}
        for u, v, (min_w, max_w) in link_pairs:
            w = __import__('random').randint(min_w, max_w)
            self.link_costs[(u, v)] = w
            self.link_costs[(v, u)] = w
            self.adj[u].append((v, w))
            self.adj[v].append((u, w))

        # Dynamic Link Failure State
        self.broken_link = None
        self.break_triggered = False
        self.alert_flash_t = 0.0
        self.toast = Toast(fonts)

        # Candidate links to break (guaranteed to leave the graph navigable)
        self.break_candidates = [
            ("B1", "B3"),
            ("B2", "B4"),
            ("B3", "B5"),
            ("B4", "B6"),
            ("B1", "B4"),
        ]

        # User Routing State
        self.user_path = ["ISP"]
        self.user_cost = 0
        self.current_router = "ISP"
        self.ttl = 10                  # Time To Live (decrements per hop)
        self.reached_dest = False
        self.score_points = 250        # Reroute achievement bonus

        # Packet animated motion
        self.packet_pos = list(self.routers["ISP"]["pos"])
        self.target_pos = list(self.routers["ISP"]["pos"])

        # Controls
        self.btn_undo  = Button(pygame.Rect(870, 115, 130, 40), "↶ Undo Hop", fonts, primary=False)
        self.btn_reset = Button(pygame.Rect(1015, 115, 135, 40), "↺ Reset Path", fonts, primary=False)

        # Completion Modal buttons
        self.btn_replay = Button(pygame.Rect(430, 580, 150, 48), "↺ Replay Route", fonts, primary=False)
        self.btn_decap  = Button(pygame.Rect(600, 580, 270, 48), "DECAPSULATE PACKET ➜", fonts, primary=True)

        self.action_replay = False
        self.action_decap  = False

        self.particles = [Particle() for _ in range(25)]
        self.celebrate_sparks = []
        self.break_sparks = []
        self._scan_surf = self._make_scanlines(1200, 750)

    def _make_scanlines(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(0, h, 4):
            pygame.draw.line(s, (0, 0, 0, 16), (0, y), (w, y))
        return s

    def get_valid_neighbors(self):
        """Neighbors of current router that haven't been visited and aren't broken."""
        if self.reached_dest:
            return []
        valid = []
        for nxt, w in self.adj[self.current_router]:
            if nxt not in self.user_path:
                pair = tuple(sorted((self.current_router, nxt)))
                if pair != self.broken_link:
                    valid.append(nxt)
        return valid

    def _trigger_link_break(self):
        """Breaks a random forward link in route to the destination."""
        if self.break_triggered:
            return
        self.break_triggered = True
        chosen = __import__('random').choice(self.break_candidates)
        self.broken_link = tuple(sorted(chosen))
        self.alert_flash_t = 1.0

        # Spawn sparks at broken link center
        u, v = self.broken_link
        p1 = self.routers[u]["pos"]
        p2 = self.routers[v]["pos"]
        mx, my = (p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2

        for _ in range(35):
            angle = __import__('random').random() * math.tau
            speed = __import__('random').random() * 180.0 + 50.0
            self.break_sparks.append({
                "x": float(mx), "y": float(my),
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "life": 1.2,
                "colour": C["red"]
            })

    def handle_event(self, event):
        pos = getattr(event, "pos", pygame.mouse.get_pos())

        if self.reached_dest:
            if self.btn_replay.handle_event(event):
                self.action_replay = True
            if self.btn_decap.handle_event(event):
                self.action_decap = True
            return

        if self.btn_undo.handle_event(event):
            self._undo_hop()
            return

        if self.btn_reset.handle_event(event):
            self._reset_path()
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Check all neighbors of current router
            for nxt, w in self.adj[self.current_router]:
                r_pos = self.routers[nxt]["pos"]
                dist = math.hypot(pos[0] - r_pos[0], pos[1] - r_pos[1])
                if dist <= 38:
                    pair = tuple(sorted((self.current_router, nxt)))
                    # If user clicked on the severed link
                    if pair == self.broken_link:
                        self.toast.show(f"✖ LINK SEVERED! Fiber cut between {pair[0]} & {pair[1]}. Dynamic rerouting required!", C["red"])
                        return
                    if nxt in self.get_valid_neighbors():
                        self._hop_to(nxt)
                        break

    def _hop_to(self, next_router):
        cost = self.link_costs[(self.current_router, next_router)]
        self.user_cost += cost
        self.user_path.append(next_router)
        self.current_router = next_router
        self.ttl = max(0, self.ttl - 1)
        self.target_pos = list(self.routers[next_router]["pos"])

        # Trigger dynamic link break after 1st hop!
        if len(self.user_path) >= 2 and not self.break_triggered:
            self._trigger_link_break()

        # Check if reached destination
        if next_router == "R_DEST":
            self.reached_dest = True
            dest_pos = self.routers["R_DEST"]["pos"]
            for _ in range(45):
                angle = __import__('random').random() * math.tau
                speed = __import__('random').random() * 240.0 + 80.0
                self.celebrate_sparks.append({
                    "x": float(dest_pos[0]), "y": float(dest_pos[1]),
                    "vx": math.cos(angle) * speed,
                    "vy": math.sin(angle) * speed,
                    "life": 1.4,
                    "colour": __import__('random').choice([C["cyan"], C["amber"], C["green"], C["white"]])
                })

    def _undo_hop(self):
        if len(self.user_path) > 1 and not self.reached_dest:
            removed = self.user_path.pop()
            prev = self.user_path[-1]
            cost = self.link_costs[(prev, removed)]
            self.user_cost -= cost
            self.ttl += 1
            self.current_router = prev
            self.packet_pos = list(self.routers[prev]["pos"])
            self.target_pos = list(self.routers[prev]["pos"])

    def _reset_path(self):
        self.user_path = ["ISP"]
        self.user_cost = 0
        self.ttl = 10
        self.current_router = "ISP"
        self.reached_dest = False
        self.packet_pos = list(self.routers["ISP"]["pos"])
        self.target_pos = list(self.routers["ISP"]["pos"])

    def update(self, dt):
        self.time_elapsed += dt

        if self.alert_flash_t > 0:
            self.alert_flash_t = max(0.0, self.alert_flash_t - dt * 1.5)

        for p in self.particles:
            p.update()

        # Animate packet motion
        dx = self.target_pos[0] - self.packet_pos[0]
        dy = self.target_pos[1] - self.packet_pos[1]
        dist = math.hypot(dx, dy)
        if dist > 1.0:
            speed = min(dist, dt * 600.0)
            self.packet_pos[0] += (dx / dist) * speed
            self.packet_pos[1] += (dy / dist) * speed
        else:
            self.packet_pos = list(self.target_pos)

        # Update sparks
        for sp in self.celebrate_sparks[:]:
            sp["x"] += sp["vx"] * dt
            sp["y"] += sp["vy"] * dt
            sp["life"] -= dt * 1.2
            if sp["life"] <= 0:
                self.celebrate_sparks.remove(sp)

        for sp in self.break_sparks[:]:
            sp["x"] += sp["vx"] * dt
            sp["y"] += sp["vy"] * dt
            sp["life"] -= dt * 1.5
            if sp["life"] <= 0:
                self.break_sparks.remove(sp)

        self.toast.update(dt)
        self.btn_undo.update(dt)
        self.btn_reset.update(dt)

        if self.reached_dest:
            self.btn_replay.update(dt)
            self.btn_decap.update(dt)

    def draw(self):
        surf = self.screen
        W, H = surf.get_width(), surf.get_height()
        t = self.time_elapsed

        # Background
        surf.fill(C["bg"])

        # Red flash if alert triggered
        if self.alert_flash_t > 0.05:
            flash_overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            flash_overlay.fill((255, 30, 50, int(self.alert_flash_t * 60)))
            surf.blit(flash_overlay, (0, 0))

        for (cx, cy, col, rad) in [
            (int(W * 0.15), int(H * 0.15), C["amber"],  260),
            (int(W * 0.85), int(H * 0.35), self.contact["colour"], 300),
            (int(W * 0.50), int(H * 0.85), C["cyan"],   250),
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
        pygame.draw.rect(surf, self.contact["colour"], logo_r, border_radius=12)
        sym = self.fonts.hero.render("↯", True, C["black"])
        surf.blit(sym, (logo_r.centerx - sym.get_width() // 2,
                        logo_r.centery - sym.get_height() // 2))

        title = self.fonts.title_lg.render("PACKET PATH", True, C["text"])
        surf.blit(title, (88, 22))

        badge_r = pygame.Rect(W - 365, 14, 335, 42)
        draw_rect_rounded(surf, (16, 28, 48), badge_r, radius=10, border=1, border_colour=C["line"])
        lvl_lbl = self.fonts.label.render("CURRENT STAGE", True, C["muted"])
        lvl_txt = self.fonts.label_lg.render("05 / DESTINATION ROUTING & FAILURE", True, C["cyan"])
        surf.blit(lvl_lbl, (badge_r.x + 14, badge_r.y + 6))
        surf.blit(lvl_txt, (badge_r.x + 14, badge_r.y + 22))

        # ── Top HUD Bar ──────────────────────────────────────────
        hud_r = pygame.Rect(30, 85, W - 60, 52)
        draw_rect_rounded(surf, C["panel"], hud_r, radius=10, border=1, border_colour=C["line"])

        # Path Status
        pos_str = " ➜ ".join(self.user_path)
        surf.blit(self.fonts.label.render("TRANSIT PATH:", True, C["muted"]), (hud_r.x + 14, hud_r.y + 8))
        surf.blit(self.fonts.mono.render(pos_str, True, C["cyan"]),           (hud_r.x + 14, hud_r.y + 26))

        # Latency / Path Cost
        c_x = hud_r.x + 400
        surf.blit(self.fonts.label.render("PATH LATENCY:", True, C["amber"]), (c_x, hud_r.y + 8))
        surf.blit(self.fonts.mono_lg.render(f"{self.user_cost} ms", True, C["text"]), (c_x, hud_r.y + 26))

        # TTL Indicator
        ttl_x = hud_r.x + 540
        ttl_col = C["green"] if self.ttl > 4 else (C["amber"] if self.ttl > 2 else C["red"])
        surf.blit(self.fonts.label.render("TTL REMAINING:", True, C["muted"]), (ttl_x, hud_r.y + 8))
        surf.blit(self.fonts.mono_lg.render(f"{self.ttl} hops", True, ttl_col), (ttl_x, hud_r.y + 26))

        # Destination Target
        d_x = hud_r.x + 680
        surf.blit(self.fonts.label.render("RECIPIENT GATEWAY:", True, C["muted"]), (d_x, hud_r.y + 8))
        surf.blit(self.fonts.mono.render(f"{self.contact['name']} ({self.contact['ip']})", True, self.contact["colour"]), (d_x, hud_r.y + 26))

        # Controls
        if not self.reached_dest:
            self.btn_undo.draw(surf)
            self.btn_reset.draw(surf)

        # ── Dynamic Link Failure Alert Banner ────────────────────
        alert_r = pygame.Rect(30, 142, W - 60, 28)
        if self.break_triggered:
            pulse = 0.5 + 0.5 * math.sin(t * 8)
            a_bg = (45, 15, 20)
            a_bdr = tuple(int(C["red"][c] * (0.7 + 0.3 * pulse)) for c in range(3))
            draw_rect_rounded(surf, a_bg, alert_r, radius=6, border=1, border_colour=a_bdr)
            u, v = self.broken_link
            a_text = f"⚠ CRITICAL ALERT: FIBER SEVERED! LINK [{u} ✖ {v}] IS DOWN! DYNAMIC REROUTE REQUIRED!"
            a_surf = self.fonts.mono_sm.render(a_text, True, C["red"])
            surf.blit(a_surf, (alert_r.centerx - a_surf.get_width() // 2, alert_r.y + 7))
        else:
            draw_rect_rounded(surf, (14, 22, 36), alert_r, radius=6, border=1, border_colour=C["line"])
            n_text = "TRANSIT STATUS: ALL BACKBONE FIBER LINKS OPERATIONAL · MONITORING LINK INTEGRITY..."
            n_surf = self.fonts.mono_sm.render(n_text, True, (80, 110, 145))
            surf.blit(n_surf, (alert_r.centerx - n_surf.get_width() // 2, alert_r.y + 7))

        # ── Graph Canvas ─────────────────────────────────────────
        # 1. Draw Links
        user_edges = set()
        for i in range(len(self.user_path) - 1):
            user_edges.add((self.user_path[i], self.user_path[i+1]))
            user_edges.add((self.user_path[i+1], self.user_path[i]))

        drawn_links = set()
        for u in self.routers:
            for v, w in self.adj[u]:
                pair = tuple(sorted((u, v)))
                if pair in drawn_links:
                    continue
                drawn_links.add(pair)

                pos_u = self.routers[u]["pos"]
                pos_v = self.routers[v]["pos"]

                is_user_edge = (u, v) in user_edges
                is_broken    = (pair == self.broken_link)

                mid_x = (pos_u[0] + pos_v[0]) // 2
                mid_y = (pos_u[1] + pos_v[1]) // 2

                # Edge rendering
                if is_broken:
                    # Broken red jagged line with electrical effect
                    pulse = 0.5 + 0.5 * math.sin(t * 12)
                    red_col = (255, int(40 * pulse), int(50 * pulse))
                    # Draw broken gap
                    gap = 25
                    dx = pos_v[0] - pos_u[0]
                    dy = pos_v[1] - pos_u[1]
                    dist = math.hypot(dx, dy)
                    ux, uy = dx / dist, dy / dist

                    p1_end = (int(mid_x - ux * gap), int(mid_y - uy * gap))
                    p2_start = (int(mid_x + ux * gap), int(mid_y + uy * gap))

                    pygame.draw.line(surf, red_col, pos_u, p1_end, 3)
                    pygame.draw.line(surf, red_col, p2_start, pos_v, 3)

                    # Broken warning badge
                    bw, bh = 85, 22
                    pill_r = pygame.Rect(mid_x - bw // 2, mid_y - bh // 2, bw, bh)
                    draw_rect_rounded(surf, (45, 12, 18), pill_r, radius=6, border=1, border_colour=C["red"])
                    b_txt = self.fonts.mono_sm.render("✖ SEVERED", True, C["red"])
                    surf.blit(b_txt, (pill_r.centerx - b_txt.get_width() // 2, pill_r.centery - b_txt.get_height() // 2))

                elif is_user_edge:
                    edge_col = C["cyan"]
                    pygame.draw.line(surf, edge_col, pos_u, pos_v, 4)
                    p_t = (t * 2.5) % 1.0
                    px = pos_u[0] + (pos_v[0] - pos_u[0]) * p_t
                    py = pos_u[1] + (pos_v[1] - pos_u[1]) * p_t
                    pygame.draw.circle(surf, C["white"], (int(px), int(py)), 3)

                    # Pill
                    bw, bh = 42, 22
                    pill_r = pygame.Rect(mid_x - bw // 2, mid_y - bh // 2, bw, bh)
                    draw_rect_rounded(surf, (24, 45, 70), pill_r, radius=6, border=1, border_colour=edge_col)
                    w_txt = self.fonts.mono_sm.render(f"{w}ms", True, C["cyan"])
                    surf.blit(w_txt, (pill_r.centerx - w_txt.get_width() // 2, pill_r.centery - w_txt.get_height() // 2))
                else:
                    edge_col = (30, 48, 70)
                    pygame.draw.line(surf, edge_col, pos_u, pos_v, 2)

                    bw, bh = 42, 22
                    pill_r = pygame.Rect(mid_x - bw // 2, mid_y - bh // 2, bw, bh)
                    draw_rect_rounded(surf, (14, 22, 36), pill_r, radius=6, border=1, border_colour=edge_col)
                    w_txt = self.fonts.mono_sm.render(f"{w}ms", True, C["muted"])
                    surf.blit(w_txt, (pill_r.centerx - w_txt.get_width() // 2, pill_r.centery - w_txt.get_height() // 2))

        # 2. Draw Router Nodes
        valid_next = set(self.get_valid_neighbors())
        mouse_pos = pygame.mouse.get_pos()

        for r_key, r_info in self.routers.items():
            rx, ry = r_info["pos"]
            is_cur   = (r_key == self.current_router)
            is_valid = (r_key in valid_next)
            is_hover = (is_valid and math.hypot(mouse_pos[0] - rx, mouse_pos[1] - ry) <= 38)
            in_path  = (r_key in self.user_path)

            node_radius = 34

            if is_valid:
                pulse = 0.5 + 0.5 * math.sin(t * 6)
                g_col = C["green"] if not is_hover else C["cyan"]
                glow = glow_surface(node_radius + 18, g_col, alpha=int(40 * pulse) if not is_hover else 75)
                surf.blit(glow, (rx - node_radius - 18, ry - node_radius - 18))
            elif is_cur:
                glow = glow_surface(node_radius + 15, C["cyan"], alpha=50)
                surf.blit(glow, (rx - node_radius - 15, ry - node_radius - 15))

            if is_cur:
                bg_col = (20, 48, 72)
                bdr_col = C["cyan"]
            elif in_path:
                bg_col = (18, 38, 56)
                bdr_col = C["cyan"]
            elif is_valid:
                bg_col = (18, 36, 42) if not is_hover else (24, 52, 60)
                bdr_col = C["green"] if not is_hover else C["cyan"]
            else:
                bg_col = (13, 20, 34)
                bdr_col = C["line"]

            pygame.draw.circle(surf, bg_col, (rx, ry), node_radius)
            pygame.draw.circle(surf, bdr_col, (rx, ry), node_radius, width=2)

            name_s = self.fonts.label_lg.render(r_key, True, C["text"])
            surf.blit(name_s, (rx - name_s.get_width() // 2, ry - 14))

            sub_txt = self.fonts.mono_sm.render(r_info["ip"].split(".")[-1], True, r_info["col"])
            surf.blit(sub_txt, (rx - sub_txt.get_width() // 2, ry + 4))

            if is_hover:
                tip = self.fonts.mono_sm.render("REROUTE HERE", True, C["green"])
                surf.blit(tip, (rx - tip.get_width() // 2, ry + node_radius + 6))
            else:
                tip = self.fonts.body_sm.render(r_info["name"].split(" ")[0], True, C["muted"])
                surf.blit(tip, (rx - tip.get_width() // 2, ry + node_radius + 6))

        # 3. Draw Traveling Packet Sprite
        px, py = int(self.packet_pos[0]), int(self.packet_pos[1])
        pkt_glow = glow_surface(26, C["cyan"], alpha=90)
        surf.blit(pkt_glow, (px - 26, py - 26))
        pygame.draw.circle(surf, C["white"], (px, py), 10)
        pygame.draw.circle(surf, C["cyan"],  (px, py), 12, width=2)

        # 4. Draw sparks
        for sp in self.celebrate_sparks:
            r = int(max(2, sp["life"] * 5))
            pygame.draw.circle(surf, sp["colour"], (int(sp["x"]), int(sp["y"])), r)

        for sp in self.break_sparks:
            r = int(max(1, sp["life"] * 4))
            pygame.draw.circle(surf, sp["colour"], (int(sp["x"]), int(sp["y"])), r)

        self.toast.draw(surf)

        # ── Completion Modal ─────────────────────────────────────
        if self.reached_dest:
            self._draw_results_modal(surf)

    def _draw_results_modal(self, surf):
        W, H = surf.get_width(), surf.get_height()

        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        surf.blit(overlay, (0, 0))

        mw, mh = 680, 470
        mx = (W - mw) // 2
        my = (H - mh) // 2
        card_r = pygame.Rect(mx, my, mw, mh)

        draw_rect_rounded(surf, (14, 25, 42), card_r, radius=16, border=2, border_colour=C["green"])
        glow = glow_surface(mw // 2 + 20, C["green"], alpha=35)
        surf.blit(glow, (card_r.centerx - mw // 2 - 20, card_r.centery - mw // 2 - 20))

        m_title = self.fonts.title_lg.render("PACKET DELIVERED TO DESTINATION ROUTER!", True, C["text"])
        surf.blit(m_title, (card_r.centerx - m_title.get_width() // 2, my + 24))

        m_sub = self.fonts.body_sm.render(
            f"Dynamic link failure successfully avoided! The packet safely reached {self.contact['name']}'s router.",
            True, C["muted"]
        )
        surf.blit(m_sub, (card_r.centerx - m_sub.get_width() // 2, my + 56))

        # Details Box
        u_box = pygame.Rect(mx + 30, my + 88, mw - 60, 205)
        draw_rect_rounded(surf, (10, 18, 30), u_box, radius=10, border=1, border_colour=C["line"])

        # Path Taken
        surf.blit(self.fonts.label.render("FINAL REROUTED PATH:", True, C["muted"]), (u_box.x + 14, u_box.y + 12))
        surf.blit(self.fonts.mono.render(" ➜ ".join(self.user_path), True, C["cyan"]), (u_box.x + 14, u_box.y + 28))

        # Severed Link Handled
        u_brk = self.broken_link if self.broken_link else ("B1", "B3")
        surf.blit(self.fonts.label.render("FAILED LINK AVOIDED:", True, C["red"]), (u_box.x + 14, u_box.y + 58))
        surf.blit(self.fonts.mono.render(f"{u_brk[0]} ✖ {u_brk[1]} (Fiber Cut / Cable Severed)", True, C["red"]), (u_box.x + 14, u_box.y + 74))

        # Latency & TTL
        surf.blit(self.fonts.label.render("TOTAL TRANSIT LATENCY:", True, C["amber"]), (u_box.x + 14, u_box.y + 104))
        surf.blit(self.fonts.mono_lg.render(f"{self.user_cost} ms", True, C["text"]), (u_box.x + 14, u_box.y + 120))

        surf.blit(self.fonts.label.render("REMAINING TTL:", True, C["green"]), (u_box.x + 360, u_box.y + 104))
        surf.blit(self.fonts.mono_lg.render(f"{self.ttl} hops", True, C["green"]), (u_box.x + 360, u_box.y + 120))

        # Recipient Host
        surf.blit(self.fonts.label.render("RECIPIENT HOST:", True, self.contact["colour"]), (u_box.x + 14, u_box.y + 150))
        surf.blit(self.fonts.mono.render(f"{self.contact['name']} · Host IP: {self.contact['ip']} (Active)", True, C["text"]), (u_box.x + 14, u_box.y + 168))

        # Achievement Award Box
        score_box = pygame.Rect(mx + 30, my + 308, mw - 60, 75)
        draw_rect_rounded(surf, (18, 42, 32), score_box, radius=10, border=1, border_colour=C["green"])

        award_t = self.fonts.title_md.render("★ REROUTE SUCCESS: +250 PTS EARNED! ★", True, C["green"])
        award_d = self.fonts.body_sm.render("You adapted to dynamic topology failure and safely delivered the payload.", True, C["text"])
        surf.blit(award_t, (score_box.centerx - award_t.get_width() // 2, score_box.y + 14))
        surf.blit(award_d, (score_box.centerx - award_d.get_width() // 2, score_box.y + 44))

        # Buttons
        self.btn_replay.rect.x = mx + 60
        self.btn_replay.rect.y = my + 405
        self.btn_decap.rect.x  = mx + 240
        self.btn_decap.rect.y  = my + 405

        self.btn_replay.draw(surf)
        self.btn_decap.draw(surf)


# ---------------------------------------------------------------------------
# SCENE: LEVEL 6 — DESTINATION DECAPSULATION (REVERSE OSI)
# ---------------------------------------------------------------------------

class Level6Decapsulation:
    """
    Scene: Destination Host receives the sealed IPv4 datagram.
    User interactively decapsulates each layer in reverse order:
      Phase 0 (L3 Network): Inspect IPv4 Header, verify destination IP matches host,
                            click to strip L3 header.
      Phase 1 (L4 Transport): Inspect TCP Segment, verify Destination Port 443 & Checksum,
                              click to strip L4 header.
      Phase 2 (L7 Application): Message payload extracted and displayed in host chat,
                                user clicks to transmit TCP ACK back to sender.
    """
    def __init__(self, screen, fonts: Fonts, message: str, contact: dict, source_port: int,
                 user_cost: int, ttl: int):
        self.screen       = screen
        self.fonts        = fonts
        self.message      = message
        self.contact      = contact
        self.source_port  = source_port
        self.user_cost    = user_cost
        self.ttl          = ttl
        self.time_elapsed = 0.0

        # Phases: 0 = L3 IPv4, 1 = L4 TCP, 2 = L7 Payload
        self.phase = 0

        # Buttons
        self.btn_strip_l3 = Button(pygame.Rect(440, 640, 320, 50), "🔓 STRIP IPv4 HEADER (L3) ➜", fonts, primary=True)
        self.btn_strip_l4 = Button(pygame.Rect(440, 640, 320, 50), "🔓 STRIP TRANSPORT HEADER (L4) ➜", fonts, primary=True)
        self.btn_send_ack = Button(pygame.Rect(380, 640, 440, 50), "TRANSMIT TCP ACKNOWLEDGEMENT (ACK) ➜", fonts, primary=True)
        self.btn_reset    = Button(pygame.Rect(260, 640, 100, 50), "↺ Reset", fonts, primary=False)

        self.action_ack   = False
        self.action_reset = False

        self.particles = [Particle() for _ in range(25)]
        self.sparks    = []
        self._scan_surf = self._make_scanlines(1200, 750)

    def _make_scanlines(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(0, h, 4):
            pygame.draw.line(s, (0, 0, 0, 16), (0, y), (w, y))
        return s

    def _emit_sparks(self, cx, cy, col=None):
        for _ in range(35):
            angle = __import__('random').random() * math.tau
            speed = __import__('random').random() * 200.0 + 60.0
            self.sparks.append({
                "x": float(cx), "y": float(cy),
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "life": 1.3,
                "colour": col or __import__('random').choice([C["cyan"], C["green"], C["amber"], C["white"]])
            })

    def handle_event(self, event):
        pos = getattr(event, "pos", pygame.mouse.get_pos())

        if self.btn_reset.handle_event(event):
            self.phase = 0
            return

        if self.phase == 0:
            if self.btn_strip_l3.handle_event(event):
                self._emit_sparks(600, 380, C["cyan"])
                self.phase = 1
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if math.hypot(pos[0] - 600, pos[1] - 195) <= 32:
                    self._emit_sparks(600, 195, C["cyan"])
                    self.phase = 1

        elif self.phase == 1:
            if self.btn_strip_l4.handle_event(event):
                self._emit_sparks(600, 380, C["green"])
                self.phase = 2
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if math.hypot(pos[0] - 600, pos[1] - 250) <= 32:
                    self._emit_sparks(600, 250, C["green"])
                    self.phase = 2

        elif self.phase == 2:
            if self.btn_send_ack.handle_event(event):
                self.action_ack = True

    def update(self, dt):
        self.time_elapsed += dt
        for p in self.particles:
            p.update()

        for sp in self.sparks[:]:
            sp["x"] += sp["vx"] * dt
            sp["y"] += sp["vy"] * dt
            sp["life"] -= dt * 1.3
            if sp["life"] <= 0:
                self.sparks.remove(sp)

        if self.phase == 0:
            self.btn_strip_l3.update(dt)
        elif self.phase == 1:
            self.btn_strip_l4.update(dt)
        elif self.phase == 2:
            self.btn_send_ack.update(dt)
        self.btn_reset.update(dt)

    def draw(self):
        surf = self.screen
        W, H = surf.get_width(), surf.get_height()
        t = self.time_elapsed

        # Background
        surf.fill(C["bg"])

        for (cx, cy, col, rad) in [
            (int(W * 0.15), int(H * 0.20), C["blue"],   260),
            (int(W * 0.85), int(H * 0.25), self.contact["colour"], 280),
            (int(W * 0.50), int(H * 0.80), C["green"],  300),
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
        pygame.draw.rect(surf, self.contact["colour"], logo_r, border_radius=12)
        sym = self.fonts.hero.render("↯", True, C["black"])
        surf.blit(sym, (logo_r.centerx - sym.get_width() // 2,
                        logo_r.centery - sym.get_height() // 2))

        title = self.fonts.title_lg.render("PACKET PATH", True, C["text"])
        surf.blit(title, (88, 22))

        badge_r = pygame.Rect(W - 365, 14, 335, 42)
        draw_rect_rounded(surf, (16, 28, 48), badge_r, radius=10, border=1, border_colour=C["line"])
        lvl_lbl = self.fonts.label.render("CURRENT STAGE", True, C["muted"])
        lvl_txt = self.fonts.label_lg.render("06 / DECAPSULATION AT DESTINATION", True, C["green"])
        surf.blit(lvl_lbl, (badge_r.x + 14, badge_r.y + 6))
        surf.blit(lvl_txt, (badge_r.x + 14, badge_r.y + 22))

        # ── Pipeline Progress Indicator ──────────────────────────
        pipe_r = pygame.Rect(30, 82, W - 60, 48)
        draw_rect_rounded(surf, (12, 20, 34), pipe_r, radius=10, border=1, border_colour=C["line"])

        stages = [
            ("1. NETWORK LAYER (L3)", "IPv4 Header Stripping", self.phase >= 1, self.phase == 0),
            ("2. TRANSPORT LAYER (L4)", "TCP Segment Demultiplexing", self.phase >= 2, self.phase == 1),
            ("3. APPLICATION LAYER (L7)", "Payload Delivery to Recipient", self.phase == 2, self.phase == 2),
        ]
        sw = (pipe_r.w - 40) // 3
        for i, (s_name, s_sub, is_done, is_active) in enumerate(stages):
            sx = pipe_r.x + 15 + i * (sw + 8)
            s_rect = pygame.Rect(sx, pipe_r.y + 6, sw, 36)
            if is_active:
                draw_rect_rounded(surf, (20, 45, 65), s_rect, radius=6, border=1, border_colour=C["cyan"])
                c_lbl, c_sub = C["cyan"], C["text"]
            elif is_done:
                draw_rect_rounded(surf, (18, 40, 28), s_rect, radius=6, border=1, border_colour=C["green"])
                c_lbl, c_sub = C["green"], C["muted"]
            else:
                draw_rect_rounded(surf, (14, 22, 34), s_rect, radius=6, border=1, border_colour=C["line"])
                c_lbl, c_sub = C["muted"], (70, 95, 125)

            prefix = "✓ " if is_done else ("▶ " if is_active else "○ ")
            surf.blit(self.fonts.label.render(prefix + s_name, True, c_lbl), (s_rect.x + 10, s_rect.y + 3))
            surf.blit(self.fonts.mono_sm.render(s_sub, True, c_sub), (s_rect.x + 10, s_rect.y + 19))

        # ── Main Stage Area ──────────────────────────────────────
        if self.phase == 0:
            self._draw_phase_l3(surf, t)
        elif self.phase == 1:
            self._draw_phase_l4(surf, t)
        elif self.phase == 2:
            self._draw_phase_l7(surf, t)

        # Draw sparks
        for sp in self.sparks:
            r = int(max(2, sp["life"] * 5))
            pygame.draw.circle(surf, sp["colour"], (int(sp["x"]), int(sp["y"])), r)

        # ── Bottom Action Buttons ────────────────────────────────
        if self.phase == 0:
            self.btn_strip_l3.draw(surf)
        elif self.phase == 1:
            self.btn_strip_l4.draw(surf)
        elif self.phase == 2:
            self.btn_send_ack.draw(surf)
        self.btn_reset.draw(surf)

    def _draw_phase_l3(self, surf, t):
        cw, ch = 840, 470
        cx = (surf.get_width() - cw) // 2
        cy = 145
        card = pygame.Rect(cx, cy, cw, ch)

        draw_rect_rounded(surf, (14, 24, 38), card, radius=14, border=1, border_colour=C["cyan_dim"])

        # Cyber Seal
        seal_pulse = 0.5 + 0.5 * math.sin(t * 6)
        seal_glow = glow_surface(34, C["cyan"], alpha=int(40 * seal_pulse))
        surf.blit(seal_glow, (card.centerx - 34, cy + 22 - 34))
        pygame.draw.circle(surf, C["cyan"], (card.centerx, cy + 22), 22)
        pygame.draw.circle(surf, C["white"], (card.centerx, cy + 22), 22, width=2)
        s_lbl = self.fonts.label.render("✓L3", True, C["black"])
        surf.blit(s_lbl, (card.centerx - s_lbl.get_width() // 2, cy + 22 - s_lbl.get_height() // 2))

        # Title
        t_s = self.fonts.title_lg.render("SEALED IPv4 DATAGRAM RECEIVED AT DESTINATION", True, C["text"])
        surf.blit(t_s, (card.centerx - t_s.get_width() // 2, cy + 54))

        sub_s = self.fonts.body_sm.render(
            f"Physical Network Interface (NIC) at {self.contact['name']}'s host accepts incoming frame.",
            True, C["muted"]
        )
        surf.blit(sub_s, (card.centerx - sub_s.get_width() // 2, cy + 86))

        # Header Grid Card
        grid_r = pygame.Rect(cx + 40, cy + 118, cw - 80, 200)
        draw_rect_rounded(surf, (10, 18, 30), grid_r, radius=10, border=1, border_colour=C["line"])

        # Row 1: IP Header Fields
        cells = [
            ("Version", "4 (IPv4)", C["cyan"], 140),
            ("IHL / Length", "20 Bytes", C["text"], 140),
            ("Protocol", "6 (TCP)", C["violet"], 140),
            ("Hop Limit / TTL", f"{self.ttl} Hops Left", C["green"], 140),
            ("Header Checksum", "0x9F3B (Valid)", C["green"], 160),
        ]
        cur_x = grid_r.x + 16
        for lbl, val, col, w in cells:
            cell_box = pygame.Rect(cur_x, grid_r.y + 14, w, 56)
            draw_rect_rounded(surf, (14, 22, 34), cell_box, radius=6, border=1, border_colour=C["line"])
            surf.blit(self.fonts.label.render(lbl, True, C["muted"]), (cell_box.x + 8, cell_box.y + 6))
            surf.blit(self.fonts.mono.render(val, True, col), (cell_box.x + 8, cell_box.y + 26))
            cur_x += w + 10

        # Row 2: Source IP
        src_box = pygame.Rect(grid_r.x + 16, grid_r.y + 80, (grid_r.w - 42) // 2, 54)
        draw_rect_rounded(surf, (16, 28, 46), src_box, radius=6, border=1, border_colour=C["cyan_dim"])
        surf.blit(self.fonts.label.render("Source IP (Transmitting Host)", True, C["cyan"]), (src_box.x + 10, src_box.y + 6))
        surf.blit(self.fonts.mono_lg.render("192.168.1.10  (Client PC-01)", True, C["text"]), (src_box.x + 10, src_box.y + 24))

        # Row 3: Destination IP
        dst_box = pygame.Rect(grid_r.x + 26 + src_box.w, grid_r.y + 80, src_box.w, 54)
        draw_rect_rounded(surf, (18, 38, 32), dst_box, radius=6, border=1, border_colour=C["green"])
        surf.blit(self.fonts.label.render("Destination IP (Target Host Interface)", True, C["green"]), (dst_box.x + 10, dst_box.y + 6))
        surf.blit(self.fonts.mono_lg.render(f"{self.contact['ip']}  ({self.contact['name']} · MATCHED ✓)", True, C["green"]), (dst_box.x + 10, dst_box.y + 24))

        # Nested Payload Tray
        data_tray = pygame.Rect(grid_r.x + 16, grid_r.y + 144, grid_r.w - 32, 44)
        draw_rect_rounded(surf, (14, 24, 40), data_tray, radius=6, border=1, border_colour=C["cyan_dim"])
        surf.blit(self.fonts.label.render("ENCLOSED DATA PAYLOAD:", True, C["amber"]), (data_tray.x + 12, data_tray.y + 12))
        surf.blit(self.fonts.mono.render("Layer 4 TCP Segment Envelope (Locked inside)", True, C["text"]), (data_tray.x + 220, data_tray.y + 12))

        # Verification Box
        v_box = pygame.Rect(cx + 40, cy + 332, cw - 80, 80)
        draw_rect_rounded(surf, (18, 40, 30), v_box, radius=10, border=1, border_colour=C["green"])
        v_t = self.fonts.label_lg.render("✓ LAYER 3 VERIFICATION PASSED: DESTINATION IP MATCHES LOCAL INTERFACE", True, C["green"])
        v_d = self.fonts.body_sm.render(
            f"The incoming packet's IP destination matches this machine's IP ({self.contact['ip']}). "
            "The network stack now strips the IPv4 header and passes the payload to Layer 4 (Transport).",
            True, C["text"]
        )
        surf.blit(v_t, (v_box.x + 14, v_box.y + 14))
        surf.blit(v_d, (v_box.x + 14, v_box.y + 38))

    def _draw_phase_l4(self, surf, t):
        cw, ch = 840, 470
        cx = (surf.get_width() - cw) // 2
        cy = 145
        card = pygame.Rect(cx, cy, cw, ch)

        draw_rect_rounded(surf, (14, 24, 38), card, radius=14, border=1, border_colour=C["green"])

        # Cyber Seal L4
        seal_pulse = 0.5 + 0.5 * math.sin(t * 6)
        seal_glow = glow_surface(34, C["green"], alpha=int(45 * seal_pulse))
        surf.blit(seal_glow, (card.centerx - 34, cy + 22 - 34))
        pygame.draw.circle(surf, C["amber"], (card.centerx, cy + 22), 22)
        pygame.draw.circle(surf, C["white"], (card.centerx, cy + 22), 22, width=2)
        s_lbl = self.fonts.label.render("✓L4", True, C["black"])
        surf.blit(s_lbl, (card.centerx - s_lbl.get_width() // 2, cy + 22 - s_lbl.get_height() // 2))

        # Title
        t_s = self.fonts.title_lg.render("LAYER 4: TCP TRANSPORT SEGMENT DEMULTIPLEXING", True, C["text"])
        surf.blit(t_s, (card.centerx - t_s.get_width() // 2, cy + 54))

        sub_s = self.fonts.body_sm.render(
            "Operating system inspects the Transport header to identify the target application port.",
            True, C["muted"]
        )
        surf.blit(sub_s, (card.centerx - sub_s.get_width() // 2, cy + 86))

        # Transport Chips Display
        chips_r = pygame.Rect(cx + 40, cy + 118, cw - 80, 200)
        draw_rect_rounded(surf, (10, 18, 30), chips_r, radius=10, border=1, border_colour=C["line"])

        # Chip 1: Source Port
        c1 = pygame.Rect(chips_r.x + 18, chips_r.y + 20, 220, 85)
        draw_rect_rounded(surf, (16, 28, 48), c1, radius=8, border=1, border_colour=C["cyan"])
        surf.blit(self.fonts.label.render("SOURCE PORT (CLIENT)", True, C["cyan"]), (c1.x + 12, c1.y + 10))
        surf.blit(self.fonts.mono_lg.render(str(self.source_port), True, C["text"]), (c1.x + 12, c1.y + 32))
        surf.blit(self.fonts.mono_sm.render("Ephemeral OS Socket", True, C["muted"]), (c1.x + 12, c1.y + 58))

        # Chip 2: Dest Port 443
        c2 = pygame.Rect(chips_r.x + 258, chips_r.y + 20, 220, 85)
        draw_rect_rounded(surf, (18, 42, 32), c2, radius=8, border=1, border_colour=C["green"])
        surf.blit(self.fonts.label.render("DEST PORT (APPLICATION)", True, C["green"]), (c2.x + 12, c2.y + 10))
        surf.blit(self.fonts.mono_lg.render("443 (HTTPS / TLS)", True, C["green"]), (c2.x + 12, c2.y + 32))
        surf.blit(self.fonts.mono_sm.render("Matched Active Listening Daemon ✓", True, C["muted"]), (c2.x + 12, c2.y + 58))

        # Chip 3: Checksum
        c3 = pygame.Rect(chips_r.x + 498, chips_r.y + 20, 240, 85)
        draw_rect_rounded(surf, (18, 38, 48), c3, radius=8, border=1, border_colour=C["cyan_dim"])
        surf.blit(self.fonts.label.render("HEADER & DATA CHECKSUM", True, C["amber"]), (c3.x + 12, c3.y + 10))
        surf.blit(self.fonts.mono_lg.render("0x7A4F (VALID ✓)", True, C["green"]), (c3.x + 12, c3.y + 32))
        surf.blit(self.fonts.mono_sm.render("Zero Bit Corruption Detected", True, C["muted"]), (c3.x + 12, c3.y + 58))

        # Enclosed Raw Application Data Strip
        raw_box = pygame.Rect(chips_r.x + 18, chips_r.y + 125, chips_r.w - 36, 55)
        draw_rect_rounded(surf, (16, 24, 38), raw_box, radius=8, border=1, border_colour=C["cyan_dim"])
        surf.blit(self.fonts.label.render("ENCLOSED APPLICATION PAYLOAD:", True, C["cyan"]), (raw_box.x + 14, raw_box.y + 10))
        surf.blit(self.fonts.mono.render(f"Encrypted TLS Record ({len(self.message)} Bytes payload)", True, C["text"]), (raw_box.x + 14, raw_box.y + 28))

        # Verification Box
        v_box = pygame.Rect(cx + 40, cy + 332, cw - 80, 80)
        draw_rect_rounded(surf, (18, 40, 30), v_box, radius=10, border=1, border_colour=C["green"])
        v_t = self.fonts.label_lg.render("✓ LAYER 4 VERIFICATION PASSED: PORT DEMULTIPLEXED & CHECKSUM VERIFIED", True, C["green"])
        v_d = self.fonts.body_sm.render(
            "The destination port 443 routes directly to the active web socket daemon. "
            "Integrity checksum passed without packet corruption. Ready to extract application data.",
            True, C["text"]
        )
        surf.blit(v_t, (v_box.x + 14, v_box.y + 14))
        surf.blit(v_d, (v_box.x + 14, v_box.y + 38))

    def _draw_phase_l7(self, surf, t):
        cw, ch = 840, 470
        cx = (surf.get_width() - cw) // 2
        cy = 145
        card = pygame.Rect(cx, cy, cw, ch)

        draw_rect_rounded(surf, (14, 24, 38), card, radius=14, border=1, border_colour=self.contact["colour"])

        # Header Title
        t_s = self.fonts.title_lg.render(f"APPLICATION LAYER (L7) · DELIVERED TO {self.contact['name'].upper()}", True, C["text"])
        surf.blit(t_s, (card.centerx - t_s.get_width() // 2, cy + 24))

        sub_s = self.fonts.body_sm.render(
            f"The message has traveled through all network layers and arrived on {self.contact['name']}'s host terminal.",
            True, C["muted"]
        )
        surf.blit(sub_s, (card.centerx - sub_s.get_width() // 2, cy + 54))

        # Terminal / Chat Window
        term_r = pygame.Rect(cx + 50, cy + 86, cw - 100, 225)
        draw_rect_rounded(surf, (10, 16, 26), term_r, radius=12, border=1, border_colour=C["line"])

        # Terminal Top Bar
        bar_r = pygame.Rect(term_r.x, term_r.y, term_r.w, 34)
        draw_gradient_rect(surf, bar_r, (18, 28, 44), (12, 18, 30), radius=12)
        pygame.draw.circle(surf, (255, 95, 86), (bar_r.x + 16, bar_r.centery), 5)
        pygame.draw.circle(surf, (255, 189, 46), (bar_r.x + 32, bar_r.centery), 5)
        pygame.draw.circle(surf, (39, 201, 63), (bar_r.x + 48, bar_r.centery), 5)

        term_title = self.fonts.mono_sm.render(f"session: 192.168.1.10:{self.source_port} ➜ {self.contact['ip']}:443 [HTTPS]", True, C["muted"])
        surf.blit(term_title, (bar_r.x + 70, bar_r.y + 8))

        # Avatar & Chat Bubble
        av_r = pygame.Rect(term_r.x + 24, term_r.y + 54, 46, 46)
        pygame.draw.rect(surf, self.contact["colour"], av_r, border_radius=12)
        av_txt = self.fonts.title_md.render(self.contact["avatar"], True, C["black"])
        surf.blit(av_txt, (av_r.centerx - av_txt.get_width() // 2, av_r.centery - av_txt.get_height() // 2))

        # Recipient Name & Status
        surf.blit(self.fonts.label_lg.render(f"{self.contact['name']} (Recipient Host)", True, self.contact["colour"]), (term_r.x + 82, term_r.y + 52))
        surf.blit(self.fonts.mono_sm.render("● Online · Decapsulation Complete", True, C["green"]), (term_r.x + 82, term_r.y + 72))

        # Message Bubble
        msg_bubble = pygame.Rect(term_r.x + 82, term_r.y + 98, term_r.w - 110, 80)
        draw_rect_rounded(surf, (20, 36, 56), msg_bubble, radius=10, border=1, border_colour=C["cyan_dim"])

        surf.blit(self.fonts.mono_sm.render("EXTRACTED PAYLOAD CONTENT:", True, C["muted"]), (msg_bubble.x + 14, msg_bubble.y + 10))
        disp_m = f'"{self.message}"' if len(self.message) <= 65 else f'"{self.message[:62]}…"'
        surf.blit(self.fonts.title_md.render(disp_m, True, C["white"]), (g_bubble.x + 14, msg_bubble.y + 32))

        # Telemetry Pill
        tele_txt = self.fonts.mono_sm.render(f"Size: {len(self.message)} Bytes · Protocol: TLS/HTTPS · Checksum: 0x7A4F (OK)", True, C["green"])
        surf.blit(tele_txt, (msg_bubble.x + 14, msg_bubble.y + 60))

        # Decapsulation Complete Banner
        sum_box = pygame.Rect(cx + 50, cy + 325, cw - 100, 86)
        draw_rect_rounded(surf, (18, 42, 32), sum_box, radius=10, border=1, border_colour=C["green"])

        t_lbl = self.fonts.title_md.render("★ ALL OSI LAYERS SUCCESSFULLY DECAPSULATED! ★", True, C["green"])
        d_lbl = self.fonts.body_sm.render(
            "The message payload was verified and delivered. "
            "Reliable TCP transmission protocol requires returning an Acknowledgement (ACK) along the user's route.",
            True, C["text"]
        )
        surf.blit(t_lbl, (sum_box.centerx - t_lbl.get_width() // 2, sum_box.y + 14))
        surf.blit(d_lbl, (sum_box.centerx - d_lbl.get_width() // 2, sum_box.y + 46))


# ---------------------------------------------------------------------------
# SCENE: LEVEL 7 — ACKNOWLEDGEMENT RETURN ROUTE & CONNECTION ESTABLISHED
# ---------------------------------------------------------------------------

class Level7AckReturn:
    """
    Scene: The ACK packet travels backwards along the exact same route chosen by the user!
    Once the ACK packet reaches the source host (PC-01), the prompt:
        "Connection Established"
    is displayed with celebration particles, transmission telemetry, and final score.
    """
    def __init__(self, screen, fonts: Fonts, message: str, contact: dict, source_port: int,
                 path_l4: list, path_l5: list, cost_l4: int, cost_l5: int, total_score: int):
        self.screen       = screen
        self.fonts        = fonts
        self.message      = message
        self.contact      = contact
        self.source_port  = source_port
        self.path_l4      = list(path_l4)
        self.path_l5      = list(path_l5)
        self.cost_l4      = cost_l4
        self.cost_l5      = cost_l5
        self.total_score  = total_score

        self.time_elapsed = 0.0

        # Full forward path taken by user:
        # e.g. path_l4 = ['R1', 'R2', 'R4', 'R6', 'ISP']
        #      path_l5 = ['ISP', 'B1', 'B4', 'B6', 'R_DEST']
        self.forward_path = self.path_l4 + self.path_l5[1:]
        
        # Reverse path for ACK:
        # ['R_DEST', 'B6', 'B4', 'B1', 'ISP', 'R6', 'R4', 'R2', 'R1']
        self.reverse_path = list(reversed(self.forward_path))

        # Build visual node sequence
        # Top tier: Destination Host ➜ R_DEST ➜ ... ➜ ISP
        # Bottom tier: ISP ➜ ... ➜ R1 ➜ PC-01 Source Host
        self.nodes, self.node_coords = self._build_layout()
        self.num_legs = len(self.node_coords) - 1

        # Hop progress tracking
        self.current_leg  = 0
        self.leg_progress = 0.0      # 0.0 to 1.0 along current leg
        self.leg_duration = 0.85     # seconds per leg
        self.arrived      = False

        # Completion prompt buttons
        self.btn_replay  = Button(pygame.Rect(410, 580, 160, 48), "↺ Replay ACK", fonts, primary=False)
        self.btn_compose = Button(pygame.Rect(590, 580, 220, 48), "✉ New Message",  fonts, primary=True)
        self.action_replay  = False
        self.action_compose = False

        self.particles = [Particle() for _ in range(25)]
        self.celebrate_sparks = []
        self.trail_sparks     = []
        self._scan_surf = self._make_scanlines(1200, 750)

    def _make_scanlines(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(0, h, 4):
            pygame.draw.line(s, (0, 0, 0, 16), (0, y), (w, y))
        return s

    def _build_layout(self):
        # We find ISP in reverse path
        isp_idx = self.reverse_path.index("ISP")
        backbone_nodes = self.reverse_path[:isp_idx + 1]  # from R_DEST to ISP
        local_nodes    = self.reverse_path[isp_idx:]      # from ISP to R1

        # Complete sequence with terminal hosts
        # Bottom: local_nodes ➜ [Host (PC-01)]
        top_list    = [f"Host ({self.contact['name']})"] + backbone_nodes
        bottom_list = local_nodes + ["Host (PC-01)"]

        coords = []
        node_dicts = []

        # Top tier coordinates: from right (x=1080) to left (x=120) at y=250
        n_top = len(top_list)
        for i, name in enumerate(top_list):
            if n_top > 1:
                x = int(1080 - i * (960 / (n_top - 1)))
            else:
                x = 600
            y = 250
            coords.append((x, y))
            node_dicts.append({"name": name, "pos": (x, y), "tier": "top"})

        # Vertical conduit: top ISP to bottom ISP
        # Bottom tier coordinates: from left (x=120) to right (x=1080) at y=480
        n_bot = len(bottom_list)
        for i, name in enumerate(bottom_list):
            if i == 0:
                # This is bottom ISP
                x = 120
            else:
                x = int(120 + i * (960 / (n_bot - 1)))
            y = 480
            coords.append((x, y))
            node_dicts.append({"name": name, "pos": (x, y), "tier": "bottom"})

        return node_dicts, coords

    def handle_event(self, event):
        if self.arrived:
            if self.btn_replay.handle_event(event):
                self.action_replay = True
            if self.btn_compose.handle_event(event):
                self.action_compose = True

    def update(self, dt):
        self.time_elapsed += dt
        for p in self.particles:
            p.update()

        # Update ACK packet traversal
        if not self.arrived:
            self.leg_progress += dt / self.leg_duration
            if self.leg_progress >= 1.0:
                self.leg_progress = 0.0
                self.current_leg += 1

                # Check if arrived at end
                if self.current_leg >= self.num_legs:
                    self.arrived = True
                    # Fireworks
                    end_pos = self.node_coords[-1]
                    for _ in range(60):
                        angle = __import__('random').random() * math.tau
                        speed = __import__('random').random() * 260.0 + 80.0
                        self.celebrate_sparks.append({
                            "x": float(end_pos[0]), "y": float(end_pos[1]),
                            "vx": math.cos(angle) * speed,
                            "vy": math.sin(angle) * speed,
                            "life": 1.6,
                            "colour": __import__('random').choice([C["green"], C["cyan"], C["amber"], C["white"]])
                        })
                else:
                    # Leg hop burst
                    hop_pos = self.node_coords[self.current_leg]
                    for _ in range(12):
                        angle = __import__('random').random() * math.tau
                        speed = __import__('random').random() * 120.0 + 30.0
                        self.trail_sparks.append({
                            "x": float(hop_pos[0]), "y": float(hop_pos[1]),
                            "vx": math.cos(angle) * speed,
                            "vy": math.sin(angle) * speed,
                            "life": 0.8,
                            "colour": C["amber"]
                        })

        # Update sparks
        for sp in self.celebrate_sparks[:]:
            sp["x"] += sp["vx"] * dt
            sp["y"] += sp["vy"] * dt
            sp["life"] -= dt * 1.2
            if sp["life"] <= 0:
                self.celebrate_sparks.remove(sp)

        for sp in self.trail_sparks[:]:
            sp["x"] += sp["vx"] * dt
            sp["y"] += sp["vy"] * dt
            sp["life"] -= dt * 2.0
            if sp["life"] <= 0:
                self.trail_sparks.remove(sp)

        if self.arrived:
            self.btn_replay.update(dt)
            self.btn_compose.update(dt)

    def draw(self):
        surf = self.screen
        W, H = surf.get_width(), surf.get_height()
        t = self.time_elapsed

        # Background
        surf.fill(C["bg"])

        for (cx, cy, col, rad) in [
            (int(W * 0.85), int(H * 0.30), self.contact["colour"], 260),
            (int(W * 0.15), int(H * 0.50), C["amber"],  260),
            (int(W * 0.85), int(H * 0.65), C["cyan"],   280),
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
        pygame.draw.rect(surf, C["amber"], logo_r, border_radius=12)
        sym = self.fonts.hero.render("↯", True, C["black"])
        surf.blit(sym, (logo_r.centerx - sym.get_width() // 2,
                        logo_r.centery - sym.get_height() // 2))

        title = self.fonts.title_lg.render("PACKET PATH", True, C["text"])
        surf.blit(title, (88, 22))

        badge_r = pygame.Rect(W - 380, 14, 350, 42)
        draw_rect_rounded(surf, (16, 28, 48), badge_r, radius=10, border=1, border_colour=C["line"])
        lvl_lbl = self.fonts.label.render("CURRENT STAGE", True, C["muted"])
        lvl_txt = self.fonts.label_lg.render("07 / ACKNOWLEDGEMENT (ACK) RETURN ROUTE", True, C["amber"])
        surf.blit(lvl_lbl, (badge_r.x + 14, badge_r.y + 6))
        surf.blit(lvl_txt, (badge_r.x + 14, badge_r.y + 22))

        # ── HUD Banner ───────────────────────────────────────────
        hud_r = pygame.Rect(30, 85, W - 60, 52)
        draw_rect_rounded(surf, C["panel"], hud_r, radius=10, border=1, border_colour=C["line"])

        # Retraced Path
        cur_from = self.nodes[self.current_leg]["name"] if not self.arrived else self.nodes[-2]["name"]
        cur_to   = self.nodes[min(len(self.nodes)-1, self.current_leg + 1)]["name"] if not self.arrived else self.nodes[-1]["name"]

        surf.blit(self.fonts.label.render("CURRENT ACK HOP:", True, C["muted"]), (hud_r.x + 14, hud_r.y + 8))
        surf.blit(self.fonts.mono.render(f"{cur_from} ➜ {cur_to}", True, C["amber"]), (hud_r.x + 14, hud_r.y + 26))

        surf.blit(self.fonts.label.render("TCP PACKET TYPE:", True, C["muted"]), (hud_r.x + 360, hud_r.y + 8))
        surf.blit(self.fonts.mono.render("TCP ACK (Flags: ACK=1, SYN=0)", True, C["green"]), (hud_r.x + 360, hud_r.y + 26))

        surf.blit(self.fonts.label.render("ROUND TRIP LATENCY:", True, C["muted"]), (hud_r.x + 680, hud_r.y + 8))
        surf.blit(self.fonts.mono_lg.render(f"{2 * (self.cost_l4 + self.cost_l5)} ms (RTT)", True, C["text"]), (hud_r.x + 680, hud_r.y + 26))

        surf.blit(self.fonts.label.render("ROUTE STATUS:", True, C["muted"]), (hud_r.x + 900, hud_r.y + 8))
        status_s = "ACK DELIVERED ✓" if self.arrived else "RETRACING USER ROUTE..."
        surf.blit(self.fonts.mono.render(status_s, True, C["green"] if self.arrived else C["cyan"]), (hud_r.x + 900, hud_r.y + 26))

        # Tier Labels
        top_lbl = self.fonts.label.render("▲ TRANSIT BACKBONE ROUTE (RETURN LEG) ▲", True, (75, 105, 140))
        surf.blit(top_lbl, (W // 2 - top_lbl.get_width() // 2, 160))

        bot_lbl = self.fonts.label.render("▼ LOCAL ACCESS NETWORK ROUTE (DELIVERY LEG) ▼", True, (75, 105, 140))
        surf.blit(bot_lbl, (W // 2 - bot_lbl.get_width() // 2, 385))

        # ── Draw Circuit Links ───────────────────────────────────
        for i in range(self.num_legs):
            p1 = self.node_coords[i]
            p2 = self.node_coords[i+1]
            is_done = (i < self.current_leg)
            is_cur  = (i == self.current_leg and not self.arrived)

            if is_done:
                edge_col = C["amber"]
                pygame.draw.line(surf, edge_col, p1, p2, 4)
                # Static flow dots
                for frac in [0.25, 0.5, 0.75]:
                    dot_x = p1[0] + (p2[0] - p1[0]) * frac
                    dot_y = p1[1] + (p2[1] - p1[1]) * frac
                    pygame.draw.circle(surf, C["white"], (int(dot_x), int(dot_y)), 2)
            elif is_cur:
                edge_col = C["cyan"]
                pygame.draw.line(surf, (30, 50, 75), p1, p2, 2)
                # Animated current beam
                end_x = p1[0] + (p2[0] - p1[0]) * self.leg_progress
                end_y = p1[1] + (p2[1] - p1[1]) * self.leg_progress
                pygame.draw.line(surf, edge_col, p1, (int(end_x), int(end_y)), 4)
            else:
                pygame.draw.line(surf, (25, 40, 60), p1, p2, 2)

        # ── Draw Nodes ───────────────────────────────────────────
        for i, (node, (nx, ny)) in enumerate(zip(self.nodes, self.node_coords)):
            is_active   = (i <= self.current_leg or self.arrived)
            is_cur_head = (i == self.current_leg and not self.arrived)

            radius = 32
            if "Host" in node["name"]:
                radius = 36
                node_bg = (18, 38, 56) if is_active else (12, 18, 28)
                node_bdr = C["cyan"] if is_active else C["line"]
            elif node["name"] == "ISP":
                radius = 34
                node_bg = (38, 32, 16) if is_active else (14, 20, 30)
                node_bdr = C["amber"] if is_active else C["line"]
            else:
                node_bg = (18, 32, 48) if is_active else (12, 18, 28)
                node_bdr = C["amber"] if is_active else C["line"]

            if is_cur_head:
                pulse = 0.5 + 0.5 * math.sin(t * 8)
                glow = glow_surface(radius + 16, C["amber"], alpha=int(60 * pulse))
                surf.blit(glow, (nx - radius - 16, ny - radius - 16))

            pygame.draw.circle(surf, node_bg, (nx, ny), radius)
            pygame.draw.circle(surf, node_bdr, (nx, ny), radius, width=2)

            # Node label
            name_s = self.fonts.label.render(node["name"].split(" ")[0], True, C["text"] if is_active else C["muted"])
            surf.blit(name_s, (nx - name_s.get_width() // 2, ny - 6))

            sub_txt = "✓" if is_active else "○"
            sub_s = self.fonts.mono_sm.render(sub_txt, True, C["green"] if is_active else C["muted"])
            surf.blit(sub_s, (nx - sub_s.get_width() // 2, ny + 8))

            # Full label below
            full_s = self.fonts.body_sm.render(node["name"], True, C["muted"])
            surf.blit(full_s, (nx - full_s.get_width() // 2, ny + radius + 4))

        # ── Draw Traveling ACK Packet ────────────────────────────
        if not self.arrived and self.current_leg < self.num_legs:
            p1 = self.node_coords[self.current_leg]
            p2 = self.node_coords[self.current_leg + 1]
            px = p1[0] + (p2[0] - p1[0]) * self.leg_progress
            py = p1[1] + (p2[1] - p1[1]) * self.leg_progress

            # Glow halo
            pkt_glow = glow_surface(32, C["amber"], alpha=95)
            surf.blit(pkt_glow, (int(px - 32), int(py - 32)))

            pygame.draw.circle(surf, C["white"], (int(px), int(py)), 10)
            pygame.draw.circle(surf, C["amber"], (int(px), int(py)), 13, width=2)

            # Floating Tag
            tag_r = pygame.Rect(int(px - 44), int(py - 32), 88, 20)
            draw_rect_rounded(surf, (20, 32, 48), tag_r, radius=5, border=1, border_colour=C["amber"])
            tag_txt = self.fonts.mono_sm.render("TCP ACK", True, C["amber"])
            surf.blit(tag_txt, (tag_r.centerx - tag_txt.get_width() // 2, tag_r.centery - tag_txt.get_height() // 2))

        # Draw sparks
        for sp in self.celebrate_sparks:
            r = int(max(2, sp["life"] * 5))
            pygame.draw.circle(surf, sp["colour"], (int(sp["x"]), int(sp["y"])), r)

        for sp in self.trail_sparks:
            r = int(max(1, sp["life"] * 4))
            pygame.draw.circle(surf, sp["colour"], (int(sp["x"]), int(sp["y"])), r)

        # ── Prompt: Connection Established ───────────────────────
        if self.arrived:
            self._draw_connection_established_prompt(surf)

    def _draw_connection_established_prompt(self, surf):
        W, H = surf.get_width(), surf.get_height()

        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surf.blit(overlay, (0, 0))

        mw, mh = 700, 490
        mx = (W - mw) // 2
        my = (H - mh) // 2
        card_r = pygame.Rect(mx, my, mw, mh)

        draw_rect_rounded(surf, (14, 25, 42), card_r, radius=16, border=2, border_colour=C["green"])
        glow = glow_surface(mw // 2 + 20, C["green"], alpha=40)
        surf.blit(glow, (card_r.centerx - mw // 2 - 20, card_r.centery - mw // 2 - 20))

        # Main prompt heading: "Connection Established"
        m_title = self.fonts.title_xl.render("Connection Established", True, C["green"])
        surf.blit(m_title, (card_r.centerx - m_title.get_width() // 2, my + 24))

        m_sub = self.fonts.body_sm.render(
            "TCP 3-Way Handshake Confirmed · Full Bidirectional Transmission Complete",
            True, C["cyan"]
        )
        surf.blit(m_sub, (card_r.centerx - m_sub.get_width() // 2, my + 64))

        # Details Box
        u_box = pygame.Rect(mx + 30, my + 96, mw - 60, 260)
        draw_rect_rounded(surf, (10, 18, 30), u_box, radius=10, border=1, border_colour=C["line"])

        # 1. Delivered Message
        surf.blit(self.fonts.label.render("DELIVERED PAYLOAD:", True, C["muted"]), (u_box.x + 14, u_box.y + 12))
        disp_m = f'"{self.message}"' if len(self.message) <= 75 else f'"{self.message[:72]}…"'
        surf.blit(self.fonts.mono.render(disp_m, True, C["white"]), (u_box.x + 14, u_box.y + 28))

        # 2. Recipient
        surf.blit(self.fonts.label.render("RECIPIENT HOST:", True, self.contact["colour"]), (u_box.x + 14, u_box.y + 58))
        surf.blit(self.fonts.mono.render(f"{self.contact['name']} ({self.contact['ip']}) · Port 443 [HTTPS]", True, C["text"]), (u_box.x + 14, u_box.y + 74))

        # 3. Forward Route
        surf.blit(self.fonts.label.render("FORWARD DATA PATH:", True, C["cyan"]), (u_box.x + 14, u_box.y + 104))
        surf.blit(self.fonts.mono_sm.render(" ➜ ".join(self.forward_path), True, C["cyan"]), (u_box.x + 14, u_box.y + 120))

        # 4. ACK Return Route
        surf.blit(self.fonts.label.render("ACK RETRACED RETURN PATH (EXACT SAME ROUTE):", True, C["amber"]), (u_box.x + 14, u_box.y + 148))
        surf.blit(self.fonts.mono_sm.render(" ➜ ".join(self.reverse_path), True, C["amber"]), (u_box.x + 14, u_box.y + 164))

        # 5. Round Trip Time (RTT) & Total Score
        rtt = 2 * (self.cost_l4 + self.cost_l5)
        surf.blit(self.fonts.label.render("TOTAL ROUND TRIP TIME (RTT):", True, C["muted"]), (u_box.x + 14, u_box.y + 196))
        surf.blit(self.fonts.mono_lg.render(f"{rtt} ms", True, C["text"]), (u_box.x + 14, u_box.y + 214))

        surf.blit(self.fonts.label.render("FINAL CUMULATIVE SCORE:", True, C["green"]), (u_box.x + 360, u_box.y + 196))
        surf.blit(self.fonts.title_md.render(f"{self.total_score} PTS", True, C["green"]), (u_box.x + 360, u_box.y + 214))

        # Celebration summary badge
        badge_box = pygame.Rect(mx + 30, my + 370, mw - 60, 52)
        draw_rect_rounded(surf, (18, 42, 32), badge_box, radius=8, border=1, border_colour=C["green"])
        b_txt = self.fonts.label_lg.render("★ END-TO-END TRANSMISSION VERIFIED: DATA + ACK SUCCESSFUL! ★", True, C["green"])
        surf.blit(b_txt, (badge_box.centerx - b_txt.get_width() // 2, badge_box.y + 16))

        # Buttons
        self.btn_replay.rect.x = mx + 140
        self.btn_replay.rect.y = my + 434
        self.btn_compose.rect.x = mx + 320
        self.btn_compose.rect.y = my + 434

        self.btn_replay.draw(surf)
        self.btn_compose.draw(surf)


# ---------------------------------------------------------------------------
# MAIN GAME  — state machine
# ---------------------------------------------------------------------------

class Game:
    STATE_COMPOSE       = "compose"
    STATE_OS_PORTS      = "os_ports"
    STATE_HANDSHAKE     = "handshake"    # NEW — TCP/UDP handshake scene
    STATE_INSIDE_OS     = "inside_os"
    STATE_IP_ENCAP      = "ip_encap"
    STATE_FRAGMENT      = "fragment"     # NEW — IPv4 fragmentation scene
    STATE_ROUTING       = "routing"
    STATE_DEST_ROUTING  = "dest_routing"
    STATE_DECAPSULATION = "decapsulation"
    STATE_ACK_RETURN    = "ack_return"

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

        # Cumulative Points & Routes
        self.total_score = 0
        self.path_l4     = []
        self.path_l5     = []
        self.cost_l4     = 0
        self.cost_l5     = 0

        # Scenes
        self.compose       = Level1Compose(self.screen, self.fonts, self.clock)
        self.os_ports      = None
        self.handshake     = None        # NEW
        self.inside_os     = None
        self.ip_encap      = None
        self.fragmentation = None
        self.routing       = None
        self.dest_routing  = None
        self.decapsulation = None
        self.ack_return    = None
        self.protocol      = "TCP"       # chosen in handshake scene

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
        elif self.state == self.STATE_HANDSHAKE:
            if self.handshake:
                self.handshake.handle_event(event)
        elif self.state == self.STATE_INSIDE_OS:
            if self.inside_os:
                self.inside_os.handle_event(event)
        elif self.state == self.STATE_IP_ENCAP:
            if self.ip_encap:
                self.ip_encap.handle_event(event)
        elif self.state == self.STATE_FRAGMENT:
            if self.fragmentation:
                self.fragmentation.handle_event(event)
        elif self.state == self.STATE_ROUTING:
            if self.routing:
                self.routing.handle_event(event)
        elif self.state == self.STATE_DEST_ROUTING:
            if self.dest_routing:
                self.dest_routing.handle_event(event)
        elif self.state == self.STATE_DECAPSULATION:
            if self.decapsulation:
                self.decapsulation.handle_event(event)
        elif self.state == self.STATE_ACK_RETURN:
            if self.ack_return:
                self.ack_return.handle_event(event)

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
            if self.os_ports.proceed:
                # ── Go to Handshake scene first ──────────────────────
                self.handshake = LevelL4Handshake(
                    self.screen, self.fonts,
                    self.message, self.contact,
                    self.os_ports.source_port
                )
                self.state = self.STATE_HANDSHAKE

        elif self.state == self.STATE_HANDSHAKE:
            self.handshake.update(dt)
            if self.handshake.action_next:
                self.protocol  = self.handshake.protocol or "TCP"
                self.inside_os = LevelInsideOS(
                    self.screen, self.fonts,
                    self.message, self.contact,
                    self.os_ports.source_port
                )
                self.state = self.STATE_INSIDE_OS

        elif self.state == self.STATE_INSIDE_OS:
            self.inside_os.update(dt)
            if self.inside_os.action_replay:
                self.inside_os = LevelInsideOS(
                    self.screen, self.fonts,
                    self.message, self.contact,
                    self.os_ports.source_port
                )
            elif self.inside_os.action_next:
                self.ip_encap = Level3IPEncapsulation(
                    self.screen, self.fonts,
                    self.message, self.contact,
                    self.os_ports.source_port
                )
                self.state = self.STATE_IP_ENCAP

        elif self.state == self.STATE_IP_ENCAP:
            self.ip_encap.update(dt)
            if self.ip_encap.action_replay:
                self.ip_encap = Level3IPEncapsulation(
                    self.screen, self.fonts,
                    self.message, self.contact,
                    self.os_ports.source_port
                )
            elif self.ip_encap.action_routing:
                # ── Go to Fragmentation scene first ──────────────────────────
                self.fragmentation = LevelFragmentation(
                    self.screen, self.fonts,
                    self.message, self.contact,
                    self.os_ports.source_port
                )
                self.state = self.STATE_FRAGMENT

        elif self.state == self.STATE_FRAGMENT:
            self.fragmentation.update(dt)
            if self.fragmentation.action_replay:
                self.fragmentation = LevelFragmentation(
                    self.screen, self.fonts,
                    self.message, self.contact,
                    self.os_ports.source_port
                )
            elif self.fragmentation.action_proceed:
                self.routing = Level4Routing(
                    self.screen, self.fonts,
                    self.message, self.contact
                )
                self.state = self.STATE_ROUTING

        elif self.state == self.STATE_ROUTING:
            self.routing.update(dt)
            if self.routing.action_replay:
                self.routing = Level4Routing(
                    self.screen, self.fonts,
                    self.message, self.contact
                )
            elif self.routing.action_next_route:
                self.path_l4 = list(self.routing.user_path)
                self.cost_l4 = self.routing.user_cost
                self.total_score += self.routing.score_points
                self.dest_routing = Level5DestRouting(
                    self.screen, self.fonts,
                    self.message, self.contact
                )
                self.state = self.STATE_DEST_ROUTING

        elif self.state == self.STATE_DEST_ROUTING:
            self.dest_routing.update(dt)
            if self.dest_routing.action_replay:
                self.dest_routing = Level5DestRouting(
                    self.screen, self.fonts,
                    self.message, self.contact
                )
            elif self.dest_routing.action_decap:
                self.path_l5 = list(self.dest_routing.user_path)
                self.cost_l5 = self.dest_routing.user_cost
                self.total_score += self.dest_routing.score_points
                self.decapsulation = Level6Decapsulation(
                    self.screen, self.fonts,
                    self.message, self.contact,
                    self.os_ports.source_port if self.os_ports else 52143,
                    self.cost_l4 + self.cost_l5,
                    self.dest_routing.ttl
                )
                self.state = self.STATE_DECAPSULATION

        elif self.state == self.STATE_DECAPSULATION:
            self.decapsulation.update(dt)
            if self.decapsulation.action_reset:
                self.decapsulation.phase = 0
            elif self.decapsulation.action_ack:
                self.ack_return = Level7AckReturn(
                    self.screen, self.fonts,
                    self.message, self.contact,
                    self.os_ports.source_port if self.os_ports else 52143,
                    self.path_l4, self.path_l5,
                    self.cost_l4, self.cost_l5,
                    self.total_score
                )
                self.state = self.STATE_ACK_RETURN

        elif self.state == self.STATE_ACK_RETURN:
            self.ack_return.update(dt)
            if self.ack_return.action_replay:
                self.ack_return = Level7AckReturn(
                    self.screen, self.fonts,
                    self.message, self.contact,
                    self.os_ports.source_port if self.os_ports else 52143,
                    self.path_l4, self.path_l5,
                    self.cost_l4, self.cost_l5,
                    self.total_score
                )
            elif self.ack_return.action_compose:
                self.compose.result_msg = None
                self.compose.input.text = ""
                self.total_score = 0
                self.state = self.STATE_COMPOSE

    def _draw(self):
        if self.state == self.STATE_COMPOSE:
            self.compose.draw()
        elif self.state == self.STATE_OS_PORTS:
            if self.os_ports:
                self.os_ports.draw()
        elif self.state == self.STATE_HANDSHAKE:
            if self.handshake:
                self.handshake.draw()
        elif self.state == self.STATE_INSIDE_OS:
            if self.inside_os:
                self.inside_os.draw()
        elif self.state == self.STATE_IP_ENCAP:
            if self.ip_encap:
                self.ip_encap.draw()
        elif self.state == self.STATE_FRAGMENT:
            if self.fragmentation:
                self.fragmentation.draw()
        elif self.state == self.STATE_ROUTING:
            if self.routing:
                self.routing.draw()
        elif self.state == self.STATE_DEST_ROUTING:
            if self.dest_routing:
                self.dest_routing.draw()
        elif self.state == self.STATE_DECAPSULATION:
            if self.decapsulation:
                self.decapsulation.draw()
        elif self.state == self.STATE_ACK_RETURN:
            if self.ack_return:
                self.ack_return.draw()

    def _quit(self):
        pygame.quit()
        sys.exit()


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    Game().run()




