# ⚡ Quick Checklist - Get Glasses UI Working in 5 Minutes

## Step 1: Verify Setup ✓

- [ ] PC IP: 192.168.1.105 (or note your actual IP)
- [ ] Glasses on same WiFi network
- [ ] Flask app running: `python app.py`
- [ ] Glove connected (USB to PC)
- [ ] receive.py running (if separate)

**Check PC IP:**
```bash
# Windows PowerShell
ipconfig
# Look for: IPv4 Address: 192.168.x.x

# Linux/Mac
ifconfig | grep 192.168
```

---

## Step 2: Add Glasses UI Endpoint ✓

**Open your `app.py` file**

**At the top, make sure you have:**
```python
from flask import Flask, render_template_string, jsonify
```

**Before the line `if __name__ == "__main__":`**

Add this endpoint:

```python
# =========================================================
# GLASSES UI - Ray-Ban Meta Display
# =========================================================
GLASSES_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hanoi - Glasses</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            width: 400px; height: 400px; background: #07111d; color: #ecf3ff;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            overflow: hidden; padding: 12px; display: flex; flex-direction: column; gap: 8px;
        }
        .container { flex: 1; display: flex; flex-direction: column; gap: 8px; overflow-y: auto; }
        .header { font-size: 16px; font-weight: bold; color: #6fe7da; }
        .section { background: rgba(10,20,34,.8); border: 1px solid rgba(255,255,255,.1); 
                   border-radius: 12px; padding: 8px; font-size: 13px; }
        .instruction { background: rgba(99,174,252,.15); border-left: 3px solid #63aefc;
                       padding: 8px; border-radius: 8px; font-size: 14px; font-weight: 600;
                       line-height: 1.3; min-height: 50px; display: flex; align-items: center; }
        .warning { background: rgba(255,183,97,.2); color: #ffb761; border-left: 3px solid #ffb761;
                   padding: 6px; border-radius: 6px; font-size: 11px; display: none; }
        .warning.show { display: block; }
        .status-row { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; font-size: 12px; }
        .status-item { background: rgba(20,30,50,.6); padding: 6px; border-radius: 6px;
                       border: 1px solid rgba(255,255,255,.05); }
        .status-label { color: #8ea4bf; font-size: 10px; text-transform: uppercase; letter-spacing: .5px; }
        .status-value { color: #ecf3ff; font-weight: bold; font-size: 14px; margin-top: 2px; }
        .pegs { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; font-size: 12px; }
        .peg { background: rgba(20,30,50,.6); padding: 6px; border-radius: 8px; 
               border: 1px solid rgba(255,255,255,.1); text-align: center; }
        .peg-label { color: #8ea4bf; font-size: 11px; font-weight: bold; }
        .peg-rings { color: #6fe7da; font-weight: bold; margin-top: 4px; }
        .peg.source { border-color: #63aefc; background: rgba(99,174,252,.1); }
        .peg.target { border-color: #6fe7da; background: rgba(111,231,218,.15); }
        .hand-state { background: rgba(20,30,50,.6); padding: 6px; border-radius: 8px;
                      border: 1px solid rgba(255,255,255,.1); font-size: 12px; }
        .hand-state.holding { background: rgba(255,183,97,.15); border-color: #ffb761; color: #ffb761; }
        .finger-state { display: grid; grid-template-columns: repeat(5, 1fr); gap: 4px; font-size: 10px; }
        .finger { background: rgba(20,30,50,.6); padding: 4px; border-radius: 6px; text-align: center;
                  border: 1px solid rgba(255,255,255,.05); }
        .finger.active { background: rgba(111,231,218,.2); border-color: #6fe7da; color: #6fe7da; font-weight: bold; }
        .footer { font-size: 11px; color: #8ea4bf; border-top: 1px solid rgba(255,255,255,.1);
                  padding-top: 6px; text-align: center; }
        .move-counter { background: rgba(99,174,252,.1); padding: 4px 8px; border-radius: 6px;
                        font-size: 11px; text-align: center; border: 1px solid rgba(99,174,252,.2); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">🗼 Tower of Hanoi</div>
        <div class="move-counter" id="moveCounter">Move 1/7</div>
        <div class="instruction" id="instruction">Pick ring 1 from peg A and place it on peg B.</div>
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
                <div class="peg" id="pegA"><div class="peg-label">A</div><div class="peg-rings" id="pegA-rings">4,3,2,1</div></div>
                <div class="peg" id="pegB"><div class="peg-label">B</div><div class="peg-rings" id="pegB-rings">—</div></div>
                <div class="peg" id="pegC"><div class="peg-label">C</div><div class="peg-rings" id="pegC-rings">—</div></div>
            </div>
        </div>
        <div class="hand-state" id="handState">Status: Waiting for hand activation</div>
        <div class="section">
            <div style="color: #8ea4bf; font-size: 10px; margin-bottom: 4px; text-transform: uppercase;">Fingers</div>
            <div class="finger-state" id="fingerState">
                <div class="finger">👍</div><div class="finger">👆</div><div class="finger">🖕</div>
                <div class="finger">👉</div><div class="finger">✋</div>
            </div>
        </div>
        <div class="section" style="font-size: 11px;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px;">
                <div><div style="color: #8ea4bf;">Max Pressure</div><div style="color: #63aefc; font-weight: bold;" id="maxPressure">0</div></div>
                <div><div style="color: #8ea4bf;">Active Fingers</div><div style="color: #6fe7da; font-weight: bold;" id="activeFingersCount">0</div></div>
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
                document.getElementById('inHand').textContent = state.game.in_hand === null ? 'None' : `Ring ${state.game.in_hand}`;
                ['A', 'B', 'C'].forEach(letter => {
                    const pegEl = document.getElementById(`peg${letter}`);
                    const rings = state.game.pegs[letter] || [];
                    document.getElementById(`peg${letter}-rings`).textContent = rings.length > 0 ? rings.join(',') : '—';
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

@app.route('/glasses')
def glasses_ui():
    """Glasses-optimized UI endpoint"""
    return render_template_string(GLASSES_HTML)
```

---

## Step 3: Restart Flask ✓

```bash
# Stop current Flask (Ctrl+C)

# Restart
python app.py
```

You should see output like:
```
[UDP] Listening on 127.0.0.1:53000
 * Running on http://127.0.0.1:5000
```

---

## Step 4: Test on Desktop ✓

Open browser on your PC:

```
http://192.168.1.105:5000/glasses
```

You should see:
- 🗼 Tower of Hanoi
- Move 1/7
- Pink/purple instructions
- Three pegs (A, B, C)
- Finger emojis (👍👆🖕👉✋)

**Does it look good?** ✓ Continue

**Errors?** Check console (F12 → Console) for error messages

---

## Step 5: Access from Glasses ✓

### On Your Phone:
1. Open Meta View app
2. Ensure Ray-Ban Display is paired
3. Open web browser in Meta View

### In Browser:
1. Type or paste: `http://192.168.1.105:5000/glasses`
2. Press Enter

**Important:** Make sure to use YOUR actual IP address!

```
Not 192.168.1.105? Replace with YOUR IP from Step 1
Example: http://192.168.1.234:5000/glasses
```

---

## Step 6: Test Live Updates ✓

### While page is open on glasses:

1. **Touch your glove** (apply pressure to any sensor)
2. **Watch glasses display update:**
   - Finger emojis should turn green/cyan when active
   - "Max Pressure" number should increase
   - "Active Fingers" count should increase
   - Status should change

**Does it update?** ✓ SUCCESS! 🎉

**Doesn't update?** 
- [ ] Check Flask is receiving UDP data (look at console)
- [ ] Check network (can PC ping glasses? Can glasses reach PC?)
- [ ] Hard refresh glasses browser: Ctrl+Shift+R

---

## Step 7: Bookmark for Quick Access ✓

In glasses browser:

1. Press **menu/options button**
2. Select **Bookmark**
3. Now you can access with one tap!

---

## What You Should See

**On Glasses Display:**
```
🗼 Tower of Hanoi
Move 1/7

Pick ring 1 from peg A
and place it on peg B

Expected: Ring 1 | In Hand: None

Pegs:
A: 4,3,2,1  B: —  C: —

Status: Waiting for hand...
Fingers: 👍👆🖕👉✋

Max Pressure: 456
Active Fingers: 0

◌ Active • 1247 packets
```

---

## If Something Goes Wrong

### Error: Connection Refused
- Flask not running? → `python app.py`
- Wrong IP? → Check Step 1 again

### Error: Page Times Out
- Glasses not on WiFi? → Connect to same WiFi as PC
- Firewall blocking? → Allow Python through firewall
- Check: Can you reach `http://192.168.1.105:5000/` on desktop?

### Updates Not Showing
- Hard refresh: Ctrl+Shift+R
- Check console: F12 → Console → look for errors
- Is glove connected? → Check Flask console for UDP data

### Finger Emoji Not Lighting Up When Touching Glove
- This is the critical test!
- If emojis stay inactive when you touch glove:
  - UDP data might not be reaching Flask
  - Check `receive.py` is running
  - Check Flask can parse packets
  - Look at Flask console for errors

---

## Success Checklist ✓

- [ ] Flask running
- [ ] Glasses can access `http://192.168.1.105:5000/glasses`
- [ ] Page loads (shows Hanoi UI)
- [ ] Page updates every ~200ms (bottom shows packet count increasing)
- [ ] Touch glove → finger emojis light up
- [ ] Touch glove → "Max Pressure" increases
- [ ] Touch glove → "Active Fingers" increases
- [ ] No errors in Flask console
- [ ] No errors in glasses browser console

**All checkmarks?** 🎉 **You're done!**

Your glasses now display your Tower of Hanoi game in real-time!

---

## Next Steps

Phase 2 (optional):
1. Add camera capture (see rings)
2. Add vision AI (detect ring positions)
3. Merge pressure + vision data
4. Add gesture input (Neural Band)

For now, enjoy having your Hanoi game on your glasses! 👓✨
