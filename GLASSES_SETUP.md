# Ray-Ban Meta Display - Hanoi UI Setup Guide

## Quick Start (5 minutes)

### Option A: Use Your Existing app.py (RECOMMENDED)

1. **Copy the glasses UI code into your existing app.py**

   In your current `app.py`, find the Flask app creation section and ADD these imports at the top:

   ```python
   from flask import Flask, render_template_string
   ```

   Then ADD this endpoint before `if __name__ == "__main__":`:

   ```python
   GLASSES_HTML = r"""
   [COPY THE ENTIRE HTML STRING FROM: /home/claude/app_modified.py lines 400-650]
   """

   @app.route('/glasses')
   def glasses_ui():
       """Glasses-optimized UI - access from Ray-Ban Display"""
       return render_template_string(GLASSES_HTML)
   ```

2. **Restart Flask**
   ```bash
   python app.py
   ```

3. **Access from glasses**
   - In Ray-Ban Display: Open browser
   - Navigate to: `http://192.168.1.105:5000/glasses`
   - Bookmark it for quick access

---

### Option B: Use the New Modified App

If you want a fresh start:

```bash
# Copy the modified app
cp /home/claude/app_modified.py ./app_glasses.py

# Make sure you have your sensor.py in the same folder
# Then run it
python app_glasses.py
```

Then access:
- Desktop: `http://192.168.1.105:5000/`
- Glasses: `http://192.168.1.105:5000/glasses`

---

## What You're Getting

The `/glasses` endpoint provides:

### **Optimized for Monocular Display**
- ✅ 400x400px layout (fits glasses display)
- ✅ Large readable fonts (14-16px minimum)
- ✅ High contrast colors (dark theme)
- ✅ Minimal information density

### **Shows Real-Time Updates**
- 🔄 Current instruction
- 📊 Expected ring number
- 🤚 Finger activation states
- 📍 Peg states (A, B, C)
- 🎯 Ring in hand status
- ⚠️  Warnings

### **Refreshes Every 200ms**
- Polls `/api/state` endpoint
- Updates in real-time as glove data changes
- Responsive to pressure changes

---

## Testing Without Glasses

You can test the layout in a desktop browser:

```bash
# Resize your browser to 400x400px
# Or open DevTools and set device mode to custom 400x400
# Then view: http://192.168.1.105:5000/glasses
```

The UI is designed to look good at any size, but 400x400 is the actual glasses display resolution.

---

## How to Access from Glasses

### Step 1: Pair Glasses with Phone
- On your phone, open Meta View app
- Pair Ray-Ban Meta Display if not already done

### Step 2: Enable Developer Mode (if needed)
- In Meta View app → Settings → Developer
- Enable Developer Mode

### Step 3: Access in Glasses
- Open browser app on phone/glasses
- Navigate to: `http://192.168.1.105:5000/glasses`
- **Important:** Make sure glasses are on same WiFi as your PC!

### Step 4: Bookmark for Quick Access
- Once loaded, bookmark the URL
- Now you can access with one tap

---

## Network Setup

Make sure your setup is correct:

```
PC (Flask Server):       192.168.1.105
Glasses (same WiFi):     192.168.1.xxx
Glove ESP32 (UDP):       192.168.1.xxx
```

All on same WiFi network.

**To check your PC IP:**
```bash
# Linux/Mac
ifconfig | grep 192.168

# Windows PowerShell
ipconfig
```

Update the URL if your IP is different.

---

## What's Different from Desktop UI

| Aspect | Desktop | Glasses |
|--------|---------|---------|
| Size | Full screen | 400x400px |
| Layout | Multi-column grid | Vertical stack |
| Fonts | Small (12-15px) | Larger (13-16px) |
| Info Density | High (all data) | Low (essential only) |
| Animations | Rich, smooth | Minimal (simpler) |
| Refresh Rate | 80ms | 200ms (less intensive) |
| Colors | Full gradient | High contrast |

---

## Troubleshooting

### Page Not Loading
```
Error: Connection refused
→ Make sure Flask server is running
→ Check IP address is correct
→ Check glasses and PC are on same WiFi
```

### Updates Not Showing
```
→ Hard refresh: Ctrl+Shift+R (or Cmd+Shift+R on Mac)
→ Check network latency (look at footer for packet count)
→ Glasses display may be low bandwidth - if updates lag, it's normal
```

### Font Too Small
```
→ Browser zoom: Ctrl+Plus (or Cmd+Plus)
→ The UI is designed for 400x400, fonts should be readable
→ If still too small, you can edit CSS to increase font sizes
```

### Layout Broken
```
→ Make sure you're viewing at 400px width
→ Check browser developer tools - should show no errors
→ Clear browser cache: Ctrl+Shift+Delete
```

---

## Customization

Want to change the glasses UI? Edit the `GLASSES_HTML` string:

### Change Colors
```css
/* Find these in the <style> section */
--bg: #07111d;        /* Dark background */
--text: #ecf3ff;      /* Text color */
--cyan: #6fe7da;      /* Highlight color */
--blue: #63aefc;      /* Secondary color */
```

### Change Font Size
```css
body {
    font-size: 13px;  /* Change this */
}
```

### Reduce Update Frequency
```javascript
const POLL_MS = 200;  /* Change to 500 for less frequent updates */
```

### Add More Info
Add new sections in the HTML:
```html
<div class="section">
    <div style="color: #8ea4bf; font-size: 10px;">YOUR LABEL</div>
    <div id="your-id" style="font-size: 14px; font-weight: bold;">Data here</div>
</div>
```

Then update it in the JavaScript:
```javascript
document.getElementById('your-id').textContent = state.your_data;
```

---

## Next Steps

1. ✅ **Get basic UI working** (you are here)
2. 📸 **Add camera capture** (next phase)
3. 🤖 **Add vision AI** (to detect rings)
4. 🎮 **Add gesture input** (Neural Band EMG)
5. 🔄 **Full integration** (all sensors + display)

For now, just test that the UI appears and updates with your glove data!

---

## Need Help?

Issues?
- Check Flask console for errors
- Look at browser console (DevTools → Console)
- Check network tab (DevTools → Network) to see if `/api/state` is being called
- Verify IP address is correct

The UI should update in real-time as your glove sends pressure data through UDP.

Enjoy! 👓✨
