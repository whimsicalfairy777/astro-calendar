import swisseph as swe
from datetime import datetime, timezone
import pytz
import json

# 1) Point to the folder with .se1 files
swe.set_ephe_path('ephe')  # make sure this folder exists and contains the .se1 data

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

# 3) Helper: get ecliptic longitude and speed
def get_pos_and_speed(pid, jd):
    pos = swe.calc_ut(jd, pid)[0]
    lon = pos[0] % 360
    speed = pos[3]
    return lon, speed

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

# 5) Convert Julian Day to Warsaw‐time datetime
def jd_to_datetime(jd):
    y, m, d, frac = swe.revjul(jd)
    total_seconds = frac * 86400.0
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    # clamp overflow if rounding pushed us to 24:00:00
    if hours >= 24:
        hours, minutes, seconds = 23, 59, 59
    dt_utc = datetime(int(y), int(m), int(d), hours, minutes, seconds, tzinfo=timezone.utc)
    warsaw = pytz.timezone('Europe/Warsaw')
    return dt_utc.astimezone(warsaw)

# 6) Date range
jd_start = swe.julday(2025, 1, 1)
jd_end   = swe.julday(2031, 12, 31)
step = 1.0  # days

# 7) Planetary ingresses & retrograde/direct stations
for name, pid in PLANETS.items():
    jd = jd_start
    lon_prev, speed_prev = get_pos_and_speed(pid, jd)
    sign_prev = int(lon_prev // 30)

    while jd < jd_end:
        jd_next = jd + step
        lon, speed = get_pos_and_speed(pid, jd_next)
        sign = int(lon // 30)

        # Ingress: sign boundary crossed?
        if sign != sign_prev:
            root = find_event(lambda t: swe.calc_ut(t, pid)[0][0] % 360, jd, jd_next, sign * 30)
            dt = jd_to_datetime(root)
            events.append({
                'datetime': dt.isoformat(),
                'event': f"{name} enters {SIGN_NAMES[sign]}"
            })
            sign_prev = sign

        # Retrograde/direct station?
        if (speed_prev > 0 and speed < 0) or (speed_prev < 0 and speed > 0):
            root = find_event(lambda t: swe.calc_ut(t, pid)[0][3], jd, jd_next, 0)
            dt = jd_to_datetime(root)
            motion = 'goes retrograde' if speed_prev > 0 else 'goes direct'
            events.append({
                'datetime': dt.isoformat(),
                'event': f"{name} {motion} in {SIGN_NAMES[int(lon//30)]}"
            })

        jd = jd_next
        lon_prev, speed_prev = lon, speed

# 8) Moon phases (approx every 30 days)
phase_angles = [0, 90, 180, 270]
phase_names  = ["New Moon", "First Quarter", "Full Moon", "Last Quarter"]
jd_val = jd_start

while jd_val < jd_end:
    for angle, pname in zip(phase_angles, phase_names):
        root = find_event(
            lambda t: (swe.calc_ut(t, swe.MOON)[0][0] - swe.calc_ut(t, swe.SUN)[0][0]) % 360,
            jd_val, jd_val + 30, angle
        )
        dt = jd_to_datetime(root)
        moon_lon = swe.calc_ut(root, swe.MOON)[0][0] % 360
        events.append({
            'datetime': dt.isoformat(),
            'event': f"{pname} in {SIGN_NAMES[int(moon_lon // 30)]}"
        })
    jd_val += 30

# 9) Save to JSON
with open('events.json', 'w', encoding='utf-8') as f:
    json.dump(sorted(events, key=lambda e: e['datetime']),
              f, ensure_ascii=False, indent=2)

print("✅ events.json generated with", len(events), "entries.")
