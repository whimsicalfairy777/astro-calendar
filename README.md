# README.md

# Astro & Lunar Calendar Widget (Swiss Ephemeris)

This repository helps you generate a 7-year database of tropical astrological events (2025–2031) and host a web calendar widget that displays events when you click a date.

---

## 📂 Files in This Repo

```
astro-calendar/
├── ephe/                  # Swiss Ephemeris data files (.se1)
├── generate_events.py     # Python script to compute and output events.json
├── events.json            # Generated JSON database of astrological events
└── index.html             # Calendar widget that reads events.json and displays events
```

---

## 1) Install Prerequisites

1. **Install Python 3.8+** from [https://python.org](https://python.org)
   - On Windows, download the **Windows x86-64 executable installer**, check **Add Python to PATH**.
2. **Verify** installation:
   ```bash
   python --version
   ```
3. **Install** the Swiss Ephemeris Python package:
   ```bash
   python -m pip install pyswisseph backports.zoneinfo
   ```
4. **Download Ephemeris Data**:
   - Because you’ve been redirected to the GitHub mirror, you can **clone** or **download** the entire repo which already contains the `ephe/` folder with `.se1` files:
     1. On GitHub, click the **Code** button and choose **"Download ZIP"**, or copy the **HTTPS URL** and run:
        ```bash
        git clone https://github.com/aloistr/swisseph.git ephe
        ```
     2. Ensure that your local `astro-calendar` folder contains the `ephe/` directory filled with `.se1` files.
     3. Confirm with:
        ```bash
        dir ephe\*.se1
        ```
        You should see a long list of `.se1` files.

---

## 2) Generate events.json

1. **Open** a terminal/command prompt in the `astro-calendar` folder:
   ```bash
   cd path/to/astro-calendar
   ```
2. **Run** the generator script:
   ```bash
   python generate_events.py
   ```
3. After completion, a file **events.json** will appear, containing all event records in ISO timestamp (Poland local time) and description.

---

## 3) Host with GitHub Pages

1. **Create** a new GitHub repository (e.g. `astro-calendar`) and push **all files** (`ephe/`, `generate_events.py`, `events.json`, `index.html`).
2. On GitHub, go to **Settings → Pages**, select **main** branch, root, then **Save**.
3. Your site will be live at:
   ```
   https://<your-username>.github.io/astro-calendar/
   ```

---

## 4) Embed in Notion

1. In Notion, type `/embed` and choose **Embed**.
2. Paste your GitHub Pages URL.
3. The calendar widget will appear, displaying events on click.

---

# generate\_events.py

```python
import swisseph as swe
from datetime import datetime, timedelta, timezone
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except ImportError:
    from backports.zoneinfo import ZoneInfo  # for Python 3.8
import json

# 1) Setup ephemeris path
ephe_path = 'ephe'
swe.set_ephe_path(ephe_path)  # folder with .se1 files

# 2) Constants
events = []
SIGN_NAMES = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]
PLANETS = {
    'Sun': swe.SUN, 'Moon': swe.MOON,
    'Mercury': swe.MERCURY, 'Venus': swe.VENUS,
    'Mars': swe.MARS, 'Jupiter': swe.JUPITER,
    'Saturn': swe.SATURN, 'Uranus': swe.URANUS,
    'Neptune': swe.NEPTUNE, 'Pluto': swe.PLUTO
}

# 3) Helper: position and speed

def get_pos_and_speed(pid, jd):
    pos = swe.calc_ut(jd, pid)[0]
    return pos[0] % 360, pos[3]

# 4) Binary search to refine event times

def find_event(func, start, end, target):
    for _ in range(30):
        mid = (start + end) / 2
        val = func(mid) - target
        if abs(val) < 1e-6:
            return mid
        if (func(start) - target) * val < 0:
            end = mid
        else:
            start = mid
    return mid

# 5) Julian day to datetime helper

def jd_to_datetime(jd):
    # Convert Julian Day to UTC datetime, then to Warsaw time
    y, m, d, frac = swe.revjul(jd)
    total_seconds = frac * 86400.0
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    # clamp overflow
    if hours >= 24:
        hours = 23; minutes = 59; seconds = 59
    dt_utc = datetime(int(y), int(m), int(d), hours, minutes, seconds, tzinfo=timezone.utc)
    return dt_utc.astimezone(ZoneInfo('Europe/Warsaw'))

# 6) Date range and step

d_start = swe.julday(2025, 1, 1)
 d_end = swe.julday(2031, 12, 31)
step = 1.0  # one-day steps

# 7) Planetary ingresses & retro/direct stations

for name, pid in PLANETS.items():
    jd = d_start
    lon_prev, speed_prev = get_pos_and_speed(pid, jd)
    sign_prev = int(lon_prev // 30)

    while jd < d_end:
        jd_next = jd + step
        lon, speed = get_pos_and_speed(pid, jd_next)
        sign = int(lon // 30)

        # Ingress detection
        if sign != sign_prev:
            root = find_event(lambda t: swe.calc_ut(t, pid)[0][0] % 360, jd, jd_next, sign * 30)
            dt = jd_to_datetime(root)
            events.append({'datetime': dt.isoformat(), 'event': f"{name} enters {SIGN_NAMES[sign]}"})
            sign_prev = sign

        # Retrograde/direct station
        if (speed_prev > 0 and speed < 0) or (speed_prev < 0 and speed > 0):
            root = find_event(lambda t: swe.calc_ut(t, pid)[0][3], jd, jd_next, 0)
            dt = jd_to_datetime(root)
            motion = 'goes retrograde' if speed_prev > 0 else 'goes direct'
            events.append({'datetime': dt.isoformat(), 'event': f"{name} {motion} in {SIGN_NAMES[int(lon//30)]}"})

        jd = jd_next
        lon_prev, speed_prev = lon, speed

# 8) Moon phases (approx every 30 days)

angles = [0, 90, 180, 270]
names = ["New Moon", "First Quarter", "Full Moon", "Last Quarter"]
jd_val = d_start
while jd_val < d_end:
    for angle, pname in zip(angles, names):
        root = find_event(
            lambda t: (swe.calc_ut(t, swe.MOON)[0][0] - swe.calc_ut(t, swe.SUN)[0][0]) % 360,
            jd_val, jd_val + 30, angle
        )
        dt = jd_to_datetime(root)
        moon_lon = swe.calc_ut(root, swe.MOON)[0][0] % 360
        events.append({'datetime': dt.isoformat(), 'event': f"{pname} in {SIGN_NAMES[int(moon_lon // 30)]}"})
    jd_val += 30

# 9) Save to JSON

with open('events.json', 'w', encoding='utf-8') as f:
    json.dump(sorted(events, key=lambda e: e['datetime']), f, ensure_ascii=False, indent=2)
```

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Astro & Lunar Calendar</title>
  <link href="https://fonts.googleapis.com/css2?family=UnifrakturMaguntia&display=swap" rel="stylesheet"/>
  <style>
    body { font-family:'UnifrakturMaguntia',cursive; background:#EEF3ED; text-align:center; padding:20px; overflow:hidden; color:#303328; }
    .calendar-container { background:#EEF3ED; border:3px solid #D1C9BD; padding:20px; display:inline-block; box-shadow:5px 5px 15px rgba(0,0,0,0.1); }
    h1 { margin:0 0 10px; background:#9C816E; color:#303328; padding:10px 20px; border:2px solid #D1C9BD; display:inline-block; font-size:32px; }
    .calendar { display:grid; grid-template-columns:repeat(7,40px); grid-gap:5px; justify-content:center; margin-bottom:15px; }
    .calendar div { width:40px; height:40px; line-height:40px; cursor:pointer; color:#303328; background:#F3EEEE; border:1px solid #D1C9BD; transition:all .2s; }
    .calendar .header { font-weight:bold; background:#D1C9BD; }
    .calendar div:hover { background:rgba(48,51,40,0.1); border-color:#303328; }
    .calendar .today { background:rgba(48,51,40,0.2); border-color:#303328; }
    #eventSummary { font-size:20px; padding:10px; background:#D1C9BD; border:2px solid #303328; display:inline-block; text-align:left; min-width:300px; max-width:90vw; color:#303328; }
    .star { position:absolute; color:#fff; animation:floatStars 5s linear infinite; opacity:0.8; }
    @keyframes floatStars { 0% { transform:translateY(0) scale(1); opacity:0.8 } 100% { transform:translateY(-100vh) scale(0.5); opacity:0 } }
  </style>
</head>
<body>
  <div class="calendar-container">
    <h1>✦ Astro & Lunar Calendar ✦</h1>
    <div id="calendar" class="calendar"></div>
    <div id="eventSummary">Loading events…</div>
  </div>
  <script>
    let events = [];
    fetch('events.json')
      .then(r => r.json())
      .then(data => { events = data; buildCalendar(); document.getElementById('eventSummary').innerText = 'Click any date'; });

    function buildCalendar() {
      const cal = document.getElementById('calendar'); cal.innerHTML = '';
      ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].forEach(d => { const h = document.createElement('div'); h.textContent = d; h.classList.add('header'); cal.appendChild(h); });
      const today = new Date(), y = today.getFullYear(), m = today.getMonth();
      const first = new Date(y,m,1).getDay(), days = new Date(y,m+1,0).getDate();
      for(let i=0;i<first;i++) cal.appendChild(document.createElement('div'));
      for(let d=1; d<=days; d++) {
        const dtStr = `${y}-${String(m+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
        const cell = document.createElement('div'); cell.textContent = d;
        if(dtStr === new Date().toISOString().slice(0,10)) cell.classList.add('today');
        cell.onclick = () => {
          const sum = document.getElementById('eventSummary');
          const ev = events.filter(e => e.datetime.slice(0,10) === dtStr);
          sum.innerHTML = ev.length ? `<strong>${dtStr}</strong><br>` + ev.map(e => `• ${e.event}`).join('<br>') : `<strong>${dtStr}</strong><br>No events recorded.`;
        };
        cal.appendChild(cell);
      }
    }
    function createStar() { const s = document.createElement('div'); s.className = 'star'; s.textContent = '✦'; s.style.fontSize = Math.random()*16+8+'px'; s.style.left = Math.random()*100+'vw'; s.style.animationDuration = Math.random()*3+2+'s'; document.body.appendChild(s); setTimeout(()=>s.remove(),5000); }
    setInterval(createStar, 300);
  </script>
</body>
</html>
```

