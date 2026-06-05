"""
Glasses-Optimized Hanoi UI
This runs alongside your existing app.py on the same Flask server
Access from Ray-Ban Display glasses at: http://192.168.1.105:5000/glasses
"""

from flask import Flask, render_template_string, jsonify

# Import your existing app STATE from app.py
# For now, we'll create a simple version
import socket
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

# =========================================================
# MINIMAL STATE (same as app.py but simplified)
# =========================================================
@dataclass
class FrameState:
    packet_count: int = 0
    pressure: list[float] = field(default_factory=lambda: [0.0] * 40)
    mean_pressure: float = 0.0
    max_pressure: float = 0.0

@dataclass
class DetectionState:
    finger_values: dict[str, float] = field(default_factory=dict)
    finger_active: dict[str, bool] = field(default_factory=dict)
    active_finger_count: int = 0
    ring_candidate: int | None = None
    status: str = "Waiting for ring pickup."
    warning: str | None = None

@dataclass
class GameState:
    pegs: dict[str, list[int]] = field(default_factory=lambda: {"A": [4, 3, 2, 1], "B": [], "C": []})
    move_index: int = 0
    in_hand: int | None = None
    completed: bool = False

class AppState:
    def __init__(self):
        self.lock = threading.Lock()
        self.frame = FrameState()
        self.detect = DetectionState()
        self.game = GameState()
        self.moves = [
            {"ring": 1, "source": "A", "target": "B"},
            {"ring": 2, "source": "A", "target": "C"},
            {"ring": 1, "source": "B", "target": "C"},
            {"ring": 3, "source": "A", "target": "B"},
            {"ring": 1, "source": "C", "target": "A"},
            {"ring": 2, "source": "C", "target": "B"},
            {"ring": 1, "source": "A", "target": "B"},
        ]

    def expected_move(self):
        if self.game.move_index >= len(self.moves):
            return None
        return self.moves[self.game.move_index]

    def current_instruction(self) -> str:
        move = self.expected_move()
        if move is None:
            return "Puzzle solved!"
        return f"Pick ring {move['ring']} from peg {move['source']} and place it on peg {move['target']}."

STATE = AppState()

# =========================================================
# GLASSES UI - Optimized for monocular 400x400px display
# =========================================================
GLASSES_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hanoi - Glasses</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            width: 400px;
            height: 400px;
            background: #07111d;
            color: #ecf3ff;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            overflow: hidden;
            padding: 12px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .container {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 8px;
            overflow-y: auto;
        }

        .header {
            font-size: 16px;
            font-weight: bold;
            color: #6fe7da;
        }

        .section {
            background: rgba(10, 20, 34, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 8px;
            font-size: 13px;
        }

        .instruction {
            background: rgba(99, 174, 252, 0.15);
            border-left: 3px solid #63aefc;
            padding: 8px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            line-height: 1.3;
            min-height: 50px;
            display: flex;
            align-items: center;
        }

        .warning {
            background: rgba(255, 183, 97, 0.2);
            color: #ffb761;
            border-left: 3px solid #ffb761;
            padding: 6px;
            border-radius: 6px;
            font-size: 11px;
            display: none;
        }

        .warning.show {
            display: block;
        }

        .status-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 6px;
            font-size: 12px;
        }

        .status-item {
            background: rgba(20, 30, 50, 0.6);
            padding: 6px;
            border-radius: 6px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .status-label {
            color: #8ea4bf;
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .status-value {
            color: #ecf3ff;
            font-weight: bold;
            font-size: 14px;
            margin-top: 2px;
        }

        .pegs {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 6px;
            font-size: 12px;
        }

        .peg {
            background: rgba(20, 30, 50, 0.6);
            padding: 6px;
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            text-align: center;
        }

        .peg-label {
            color: #8ea4bf;
            font-size: 11px;
            font-weight: bold;
        }

        .peg-rings {
            color: #6fe7da;
            font-weight: bold;
            margin-top: 4px;
        }

        .peg.active {
            border-color: #6fe7da;
            background: rgba(111, 231, 218, 0.1);
            box-shadow: 0 0 8px rgba(111, 231, 218, 0.2);
        }

        .peg.source {
            border-color: #63aefc;
            background: rgba(99, 174, 252, 0.1);
        }

        .peg.target {
            border-color: #6fe7da;
            background: rgba(111, 231, 218, 0.15);
        }

        .hand-state {
            background: rgba(20, 30, 50, 0.6);
            padding: 6px;
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            font-size: 12px;
        }

        .hand-state.holding {
            background: rgba(255, 183, 97, 0.15);
            border-color: #ffb761;
            color: #ffb761;
        }

        .finger-state {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 4px;
            font-size: 10px;
        }

        .finger {
            background: rgba(20, 30, 50, 0.6);
            padding: 4px;
            border-radius: 6px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .finger.active {
            background: rgba(111, 231, 218, 0.2);
            border-color: #6fe7da;
            color: #6fe7da;
            font-weight: bold;
        }

        .footer {
            font-size: 11px;
            color: #8ea4bf;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            padding-top: 6px;
            text-align: center;
        }

        .move-counter {
            background: rgba(99, 174, 252, 0.1);
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 11px;
            text-align: center;
            border: 1px solid rgba(99, 174, 252, 0.2);
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">🗼 Tower of Hanoi</div>

        <!-- Move Counter -->
        <div class="move-counter" id="moveCounter">Move 1/7</div>

        <!-- Main Instruction -->
        <div class="instruction" id="instruction">
            Pick ring 1 from peg A and place it on peg B.
        </div>

        <!-- Warning -->
        <div class="warning" id="warning"></div>

        <!-- Ring Status -->
        <div class="section">
            <div class="status-row">
                <div class="status-item">
                    <div class="status-label">Expected Ring</div>
                    <div class="status-value" id="expectedRing">Ring 1</div>
                </div>
                <div class="status-item">
                    <div class="status-label">In Hand</div>
                    <div class="status-value" id="inHand">None</div>
                </div>
            </div>
        </div>

        <!-- Peg State -->
        <div class="section">
            <div style="color: #8ea4bf; font-size: 10px; margin-bottom: 6px; text-transform: uppercase;">Pegs</div>
            <div class="pegs">
                <div class="peg" id="pegA">
                    <div class="peg-label">A</div>
                    <div class="peg-rings" id="pegA-rings">4,3,2,1</div>
                </div>
                <div class="peg" id="pegB">
                    <div class="peg-label">B</div>
                    <div class="peg-rings" id="pegB-rings">—</div>
                </div>
                <div class="peg" id="pegC">
                    <div class="peg-label">C</div>
                    <div class="peg-rings" id="pegC-rings">—</div>
                </div>
            </div>
        </div>

        <!-- Hand State -->
        <div class="hand-state" id="handState">
            Status: Waiting for hand activation
        </div>

        <!-- Finger States (compact) -->
        <div class="section">
            <div style="color: #8ea4bf; font-size: 10px; margin-bottom: 4px; text-transform: uppercase;">Fingers</div>
            <div class="finger-state" id="fingerState">
                <div class="finger">👍</div>
                <div class="finger">👆</div>
                <div class="finger">🖕</div>
                <div class="finger">👉</div>
                <div class="finger">✋</div>
            </div>
        </div>

        <!-- Live Metrics (minimal) -->
        <div class="section" style="font-size: 11px;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px;">
                <div>
                    <div style="color: #8ea4bf;">Max Pressure</div>
                    <div style="color: #63aefc; font-weight: bold;" id="maxPressure">0</div>
                </div>
                <div>
                    <div style="color: #8ea4bf;">Active Fingers</div>
                    <div style="color: #6fe7da; font-weight: bold;" id="activeFingersCount">0</div>
                </div>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <div class="footer" id="footer">Initializing...</div>

    <script>
        const POLL_MS = 200;  // Poll every 200ms for glasses (less aggressive)

        async function updateUI() {
            try {
                const response = await fetch('/api/state', { cache: 'no-store' });
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                
                const state = await response.json();

                // Update instruction
                document.getElementById('instruction').textContent = state.instruction || '—';

                // Update move counter
                const moveNum = state.game.move_index + 1;
                const totalMoves = 7;
                document.getElementById('moveCounter').textContent = `Move ${moveNum}/${totalMoves}`;

                // Update ring status
                if (state.expected_move) {
                    document.getElementById('expectedRing').textContent = `Ring ${state.expected_move.ring}`;
                } else {
                    document.getElementById('expectedRing').textContent = 'Done';
                }

                document.getElementById('inHand').textContent = 
                    state.game.in_hand === null ? 'None' : `Ring ${state.game.in_hand}`;

                // Update pegs
                const pegLetters = ['A', 'B', 'C'];
                pegLetters.forEach(letter => {
                    const pegEl = document.getElementById(`peg${letter}`);
                    const rings = state.game.pegs[letter] || [];
                    document.getElementById(`peg${letter}-rings`).textContent = 
                        rings.length > 0 ? rings.join(',') : '—';

                    // Highlight pegs
                    pegEl.classList.remove('source', 'target', 'active');
                    if (state.expected_move) {
                        if (state.expected_move.source === letter) {
                            pegEl.classList.add('source');
                        }
                        if (state.expected_move.target === letter) {
                            pegEl.classList.add('target');
                        }
                    }
                });

                // Update hand state
                const handEl = document.getElementById('handState');
                if (state.game.in_hand !== null) {
                    handEl.textContent = `Holding: Ring ${state.game.in_hand}`;
                    handEl.classList.add('holding');
                } else {
                    handEl.textContent = `Status: ${state.detect.status || 'Waiting'}`;
                    handEl.classList.remove('holding');
                }

                // Update warning
                const warningEl = document.getElementById('warning');
                if (state.detect.warning) {
                    warningEl.textContent = state.detect.warning;
                    warningEl.classList.add('show');
                } else {
                    warningEl.classList.remove('show');
                }

                // Update finger states (simplified)
                const fingerEls = document.querySelectorAll('.finger');
                const fingerNames = ['thumb', 'index', 'middle', 'ring', 'little'];
                const emojis = ['👍', '👆', '🖕', '👉', '✋'];
                
                fingerNames.forEach((name, idx) => {
                    const el = fingerEls[idx];
                    const isActive = state.detect.finger_active[name] || false;
                    el.classList.toggle('active', isActive);
                    el.textContent = emojis[idx];
                    el.title = `${name}: ${Math.round(state.detect.finger_values[name] || 0)}`;
                });

                // Update metrics
                document.getElementById('maxPressure').textContent = Math.round(state.frame.max_pressure || 0);
                document.getElementById('activeFingersCount').textContent = state.detect.active_finger_count;

                // Update footer
                const completed = state.game.completed ? '✓ Complete' : '◌ Active';
                const packets = state.frame.packet_count || 0;
                document.getElementById('footer').textContent = `${completed} • ${packets} packets`;

            } catch (error) {
                console.error('Update failed:', error);
                document.getElementById('footer').textContent = 'Connection error';
            }
        }

        // Initial update
        updateUI();

        // Poll for updates
        setInterval(updateUI, POLL_MS);
    </script>
</body>
</html>
"""

app = Flask(__name__)

@app.route('/glasses')
def glasses_ui():
    """Glasses-optimized UI endpoint"""
    return render_template_string(GLASSES_HTML)

@app.route('/api/state')
def api_state():
    """Shared state endpoint (same as main app)"""
    with STATE.lock:
        return jsonify({
            "instruction": STATE.current_instruction(),
            "expected_move": STATE.expected_move(),
            "frame": {
                "packet_count": STATE.frame.packet_count,
                "pressure": STATE.frame.pressure,
                "mean_pressure": STATE.frame.mean_pressure,
                "max_pressure": STATE.frame.max_pressure,
            },
            "detect": {
                "finger_values": STATE.detect.finger_values,
                "finger_active": STATE.detect.finger_active,
                "active_finger_count": STATE.detect.active_finger_count,
                "ring_candidate": STATE.detect.ring_candidate,
                "status": STATE.detect.status,
                "warning": STATE.detect.warning,
            },
            "game": {
                "pegs": STATE.game.pegs,
                "move_index": STATE.game.move_index,
                "in_hand": STATE.game.in_hand,
                "completed": STATE.game.completed,
            },
        })

@app.route('/api/reset', methods=['POST'])
def api_reset():
    """Reset game state"""
    with STATE.lock:
        STATE.game = GameState()
        STATE.detect = DetectionState()
    return jsonify({"ok": True})

if __name__ == "__main__":
    # Run on port 5000
    print("\n" + "="*60)
    print("Glasses-Optimized Hanoi UI")
    print("="*60)
    print("\n✅ Desktop UI: http://192.168.1.105:5000/")
    print("✅ Glasses UI:  http://192.168.1.105:5000/glasses")
    print("\n📱 Open /glasses in Ray-Ban Display glasses")
    print("🖥️  Desktop browser works for testing")
    print("\n" + "="*60 + "\n")
    
    app.run(host="127.0.0.1", port=5000, debug=False)
