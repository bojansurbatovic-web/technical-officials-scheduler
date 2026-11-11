# Technical Officials Scheduler

A desktop app for Ubuntu that plans **Technical Official (TO) assignments** for World Triathlon races.
It gives each official a primary position, fills the short jobs as secondary positions without time
clashes, and shows the result as a table, a Gantt chart and a race timeline.

The rules behind the calculations come from:

* **World Triathlon Competition Rules** (13 Dec 2025) – distances, start procedure, penalty boxes,
  lapped athletes, wheel stations, TOs, athletes' briefings (2.7), protests (12.4) and the Competition Jury (12.9).
* **World Triathlon TO Checklist 2025** – pre-event, event and post-event duties for every position.
* **ITU Event Organisers' Manual 2019 (Masterfile)** – the race-day schedule, lap counts, TO motorbikes,
  radio groups, the meetings in race week (Table 14), rehearsals, familiarisation and start-to-start times.

The typical elite split times are *not* in those documents. They are editable defaults.

## Install

Ubuntu desktop (20.04 or newer) already has everything the app needs: Python 3, GTK 3 for Python, and the SVG image loader.

```bash
# option 1 – Debian package (system-wide)
./build-deb.sh
sudo apt install ./dist/wt-planner_1.3.0_all.deb

# option 2 – just for you, no sudo
./install.sh

# option 3 – run from the folder
/usr/bin/python3 -m wt_planner
```

If something is missing: `sudo apt install python3-gi gir1.2-gtk-3.0 librsvg2-common`

## Using it

| Tab | What you do there |
|---|---|
| **Calendar** (left) | Pick a day. Double-click starts a new event on it, and days with saved events are marked. Click an event to open it. |
| **Event & races** | Name, venue, date, TD, Medical Delegate, Jury, radio settings. Races are edited in the table: **date**, format (Super-sprint, Sprint, Standard, Mixed relay, Middle, Long), category, start time, legs, distances, laps, wheel and aid stations, start-line TOs, draft-legal. Under the table you can fine-tune the selected race: paces, field spread, and lounge, transition, introduction and medal times. |
| **Who works which race** | A tick box for every official in every race. Untick a race and that person is never given a job in it. For all-day jobs on a day (registration, wheel stations, transition, technology), every race of that day must be ticked. *All / none* buttons work per official and per race. |
| **Officials** | How many officials, their names, country, preferred primary position, how many secondary jobs each may take, and when they are available. You can also paste names. |
| **Meetings & briefings** | The obligations outside the races, generated from the rules (table below). Everyone who must attend is booked for that time, so the planner never gives them a clashing job. Untick *Held* if a meeting does not take place, edit its date and times, add your own meeting (with a *who attends* preset), or reset to the rules. Rule warnings are shown here. |
| **Positions** | The proposed positions are ticked. Untick, add extras, or set a different number. Each row shows its checklist or rules reference and its duty window. |
| **Duty times & tweaks** | All checklist time allowances, such as aid stations ready 30 min before the first runner. Per race, move any duty window earlier or later. |
| **Assignments** | The plan. Choose a person in any row, which locks that row; *LOC / volunteer* leaves a job deliberately without a TO. Buttons: **Auto-assign** (keeps locked rows), **re-plan from scratch**, **lock/unlock all**, **swap two officials**. Filters by race, name and problems. Status colours: OK, TIGHT (less than the hand-over buffer), CONFLICT (jobs overlap), UNFILLED. |
| **Personal schedules** | Every official's days, job by job and meeting by meeting, plus the Technical Delegate, Medical Delegate and Jury members' meetings. |
| **Gantt** | One event day at a time, by official or by position, with zoom and a dark option. Export as SVG. |
| **Timeline** | All race milestones in time order, and the splits for each race. |
| **Conflicts** | Every clash, tight hand-over, unfilled job and rule warning (for example two Elite starts closer than EOM 2.10.2 allows, or an Elite briefing moved away from 16:00). |
| **References** | Where each default comes from. |

**Events over several days:** every race has its own date and start time. Use the *Date* column, or the *Set date from calendar*, *Next day* and *Previous day* buttons. A new race starts 2 h 45 min after the previous one, or the next morning if that would be after 17:00. With more than one day:
* all-day positions (registration, wheel stations, Chief Transition, technology) are planned separately for each day, so they can be held by different people;
* each official's limit on secondary jobs applies per day, and *Available from/to* applies every day;
* times are shown as, for example, *Sat 15.05. 10:00*;
* the Excel and ODS exports get a Gantt sheet per day and a *Participation* sheet.

**Any screen size:** the window opens sized to your screen (maximized on small screens) and remembers the size you leave it at. Every tab scrolls, rows of fields and buttons wrap onto the next line, and **F9** (or the calendar button in the header) hides the calendar panel to free up width.

**Examples:** the app opens with the Question 3 example: two Elite races back to back, with 18 placeholder officials named *TO 01* to *TO 18*. The menu also opens a two-day weekend with three races, where some officials work only one day. Replace them with your team on the Officials tab, either by typing or with *Paste names…*.

**Undo / redo:** Ctrl+Z / Ctrl+Shift+Z. **Auto** in the header re-plans after every change. Rows you set yourself are never changed.

### Saving, sharing, exporting

* **Save** writes a `.wtplan.json` file. **Save to calendar library** stores it in
  `~/.local/share/wt-planner/events/`, where the calendar finds it.
* **Share JSON with another app…** opens Ubuntu's application chooser (text editor, mail client, cloud
  folder and so on). **Copy JSON** puts it on the clipboard. The `.wtplan.json` type is registered, so
  double-clicking one in Files opens the planner.
* **Export:**
  * Excel `.xlsx` or LibreOffice `.ods`, with sheets for assignments, officials and radios, participation, personal schedules, race timeline, meetings and briefings (with the people who attend), a colour Gantt grid per day (meetings in purple), conflicts and warnings, and settings and references.
  * Gantt `.svg`.
  * iCalendar `.ics`, with the races, every meeting and briefing (once each, with who attends), and every official's duties, for GNOME Calendar or Thunderbird.

## Obligations of the appointed officials (generated meetings)

Default times for the day before the first competition day; all of them can be edited.

| When | Meeting | Who must attend | Source |
|---|---|---|---|
| Day before, 08:30–09:15 | Motorbike & boat drivers' briefing | TD, Chief Bike, Chief Vehicular, TO motorbikes, Chief Swim | EOM 6.9 (all drivers meet the TD the day before), Table 14 |
| Day before, 09:30–10:00 | Medical meeting | TD, Medical Delegate | EOM Table 14 |
| Day before, 10:00–11:00 | Swim familiarisation | Chief Swim, Assistant Swim | EOM 3.2.8 |
| Day before, 11:15–12:00 | Start rehearsal | TD, Head Referee, CRO, Chief Swim, start crew | EOM 6.11.4, Table 14 |
| Day before, 11:15–12:45 | Bike familiarisation (mandatory) | Chief Bike, Chief Vehicular, TO motorbikes | EOM 3.2.8 |
| Day before, 12:45–13:15 | Finish rehearsal | TD, Chief Finish, Assistant Finish, Chief Technology | EOM Table 14 |
| Day before, 13:15 / 13:45 | Timing meeting, TV meeting | TD with Chief Technology / Video Review | EOM Table 14 |
| Day before, 14:00–15:00 | TOs' meeting | TD and all TOs | EOM Table 14, 2.13 |
| Day before, 15:00 (off by default) | Coaches' meeting | TD | CR 2.7 b(i): 1 h before the briefing, if scheduled |
| Day before, 15:30–17:30 | Briefing check-in and race packets | Registration | CR 2.7 b(vi), c(ii) |
| **Day before, 16:00–17:00** | **Elite athletes' briefing** | TD, Head Referee | **CR 2.7 b(iv), (vii)** |
| After the briefing | Competition Jury meeting | TD, Jury | CR 12.9 |
| Each competition day | TO briefing (radios, vests) 75 min before the first lounge; de-briefing 45 min after the last finisher | All TOs | EOM 2.13 e |
| Each race | Jury meeting 1 h before the start, and after the last finisher once the protest time is over | TD, Jury | CR 12.9 |

* U23, Junior, Para and Mixed-relay briefings are also held the day before their own race. A second group on the same day follows 75 min after the first. A Mixed relay on the same day as the Elite races shares their briefing (CR 2.7 b(v), (viii)).
* When a race's post-race Jury meeting runs into the next race's pre-race meeting, the two become one meeting.
* The **Head Referee's** duty ends when the protest time is over: last finisher + results sign-off + protest time. That is 5 + 15 min for Elite standard distance and shorter, and 15 + 30 min for middle/long distance and Age-Group (CR 12.4). In back-to-back racing, the Head Referee is therefore usually still busy when the next race starts, and the planner gives that Starter job to the CRO.
* **Start-to-start times** between Elite races on the same day are checked against EOM 2.10.2 Table 3: sprint 2 h, standard 3 h, Mixed relay 2 h 30, or 15 min less with TD approval.
* The day before the first race becomes part of the event, so it gets its own Gantt sheet, calendar entries and personal schedule lines.

## How the plan is calculated

1. **Race timeline.** Paces per category and distances per format give the leader's swim, T1, bike, T2 and run. A spread percentage gives the last athlete out of the water, the last into T2 and the last finisher. Relays repeat the leg. Lounge, transition and introduction times are offsets from the start, as in the Masterfile example (−75/−30, −60/−15, −10 min).
2. **Duty windows.** Each position's checklist duties become a time window per race. For example, Chief Finish runs from 25 min before the winner to 10 min after the last finisher.
3. **All-day positions.** Registration, wheel stations, Chief Transition, Technology and the VCC are merged across races. In back-to-back racing the next race's check-in runs during the current race.
4. **Primary positions** are given by priority, honouring each person's preferred position and availability.
5. **Secondary jobs** are filled with people whose own windows leave room, using the hand-over buffer (5 min by default). The planner prefers the same person in every race and the natural holder (Head Referee as Starter, CRO as Assistant Starter). Positions marked "no secondary" are never given extra jobs: Registration, wheel stations, Chief Transition and Chief Technology.
6. **Meetings and briefings** count as busy time. A job also books its holder into the meetings that belong to it: Assistant Finish into the finish rehearsal, Start-line officials into the start rehearsal, and so on.
7. **Anything that cannot be covered** is listed as UNFILLED, so you can add an official, accept a volunteer, or change a duty time.

**Radios:** one for every TO, plus the TD and the Medical Delegate, plus 1 VCC base radio, plus 10 % spares. All of these can be edited (Masterfile 6.6.2).

## Tests

```bash
python3 tests/test_engine.py      # 22 tests: timelines, plans, formats, locks, availability, multi-day, participation,
                                  #   exports, briefings, Jury meetings, protest windows, start-to-start times
python3 tests/test_gui_smoke.py   # runs all window code against a stand-in toolkit (no display)
```

## File format (`.wtplan.json`)

```json
{
  "app": "wt-planner", "version": 1,
  "event": {"name": "...", "venue": "...", "date": "YYYY-MM-DD", "td": "...", "md": "...", "jury": ["", ""]},
  "settings": {"buffer": 5, "aid_pre": 30, "...": "duty minutes"},
  "races": [{"id": "r1a2b3c", "name": "Elite Women", "format": "standard", "category": "elite_women",
             "date": "2026-11-21", "start": "10:00", "legs": 1, "swim_m": 1500, "bike_km": 40, "run_km": 10,
             "laps": {"swim": 2, "bike": 8, "run": 2}, "wheel_stations": 2, "aid_stations": 2,
             "start_line": 4, "draft_legal": true, "paces": {"...": 0}, "schedule": {"...": 0},
             "shifts": {"finish_asst": [-5, 0]}}],
  "officials": [{"name": "...", "country": "", "primary": "chief_swim", "max_secondary": 3,
                 "available_from": "", "available_to": "", "radio": true,
                 "races": {"r1a2b3c": false}}],
  "positions": {"asst_finish": {"enabled": true, "count": null}},
  "assignments": {"asst_finish#1|r1a2b3c": {"official": "...", "locked": true}},
  "sessions": {"athletes_briefing:elite": {"enabled": true, "date": "2026-11-20", "start": "16:00", "end": "17:00"}},
  "custom_sessions": [{"id": "s1a2b3", "name": "Welcome dinner", "date": "2026-11-20", "start": "19:00",
                       "end": "21:00", "attendees": ["td", "all_tos"]}]
}
```

Assignment keys are `position#n|race-id`, or `position#n|day:YYYY-MM-DD` for all-day positions. In `races`, an official's `false` entries are the races they do not work.
