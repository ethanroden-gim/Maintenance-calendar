#!/usr/bin/env python3
"""Fetch events from the GIM maintenance calendar JSON feed (an Apps Script web
app) and render a branded static page to public/index.html.

Env:
  CALENDAR_FEED_URL  full URL of the Apps Script /exec feed (incl. ?token=... if set).
                     Required unless DEMO=1.
  DAYS_AHEAD         window length shown in the header label (default 120).
  DEMO               if "1", render sample events instead of fetching (local preview).
"""
import os
import re
import json
import html
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/New_York")
DAYS_AHEAD = int(os.environ.get("DAYS_AHEAD", "120"))


def fetch_events():
    """Return a list of normalized event dicts:
    {title, start, end, allDay, location, description}."""
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


def fmt_time(dt):
    return dt.strftime("%I:%M %p").lstrip("0")


def time_label(sd, ed, all_day):
    if all_day:
        return "All day"
    return f"{fmt_time(sd)} – {fmt_time(ed)}"


def clean_desc(desc):
    if not desc:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", desc, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)  # strip any remaining HTML tags
    return html.unescape(text).strip()


PIN_SVG = (
    '<svg width="13" height="13" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">'
    '<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 '
    '9.5a2.5 2.5 0 110-5 2.5 2.5 0 010 5z"/></svg>'
)


def fmt_heading(d):
    # %-d isn't portable to Windows; strip the leading zero manually.
    return d.strftime("%A, %B ") + str(d.day) + d.strftime(", %Y")


def render_events(events):
    if not events:
        return (
            '<div class="empty">No scheduled maintenance in the next '
            f"{DAYS_AHEAD} days.</div>"
        )

    # group by Eastern calendar date, preserving chronological order
    groups, order = {}, []
    for ev in events:
        sd, ed, all_day = parse_times(ev)
        key = sd.date()
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append((sd, ed, all_day, ev))

    out = []
    for key in order:
        out.append('<section class="day-group">')
        out.append(f'<div class="day-heading">{html.escape(fmt_heading(key))}</div>')
        for sd, ed, all_day, ev in groups[key]:
            out.append('<div class="event">')
            out.append(
                f'<div class="event-time">{html.escape(time_label(sd, ed, all_day))}</div>'
            )
            out.append(
                f'<div class="event-title">{html.escape(ev.get("title", "(no title)"))}</div>'
            )
            loc = ev.get("location")
            if loc:
                out.append(
                    f'<div class="event-meta">{PIN_SVG}<span>{html.escape(loc)}</span></div>'
                )
            desc = clean_desc(ev.get("description"))
            if desc:
                out.append(f'<div class="event-desc">{html.escape(desc)}</div>')
            out.append("</div>")
        out.append("</section>")
    return "\n".join(out)


def main():
    events = fetch_events()
    now_et = datetime.now(TZ)
    end_et = now_et + timedelta(days=DAYS_AHEAD)
    rng = f"{now_et.strftime('%b ')}{now_et.day} – {end_et.strftime('%b ')}{end_et.day}, {end_et.year}"
    updated = now_et.strftime("%b ") + str(now_et.day) + now_et.strftime(", %Y at ") + fmt_time(now_et) + " ET"

    template = open("template.html", encoding="utf-8").read()
    page = (
        template.replace("{{EVENTS}}", render_events(events))
        .replace("{{UPDATED}}", html.escape(updated))
        .replace("{{RANGE}}", html.escape(rng))
    )

    os.makedirs("public", exist_ok=True)
    with open("public/index.html", "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Wrote public/index.html with {len(events)} event(s).")


def _sample_events():
    base = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    return [
        {
            "title": "HVAC Filter Replacement",
            "start": (base + timedelta(days=1, hours=9)).isoformat(),
            "end": (base + timedelta(days=1, hours=11)).isoformat(),
            "allDay": False,
            "location": "Building A, Roof Units 1-4",
            "description": "Replace all primary filters. Coordinate with facilities for roof access.",
        },
        {
            "title": "Generator Load Test",
            "start": (base + timedelta(days=1, hours=14)).isoformat(),
            "end": (base + timedelta(days=1, hours=15, minutes=30)).isoformat(),
            "allDay": False,
            "location": "Main Electrical Room",
            "description": "",
        },
        {
            "title": "Fire Suppression Inspection",
            "start": (base + timedelta(days=8)).date().isoformat(),
            "end": (base + timedelta(days=9)).date().isoformat(),
            "allDay": True,
            "location": "Entire Facility",
            "description": "Annual inspection by certified vendor.\nExpect brief alarm tests.",
        },
    ]


if __name__ == "__main__":
    main()
