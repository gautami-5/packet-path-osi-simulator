# PACKET PATH — OSI Transmission Lab

A self-contained, browser-based educational OSI message-transmission simulator.

## Run on macOS
1. Unzip the project.
2. Open the `packet_path_osi_simulator` folder in VS Code.
3. Open `index.html` in a browser. You can double-click it in Finder, or use the VS Code Live Server extension.
4. Enter a message and click **Transmit Message**.

No npm install, backend, or internet connection is required.

## Features
- Seven OSI layers with selectable explanations
- Sender-side encapsulation and receiver-side decapsulation
- Dijkstra shortest-path route selection on a predefined weighted graph
- Animated packet journey through source, switches, and routers
- TCP/UDP selection and illustrative packet inspector
- Guided and Explore modes, pause/resume, step forward, speed selection
- Event timeline, payload byte count, simulated elapsed time, and delivery result
- Responsive dark interface

## Important academic limitation
This is a client-side simulation. It does not transmit actual network packets. Protocol headers, MAC addresses, TTL, and frame details are illustrative. Layers 5 and 6 are shown as conceptual OSI responsibilities. Dijkstra is used to demonstrate shortest-path routing; this is not a complete implementation of OSPF or a real router.
