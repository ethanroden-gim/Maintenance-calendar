#!/usr/bin/env python3
"""Fetch events from the (private) GIM Google Calendar via a service account
and render a branded static page to public/index.html.

Env:
  GCAL_CREDENTIALS  JSON contents of the service-account key (required unless DEMO=1)
  CALENDAR_ID       calendar id to read (defaults to the GIM maintenance calendar)
  DAYS_AHEAD        how many days forward to include (default 120)
  DEMO              if "1", render sample events instead of calling Google (for local preview)
"""
import os
import re
import json
import html
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/New_York")
CAL_ID = os.environ.get(
    "CALENDAR_ID",
    "c_011ab1d11b9179320e205449f4476366f311a597cdd8b3599e0c0dc6be0b4663@group.calendar.google.com",
)
DAYS_AHEAD = int(os.environ.get("DAYS_AHEAD", "120"))
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def fetch_events():
    """Return a list of Google Calendar event dicts."""
    if os.environ.get("DEMO") == "1":
        return _sample_events()
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    info = json.loads(os.environ["GCAL_CREDENTIALS"])
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    svc = build("calendar", "v3", credentials=creds, cache_discovery=False)

    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=DAYS_AHEAD)).isoformat()

    items, page_token = [], None
    while True:
        resp = (
            svc.events()
            .list(
                calendarId=CAL_ID,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
                maxResults=250,
                pageToken=page_token,
            )
            .execute()
        )
        items.extend(resp.get("items", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return items


def parse_times(ev):
    """Return (start_dt, end_dt, all_day) in Eastern time."""
    start, end = ev["start"], ev["end"]
    if "dateTime" in start:
        sd = datetime.fromisoformat(start["dateTime"]).astimezone(TZ)
        ed = datetime.fromisoformat(end["dateTime"]).astimezone(TZ)
        return sd, ed, False
    sd = datetime.fromisoformat(start["date"]).replace(tzinfo=TZ)
    ed = datetime.fromisoformat(end["date"]).replace(tzinfo=TZ)
    return sd, ed, True


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


def render_events(events):
    if not events:
        return '<div class="empty">No scheduled maintenance in the next {} days.</div>'.format(
            DAYS_AHEAD
        )

    # group by Eastern calendar date, preserving chronological order
    groups = {}
    order = []
    for ev in events:
        sd, ed, all_day = parse_times(ev)
        key = sd.date()
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append((sd, ed, all_day, ev))

    out = []
    for key in order:
        heading = key.strftime("%A, %B %-d, %Y") if os.name != "nt" else key.strftime("%A, %B %d, %Y")
        out.append('<section class="day-group">')
        out.append(f'<div class="day-heading">{html.escape(heading)}</div>')
        for sd, ed, all_day, ev in groups[key]:
            title = html.escape(ev.get("summary", "(no title)"))
            out.append('<div class="event">')
            out.append(f'<div class="event-time">{html.escape(time_label(sd, ed, all_day))}</div>')
            out.append(f'<div class="event-title">{title}</div>')
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
    rng = f"{now_et.strftime('%b %d')} – {end_et.strftime('%b %d, %Y')}"
    updated = now_et.strftime("%b %d, %Y at %I:%M %p ET").replace(" 0", " ")

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
    def iso(d):
        return d.isoformat()
    return [
        {
            "summary": "HVAC Filter Replacement",
            "start": {"dateTime": iso(base + timedelta(days=1, hours=9))},
            "end": {"dateTime": iso(base + timedelta(days=1, hours=11))},
            "location": "Building A, Roof Units 1-4",
            "description": "Replace all primary filters. Coordinate with facilities for roof access.",
        },
        {
            "summary": "Generator Load Test",
            "start": {"dateTime": iso(base + timedelta(days=1, hours=14))},
            "end": {"dateTime": iso(base + timedelta(days=1, hours=15, minutes=30))},
            "location": "Main Electrical Room",
        },
        {
            "summary": "Fire Suppression Inspection",
            "start": {"date": (base + timedelta(days=8)).date().isoformat()},
            "end": {"date": (base + timedelta(days=9)).date().isoformat()},
            "location": "Entire Facility",
            "description": "Annual inspection by certified vendor.\nExpect brief alarm tests.",
        },
    ]


if __name__ == "__main__":
    main()
