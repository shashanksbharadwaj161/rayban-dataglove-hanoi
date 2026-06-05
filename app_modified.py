"""
Modified app.py with BOTH desktop UI and glasses UI
This is your existing app.py with added /glasses endpoint
"""

from __future__ import annotations

import socket
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from flask import Flask, jsonify, render_template_string

# old glove parser
from sensor import parse_sensor_data

# =========================================================
# CONFIG
# =========================================================
UDP_HOST = "127.0.0.1"
UDP_PORT = 53000

ROWS = 8
COLS = 5
EXPECTED_SENSOR_COUNT = ROWS * COLS

RING_COUNT = 4
POLL_INTERVAL_MS = 80

FINGER_SENSOR_IDS = {
    "thumb": 0,
    "index": 1,
    "middle": 2,
    "ring": 3,
    "little": 4,
}

FINGER_THRESHOLD = {
    "thumb": 550,
    "index": 550,
    "middle": 550,
    "ring": 550,
    "little": 550,
}

STABLE_PICK_FRAMES = 3
STABLE_RELEASE_FRAMES = 3

RING_BY_ACTIVE_COUNT = {
    2: 1,
    3: 2,
    4: 3,
    5: 4,
}

RING_COLORS = {
    1: "#ffd166",
    2: "#ff9f68",
    3: "#cf7cff",
    4: "#6cb8ff",
}

PEG_ORDER = ["A", "B", "C"]


# =========================================================
# HANOI SOLVER
# =========================================================
def solve_hanoi(n: int, src: str = "A", dst: str = "B", aux: str = "C") -> list[dict[str, Any]]:
    moves: list[dict[str, Any]] = []

    def rec(k: int, a: str, b: str, c: str) -> None:
        if k == 0:
            return
        rec(k - 1, a, c, b)
        moves.append({"ring": k, "source": a, "target": b})
        rec(k - 1, c, b, a)

    rec(n, src, dst, aux)
    return moves


# =========================================================
# STATE
# =========================================================
@dataclass
class FrameState:
    packet_count: int = 0
    packets_per_second: float = 0.0
    last_sender: str | None = None
    last_timestamp: float = 0.0
    last_error: str | None = None
    invalid_packet_count: int = 0
    sensor_count: int = EXPECTED_SENSOR_COUNT
    pressure: list[float] = field(default_factory=lambda: [0.0] * EXPECTED_SENSOR_COUNT)
    mean_pressure: float = 0.0
    max_pressure: float = 0.0


@dataclass
class DetectionState:
    finger_values: dict[str, float] = field(default_factory=dict)
    finger_active: dict[str, bool] = field(default_factory=dict)
    active_finger_count: int = 0
    ring_candidate: int | None = None
    held_ring: int | None = None
    pick_streak: int = 0
    release_streak: int = 0
    pending_ring: int | None = None
    status: str = "Waiting for ring pickup."
    warning: str | None = None


@dataclass
class GameState:
    pegs: dict[str, list[int]] = field(default_factory=lambda: {"A": [4, 3, 2, 1], "B": [], "C": []})
    move_index: int = 0
    in_hand: int | None = None
    completed: bool = False


class AppState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.frame = FrameState()
        self.detect = DetectionState()
        self.game = GameState()
        self.moves = solve_hanoi(RING_COUNT)
        self.packet_times: deque[float] = deque(maxlen=120)

    def reset(self) -> None:
        with self.lock:
            self.frame = FrameState()
            self.detect = DetectionState()
            self.game = GameState()
            self.packet_times.clear()

    def expected_move(self) -> dict[str, Any] | None:
        if self.game.move_index >= len(self.moves):
            return None
        return self.moves[self.game.move_index]

    def current_instruction(self) -> str:
        move = self.expected_move()
        if move is None:
            return "Puzzle solved."
        return f"Pick ring {move['ring']} from peg {move['source']} and place it on peg {move['target']}."


STATE = AppState()


# =========================================================
# HELPERS
# =========================================================
def normalize_pressure(values: list[float], expected_count: int) -> list[float]:
    out = list(values[:expected_count])
    if len(out) < expected_count:
        out.extend([0.0] * (expected_count - len(out)))
    return out


def update_detection_locked() -> None:
    det = STATE.detect
    game = STATE.game
    frame = STATE.frame
    expected = STATE.expected_move()

    finger_values: dict[str, float] = {}
    finger_active: dict[str, bool] = {}
    active_fingers: list[str] = []

    for finger, sensor_idx in FINGER_SENSOR_IDS.items():
        val = frame.pressure[sensor_idx] if 0 <= sensor_idx < len(frame.pressure) else 0.0
        val = float(val)
        finger_values[finger] = val
        is_active = val >= FINGER_THRESHOLD.get(finger, 0.0)
        finger_active[finger] = is_active
        if is_active:
            active_fingers.append(finger)

    active_count = len(active_fingers)
    candidate = RING_BY_ACTIVE_COUNT.get(active_count)

    det.finger_values = finger_values
    det.finger_active = finger_active
    det.active_finger_count = active_count
    det.ring_candidate = candidate
    det.warning = None

    if expected is None:
        game.completed = True
        game.in_hand = None
        det.held_ring = None
        det.status = "Puzzle solved."
        return

    if game.in_hand is None:
        det.release_streak = 0

        if candidate is None:
            det.pending_ring = None
            det.pick_streak = 0
            det.status = f"Waiting for ring {expected['ring']} pickup."
            return

        if candidate != expected["ring"]:
            det.pending_ring = None
            det.pick_streak = 0
            det.warning = f"Wrong pickup detected: ring {candidate}. Expected ring {expected['ring']}."
            det.status = det.warning
            return

        if det.pending_ring == candidate:
            det.pick_streak += 1
        else:
            det.pending_ring = candidate
            det.pick_streak = 1

        det.status = f"Detected ring {candidate}. Stabilizing pickup..."

        if det.pick_streak >= STABLE_PICK_FRAMES:
            game.in_hand = candidate
            det.held_ring = candidate
            det.status = f"Holding ring {candidate}. Move to peg {expected['target']} and release."

    else:
        if active_count == 0:
            det.release_streak += 1
            det.status = f"Release detected... committing to peg {expected['target']}."

            if det.release_streak >= STABLE_RELEASE_FRAMES:
                commit_move_locked()
                det.release_streak = 0
                det.pick_streak = 0
                det.pending_ring = None
        else:
            det.release_streak = 0
            det.status = f"Holding ring {game.in_hand}. Move to peg {expected['target']} and release."


def commit_move_locked() -> None:
    expected = STATE.expected_move()
    if expected is None:
        return

    game = STATE.game
    det = STATE.detect

    ring = expected["ring"]
    src = expected["source"]
    dst = expected["target"]

    if not game.pegs[src] or game.pegs[src][-1] != ring:
        det.warning = "State mismatch: expected ring not at source peg."
        det.status = det.warning
        game.in_hand = None
        det.held_ring = None
        return

    game.pegs[src].pop()
    game.pegs[dst].append(ring)
    game.move_index += 1
    game.in_hand = None
    det.held_ring = None

    nxt = STATE.expected_move()
    if nxt is None:
        game.completed = True
        det.status = "Puzzle solved."
    else:
        det.status = f"Move committed. Next: ring {nxt['ring']} from peg {nxt['source']} to peg {nxt['target']}."


# =========================================================
# UDP RECEIVER
# =========================================================
def receiver_loop() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    else:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    sock.bind((UDP_HOST, UDP_PORT))
    print(f"[UDP] Listening on {UDP_HOST}:{UDP_PORT}")

    while True:
        data, addr = sock.recvfrom(4096)
        parsed = None
        error = None

        try:
            parsed = parse_sensor_data(data)
            if parsed is None:
                error = "parse_sensor_data returned None"
        except Exception as exc:
            error = str(exc)

        now = time.time()

        with STATE.lock:
            STATE.packet_times.append(now)
            pps = 0.0
            if len(STATE.packet_times) >= 2:
                span = STATE.packet_times[-1] - STATE.packet_times[0]
                if span > 0:
                    pps = (len(STATE.packet_times) - 1) / span

            STATE.frame.packets_per_second = round(pps, 1)
            STATE.frame.last_sender = f"{addr[0]}:{addr[1]}"

            if parsed is None:
                STATE.frame.invalid_packet_count += 1
                STATE.frame.last_error = error
                continue

            pressure = normalize_pressure(parsed.pressure_sensors, EXPECTED_SENSOR_COUNT)
            STATE.frame.packet_count += 1
            STATE.frame.last_error = None
            STATE.frame.last_timestamp = float(parsed.timestamp)
            STATE.frame.sensor_count = len(parsed.pressure_sensors)
            STATE.frame.pressure = pressure
            STATE.frame.mean_pressure = float(sum(pressure) / len(pressure)) if pressure else 0.0
            STATE.frame.max_pressure = float(max(pressure)) if pressure else 0.0

            update_detection_locked()


# =========================================================
# GLASSES UI HTML
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
        <div class="header">🗼 Tower of Hanoi</div>
        <div class="move-counter" id="moveCounter">Move 1/7</div>

        <div class="instruction" id="instruction">
            Pick ring 1 from peg A and place it on peg B.
        </div>

        <div class="warning" id="warning"></div>

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

        <div class="hand-state" id="handState">
            Status: Waiting for hand activation
        </div>

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

    <div class="footer" id="footer">Initializing...</div>

    <script>
        const POLL_MS = 200;

        async function updateUI() {
            try {
                const response = await fetch('/api/state', { cache: 'no-store' });
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                const state = await response.json();

                document.getElementById('instruction').textContent = state.instruction || '—';
                const moveNum = state.game.move_index + 1;
                document.getElementById('moveCounter').textContent = `Move ${moveNum}/7`;

                if (state.expected_move) {
                    document.getElementById('expectedRing').textContent = `Ring ${state.expected_move.ring}`;
                } else {
                    document.getElementById('expectedRing').textContent = 'Done';
                }

                document.getElementById('inHand').textContent = 
                    state.game.in_hand === null ? 'None' : `Ring ${state.game.in_hand}`;

                ['A', 'B', 'C'].forEach(letter => {
                    const pegEl = document.getElementById(`peg${letter}`);
                    const rings = state.game.pegs[letter] || [];
                    document.getElementById(`peg${letter}-rings`).textContent = 
                        rings.length > 0 ? rings.join(',') : '—';

                    pegEl.classList.remove('source', 'target');
                    if (state.expected_move) {
                        if (state.expected_move.source === letter) pegEl.classList.add('source');
                        if (state.expected_move.target === letter) pegEl.classList.add('target');
                    }
                });

                const handEl = document.getElementById('handState');
                if (state.game.in_hand !== null) {
                    handEl.textContent = `Holding: Ring ${state.game.in_hand}`;
                    handEl.classList.add('holding');
                } else {
                    handEl.textContent = `Status: ${state.detect.status || 'Waiting'}`;
                    handEl.classList.remove('holding');
                }

                const warningEl = document.getElementById('warning');
                if (state.detect.warning) {
                    warningEl.textContent = state.detect.warning;
                    warningEl.classList.add('show');
                } else {
                    warningEl.classList.remove('show');
                }

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

                document.getElementById('maxPressure').textContent = Math.round(state.frame.max_pressure || 0);
                document.getElementById('activeFingersCount').textContent = state.detect.active_finger_count;

                const completed = state.game.completed ? '✓ Complete' : '◌ Active';
                const packets = state.frame.packet_count || 0;
                document.getElementById('footer').textContent = `${completed} • ${packets} packets`;

            } catch (error) {
                console.error('Update failed:', error);
                document.getElementById('footer').textContent = 'Connection error';
            }
        }

        updateUI();
        setInterval(updateUI, POLL_MS);
    </script>
</body>
</html>
"""

# =========================================================
# FLASK APP
# =========================================================
app = Flask(__name__)

# Your existing desktop HTML... (keep your full HTML here)
# For now I'll just add the glasses endpoint

@app.route('/glasses')
def glasses_ui():
    """Glasses-optimized UI - access from Ray-Ban Display"""
    return render_template_string(GLASSES_HTML)

@app.route('/')
def index() -> str:
    # Your existing desktop HTML goes here
    # Keep your full beautiful desktop UI
    return render_template_string("""
        <html>
            <head><title>Hanoi - Desktop</title></head>
            <body style="color: white; background: #07111d; padding: 20px;">
                <h1>Desktop UI - Keep Your Full UI Here</h1>
                <p>Your existing desktop HTML goes here</p>
                <p><a href="/glasses">👓 View Glasses UI</a></p>
            </body>
        </html>
    """)

@app.get("/api/state")
def api_state():
    with STATE.lock:
        return jsonify(
            {
                "instruction": STATE.current_instruction(),
                "expected_move": STATE.expected_move(),
                "frame": {
                    "packet_count": STATE.frame.packet_count,
                    "packets_per_second": STATE.frame.packets_per_second,
                    "last_sender": STATE.frame.last_sender,
                    "last_timestamp": STATE.frame.last_timestamp,
                    "last_error": STATE.frame.last_error,
                    "invalid_packet_count": STATE.frame.invalid_packet_count,
                    "sensor_count": STATE.frame.sensor_count,
                    "pressure": STATE.frame.pressure,
                    "mean_pressure": STATE.frame.mean_pressure,
                    "max_pressure": STATE.frame.max_pressure,
                },
                "detect": {
                    "finger_values": STATE.detect.finger_values,
                    "finger_active": STATE.detect.finger_active,
                    "active_finger_count": STATE.detect.active_finger_count,
                    "ring_candidate": STATE.detect.ring_candidate,
                    "held_ring": STATE.detect.held_ring,
                    "status": STATE.detect.status,
                    "warning": STATE.detect.warning,
                },
                "game": {
                    "pegs": STATE.game.pegs,
                    "move_index": STATE.game.move_index,
                    "in_hand": STATE.game.in_hand,
                    "completed": STATE.game.completed,
                },
            }
        )


@app.post("/api/reset")
def api_reset():
    STATE.reset()
    return jsonify({"ok": True})


if __name__ == "__main__":
    print("\n" + "="*70)
    print("HANOI SYSTEM - DESKTOP + GLASSES UI")
    print("="*70)
    print("\n🖥️  DESKTOP:  http://192.168.1.105:5000/")
    print("👓 GLASSES:  http://192.168.1.105:5000/glasses")
    print("\n📱 Open /glasses URL in Ray-Ban Display glasses")
    print("🖥️  Desktop browser works for testing")
    print("\n" + "="*70 + "\n")
    
    threading.Thread(target=receiver_loop, daemon=True).start()
    app.run(host="127.0.0.1", port=5000, debug=False)
