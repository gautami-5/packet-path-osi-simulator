"""
Temporary verification file for LevelDataLink
"""
import pygame
import sys
import math
import time
import zlib

SCREEN_W, SCREEN_H = 1200, 750

C = {
    "bg":        (8,   13,  24),
    "panel":     (16,  24,  39),
    "panel2":    (13,  20,  34),
    "line":      (38,  53,  74),
    "text":      (237, 245, 255),
    "muted":     (145, 164, 191),
    "cyan":      (85,  230, 255),
    "cyan_dim":  (40,  110, 130),
    "blue":      (109, 140, 255),
    "violet":    (178, 140, 255),
    "green":     (98,  237, 178),
    "amber":     (255, 200, 107),
    "red":       (255, 107, 130),
    "white":     (255, 255, 255),
    "black":     (0,   0,   0),
}

def draw_rect_rounded(surf, colour, rect, radius=12, border=0, border_colour=None):
    if border and border_colour:
        pygame.draw.rect(surf, border_colour, rect, border_radius=radius)
        inner = pygame.Rect(rect.x + border, rect.y + border,
                            rect.w - border * 2, rect.h - border * 2)
        pygame.draw.rect(surf, colour, inner, border_radius=max(0, radius - border))
    else:
        pygame.draw.rect(surf, colour, rect, border_radius=radius)

def draw_gradient_rect(surf, rect, col_top, col_bot, radius=0):
    for y in range(rect.h):
        t = y / max(rect.h - 1, 1)
        r = int(col_top[0] + (col_bot[0] - col_top[0]) * t)
        g = int(col_top[1] + (col_bot[1] - col_top[1]) * t)
        b = int(col_top[2] + (col_bot[2] - col_top[2]) * t)
        pygame.draw.line(surf, (r, g, b), (rect.x, rect.y + y), (rect.x + rect.w - 1, rect.y + y))

class Fonts:
    def __init__(self):
        pygame.font.init()
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

class Button:
    def __init__(self, rect, label, fonts: Fonts, primary=True):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.fonts = fonts
        self.primary = primary
        self.hover = False
        self._anim_t = 0.0

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

    def update(self, dt):
        target = 1.0 if self.hover else 0.0
        self.hover = self.rect.collidepoint(pygame.mouse.get_pos())
        self._anim_t += (target - self._anim_t) * min(1.0, dt * 10)

    def draw(self, surf):
        t = self._anim_t
        lift = int(t * 3)
        r = self.rect.move(0, -lift)
        if self.primary:
            col_l = tuple(int(C["green"][i] + (C["cyan"][i] - C["green"][i]) * t) for i in range(3))
            col_r = tuple(int(C["cyan"][i] + (C["blue"][i] - C["cyan"][i]) * t) for i in range(3))
            draw_gradient_rect(surf, r, col_l, col_r, radius=12)
            pygame.draw.rect(surf, col_l, r, border_radius=12, width=0)
            text_col = C["black"]
        else:
            border_col = tuple(int(C["line"][i] + (C["green"][i] - C["line"][i]) * t) for i in range(3))
            draw_rect_rounded(surf, C["panel"], r, radius=12, border=1, border_colour=border_col)
            text_col = C["text"]
        label_surf = self.fonts.btn.render(self.label, True, text_col)
        surf.blit(label_surf, (r.centerx - label_surf.get_width() // 2,
                                r.centery - label_surf.get_height() // 2))

class Particle:
    def __init__(self):
        self.reset()
    def reset(self):
        import random
        self.x = float(1200) * (0.1 + 0.8 * random.random())
        self.y = float(750) + 10
        self.vy = -(random.random() * 0.4 + 0.1)
        self.vx = (random.random() - 0.5) * 0.2
        self.alpha = int(random.random() * 80 + 20)
        self.radius = random.random() * 1.5 + 0.5
        self.colour = random.choice([C["green"], C["cyan"], C["blue"]])
    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.y < -10:
            self.reset()
            self.y = 760.0
    def draw(self, surf):
        pass

# Now the complete LevelDataLink implementation
class LevelDataLink:
    """
    OSI Layer 2 · Data Link Layer Simulation
    ========================================
    Teaches the student:
      1. ARP (Address Resolution Protocol):
         - Resolving next-hop Gateway IP (192.168.1.1) to 48-bit MAC address.
         - Broadcast ARP Request (FF:FF:FF:FF:FF:FF) flooded by local Switch.
         - Unicast ARP Reply from Gateway router, cached in local ARP Table.
      2. Ethernet II Frame Encapsulation:
         - Wrapping IP Datagram with Ethernet Header & Trailer.
         - Preamble/SFD (8 B), Dst MAC (6 B), Src MAC (6 B), EtherType (0x0800, 2 B),
           Payload (46-1500 B), FCS/CRC-32 (4 B).
      3. CRC-32 Frame Check Sequence & Error Detection:
         - Integrity verification using cyclic redundancy check.
         - Interactive bit-flip noise simulation: shows why damaged frames are dropped at Layer 2.
      4. Key Distinction: IP Address (End-to-End, Logical) vs MAC Address (Hop-to-Hop, Physical).
    """

    def __init__(self, screen, fonts: Fonts, message: str, contact: dict, source_port: int = 52143):
        self.screen      = screen
        self.fonts       = fonts
        self.message     = message
        self.contact     = contact
        self.source_port = source_port

        self.time_elapsed = 0.0
        self.action_proceed = False
        self.action_replay  = False

        # Addresses
        self.host_ip       = "192.168.1.10"
        self.host_mac      = "B4:2E:99:A1:7C:12"
        self.gateway_ip    = "192.168.1.1"
        self.gateway_mac   = "00:1A:2B:3C:4D:5E"
        self.broadcast_mac = "FF:FF:FF:FF:FF:FF"
        self.dest_ip       = contact.get("ip", "10.42.17.83")

        # LAN devices for ARP simulation
        self.lan_devices = [
            {"id": "gateway", "name": "Gateway (R1)", "ip": "192.168.1.1",  "mac": "00:1A:2B:3C:4D:5E", "is_target": True,  "pos": (650, 230), "col": C["cyan"]},
            {"id": "printer", "name": "Office Printer", "ip": "192.168.1.25", "mac": "70:85:C2:A0:11:3F", "is_target": False, "pos": (650, 350), "col": C["muted"]},
            {"id": "smarttv", "name": "Smart TV",      "ip": "192.168.1.50", "mac": "A4:C1:38:F2:99:04", "is_target": False, "pos": (650, 470), "col": C["muted"]},
        ]

        # Payload and Frame sizing
        self.payload_bytes = max(46, len(self.message) + 20 + 20)
        self.total_frame_bytes = 14 + self.payload_bytes + 4

        # Real CRC-32 calculation
        raw_bytes = f"IPv4-SRC:{self.host_ip}-DST:{self.dest_ip}-DATA:{self.message}".encode("utf-8")
        self.crc32_val = zlib.crc32(raw_bytes) & 0xFFFFFFFF
        self.crc32_hex = f"0x{self.crc32_val:08X}"
        self.corrupted_crc = (self.crc32_val ^ 0x0482B107) & 0xFFFFFFFF
        self.corrupted_hex = f"0x{self.corrupted_crc:08X}"

        # Tabs: 0 = ARP Resolution, 1 = Frame Encapsulation, 2 = CRC-32 & IP vs MAC
        self.active_tab = 0
        self.tab_names = [
            "1. ARP Resolution (IP ➔ MAC)",
            "2. Ethernet II Framing",
            "3. CRC-32 & IP vs MAC Lab",
        ]
        self.tab_rects = [
            pygame.Rect(140, 96, 290, 36),
            pygame.Rect(455, 96, 290, 36),
            pygame.Rect(770, 96, 290, 36),
        ]

        # Tab 0: ARP State
        # 0 = Idle / Cache Miss
        # 1 = ARP Request traveling (Host -> Switch -> Broadcast to 3 devices)
        # 2 = Device evaluation (Printer/TV drop, Gateway matches)
        # 3 = ARP Reply traveling (Gateway -> Switch -> Host)
        # 4 = Resolved & Cached
        self.arp_step = 0
        self.arp_t = 0.0
        self.arp_sparks = []
        self.btn_arp_req = Button(pygame.Rect(800, 580, 350, 44), "BROADCAST ARP REQUEST ➜", fonts, primary=True)
        self.btn_arp_rst = Button(pygame.Rect(800, 580, 160, 44), "↺ Re-run ARP", fonts, primary=False)

        # Tab 1: Frame field inspection
        self.selected_field = 1  # 0..5
        self.frame_fields = [
            {
                "name": "PREAMBLE + SFD",
                "bytes": 8,
                "val": "10101010...10101011",
                "col": (65, 88, 120),
                "desc": "Preamble (7 B) + Start Frame Delimiter (1 B). Alternating 10101010 bit pattern allows hardware receiver physical layer to synchronize clock frequencies before actual data starts.",
                "rule": "IEEE 802.3 standard clock sync; stripped by receiving NIC before passing to driver.",
            },
            {
                "name": "DESTINATION MAC",
                "bytes": 6,
                "val": self.gateway_mac,
                "col": C["cyan"],
                "desc": f"48-bit physical MAC address of next immediate hop: Default Gateway R1 ({self.gateway_mac}).",
                "rule": f"CRUCIAL: Even though final destination is {self.dest_ip}, Ethernet only delivers across local wire to the next router (Gateway)! Destination MAC changes at every hop.",
            },
            {
                "name": "SOURCE MAC",
                "bytes": 6,
                "val": self.host_mac,
                "col": C["blue"],
                "desc": f"48-bit physical MAC address burned into sender's local NIC: Host ({self.host_mac}).",
                "rule": "Uniquely identifies this physical network adapter. Used by switches to build MAC Address Tables (CAM table).",
            },
            {
                "name": "ETHERTYPE",
                "bytes": 2,
                "val": "0x0800 (IPv4)",
                "col": C["amber"],
                "desc": "Protocol identifier: 0x0800 indicates the payload inside this Ethernet frame is an IPv4 packet.",
                "rule": "Demultiplexing tag. If payload was ARP, EtherType would be 0x0806; if IPv6, it would be 0x86DD.",
            },
            {
                "name": "PAYLOAD (IP DATAGRAM)",
                "bytes": self.payload_bytes,
                "val": f"IPv4 Datagram ({self.payload_bytes} B)",
                "col": C["violet"],
                "desc": f"The encapsulated Layer 3 IPv4 packet containing IPv4 Header (20 B) + TCP Segment + message ('{self.message}').",
                "rule": "Ethernet standard requires minimum 46 bytes (padded if smaller) up to 1500 bytes (standard MTU).",
            },
            {
                "name": "FCS (CRC-32)",
                "bytes": 4,
                "val": self.crc32_hex,
                "col": C["green"],
                "desc": f"Frame Check Sequence: 32-bit Cyclic Redundancy Check trailer computed over header + payload: {self.crc32_hex}.",
                "rule": "If any bit flips on the wire during transmission, receiver CRC will mismatch and frame is immediately dropped.",
            },
        ]

        # Tab 2: Error Lab state
        self.noise_injected = False
        self.btn_clean_sig = Button(pygame.Rect(60, 475, 230, 42), "✓ Clean Wire (Normal)", fonts, primary=True)
        self.btn_noise_sig = Button(pygame.Rect(310, 475, 230, 42), "⚡ Inject Bit Flip (Noise)", fonts, primary=False)

        # Global Bottom navigation buttons
        self.btn_replay   = Button(pygame.Rect(40, 680, 140, 46), "↺ Replay L2", fonts, primary=False)
        self.btn_prev_tab = Button(pygame.Rect(200, 680, 150, 46), "↶ Prev Tab", fonts, primary=False)
        self.btn_next_tab = Button(pygame.Rect(365, 680, 150, 46), "Next Tab ➜", fonts, primary=False)
        self.btn_proceed  = Button(pygame.Rect(840, 680, 320, 46), "TRANSMIT FRAME TO ROUTING ➜", fonts, primary=True)

        self.particles  = [Particle() for _ in range(25)]
        self._scan_surf = self._make_scanlines(SCREEN_W, SCREEN_H)

    def _make_scanlines(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(0, h, 4):
            pygame.draw.line(s, (0, 0, 0, 16), (0, y), (w, y))
        return s

    def _spawn_sparks(self, cx, cy, count=30, colours=None):
        import random, math as _m
        colours = colours or [C["green"], C["cyan"], C["white"]]
        for _ in range(count):
            angle = _m.tau * random.random()
            speed = random.random() * 220 + 50
            self.arp_sparks.append({
                "x": float(cx), "y": float(cy),
                "vx": _m.cos(angle) * speed,
                "vy": _m.sin(angle) * speed,
                "life": random.uniform(0.4, 0.9),
                "colour": random.choice(colours),
            })

    def update(self, dt):
        self.time_elapsed += dt
        for p in self.particles:
            p.update()

        self.btn_replay.update(dt)
        self.btn_prev_tab.update(dt)
        self.btn_next_tab.update(dt)
        self.btn_proceed.update(dt)

        if self.active_tab == 0:
            if self.arp_step == 0:
                self.btn_arp_req.update(dt)
            elif self.arp_step == 4:
                self.btn_arp_rst.update(dt)
            elif self.arp_step in (1, 2, 3):
                self.arp_t += dt * 0.95
                if self.arp_step == 1 and self.arp_t >= 1.0:
                    self.arp_step = 2
                    self.arp_t = 0.0
                elif self.arp_step == 2 and self.arp_t >= 1.2:
                    self.arp_step = 3
                    self.arp_t = 0.0
                elif self.arp_step == 3 and self.arp_t >= 1.0:
                    self.arp_step = 4
                    self.arp_t = 0.0
                    self._spawn_sparks(100, 350, 35, [C["green"], C["cyan"], C["white"]])

        elif self.active_tab == 2:
            self.btn_clean_sig.update(dt)
            self.btn_noise_sig.update(dt)

        surviving = []
        for sp in self.arp_sparks:
            sp["x"] += sp["vx"] * dt
            sp["y"] += sp["vy"] * dt
            sp["life"] -= dt
            if sp["life"] > 0:
                surviving.append(sp)
        self.arp_sparks = surviving

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.tab_rects):
                if r.collidepoint(event.pos):
                    self.active_tab = i
                    return

            if self.active_tab == 1:
                bx = 40
                field_widths = [120, 200, 200, 130, 330, 140]
                for i, w in enumerate(field_widths):
                    rect = pygame.Rect(bx, 245, w, 85)
                    if rect.collidepoint(event.pos):
                        self.selected_field = i
                        return
                    bx += w

        if self.btn_replay.handle_event(event):
            self.action_replay = True
            return
        if self.btn_proceed.handle_event(event):
            self.action_proceed = True
            return
        if self.btn_prev_tab.handle_event(event):
            self.active_tab = max(0, self.active_tab - 1)
            return
        if self.btn_next_tab.handle_event(event):
            self.active_tab = min(len(self.tab_names) - 1, self.active_tab + 1)
            return

        if self.active_tab == 0:
            if self.arp_step == 0 and self.btn_arp_req.handle_event(event):
                self.arp_step = 1
                self.arp_t = 0.0
                self._spawn_sparks(100, 350, 20, [C["cyan"], C["white"]])
            elif self.arp_step == 4 and self.btn_arp_rst.handle_event(event):
                self.arp_step = 0
                self.arp_t = 0.0

        elif self.active_tab == 2:
            if self.btn_clean_sig.handle_event(event):
                self.noise_injected = False
            elif self.btn_noise_sig.handle_event(event):
                self.noise_injected = True
                self._spawn_sparks(280, 360, 25, [C["red"], C["amber"], C["white"]])

    def draw(self):
        surf = self.screen
        surf.fill(C["bg"])

        for p in self.particles:
            p.draw(surf)

        self._draw_header(surf)

        if self.active_tab == 0:
            self._draw_tab0_arp(surf)
        elif self.active_tab == 1:
            self._draw_tab1_framing(surf)
        elif self.active_tab == 2:
            self._draw_tab2_crc_and_comparison(surf)

        self._draw_bottom_bar(surf)

        for sp in self.arp_sparks:
            r = max(2, int(sp["life"] * 6))
            pygame.draw.circle(surf, sp["colour"], (int(sp["x"]), int(sp["y"])), r)

        surf.blit(self._scan_surf, (0, 0))

    def _draw_header(self, surf):
        W = surf.get_width()
        logo_r = pygame.Rect(32, 13, 44, 44)
        pygame.draw.rect(surf, C["green"], logo_r, border_radius=12)
        sym = self.fonts.hero.render("⧉", True, C["black"])
        surf.blit(sym, (logo_r.centerx - sym.get_width() // 2,
                        logo_r.centery - sym.get_height() // 2 - 2))
        surf.blit(self.fonts.title_lg.render("PACKET PATH", True, C["text"]), (88, 22))

        badge_r = pygame.Rect(W - 370, 14, 338, 42)
        draw_rect_rounded(surf, (16, 32, 28), badge_r, radius=10, border=1, border_colour=C["green"])
        surf.blit(self.fonts.label.render("CURRENT LAYER", True, C["muted"]),
                  (badge_r.x + 14, badge_r.y + 6))
        surf.blit(self.fonts.label_lg.render("LAYER 2 · DATA LINK LAYER", True, C["green"]),
                  (badge_r.x + 14, badge_r.y + 22))

        sub_txt = "LOCAL ETHERNET FRAMING · ARP (IP ➔ MAC) · CRC-32 ERROR DETECTION"
        hs = self.fonts.mono_sm.render(sub_txt, True, C["cyan"])
        surf.blit(hs, (W // 2 - hs.get_width() // 2, 72))

        # Tabs
        for i, r in enumerate(self.tab_rects):
            is_active = (i == self.active_tab)
            bg_col = (18, 30, 46) if is_active else (12, 18, 28)
            bdr_col = C["green"] if is_active else C["line"]
            draw_rect_rounded(surf, bg_col, r, radius=8, border=2 if is_active else 1, border_colour=bdr_col)
            if is_active:
                pygame.draw.circle(surf, C["green"], (r.x + 16, r.centery), 4)
            lbl_col = C["text"] if is_active else C["muted"]
            lbl_surf = self.fonts.label_lg.render(self.tab_names[i], True, lbl_col)
            surf.blit(lbl_surf, (r.x + 28 if is_active else r.centerx - lbl_surf.get_width() // 2,
                                 r.centery - lbl_surf.get_height() // 2))

    def _draw_tab0_arp(self, surf):
        # Topology panel
        pan_r = pygame.Rect(40, 145, 740, 515)
        draw_rect_rounded(surf, C["panel"], pan_r, radius=12, border=1, border_colour=C["line"])
        title = self.fonts.title_md.render("LOCAL SUBNET TOPOLOGY (192.168.1.0/24)", True, C["text"])
        surf.blit(title, (pan_r.x + 20, pan_r.y + 16))
        sub = self.fonts.body_sm.render("Host needs to send to Gateway R1, but only has its IP. ARP resolves Gateway MAC.", True, C["muted"])
        surf.blit(sub, (pan_r.x + 20, pan_r.y + 42))

        # Nodes
        host_pos = (120, 350)
        sw_pos   = (380, 350)

        # Links
        pygame.draw.line(surf, C["line"], (host_pos[0] + 50, host_pos[1]), (sw_pos[0] - 40, sw_pos[1]), 2)
        for dev in self.lan_devices:
            dpos = dev["pos"]
            link_col = C["green"] if (self.arp_step >= 2 and dev["is_target"]) else C["line"]
            pygame.draw.line(surf, link_col, (sw_pos[0] + 40, sw_pos[1]), (dpos[0] - 50, dpos[1]), 2)

        # Draw Host node
        hr = pygame.Rect(host_pos[0] - 50, host_pos[1] - 45, 100, 90)
        draw_rect_rounded(surf, (18, 28, 48), hr, radius=10, border=2, border_colour=C["blue"])
        h_icon = self.fonts.title_md.render("💻 HOST", True, C["blue"])
        surf.blit(h_icon, (hr.centerx - h_icon.get_width() // 2, hr.y + 10))
        h_ip = self.fonts.mono_sm.render(self.host_ip, True, C["text"])
        surf.blit(h_ip, (hr.centerx - h_ip.get_width() // 2, hr.y + 36))
        h_mac = self.fonts.counter.render(self.host_mac, True, C["muted"])
        surf.blit(h_mac, (hr.centerx - h_mac.get_width() // 2, hr.y + 58))

        # Draw Switch node
        sr = pygame.Rect(sw_pos[0] - 45, sw_pos[1] - 45, 90, 90)
        draw_rect_rounded(surf, (15, 24, 38), sr, radius=10, border=1, border_colour=C["cyan_dim"])
        s_icon = self.fonts.title_md.render("🔀 SWITCH", True, C["cyan"])
        surf.blit(s_icon, (sr.centerx - s_icon.get_width() // 2, sr.y + 14))
        s_sub = self.fonts.counter.render("Layer 2 Hub", True, C["muted"])
        surf.blit(s_sub, (sr.centerx - s_sub.get_width() // 2, sr.y + 44))
        s_sub2 = self.fonts.counter.render("Floods B-cast", True, C["muted"])
        surf.blit(s_sub2, (sr.centerx - s_sub2.get_width() // 2, sr.y + 60))

        # Draw Devices
        for dev in self.lan_devices:
            dp = dev["pos"]
            dr = pygame.Rect(dp[0] - 50, dp[1] - 40, 150, 80)
            is_match = (self.arp_step >= 2 and dev["is_target"])
            bdr = C["green"] if is_match else dev["col"]
            bg = (20, 40, 30) if is_match else (15, 22, 34)
            draw_rect_rounded(surf, bg, dr, radius=10, border=2 if is_match else 1, border_colour=bdr)
            dname = self.fonts.label_lg.render(dev["name"], True, bdr)
            surf.blit(dname, (dr.centerx - dname.get_width() // 2, dr.y + 8))
            dip = self.fonts.mono_sm.render(dev["ip"], True, C["text"])
            surf.blit(dip, (dr.centerx - dip.get_width() // 2, dr.y + 30))
            dmac = self.fonts.counter.render(dev["mac"], True, C["muted"])
            surf.blit(dmac, (dr.centerx - dmac.get_width() // 2, dr.y + 50))

            # Evaluation tags
            if self.arp_step in (2, 3, 4):
                if dev["is_target"]:
                    tag = self.fonts.label.render("✓ IP MATCH (REPLY)", True, C["green"])
                else:
                    tag = self.fonts.label.render("✗ IP MISMATCH (DROP)", True, C["red"])
                surf.blit(tag, (dr.right + 10, dr.centery - tag.get_height() // 2))

        # Flying packets
        if self.arp_step == 1:
            t = self.arp_t
            if t <= 0.45:
                # Host -> Switch
                sub_t = t / 0.45
                px = host_pos[0] + (sw_pos[0] - host_pos[0]) * sub_t
                py = host_pos[1]
                pygame.draw.circle(surf, C["cyan"], (int(px), int(py)), 9)
                pkt_s = self.fonts.counter.render("ARP REQ (B-CAST)", True, C["cyan"])
                surf.blit(pkt_s, (int(px) - pkt_s.get_width() // 2, int(py) - 22))
            else:
                # Fan out from Switch to 3 devices
                sub_t = (t - 0.45) / 0.55
                for dev in self.lan_devices:
                    dp = dev["pos"]
                    px = sw_pos[0] + (dp[0] - sw_pos[0]) * sub_t
                    py = sw_pos[1] + (dp[1] - sw_pos[1]) * sub_t
                    pygame.draw.circle(surf, C["amber"], (int(px), int(py)), 7)
                pkt_s = self.fonts.counter.render("BROADCAST TO FF:FF:FF:FF:FF:FF", True, C["amber"])
                surf.blit(pkt_s, (sw_pos[0] - pkt_s.get_width() // 2, sw_pos[1] - 65))

        elif self.arp_step == 3:
            t = self.arp_t
            target_pos = self.lan_devices[0]["pos"]
            if t <= 0.5:
                # Gateway -> Switch
                sub_t = t / 0.5
                px = target_pos[0] + (sw_pos[0] - target_pos[0]) * sub_t
                py = target_pos[1] + (sw_pos[1] - target_pos[1]) * sub_t
                pygame.draw.circle(surf, C["green"], (int(px), int(py)), 9)
                pkt_s = self.fonts.counter.render("ARP REPLY (UNICAST)", True, C["green"])
                surf.blit(pkt_s, (int(px) - pkt_s.get_width() // 2, int(py) - 20))
            else:
                # Switch -> Host
                sub_t = (t - 0.5) / 0.5
                px = sw_pos[0] + (host_pos[0] - sw_pos[0]) * sub_t
                py = sw_pos[1]
                pygame.draw.circle(surf, C["green"], (int(px), int(py)), 9)
                pkt_s = self.fonts.counter.render("MAC: " + self.gateway_mac, True, C["green"])
                surf.blit(pkt_s, (int(px) - pkt_s.get_width() // 2, int(py) - 20))

        # Bottom status in Tab 0
        if self.arp_step == 4:
            s_banner = pygame.Rect(pan_r.x + 20, pan_r.bottom - 55, pan_r.w - 40, 38)
            draw_rect_rounded(surf, (18, 38, 28), s_banner, radius=8, border=1, border_colour=C["green"])
            succ = self.fonts.label_lg.render("✓ ARP RESOLUTION COMPLETE · Gateway MAC (00:1A:2B:3C:4D:5E) Cached in Host Table!", True, C["green"])
            surf.blit(succ, (s_banner.centerx - succ.get_width() // 2, s_banner.centery - succ.get_height() // 2))

        # Right Panel: ARP Table & Packet Inspector
        tab_r = pygame.Rect(800, 145, 360, 515)
        draw_rect_rounded(surf, C["panel"], tab_r, radius=12, border=1, border_colour=C["line"])
        t_title = self.fonts.title_md.render("LOCAL ARP CACHE (TABLE)", True, C["text"])
        surf.blit(t_title, (tab_r.x + 20, tab_r.y + 16))
        t_sub = self.fonts.mono_sm.render("Kernel ARP Table · eth0", True, C["muted"])
        surf.blit(t_sub, (tab_r.x + 20, tab_r.y + 40))

        # ARP Table rows
        tbl_y = tab_r.y + 70
        hdr = self.fonts.label.render("IP ADDRESS          MAC ADDRESS         TYPE", True, C["cyan"])
        surf.blit(hdr, (tab_r.x + 20, tbl_y))
        pygame.draw.line(surf, C["line"], (tab_r.x + 18, tbl_y + 18), (tab_r.right - 18, tbl_y + 18))

        # Row 1: Gateway
        r1_y = tbl_y + 26
        ip1 = self.fonts.mono_sm.render("192.168.1.1", True, C["text"])
        surf.blit(ip1, (tab_r.x + 20, r1_y))
        if self.arp_step == 4:
            mac1 = self.fonts.mono_sm.render(self.gateway_mac, True, C["green"])
            status1 = self.fonts.counter.render("DYNAMIC", True, C["green"])
        else:
            mac1 = self.fonts.mono_sm.render("[ RESOLVING... ]", True, C["amber"])
            status1 = self.fonts.counter.render("INCOMPLETE", True, C["amber"])
        surf.blit(mac1, (tab_r.x + 125, r1_y))
        surf.blit(status1, (tab_r.x + 280, r1_y))

        # Row 2: Broadcast
        r2_y = r1_y + 24
        ip2 = self.fonts.mono_sm.render("192.168.1.255", True, C["muted"])
        mac2 = self.fonts.mono_sm.render("FF:FF:FF:FF:FF:FF", True, C["muted"])
        st2 = self.fonts.counter.render("STATIC", True, C["muted"])
        surf.blit(ip2, (tab_r.x + 20, r2_y))
        surf.blit(mac2, (tab_r.x + 125, r2_y))
        surf.blit(st2, (tab_r.x + 280, r2_y))

        # ARP Protocol Details Box
        pr_box = pygame.Rect(tab_r.x + 16, r2_y + 40, tab_r.w - 32, 230)
        draw_rect_rounded(surf, (12, 18, 30), pr_box, radius=8, border=1, border_colour=C["line"])
        p_head = self.fonts.label_lg.render("ARP Packet Structure (RFC 826)", True, C["cyan"])
        surf.blit(p_head, (pr_box.x + 14, pr_box.y + 10))

        op_str = "1 (ARP Request)" if self.arp_step < 3 else "2 (ARP Reply)"
        details = [
            ("Hardware Type", "1 (Ethernet 10/100/1000)"),
            ("Protocol Type", "0x0800 (IPv4)"),
            ("Hardware Size", "6 Bytes (MAC length)"),
            ("Protocol Size", "4 Bytes (IPv4 length)"),
            ("Opcode",        op_str),
            ("Sender MAC",    self.host_mac if self.arp_step < 3 else self.gateway_mac),
            ("Sender IP",     self.host_ip if self.arp_step < 3 else self.gateway_ip),
            ("Target MAC",    self.broadcast_mac if self.arp_step < 3 else self.host_mac),
            ("Target IP",     self.gateway_ip if self.arp_step < 3 else self.host_ip),
        ]
        dy = pr_box.y + 36
        for k, v in details:
            ks = self.fonts.counter.render(f"{k}:", True, C["muted"])
            vs = self.fonts.counter.render(v, True, C["text"])
            surf.blit(ks, (pr_box.x + 14, dy))
            surf.blit(vs, (pr_box.x + 125, dy))
            dy += 20

        # Trigger or reset button
        if self.arp_step == 0:
            self.btn_arp_req.draw(surf)
        elif self.arp_step == 4:
            self.btn_arp_rst.draw(surf)

    def _draw_tab1_framing(self, surf):
        # Top PDU banner
        top_r = pygame.Rect(40, 145, 1120, 85)
        draw_rect_rounded(surf, C["panel"], top_r, radius=12, border=1, border_colour=C["line"])
        title = self.fonts.title_md.render("ETHERNET II FRAME ENCAPSULATION (PDU: FRAME)", True, C["text"])
        surf.blit(title, (top_r.x + 20, top_r.y + 14))

        # PDU Stack display
        pdu_txt = self.fonts.mono_sm.render(
            "Layer 7: Data  ➔  Layer 4: Segment  ➔  Layer 3: IP Datagram  ➔  Layer 2: [ Ethernet Header | IP Datagram | FCS Trailer ]",
            True, C["green"]
        )
        surf.blit(pdu_txt, (top_r.x + 20, top_r.y + 44))

        # Frame Fields Horizontal Strip
        bx = 40
        field_widths = [120, 200, 200, 130, 330, 140]
        for i, f in enumerate(self.frame_fields):
            w = field_widths[i]
            r = pygame.Rect(bx, 245, w, 85)
            is_sel = (i == self.selected_field)
            bg = (20, 32, 48) if is_sel else (14, 20, 32)
            draw_rect_rounded(surf, bg, r, radius=8, border=2 if is_sel else 1, border_colour=f["col"] if is_sel else C["line"])

            # Field top tag
            pygame.draw.rect(surf, f["col"], pygame.Rect(r.x, r.y, r.w, 4), border_radius=4)
            fn = self.fonts.label.render(f["name"], True, f["col"])
            surf.blit(fn, (r.centerx - fn.get_width() // 2, r.y + 10))

            # Bytes badge
            fb = self.fonts.counter.render(f"{f['bytes']} Bytes", True, C["muted"])
            surf.blit(fb, (r.centerx - fb.get_width() // 2, r.y + 30))

            # Value
            fv = self.fonts.mono_sm.render(f["val"][:18], True, C["text"])
            surf.blit(fv, (r.centerx - fv.get_width() // 2, r.y + 54))

            if is_sel:
                arr = self.fonts.label.render("▲", True, f["col"])
                surf.blit(arr, (r.centerx - arr.get_width() // 2, r.bottom + 4))

            bx += w

        # Selected Field Inspector Panel
        sel = self.frame_fields[self.selected_field]
        insp_r = pygame.Rect(40, 350, 1120, 305)
        draw_rect_rounded(surf, C["panel"], insp_r, radius=12, border=1, border_colour=sel["col"])

        # Header
        ih = self.fonts.title_md.render(f"FIELD DETAILS: {sel['name']} ({sel['bytes']} BYTES)", True, sel["col"])
        surf.blit(ih, (insp_r.x + 24, insp_r.y + 18))

        # Current value box
        val_box = pygame.Rect(insp_r.x + 24, insp_r.y + 52, 450, 38)
        draw_rect_rounded(surf, (10, 16, 26), val_box, radius=6, border=1, border_colour=C["line"])
        v_lbl = self.fonts.mono.render(f"Value: {sel['val']}", True, C["cyan"])
        surf.blit(v_lbl, (val_box.x + 14, val_box.centery - v_lbl.get_height() // 2))

        # Description
        desc_s = self.fonts.body.render(sel["desc"], True, C["text"])
        surf.blit(desc_s, (insp_r.x + 24, insp_r.y + 110))

        # Rule note
        note_box = pygame.Rect(insp_r.x + 24, insp_r.y + 150, insp_r.w - 48, 70)
        draw_rect_rounded(surf, (14, 24, 38), note_box, radius=8, border=1, border_colour=C["cyan_dim"])
        n_title = self.fonts.label_lg.render("KEY ARCHITECTURAL RULE:", True, C["amber"])
        surf.blit(n_title, (note_box.x + 14, note_box.y + 12))
        n_body = self.fonts.body_sm.render(sel["rule"], True, C["text"])
        surf.blit(n_body, (note_box.x + 14, note_box.y + 36))

        # Frame summary footer
        f_foot = self.fonts.mono_sm.render(
            f"Total Ethernet Frame Overhead: 14 B (Header) + 4 B (FCS Trailer) = 18 Bytes  |  Payload: {self.payload_bytes} B  |  Total: {self.total_frame_bytes} Bytes",
            True, C["green"]
        )
        surf.blit(f_foot, (insp_r.x + 24, insp_r.bottom - 36))

    def _draw_tab2_crc_and_comparison(self, surf):
        # Left Panel: CRC-32 Lab
        left_r = pygame.Rect(40, 145, 540, 515)
        draw_rect_rounded(surf, C["panel"], left_r, radius=12, border=1, border_colour=C["line"])
        lh = self.fonts.title_md.render("CRC-32 FRAME CHECK SEQUENCE (FCS) LAB", True, C["text"])
        surf.blit(lh, (left_r.x + 20, left_r.y + 16))
        ls = self.fonts.body_sm.render("Layer 2 verifies frame integrity across physical copper/fiber links.", True, C["muted"])
        surf.blit(ls, (left_r.x + 20, left_r.y + 40))

        # Transmitter Box
        tx_b = pygame.Rect(left_r.x + 20, left_r.y + 70, left_r.w - 40, 105)
        draw_rect_rounded(surf, (12, 18, 28), tx_b, radius=8, border=1, border_colour=C["line"])
        tx_title = self.fonts.label_lg.render("TRANSMITTER (Host NIC):", True, C["cyan"])
        surf.blit(tx_title, (tx_b.x + 14, tx_b.y + 10))
        tx_d = self.fonts.mono_sm.render(f"Calculated CRC-32 over Frame Data: {self.crc32_hex}", True, C["green"])
        surf.blit(tx_d, (tx_b.x + 14, tx_b.y + 38))
        tx_p = self.fonts.counter.render(f"Appended as 4-byte Frame Check Sequence (FCS) trailer", True, C["muted"])
        surf.blit(tx_p, (tx_b.x + 14, tx_b.y + 66))

        # Channel & Noise Controls
        ch_y = left_r.y + 195
        ch_s = self.fonts.label_lg.render("Physical Wire Transmission & Noise Simulator:", True, C["text"])
        surf.blit(ch_s, (left_r.x + 20, ch_y))

        # Receiver Box
        rx_b = pygame.Rect(left_r.x + 20, ch_y + 90, left_r.w - 40, 175)
        bdr_col = C["red"] if self.noise_injected else C["green"]
        bg_col = (30, 16, 20) if self.noise_injected else (14, 28, 22)
        draw_rect_rounded(surf, bg_col, rx_b, radius=8, border=2, border_colour=bdr_col)

        rx_h = self.fonts.label_lg.render("RECEIVER (Gateway Router NIC):", True, bdr_col)
        surf.blit(rx_h, (rx_b.x + 14, rx_b.y + 12))

        if self.noise_injected:
            r1 = self.fonts.mono_sm.render(f"Transmitted FCS: {self.crc32_hex}  |  Receiver CRC: {self.corrupted_hex}", True, C["red"])
            surf.blit(r1, (rx_b.x + 14, rx_b.y + 40))
            r2 = self.fonts.title_md.render("✗ CRC MISMATCH DETECTED!", True, C["red"])
            surf.blit(r2, (rx_b.x + 14, rx_b.y + 68))
            r3 = self.fonts.body_sm.render("Bit corrupted by electrical noise! Layer 2 drops the frame silently.", True, C["text"])
            surf.blit(r3, (rx_b.x + 14, rx_b.y + 98))
            r4 = self.fonts.counter.render("Higher layers (IP, TCP) are protected from corrupt garbage data.", True, C["muted"])
            surf.blit(r4, (rx_b.x + 14, rx_b.y + 126))
        else:
            r1 = self.fonts.mono_sm.render(f"Transmitted FCS: {self.crc32_hex}  |  Receiver CRC: {self.crc32_hex}", True, C["green"])
            surf.blit(r1, (rx_b.x + 14, rx_b.y + 40))
            r2 = self.fonts.title_md.render("✓ CRC MATCH — FRAME VALID!", True, C["green"])
            surf.blit(r2, (rx_b.x + 14, rx_b.y + 68))
            r3 = self.fonts.body_sm.render("No transmission errors detected across the physical link.", True, C["text"])
            surf.blit(r3, (rx_b.x + 14, rx_b.y + 98))
            r4 = self.fonts.counter.render("NIC strips Ethernet Header & FCS, passes IP Datagram to Layer 3.", True, C["muted"])
            surf.blit(r4, (rx_b.x + 14, rx_b.y + 126))

        # Draw buttons
        self.btn_clean_sig.draw(surf)
        self.btn_noise_sig.draw(surf)

        # Right Panel: IP vs MAC Comparison
        right_r = pygame.Rect(600, 145, 560, 515)
        draw_rect_rounded(surf, C["panel"], right_r, radius=12, border=1, border_colour=C["line"])
        rh = self.fonts.title_md.render("OSI CORE CONCEPT: IP VS MAC ADDRESS", True, C["text"])
        surf.blit(rh, (right_r.x + 20, right_r.y + 16))
        rs = self.fonts.body_sm.render("Why do networks need BOTH an IP and a MAC address?", True, C["muted"])
        surf.blit(rs, (right_r.x + 20, right_r.y + 40))

        # Card 1: IP Address
        ip_c = pygame.Rect(right_r.x + 20, right_r.y + 70, right_r.w - 40, 175)
        draw_rect_rounded(surf, (15, 22, 36), ip_c, radius=8, border=1, border_colour=C["cyan"])
        ip_t = self.fonts.title_md.render("IP ADDRESS (Layer 3 · Network)", True, C["cyan"])
        surf.blit(ip_t, (ip_c.x + 14, ip_c.y + 12))
        lines_ip = [
            ("Scope:",     "End-to-End across the entire global Internet"),
            ("Addressing:","Logical (configured by OS / DHCP)"),
            ("This Hop:",  f"{self.host_ip} ➔ {self.dest_ip}"),
            ("Rule:",      "NEVER CHANGES as the packet hops through routers!"),
        ]
        iy = ip_c.y + 42
        for k, v in lines_ip:
            ks = self.fonts.counter.render(k, True, C["muted"])
            vs = self.fonts.body_sm.render(v, True, C["green"] if "NEVER" in v else C["text"])
            surf.blit(ks, (ip_c.x + 14, iy))
            surf.blit(vs, (ip_c.x + 100, iy))
            iy += 26

        # Card 2: MAC Address
        mac_c = pygame.Rect(right_r.x + 20, right_r.y + 265, right_r.w - 40, 175)
        draw_rect_rounded(surf, (15, 28, 24), mac_c, radius=8, border=1, border_colour=C["green"])
        mac_t = self.fonts.title_md.render("MAC ADDRESS (Layer 2 · Data Link)", True, C["green"])
        surf.blit(mac_t, (mac_c.x + 14, mac_c.y + 12))
        lines_mac = [
            ("Scope:",     "Hop-to-Hop on the immediate physical wire/link"),
            ("Addressing:","Physical 48-bit (burned into hardware NIC)"),
            ("This Hop:",  f"{self.host_mac} ➔ {self.gateway_mac}"),
            ("Rule:",      "CHANGES AT EVERY SINGLE HOP!"),
        ]
        my = mac_c.y + 42
        for k, v in lines_mac:
            ks = self.fonts.counter.render(k, True, C["muted"])
            vs = self.fonts.body_sm.render(v, True, C["amber"] if "CHANGES" in v else C["text"])
            surf.blit(ks, (mac_c.x + 14, my))
            surf.blit(vs, (mac_c.x + 100, my))
            my += 26

        # Takeaway quote
        q_s = self.fonts.mono_sm.render(
            "\"IP is your final home address. MAC is the next turn on your route.\"",
            True, C["cyan"]
        )
        surf.blit(q_s, (right_r.centerx - q_s.get_width() // 2, right_r.bottom - 45))

    def _draw_bottom_bar(self, surf):
        self.btn_replay.draw(surf)
        self.btn_prev_tab.draw(surf)
        self.btn_next_tab.draw(surf)
        self.btn_proceed.draw(surf)
