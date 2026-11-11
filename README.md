# Technical Officials Scheduler

Plans the **Technical Officials (TOs)** of triathlon events run under the World Triathlon Competition Rules: a main position for every official, short jobs as second positions without time clashes, the meetings and briefings the rules require, and exports to Excel, LibreOffice, calendars and pictures.

| Version | Where |
|---|---|
| iPhone, iPad, Mac | App Store (see [PUBLISHING.md](PUBLISHING.md)) – native SwiftUI shell in [`apple/`](apple) |
| Web | https://bojansurbatovic-web.github.io/technical-officials-scheduler/app/ – works offline, can be added to the home screen |
| Ubuntu desktop (GTK) | [`linux/`](linux) – `./build-deb.sh` and then `sudo apt install ./dist/wt-planner_*.deb` |

All versions read and write the same `.wtplan.json` plan files.

*Independent tool – not affiliated with, endorsed by or sponsored by World Triathlon.*

## What it does

* **Races:** super-sprint, sprint, standard, mixed relay, middle and long distance, each with its own date and start time, on one day or across several. Typical Elite split times give the race timeline, and every value can be edited.
* **Positions:** taken from the World Triathlon TO Checklist 2025, with their duty windows (pre-event, event and post-event). Positions can be added, removed or counted differently.
* **Officials:** preferred position, daily availability, a limit on short jobs per day, and which races each official works.
* **Meetings and briefings from the rules:**
  * Elite athletes' briefing at 16:00 the day before the first competition day (CR 2.7 b)
  * Competition Jury meetings (CR 12.9)
  * the protest window that keeps the Head Referee on duty (CR 12.4)
  * start and finish rehearsals, the drivers' briefing and the TOs' meeting (EOM Table 14, 6.9, 6.11.4)
  * familiarisation (EOM 3.2.8)
  * daily TO briefings (EOM 2.13 e)
  * a warning when Elite starts are closer than EOM 2.10.2 allows
* **Plan:** auto-assign keeps the rows you set yourself. You can also swap two officials, lock everything, or leave a job to a LOC volunteer. Conflicts, tight hand-overs and unfilled jobs are listed.
* **Views:** personal schedules, a Gantt chart per day, and a timeline.
* **Exports:**
  * `.xlsx` and `.ods` workbooks: 10+ sheets with a colour Gantt per day
  * `.ics` calendar
  * `.svg` Gantt
  * the plan file
* **Privacy:** no account, no tracking, no network requests. Events stay on the device.

## Repository layout

```
web/            the app (HTML/CSS/plain JavaScript, no dependencies) – used by the web, iPhone, iPad and Mac versions
  js/engine.js      planning engine (port of linux/wt_planner/engine.py)
  js/exporters.js   XLSX / ODS / ICS / SVG / JSON
  js/reference.js   rule data, generated from linux/wt_planner/reference.py
  js/app.js         screens; js/storage.js files & sharing (native bridge or browser storage)
apple/          SwiftUI shell (iOS 16+, iPadOS, macOS 13+), XcodeGen project.yml, fastlane lanes
site/           GitHub Pages home, privacy policy and support pages
linux/          Ubuntu desktop app (Python 3 + GTK 3) – the reference implementation
tests/          engine & export tests against golden files from the Python engine, UI tests (Playwright)
tools/          generators for reference data, examples, golden files, screenshots; Apple signing helper
app-store/      listing text and screenshots for App Store Connect
.github/        CI (tests + unsigned Xcode build), Pages deployment, TestFlight upload
```

## Developing

```bash
npm install                      # Playwright for the UI tests
npm test                         # engine + exporters reproduce the Python engine exactly (9 events)
npm run serve &                  # http://localhost:8765
npm run test:ui                  # every screen at phone / tablet / desktop size, edits, exports, native bridge
python3 linux/tests/test_engine.py && python3 linux/tests/test_gui_smoke.py
```

When rule data or the Python engine changes:

```bash
python3 tools/gen_reference.py linux/wt_planner/reference.py
PYTHONHASHSEED=0 python3 tools/make_golden.py linux && python3 tools/make_golden_tables.py linux
```

The iPhone, iPad and Mac app loads `web/` from its bundle through a private `tos-app://` URL scheme. The page talks to Swift through `window.webkit.messageHandlers.tos`, which handles:
* saving events as files in Documents/Events (visible in the Files app)
* the share sheet or save panel
* the clipboard
* files opened from Files or Finder

## Licence

MIT – see [LICENSE](LICENSE).
