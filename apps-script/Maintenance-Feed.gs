/**
 * GIM MAINTENANCE CALENDAR — public JSON feed
 * -------------------------------------------
 * A tiny, standalone Apps Script that exposes ONLY the maintenance calendar as
 * JSON, so the GitHub Pages site can render it. It runs under your Google
 * account's authorization (same model as the Meeting Dashboard) — no service
 * account, no key files.
 *
 * SETUP
 *   1. script.google.com → New project → paste this file.
 *   2. Editor → Services (+) → add "Calendar API" (advanced service).
 *   3. Deploy → New deployment → type "Web app":
 *        - Execute as: Me
 *        - Who has access: Anyone
 *      Copy the /exec URL.
 *   4. (Optional, recommended) lock it down: Project Settings → Script
 *      Properties → add FEED_TOKEN = <some random string>. Then the feed only
 *      responds to <exec-url>?token=<that string>. Use that full URL as the
 *      CALENDAR_FEED_URL secret in GitHub.
 */

// The GIM maintenance calendar (same id used by the public page).
const CAL_ID =
  'c_011ab1d11b9179320e205449f4476366f311a597cdd8b3599e0c0dc6be0b4663@group.calendar.google.com';

// How many days forward to include.
const WINDOW_FUTURE_DAYS = 120;

function doGet(e) {
  const required = PropertiesService.getScriptProperties().getProperty('FEED_TOKEN');
  const provided = (e && e.parameter && e.parameter.token) || '';
  if (required && provided !== required) {
    return json_({ error: 'forbidden' });
  }

  const now = new Date();
  const end = new Date(now.getTime() + WINDOW_FUTURE_DAYS * 86400000);

  const events = [];
  let pageToken = null;
  do {
    const resp = Calendar.Events.list(CAL_ID, {
      timeMin: now.toISOString(),
      timeMax: end.toISOString(),
      singleEvents: true,
      orderBy: 'startTime',
      maxResults: 250,
      showDeleted: false,
      pageToken: pageToken
    });
    (resp.items || []).forEach(function (ev) {
      if (ev.status === 'cancelled') return;
      const allDay = !!(ev.start && ev.start.date);
      events.push({
        title: ev.summary || '(no title)',
        start: allDay ? ev.start.date : (ev.start && ev.start.dateTime),
        end: allDay ? (ev.end && ev.end.date) : (ev.end && ev.end.dateTime),
        allDay: allDay,
        location: ev.location || '',
        description: ev.description || ''
      });
    });
    pageToken = resp.nextPageToken;
  } while (pageToken);

  return json_({ updated: new Date().toISOString(), events: events });
}

function json_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
