# PACKET PATH — OSI Transmission Lab
## Project Understanding & Step-by-Step Build Plan

---

## 1. PROJECT OVERVIEW

**Project Name:** Packet Path — OSI Transmission Lab  
**Type:** Browser-based Interactive Educational Game  
**Tech Stack:** Pure HTML + Vanilla CSS + Vanilla JavaScript (no frameworks, no npm)  
**Location:** `c:\Users\HP\Desktop\RoutingGame\packet-path-osi-simulator\`

### Goal
Build a 2D browser game that teaches **Computer Networking concepts** through hands-on interactive gameplay. Players experience how data travels across a network — from composing a message, through OSI-layer encapsulation, routing via Dijkstra, handling link failures, TTL expiry, and finally delivery confirmation.

---

## 2. CURRENT STATE OF THE PROJECT

### Files Present

| File | Size | Status |
|------|------|--------|
| `index.html` | ~37 KB | Existing basic simulator |
| `game.py` | 0 bytes | Empty placeholder |
| `README.md` | 1.3 KB | Brief description |
| `.git/` | — | Git repo initialized |

### What the Existing `index.html` Already Does

The current file is a **passive simulator**, not an interactive game. It:

- Lets the user type a message and select source/destination
- Auto-animates a packet dot along a pre-calculated Dijkstra route
- Shows all 7 OSI layers in a static stack UI
- Displays a Packet Inspector with illustrative protocol fields (IP, MAC, TTL, ports)
- Has Guided mode (auto-play) and Explore mode (step forward manually)
- Logs events in a timeline panel
- Shows live telemetry (hops, bytes, elapsed time)

### What is MISSING (gaps to fill)

| Feature | Status |
|---------|--------|
| Interactive drag-and-drop encapsulation | Missing |
| Multi-level game structure (like Pokemon zones) | Missing |
| Scoring system (cost-based vs. average) | Missing |
| User-selectable routing paths | Missing |
| Real-time TTL countdown timer | Missing |
| Link failure mid-routing with reroute challenge | Missing |
| Confirmation packet return journey | Missing |
| Score leaderboard / performance feedback | Missing |
| Level transitions with animations | Missing |

---

## 3. NETWORKING CONCEPTS TO DEMONSTRATE

| Concept | Where in Game |
|---------|---------------|
| **OSI Model (7 layers)** | Level 1 - Encapsulation and Level 3 - Decapsulation |
| **Encapsulation** | Level 1 - drag message into envelope/packet layers |
| **IP Addressing** | Level 1 - source/destination IP shown on packet |
| **Routing** | Level 2 - player picks path through ISP graph |
| **Dijkstra's Algorithm** | Level 2 - optimal path pre-calculated, shown as reference |
| **Hop Count** | Level 2 - increments with each router node traversed |
| **TTL (Time To Live)** | Level 2 - countdown timer; packet dropped if TTL hits 0 |
| **Link Failure** | Level 2 - one edge breaks mid-route, force reroute |
| **Decapsulation** | Level 3 - destination unwraps layers |
| **ACK / Confirmation** | Level 4 - ACK packet travels back same path |
| **Cost-Based Scoring** | All levels - user score vs. optimal path cost |

---

## 4. GAME ARCHITECTURE — LEVEL DESIGN

### Level 1 — "Compose & Encapsulate"
**Concept taught:** OSI encapsulation, protocol selection, IP headers

**Step-by-step flow:**
1. Player sees a "PC desktop" scene with a blinking cursor text field
2. Player **types a message** (e.g., "Hello, Network!")
3. Player selects **TCP or UDP** from a dropdown — a tooltip explains the difference
4. Player clicks **"Send to OS"** — the message box slides into an OS window
5. OS window shows 7 OSI layer slots stacked like envelopes inside each other
6. Player **drags the message** into the Application layer envelope
7. Each envelope (layer) auto-wraps around the previous one with an animation, showing the header added:
   - L7 Application → L6 Presentation → L5 Session → L4 Transport (adds ports + TCP/UDP) → L3 Network (adds IP) → L2 Data Link (adds MAC) → L1 Physical (bits)
8. Player can click each layer to read what was added
9. At the end, a fully-wrapped **"Packet" object** is ready to travel
10. **Level Complete** → score awarded, transition animation to Level 2

**Scoring for Level 1:**
- Fixed score based on how quickly the player correctly drags and assembles all layers
- Compared to average time of all players (or a preset benchmark)

---

### Level 2 — "Route the Packet"
**Concept taught:** Routing, Dijkstra, hop count, TTL, link failure, rerouting

**Step-by-step flow:**
1. A **2D network topology** appears — nodes: PC → ISP-SW → [R1 or R2] → R3 → Dest-SW → Server
2. Edge **costs (weights)** are displayed on each link (e.g., R1 path cost=2, R2 path cost=5)
3. A **TTL countdown timer** starts (e.g., 30 seconds / 15 hops)
4. Player sees their **packet object** at the source node
5. Player **clicks nodes** in sequence to choose the path (interactive node selection)
6. As the packet moves hop by hop:
   - Hop count increments
   - TTL decrements by 1 per hop
   - Cost accumulates
7. **At hop 3 (mid-route):** A link turns **RED** and breaks — "Link Down!" alert appears
8. Player must **reroute** before TTL hits 0 — select a different path from current node
9. If TTL expires → packet dropped → level failed → retry with penalty
10. Packet reaches destination server
11. **Optimal path** (Dijkstra result) is revealed for comparison
12. **Score = Optimal Cost - Player's Path Cost** (positive = better, negative = worse)

**Scoring for Level 2:**
- score = avg_cost - player_cost
- If player chose better path: positive points
- If player chose worse path: negative points
- TTL remaining bonus: each remaining hop = +1 bonus point

---

### Level 3 — "Decapsulate at Destination"
**Concept taught:** Decapsulation, reverse OSI traversal, payload extraction

**Step-by-step flow:**
1. Destination server receives the packet — shown as an animated delivery
2. Reverse encapsulation: player **clicks to unwrap** each layer
3. Each click removes one layer (L1 → L2 → ... → L7) showing the header being discarded
4. Final unwrap reveals the original message
5. **Score** based on speed of correct unwrapping

---

### Level 4 — "Send Confirmation (ACK)"
**Concept taught:** Acknowledgements, return path, TCP reliability

**Step-by-step flow:**
1. Server generates an **ACK packet** automatically
2. The ACK travels back along the **exact same path** the user chose in Level 2
3. Animated journey shown in reverse on the topology
4. Each hop is highlighted as the ACK returns
5. When ACK reaches the source PC — "Connection Confirmed!"
6. Game ends — **Final Score Summary** shown

---

## 5. SCORING SYSTEM — DETAILED DESIGN

### Philosophy
The score is based on **path cost efficiency** relative to the average player's performance or a fixed benchmark.

### Formula

```
level_score = base_points + (avg_path_cost - player_path_cost) x multiplier
```

Where:
- `base_points` = 100 (awarded for completing the level)
- `avg_path_cost` = pre-set average (e.g., 8 for the routing level — midpoint between best and worst paths)
- `player_path_cost` = total cost of edges the player traversed
- `multiplier` = 10 (scale factor, adjustable)

### Score Examples

| Scenario | Optimal Cost | Player Cost | Score Delta | Final Level Score |
|----------|-------------|-------------|-------------|-------------------|
| Player chose optimal path | 7 | 7 | +0 | 100 |
| Player chose suboptimal | 7 | 11 | -40 | 60 |
| TTL expired (failed) | 7 | infinity | -100 | 0 |

### Total Score
```
total_score = level1_score + level2_score + level3_score + level4_score
max_possible = 400
```

---

## 6. GRAPH TOPOLOGY (Routing Level)

### Nodes

| Node ID | Label | Type |
|---------|-------|------|
| `pc` | PC-01 (192.168.1.10) | Source Host |
| `isp_sw` | ISP Switch | Layer-2 Switch |
| `r1` | Router R1 | Router |
| `r2` | Router R2 | Router |
| `r3` | Core Router R3 | Router |
| `dest_sw` | Dest Switch | Layer-2 Switch |
| `server` | Server-01 (10.0.0.20) | Destination Host |

### Edges and Costs

```
pc       → isp_sw  : cost 1
isp_sw   → r1      : cost 2
isp_sw   → r2      : cost 5   <- higher cost alternative
r1       → r3      : cost 2
r2       → r3      : cost 3
r3       → dest_sw : cost 1
dest_sw  → server  : cost 1
```

### Dijkstra's Optimal Path

```
pc → isp_sw → r1 → r3 → dest_sw → server
Total cost = 1 + 2 + 2 + 1 + 1 = 7
```

### Link Failure Scenario
- **Link that fails:** r1 → r3 (breaks mid-journey at hop 3)
- **Reroute required:** Player must go back to r1 → isp_sw → r2 → r3
- **Alternative cost:** 1 + 5 + 3 + 1 + 1 = 11 (higher, score penalty)

---

## 7. UI AND VISUAL DESIGN PLAN

### Design Language
- **Dark mode** — deep navy/space theme (#080d18)
- **Neon cyan and violet accents** (#55e6ff, #b28cff)
- **Glassmorphism panels** for layer inspector
- **Green glow** for success/delivered (#62edb2)
- **Red pulse** for link failure / TTL warning (#ff6b82)
- **Amber** for TTL countdown warning (#ffc86b)
- **Font:** Inter (Google Fonts) — modern, clean

### Screen Layout per Level

```
+------------------------------------------------------+
|  HEADER: Logo | Level Indicator | Score | TTL Bar   |
+------------------------------------------------------+
|                                                      |
|          MAIN GAME CANVAS (center)                   |
|   - Level 1: Compose + drag-and-drop layers          |
|   - Level 2: Network topology SVG + packet dot       |
|   - Level 3: Decapsulation unwrap UI                 |
|   - Level 4: ACK return animation                    |
|                                                      |
+-----------------+------------------------------------+
|  INSPECTOR      |  EVENT LOG / CONCEPT EXPLAINER    |
|  (Protocol      |  (what is happening + why)        |
|   fields)       |                                   |
+-----------------+------------------------------------+
```

---

## 8. IMPLEMENTATION PLAN — STEP BY STEP

### Step 1 — Set Up Game Shell
- Create a new `index.html` (overwrite existing)
- Define CSS variables (colors, fonts, spacing)
- Create a level state machine: `{ currentLevel, score, ttl, path }`
- Render a level router function: `renderLevel(n)`

### Step 2 — Build Level 1: Compose and Encapsulate
- Text input area for the message
- Protocol selector (TCP / UDP)
- 7 OSI layer "envelopes" rendered as stacked cards
- Drag-and-drop: `dragstart`, `dragover`, `drop` events on HTML5 Drag API
- Animation: each layer wraps around previous using CSS transitions
- Layer inspector: shows what header was added at each layer
- "Send" button transitions to Level 2

### Step 3 — Build the Network Topology (SVG)
- Draw nodes and edges as SVG elements
- Label each edge with its cost
- Highlight nodes on hover with glow effects
- Track user-clicked path in order (adjacency-validated)

### Step 4 — Build Level 2: Routing + TTL
- Render topology SVG
- Start TTL countdown: `setInterval` decrementing TTL display (amber → red as it drops)
- On node click: validate if adjacent, add to path, accumulate cost, animate packet dot
- At hop 3: trigger `linkFailure()` — remove edge from graph, color link red
- Show floating alert "Link Down! Reroute required!"
- On reaching destination: stop TTL, calculate score
- Reveal Dijkstra optimal path for comparison overlay

### Step 5 — Build Level 3: Decapsulate
- Show received packet as layered stack (L1 outermost)
- On each click: animate unwrapping from L1 → L7
- Show what header was removed at each step with a tooltip
- Reveal original payload at L7 with confetti / celebration

### Step 6 — Build Level 4: ACK Return
- Auto-animate packet dot along reversed user-path
- Show each hop highlighted with a trail
- On arrival at PC: show "ACK Received — Connection Established" banner

### Step 7 — Score Summary Screen
- Show score per level in a breakdown table
- Compare user path cost vs. optimal path cost
- Show total score out of 400
- "Play Again" button resets all state

### Step 8 — Polish and UX
- Add micro-animations (pulse on active node, glow on packet)
- Transition animations between levels (slide or fade)
- Mobile-responsive layout with CSS grid
- Tooltips on every network concept term using `title` attributes and custom CSS tooltips
- Sound cues (optional, using Web Audio API beeps for hop/fail events)

---

## 9. KEY TECHNICAL DECISIONS

| Decision | Choice | Reason |
|----------|--------|--------|
| Framework | None (Vanilla JS) | Self-contained, no install needed |
| Rendering | SVG + CSS | Crisp, scalable, animatable |
| Drag and Drop | HTML5 Drag and Drop API | Native, no dependencies |
| Routing Algorithm | Dijkstra in JS | Already in existing file |
| Scoring | Cost-delta formula | Fair, teaches path optimality |
| Game State | Single JS object | Simple, no Redux needed |
| Level Transitions | CSS class toggling + transitions | Smooth, lightweight |
| Timer | setInterval | Simple TTL countdown |

---

## 10. CONCEPT GLOSSARY (In-Game Tooltips)

| Term | Definition |
|------|-----------|
| **OSI Model** | 7-layer reference model for network communication |
| **Encapsulation** | Adding headers at each layer as data moves down the stack |
| **Decapsulation** | Removing headers as data moves up the stack at receiver |
| **TTL** | Time To Live — a counter that prevents packets from looping forever |
| **Routing** | Selecting the best path through a network of routers |
| **Dijkstra** | Algorithm to find shortest/cheapest path in a weighted graph |
| **Hop** | Each router a packet passes through counts as one hop |
| **Link Cost** | A weight representing delay, bandwidth, or congestion on a link |
| **ACK** | Acknowledgement — sent back to confirm data was received |
| **TCP** | Transmission Control Protocol — reliable, connection-oriented |
| **UDP** | User Datagram Protocol — fast, connectionless, no guaranteed delivery |
| **IP Address** | Logical address used to identify devices across networks |
| **MAC Address** | Physical hardware address used within a local network segment |
| **PDU** | Protocol Data Unit — name of data at each OSI layer (frame, packet, segment) |

---

## 11. FILE STRUCTURE AFTER BUILD

```
packet-path-osi-simulator/

|-- game.py          <- Python main logic using pygame
|-- word.md          <- This document
`-- README.md        <- Project readme
```

---

## 12. ACCEPTANCE CRITERIA

- [ ] Player can type a message and see it encapsulated through 7 OSI layers interactively
- [ ] Drag-and-drop into envelope works with visual feedback
- [ ] Network topology is rendered as SVG with labeled costs on edges
- [ ] Player can click to choose routing path hop by hop
- [ ] TTL countdown is visible and decrements per hop
- [ ] A link breaks mid-route (visual red line) and player must reroute
- [ ] Packet reaches destination with success animation
- [ ] Decapsulation shows layer-by-layer unwrapping with header details
- [ ] ACK travels back along user's chosen path automatically
- [ ] Score is calculated and displayed after each level
- [ ] Final score summary compares player cost vs optimal Dijkstra cost
- [ ] Game is fully self-contained (open index.html in browser, no server needed)
- [ ] Dark mode, neon aesthetic, smooth animations throughout
- [ ] All networking terms have tooltip explanations in context
