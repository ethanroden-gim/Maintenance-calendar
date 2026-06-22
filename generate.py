#!/usr/bin/env python3
"""Fetch events from the GIM calendar JSON feed (an Apps Script web app) and
render a branded static page to public/index.html.

The page shows a 5-week calendar grid (current week + next 4 weeks, Sunday-first,
with the weekend columns shrunk) followed by a full detail list. Maintenance and
holiday events are styled distinctly.

Env:
  CALENDAR_FEED_URL  full URL of the Apps Script /exec feed (incl. ?token=... if set).
                     Required unless DEMO=1.
  WEEKS              number of week rows to show (default 5).
  DEMO               if "1", render sample events instead of fetching (local preview).
"""
import os
import json
import html
import urllib.request
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/New_York")
WEEKS = int(os.environ.get("WEEKS", "3"))  # current week + next 2
GRID_DAYS = WEEKS * 7
WEEKDAY_HEADERS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]  # Sunday-first


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #
def fetch_events():
    """Return a list of normalized event dicts:
    {title, start, end, allDay, location, description, type}."""
    if os.environ.get("DEMO") == "1":
        return _sample_events()
    url = os.environ["CALENDAR_FEED_URL"]
    req = urllib.request.Request(url, headers={"User-Agent": "gim-calendar-build"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"Feed error: {data['error']} (check FEED_TOKEN / access).")
    return data.get("events", []) if isinstance(data, dict) else data


def parse_times(ev):
    """Return (start_dt, end_dt, all_day) in Eastern time."""
    if ev.get("allDay"):
        sd = datetime.fromisoformat(str(ev["start"])[:10]).replace(tzinfo=TZ)
        ed = datetime.fromisoformat(str(ev["end"])[:10]).replace(tzinfo=TZ)
        return sd, ed, True
    sd = datetime.fromisoformat(ev["start"]).astimezone(TZ)
    ed = datetime.fromisoformat(ev["end"]).astimezone(TZ)
    return sd, ed, False


def ev_type(ev):
    return ev.get("type") or "maintenance"


def covered_dates(sd, ed, all_day):
    """List of calendar dates an event covers (inclusive), handling Google's
    exclusive all-day end date and midnight-ending timed events."""
    first = sd.date()
    if all_day:
        last = ed.date() - timedelta(days=1)
    else:
        last = ed.date()
        if last > first and ed.hour == 0 and ed.minute == 0 and ed.second == 0:
            last -= timedelta(days=1)
    if last < first:
        last = first
    out, d = [], first
    while d <= last:
        out.append(d)
        d += timedelta(days=1)
    return out


# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #
def fmt_time(dt):
    return dt.strftime("%I:%M %p").lstrip("0")


def fmt_chip_time(dt):
    """Compact time for a grid chip, e.g. '9a' or '2:30p'."""
    h = dt.strftime("%I").lstrip("0")
    m = dt.strftime("%M")
    ap = dt.strftime("%p").lower()[0]
    return f"{h}{ap}" if m == "00" else f"{h}:{m}{ap}"


def fmt_short(d):
    return d.strftime("%b ") + str(d.day)


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def render_grid(events, grid_start, today):
    """Render the 5-week grid. Returns HTML for the {{GRID}} placeholder."""
    grid_dates = [grid_start + timedelta(days=i) for i in range(GRID_DAYS)]
    grid_set = set(grid_dates)

    # bucket events into day cells
    buckets = {d: [] for d in grid_dates}
    for ev in events:
        sd, ed, all_day = parse_times(ev)
        for d in covered_dates(sd, ed, all_day):
            if d in grid_set:
                buckets[d].append((0 if all_day else 1, sd, all_day, ev))

    parts = [f'<div class="cal-scroll"><div class="cal-grid" role="grid" style="--week-rows:{WEEKS}">']
    for name in WEEKDAY_HEADERS:
        cls = "cal-head weekend" if name in ("Sun", "Sat") else "cal-head"
        parts.append(f'<div class="{cls}">{name}</div>')

    for idx, d in enumerate(grid_dates):
        classes = ["cal-cell"]
        if d.weekday() in (5, 6):  # Sat=5, Sun=6
            classes.append("weekend")
        if d == today:
            classes.append("today")
        elif d < today:
            classes.append("past")
        parts.append(f'<div class="{" ".join(classes)}">')

        if d.day == 1 or idx == 0:
            daynum = d.strftime("%b ") + str(d.day)
        else:
            daynum = str(d.day)
        parts.append(f'<div class="cal-daynum">{daynum}</div>')

        items = sorted(buckets[d], key=lambda t: (t[0], t[1]))
        for _, sd, all_day, ev in items:
            inner = ""
            if not all_day:
                inner += f'<span class="chip-time">{html.escape(fmt_chip_time(sd))}</span>'
            inner += f'<span class="chip-title">{html.escape(ev.get("title", ""))}</span>'
            loc = ev.get("location")
            if loc:
                inner += f'<span class="chip-loc">{html.escape(loc)}</span>'
            parts.append(f'<div class="chip {ev_type(ev)}">{inner}</div>')
        parts.append("</div>")

    parts.append("</div></div>")
    return "".join(parts)


def main():
    events = fetch_events()
    now_et = datetime.now(TZ)
    today = now_et.date()
    grid_start = today - timedelta(days=(today.weekday() + 1) % 7)  # Sunday of this week
    grid_end = grid_start + timedelta(days=GRID_DAYS - 1)

    rng = f"Week of {fmt_short(grid_start)} – {fmt_short(grid_end)}, {grid_end.year}"
    updated = now_et.strftime("%b ") + str(now_et.day) + now_et.strftime(", %Y at ") + fmt_time(now_et) + " ET"

    template = open("template.html", encoding="utf-8").read()
    page = (
        template.replace("{{GRID}}", render_grid(events, grid_start, today))
        .replace("{{UPDATED}}", html.escape(updated))
        .replace("{{RANGE}}", html.escape(rng))
    )

    os.makedirs("public", exist_ok=True)
    with open("public/index.html", "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Wrote public/index.html with {len(events)} event(s).")


# --------------------------------------------------------------------------- #
# Demo data (DEMO=1) — anchored to the current grid so every cell type is exercised
# --------------------------------------------------------------------------- #
def _sample_events():
    today = datetime.now(TZ).date()
    gs = today - timedelta(days=(today.weekday() + 1) % 7)  # this week's Sunday

    def dt(day_offset, h, m=0):
        d = gs + timedelta(days=day_offset)
        return datetime(d.year, d.month, d.day, h, m, tzinfo=TZ).isoformat()

    def allday(day_offset, span=1):
        s = gs + timedelta(days=day_offset)
        e = s + timedelta(days=span)
        return s.isoformat(), e.isoformat()

    h_s, h_e = allday(1)            # holiday on Monday this week
    md_s, md_e = allday(4, span=4)  # multi-day maintenance crossing the week boundary
    return [
        {"title": "Presidents' Day", "start": h_s, "end": h_e, "allDay": True,
         "location": "", "description": "", "type": "holiday"},
        {"title": "HVAC Filter Replacement", "start": dt(2, 9), "end": dt(2, 11),
         "allDay": False, "location": "Building A, Roof Units 1-4",
         "description": "Replace all primary filters. Coordinate with facilities for roof access.",
         "type": "maintenance"},
        {"title": "Generator Load Test", "start": dt(2, 14), "end": dt(2, 15, 30),
         "allDay": False, "location": "Main Electrical Room", "description": "", "type": "maintenance"},
        {"title": "Elevator Inspection", "start": dt(2, 8), "end": dt(2, 9),
         "allDay": False, "location": "Lobby", "description": "", "type": "maintenance"},
        {"title": "Sprinkler Flush", "start": dt(2, 16), "end": dt(2, 17),
         "allDay": False, "location": "Zone 3", "description": "", "type": "maintenance"},
        {"title": "Roof Recoating", "start": md_s, "end": md_e, "allDay": True,
         "location": "Building C Roof", "description": "Weather permitting.", "type": "maintenance"},
        {"title": "Fire Suppression Inspection", "start": dt(15, 0), "end": dt(16, 0),
         "allDay": True, "location": "Entire Facility",
         "description": "Annual inspection by certified vendor.\nExpect brief alarm tests.",
         "type": "maintenance"},
        {"title": "Quarterly Safety Walk", "start": dt(23, 10), "end": dt(23, 12),
         "allDay": False, "location": "All Buildings", "description": "", "type": "maintenance"},
    ]


if __name__ == "__main__":
    main()
