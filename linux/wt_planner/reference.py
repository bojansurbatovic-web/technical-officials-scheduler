"""Reference data for the World Triathlon TO planner.

Every number here is a *default* that the user can change in the app.
Sources (all supplied by the user):
  CR   World Triathlon Competition Rules, edition 13 Dec 2025 (file dated 2026-04-29)
  TOC  World Triathlon Technical Officials' Checklist 2025
  EOM  ITU Event Organisers' Manual 2019 ("Masterfile")
Typical Elite split times are not in those documents; they are typical
values for World Triathlon racing and are fully editable.
"""

APP_ID = "org.wtplanner.WTPlanner"
APP_NAME = "Technical Officials Scheduler"
APP_VERSION = "1.4.0"
FILE_SUFFIX = ".wtplan.json"
MIME_TYPE = "application/x-wtplan+json"

# --------------------------------------------------------------------------
# Race formats  (CR Appendix A distances; EOM lap guidance)
# --------------------------------------------------------------------------
FORMATS = {
    "standard": {
        "label": "Standard distance (1500 m / 40 km / 10 km)",
        "swim_m": 1500, "bike_km": 40.0, "run_km": 10.0, "legs": 1,
        "laps_elite": (2, 8, 4), "laps_ag": (1, 2, 2),
        "wheel_stations": 2, "aid_stations": 2, "start_line": 4,
        "ref": "CR Appendix A · EOM 4.3.1.1 (swim ≤2 laps), 4.8 (bike 6–8), 4.11 (run 3–4)",
    },
    "sprint": {
        "label": "Sprint distance (750 m / 20 km / 5 km)",
        "swim_m": 750, "bike_km": 20.0, "run_km": 5.0, "legs": 1,
        "laps_elite": (1, 4, 2), "laps_ag": (1, 2, 1),
        "wheel_stations": 2, "aid_stations": 1, "start_line": 4,
        "ref": "CR Appendix A · EOM (swim 1 lap, bike 2–4, run 1–2)",
    },
    "super_sprint": {
        "label": "Super-sprint (300 m / 7.5 km / 2 km)",
        "swim_m": 300, "bike_km": 7.5, "run_km": 2.0, "legs": 1,
        "laps_elite": (1, 3, 2), "laps_ag": (1, 2, 1),
        "wheel_stations": 1, "aid_stations": 0, "start_line": 4,
        "ref": "CR Appendix A (250–500 m / 6.5–13 km / 1.7–3.5 km) · EOM (1–4 / 1–2 laps)",
    },
    "mixed_relay": {
        "label": "4x Mixed relay (per leg 300 m / 7 km / 2 km)",
        "swim_m": 300, "bike_km": 7.0, "run_km": 2.0, "legs": 4,
        "laps_elite": (1, 2, 2), "laps_ag": (1, 2, 2),
        "wheel_stations": 1, "aid_stations": 0, "start_line": 4,
        "ref": "CR Appendix A (relay legs 250–300 m / 5–8 km / 1.5–2 km) · TOC §24",
    },
    "middle": {
        "label": "Middle distance (1900 m / 90 km / 21.1 km)",
        "swim_m": 1900, "bike_km": 90.0, "run_km": 21.1, "legs": 1,
        "laps_elite": (1, 2, 3), "laps_ag": (1, 2, 3),
        "wheel_stations": 0, "aid_stations": 6, "start_line": 2,
        "ref": "CR Appendix A · EOM (1–3 / 1–4 laps)",
    },
    "long": {
        "label": "Long distance (3800 m / 180 km / 42.2 km)",
        "swim_m": 3800, "bike_km": 180.0, "run_km": 42.2, "legs": 1,
        "laps_elite": (1, 2, 4), "laps_ag": (1, 2, 4),
        "wheel_stations": 0, "aid_stations": 10, "start_line": 2,
        "ref": "CR Appendix A · EOM (1–3 / 1–4 laps)",
    },
}
FORMAT_ORDER = ["standard", "sprint", "super_sprint", "mixed_relay", "middle", "long"]

# --------------------------------------------------------------------------
# Categories – typical leader paces and field spread (editable per race)
#   swim_pace  min per 100 m        bike_speed  km/h       run_pace  min per km
#   gap_swim   last out of water, % of leader swim time
#   gap_t2     last athlete into T2, % of leader time to T2
#   gap_finish last finisher, % of winning time
# Calibrated on typical Elite standard-distance splits:
#   men  ≈ 17:45 / 55:00 / 30:30 (≈1:43)   women ≈ 19:30 / 60:00 / 34:00 (≈1:55)
# --------------------------------------------------------------------------
CATEGORIES = {
    "elite_men":   {"label": "Elite Men",   "swim_pace": 1.183, "bike_speed": 43.6, "run_pace": 3.05,
                    "t1": 0.75, "t2": 0.5, "gap_swim": 22, "gap_t2": 8, "gap_finish": 9, "draft_legal": True},
    "elite_women": {"label": "Elite Women", "swim_pace": 1.30,  "bike_speed": 40.0, "run_pace": 3.40,
                    "t1": 0.75, "t2": 0.5, "gap_swim": 22, "gap_t2": 8, "gap_finish": 9, "draft_legal": True},
    "u23_men":     {"label": "U23 Men",     "swim_pace": 1.20,  "bike_speed": 42.5, "run_pace": 3.12,
                    "t1": 0.75, "t2": 0.5, "gap_swim": 24, "gap_t2": 9, "gap_finish": 10, "draft_legal": True},
    "u23_women":   {"label": "U23 Women",   "swim_pace": 1.32,  "bike_speed": 39.0, "run_pace": 3.50,
                    "t1": 0.75, "t2": 0.5, "gap_swim": 24, "gap_t2": 9, "gap_finish": 10, "draft_legal": True},
    "junior_men":  {"label": "Junior Men",  "swim_pace": 1.22,  "bike_speed": 41.0, "run_pace": 3.25,
                    "t1": 0.8, "t2": 0.5, "gap_swim": 25, "gap_t2": 10, "gap_finish": 11, "draft_legal": True},
    "junior_women": {"label": "Junior Women", "swim_pace": 1.35, "bike_speed": 37.5, "run_pace": 3.60,
                    "t1": 0.8, "t2": 0.5, "gap_swim": 25, "gap_t2": 10, "gap_finish": 11, "draft_legal": True},
    "age_group":   {"label": "Age Group (draft-illegal)", "swim_pace": 1.60, "bike_speed": 36.0, "run_pace": 3.90,
                    "t1": 2.5, "t2": 1.5, "gap_swim": 90, "gap_t2": 55, "gap_finish": 70, "draft_legal": False},
    "para":        {"label": "Para triathlon", "swim_pace": 1.60, "bike_speed": 34.0, "run_pace": 4.20,
                    "t1": 2.0, "t2": 1.5, "gap_swim": 60, "gap_t2": 40, "gap_finish": 45, "draft_legal": False},
}
CATEGORY_ORDER = ["elite_women", "elite_men", "u23_women", "u23_men", "junior_women", "junior_men",
                  "age_group", "para"]

# --------------------------------------------------------------------------
# Race-day schedule offsets (EOM 2019 integrated schedule example:
#   lounge 8:45–9:30, transition 9:00–9:45, introduction 9:50, start 10:00,
#   medal ceremony 12:15 for a winner at ≈11:55)
# --------------------------------------------------------------------------
SCHEDULE_DEFAULTS = {
    "lounge_open": 75,        # minutes before start
    "lounge_close": 30,
    "tz_open": 60,
    "tz_close": 15,
    "intro": 10,
    "medal_after_winner": 20,  # minutes after the winner
}
SCHEDULE_LABELS = {
    "lounge_open": "Athlete lounge opens (min before start)",
    "lounge_close": "Athlete lounge closes (min before start)",
    "tz_open": "Transition opens (min before start)",
    "tz_close": "Transition closes (min before start)",
    "intro": "Athlete introduction (min before start)",
    "medal_after_winner": "Medal ceremony (min after winner)",
}

# --------------------------------------------------------------------------
# Duty-time parameters (TOC pre-event / event / post-event duties)
# --------------------------------------------------------------------------
DUTY_DEFAULTS = [
    # key, minutes, label, source
    ("buffer", 5, "Travel / hand-over buffer between two positions", "Assumption – gap below this is TIGHT"),
    ("start_crew_pre", 10, "Start crew in place before athlete introduction", "TOC §1, §5 start protocol"),
    ("swim_pre", 20, "Swim TOs: corral, boats, video camera before start", "TOC §5 Event"),
    ("swim_post", 15, "Swim: account for athletes, close course, de-brief after last out", "TOC §5"),
    ("water_temp_start", 62, "Water temperature reading starts (min before start)", "CR 4.2 e (1 h before) · TOC §5"),
    ("water_temp_end", 50, "Water temperature reading ends (min before start)", "TOC §5: 3 locations, 60 cm"),
    ("line_pre", 5, "Line officials in place before first athlete", "TOC §6"),
    ("trans_cleanup", 10, "Asst Transition: box clean-up after last athlete", "TOC §6"),
    ("trans_post", 30, "Chief Transition: bike collection after last finisher", "TOC §6 post"),
    ("bike_pre", 20, "Bike team: course race-ready / moto marshalling before start", "TOC §7, §9"),
    ("bike_post", 10, "Bike team: after last athlete into T2 (chips to Chief Tech)", "TOC §7"),
    ("lap_pre", 10, "Lap boards & bell in position before leader's 1st bike lap", "TOC §10"),
    ("lap_post", 5, "Lap Auditor: after last finisher (return equipment)", "TOC §10"),
    ("run_pre", 20, "Run course re-confirmed before first runner", "TOC §11"),
    ("run_post", 5, "Run officials: after last finisher", "TOC §11"),
    ("aid_pre", 30, "Aid stations ready before first runner (sealed water)", "TOC §12"),
    ("aid_post", 10, "Aid stations re-stock / clean-up after last runner", "TOC §12"),
    ("pb_pre", 15, "Penalty box in position before first runner", "TOC §14"),
    ("pb_post", 10, "Penalty box paperwork to HR after last finisher", "TOC §14"),
    ("finish_chief_pre", 25, "Chief Finish: finish ready + briefing before winner", "TOC §15"),
    ("finish_asst_pre", 10, "Assistant Finish in place before winner", "TOC §15"),
    ("finish_post", 10, "Finish: manual back-up to Chief Tech after last finisher", "TOC §15"),
    ("hr_signoff", 15, "HR: sign off official results after last finisher (then protest window, CR 12.4)", "TOC §1 · CR 12.4"),
    ("wheel_pre", 15, "Wheel delivery & UCI check before transition opens", "TOC §8"),
    ("wheel_post", 15, "Wheel returns after last finisher", "TOC §8 post"),
    ("reg_setup", 30, "Registration: lounge set-up before opening", "TOC §4"),
    ("reg_post", 20, "Registration: after last finisher (items collected)", "TOC §4 post"),
    ("tech_pre", 30, "Technology: before transition opens (chips, timing points)", "TOC §13"),
    ("tech_post", 20, "Technology: results secured after last finisher", "TOC §13"),
    ("video_pre", 30, "Video review: in OB van before start", "TOC §16"),
    ("relay_pre", 15, "Mixed relay zone ready before start", "TOC §24"),
    ("chaperone_post", 15, "Top-3 chaperone: until after medal ceremony", "TOC §15"),
]
DUTY_KEYS = [d[0] for d in DUTY_DEFAULTS]

# --------------------------------------------------------------------------
# Activities = time windows inside one race.  Each anchor is a timeline
# milestone; the offset is a duty parameter (minus = before, plus = after).
#   (key, label, start_anchor, start_param, start_sign, end_anchor, end_param, end_sign, toc)
# --------------------------------------------------------------------------
ACTIVITIES = {
    "registration":   ("Registration / athlete lounge (whole day)", "lounge_open", "reg_setup", -1, "last_finisher", "reg_post", +1, "TOC §4"),
    "start_crew":     ("Start crew", "intro", "start_crew_pre", -1, "start", None, +2, "TOC §1, §5"),
    "water_temp":     ("Water temperature", "start", "water_temp_start", -1, "start", "water_temp_end", -1, "CR 4.2 e"),
    "swim":           ("Swim course", "start", "swim_pre", -1, "swim_last_out", "swim_post", +1, "TOC §5"),
    "transition":     ("Transition (check-in → bike collection)", "tz_open", "line_pre", -1, "last_finisher", "trans_post", +1, "TOC §6"),
    "tz_checkin":     ("Transition check-in", "tz_open", None, 0, "tz_close", None, 0, "EOM"),
    "mount":          ("Mount line (T1)", "t1_first", "line_pre", -1, "t1_last", None, +2, "TOC §6"),
    "dismount":       ("Dismount line (T2)", "t2_first", "line_pre", -1, "t2_last", None, +3, "TOC §6"),
    "asst_t1":        ("Assistant Transition T1", "t1_first", "line_pre", -1, "t1_last", "trans_cleanup", +1, "TOC §6"),
    "asst_t2":        ("Assistant Transition T2", "t2_first", "line_pre", -1, "t2_last", "trans_cleanup", +1, "TOC §6"),
    "bike":           ("Bike course (motorbike)", "start", "bike_pre", -1, "t2_last", "bike_post", +1, "TOC §7, §9"),
    "wheel":          ("Wheel station", "tz_open", "wheel_pre", -1, "last_finisher", "wheel_post", +1, "TOC §8"),
    "lap_audit":      ("Lap audit bike + run", "bike_lap1", "lap_pre", -1, "last_finisher", "lap_post", +1, "TOC §10"),
    "bike_laps":      ("Bike lap counting", "bike_lap1", "lap_pre", -1, "t2_last", None, 0, "TOC §10"),
    "run_laps":       ("Run lap counting", "run_lap1_leader", "lap_pre", -1, "run_lap_last", None, +1, "TOC §10"),
    "run":            ("Run course", "run_first", "run_pre", -1, "last_finisher", "run_post", +1, "TOC §11"),
    "last_runner":    ("Last runner", "t2_last", None, 0, "last_finisher", None, 0, "TOC §11"),
    "aid":            ("Aid station", "run_first", "aid_pre", -1, "last_finisher", "aid_post", +1, "TOC §12"),
    "penalty_box":    ("Run penalty box", "run_first", "pb_pre", -1, "last_finisher", "pb_post", +1, "TOC §14 · CR 3.3 b"),
    "asst_penalty":   ("Assistant penalty box", "run_lap1_leader", None, -5, "last_finisher", "pb_post", +1, "TOC §14"),
    "bike_penalty":   ("Bike penalty box", "t1_first", "line_pre", -1, "t2_last", "pb_post", +1, "CR 10.8 b · TOC §14"),
    "finish_chief":   ("Finish (chief)", "winner", "finish_chief_pre", -1, "last_finisher", "finish_post", +1, "TOC §15"),
    "finish_asst":    ("Finish (assistant)", "winner", "finish_asst_pre", -1, "last_finisher", None, +5, "TOC §15"),
    "hr_signoff":     ("Results sign-off + protest window", "last_finisher", None, 0, "protest_close", "hr_signoff", +1, "TOC §1 · CR 12.4"),
    "race_presence":  ("Race supervision (non-blocking)", "lounge_open", None, 0, "last_finisher", None, +15, "TOC §1, §2"),
    "technology":     ("Timing & results", "tz_open", "tech_pre", -1, "last_finisher", "tech_post", +1, "TOC §13"),
    "video":          ("Video review (OB van)", "start", "video_pre", -1, "last_finisher", None, 0, "TOC §16"),
    "relay_zone":     ("Mixed relay zone", "start", "relay_pre", -1, "last_finisher", None, +2, "TOC §24"),
    "chaperone":      ("Top-3 chaperone", "winner", None, 0, "medal", "chaperone_post", +1, "TOC §15"),
    "protocol":       ("Medal ceremony", "medal", None, -10, "medal", None, +15, "TOC §17"),
    "vcc":            ("Venue control centre", "lounge_open", "reg_setup", -1, "last_finisher", "tech_post", +1, "TOC §3"),
}
NON_BLOCKING = {"race_presence"}

# --------------------------------------------------------------------------
# Position catalogue (TOC sections 1–24)
#   kind:     "primary"   – a person's main job (normally the same person all day)
#             "secondary" – short window; normally covered by someone as a secondary job
#   all_day:  windows of all races are merged into one block (job continues between races)
#   count:    int or a race attribute name whose maximum over races is used
#   applies:  condition on a race ("all", "draft_legal", "non_drafting", "relay", "laps",
#             "wheel", "aid", "bike_laps", "run_laps")
#   holder_rules: what a holder of this position may take as secondary
#             None = anything, [] = nothing, [list] = only these position keys
#   proposed: included by default in the proposal
# --------------------------------------------------------------------------
POSITIONS = [
    # key, title, toc, kind, activities, count, applies, all_day, holder_rules, prefer_holder, priority, proposed
    ("head_referee", "Head Referee", "TOC §1", "primary", ["race_presence", "hr_signoff"], 1, "all", False, ["starter"], None, 1, True),
    ("cro", "Chief Race Official", "TOC §2", "primary", ["race_presence"], 1, "all", False, None, None, 2, True),
    ("chief_technology", "Chief Technology", "TOC §13", "primary", ["technology"], 1, "all", True, [], None, 3, True),
    ("chief_registration", "Chief Registration", "TOC §4", "primary", ["registration"], 1, "all", True, [], None, 4, True),
    ("chief_swim", "Chief Swim", "TOC §5", "primary", ["water_temp", "swim"], 1, "all", False, None, None, 5, True),
    ("chief_transition", "Chief Transition", "TOC §6", "primary", ["transition"], 1, "all", True, [], None, 6, True),
    ("chief_bike", "Chief Bike (TO motorbike #1)", "TOC §7", "primary", ["bike"], 1, "all", False, None, None, 7, True),
    ("chief_run", "Chief Run", "TOC §11", "primary", ["run"], 1, "all", False, None, None, 8, True),
    ("chief_finish", "Chief Finish", "TOC §15", "primary", ["finish_chief"], 1, "all", False, None, None, 9, True),
    ("chief_penalty_box", "Chief Penalty Box (run)", "TOC §14", "primary", ["penalty_box"], 1, "all", False, None, None, 10, True),
    ("chief_wheel_station", "Chief Wheel Station", "TOC §8", "primary", ["wheel"], 1, "wheel", True, [], None, 11, True),
    ("chief_lap_auditor", "Chief Lap Auditor (bike + run)", "TOC §10", "primary", ["lap_audit"], 1, "laps", False, None, None, 12, True),
    ("chief_aid_station", "Chief Aid Station", "TOC §12", "primary", ["aid"], 1, "aid", False, None, None, 13, True),
    ("chief_vehicular", "Chief Vehicular (TO motorbike #2)", "TOC §9", "primary", ["bike"], 1, "all", False, None, None, 14, True),
    ("chief_relay_zone", "Chief Mixed Relay Zone", "TOC §24", "primary", ["relay_zone"], 1, "relay", False, [], None, 15, True),
    ("asst_swim", "Assistant Swim (TO boat)", "TOC §5", "primary", ["swim"], 1, "all", False, None, None, 16, True),
    ("asst_wheel_station", "Assistant Wheel Station", "TOC §8", "primary", ["wheel"], "wheel_extra", "wheel", True, [], None, 17, True),
    ("line_official", "Mount/Dismount line official", "TOC §6", "primary", ["mount", "dismount"], 1, "all", False, None, None, 18, True),
    ("asst_run", "Assistant Run (last runner)", "TOC §11", "primary", ["last_runner"], 1, "all", False, None, None, 19, True),
    ("asst_registration", "Assistant Registration", "TOC §4", "primary", ["registration"], 1, "all", True, [], None, 30, False),
    ("asst_transition", "Assistant Transition", "TOC §6", "primary", ["transition"], 1, "all", True, [], None, 31, False),
    ("chief_vcc", "Chief Venue Control Centre", "TOC §3", "primary", ["vcc"], 1, "all", True, [], None, 32, False),
    ("video_review", "Video Review – OB van", "TOC §16", "primary", ["video"], 1, "all", False, [], None, 33, False),
    # ----- short windows: normally covered as secondary jobs
    ("starter", "Starter", "TOC §1", "secondary", ["start_crew"], 1, "all", False, None, "head_referee", 40, True),
    ("asst_starter", "Assistant Starter (2nd horn)", "TOC §1", "secondary", ["start_crew"], 1, "all", False, None, "cro", 41, True),
    ("start_line", "Start-line official", "CR 4.5 · TOC §5", "secondary", ["start_crew"], "start_line", "all", False, None, None, 42, True),
    ("false_start", "False start official", "CR 4.7 e", "secondary", ["start_crew"], 1, "all", False, None, "chief_penalty_box", 43, True),
    ("line_official_2", "Mount/Dismount line official #2", "TOC §6", "secondary", ["mount", "dismount"], 1, "all", False, None, "cro", 44, True),
    ("asst_transition_t1", "Assistant Transition T1", "TOC §6", "secondary", ["asst_t1"], 1, "all", False, None, "chief_finish", 45, True),
    ("asst_transition_t2", "Assistant Transition T2", "TOC §6", "secondary", ["asst_t2"], 1, "all", False, None, None, 46, True),
    ("moto_to", "Assistant Bike – TO motorbike (lapped athletes)", "TOC §7", "secondary", ["bike"], 1, "draft_legal", False, None, None, 47, False),
    ("bike_penalty_box", "Bike penalty box official", "CR 10.8 b · TOC §14", "secondary", ["bike_penalty"], "bike_pb", "non_drafting", False, None, None, 48, True),
    ("asst_aid_station", "Assistant Aid Station", "TOC §12", "secondary", ["aid"], "aid_extra", "aid", False, None, "asst_swim", 49, True),
    ("asst_finish", "Assistant Finish", "TOC §15", "secondary", ["finish_asst"], 2, "all", False, None, "cro", 50, True),
    ("asst_penalty_box", "Assistant Penalty Box", "TOC §14", "secondary", ["asst_penalty"], 1, "all", False, None, "chief_swim", 51, True),
    ("asst_lap_auditor", "Assistant Lap Auditor (run laps)", "TOC §10", "secondary", ["run_laps"], 1, "run_laps", False, None, None, 52, False),
    ("asst_relay_zone", "Assistant Mixed Relay Zone", "TOC §24", "secondary", ["relay_zone"], 1, "relay", False, None, None, 53, True),
    ("chaperone", "Top-3 chaperone", "TOC §15", "secondary", ["chaperone"], 1, "all", False, None, None, 60, False),
    ("protocol", "Protocol official", "TOC §17", "secondary", ["protocol"], 1, "all", False, None, None, 61, False),
]
POSITION_FIELDS = ["key", "title", "toc", "kind", "activities", "count", "applies", "all_day",
                   "holder_rules", "prefer_holder", "priority", "proposed"]
POSITION_INDEX = {p[0]: dict(zip(POSITION_FIELDS, p)) for p in POSITIONS}

RADIO_DEFAULTS = {"vcc_base": 1, "spare_pct": 10}

# --------------------------------------------------------------------------
# Meetings, briefings, rehearsals and familiarisations (obligations outside the race)
#   attendees: "td", "md", "jury", "all_tos" (every TO working the related races) or position keys
# --------------------------------------------------------------------------
SESSIONS = {
    # once per event, on the day before the first competition day
    "drivers_briefing": ("Motorbike & boat drivers' briefing", ["td", "chief_bike", "chief_vehicular", "moto_to", "chief_swim"],
                         "EOM 6.9 (all motorbike drivers meet the TD the day before) · Table 14", True),
    "medical_meeting": ("Medical meeting", ["td", "md"], "EOM Table 14 · TOC §18", True),
    "start_rehearsal": ("Start rehearsal (pontoon, horns, false start)",
                        ["td", "head_referee", "cro", "chief_swim", "starter", "asst_starter", "start_line", "false_start"],
                        "EOM 6.11.4 c (1 day prior) · Table 14 · TOC §5", True),
    "finish_rehearsal": ("Finish rehearsal (tape, photo finish, timing)", ["td", "chief_finish", "asst_finish", "chief_technology"],
                         "EOM Table 14 · TOC §15", True),
    "timing_meeting": ("Timing meeting", ["td", "chief_technology"], "EOM Table 14 · TOC §13", True),
    "tv_meeting": ("Broadcasters' (TV) meeting", ["td", "video_review"], "EOM Table 14 · TOC §16", True),
    "to_meeting": ("TOs' meeting (race week)", ["td", "all_tos"], "EOM Table 14 · EOM 2.13 c", True),
    # per familiarisation group (Elite/U23/Junior · Para · Age-Group), day before that group's first race
    "swim_fam": ("Swim course familiarisation", ["chief_swim", "asst_swim"], "EOM 3.2.8 a · TOC §5", True),
    "bike_fam": ("Bike course familiarisation (mandatory)", ["chief_bike", "chief_vehicular", "moto_to"], "EOM 3.2.8 b · TOC §7", True),
    # per briefing group, day before that group's first race
    "coaches_meeting": ("Coaches' meeting (if scheduled)", ["td"], "CR 2.7 b(i): 1 h before athletes' briefing", False),
    "briefing_checkin": ("Briefing check-in & race packets", ["chief_registration", "asst_registration"],
                         "CR 2.7 b(vi), 2.7 c(ii) · TOC §4", True),
    "athletes_briefing": ("Athletes' briefing", ["td", "head_referee"], "CR 2.7 b(iv),(vii),(viii) · TOC §1", True),
    "jury_after_briefing": ("Competition Jury meeting (after briefing)", ["td", "jury"], "CR 12.9 a(i)", True),
    # per competition day
    "to_briefing": ("TO briefing – radios & vests", ["all_tos"], "EOM 2.13 e · TOC §2", True),
    "to_debriefing": ("TO de-briefing – radios & vests back", ["all_tos"], "EOM 2.13 e · TOC §2", True),
    # per race
    "jury_before_race": ("Competition Jury meeting (1 h before start)", ["td", "jury"], "CR 12.9 a(ii)", True),
    "jury_after_race": ("Competition Jury meeting (after last finisher / protests)", ["td", "jury"], "CR 12.9 a(iii) · 12.4", True),
}
SESSION_ORDER = list(SESSIONS)
SESSION_PRESETS = {
    "All TOs": ["all_tos"], "All TOs + TD": ["td", "all_tos"], "TD only": ["td"], "TD + Jury": ["td", "jury"],
    "Chiefs": ["head_referee", "cro", "chief_registration", "chief_swim", "chief_transition", "chief_bike", "chief_run",
               "chief_finish", "chief_penalty_box", "chief_wheel_station", "chief_lap_auditor", "chief_aid_station",
               "chief_vehicular", "chief_technology"],
    "Start team": ["head_referee", "cro", "chief_swim", "starter", "asst_starter", "start_line", "false_start"],
    "Bike team": ["chief_bike", "chief_vehicular", "moto_to"],
    "Registration": ["chief_registration", "asst_registration"],
}
BRIEFING_GROUPS = {  # category -> briefing group, familiarisation group
    "elite_men": ("elite", "elite"), "elite_women": ("elite", "elite"), "u23_men": ("u23", "elite"),
    "u23_women": ("u23", "elite"), "junior_men": ("junior", "elite"), "junior_women": ("junior", "elite"),
    "para": ("para", "para"), "age_group": ("age_group", "age_group"),
}
BRIEFING_LABELS = {"elite": "Elite", "u23": "U23", "junior": "Junior", "relay": "Mixed relay", "para": "Para triathlon",
                   "age_group": "Age-Group team managers & coaches"}
# EOM 2.10.2 Table 3: minimum time from one Elite start to the next (can be cut by 15 min with TD approval)
START_WINDOWS = {"sprint": 120, "super_sprint": 120, "standard": 180, "mixed_relay": 150}

REFERENCES = """References used for all default values
• World Triathlon Competition Rules (13 Dec 2025): distances (Appendix A), start procedure (4.5, 4.7),
  water temperature 1 h before start (4.2 e), Elite penalties served at run penalty box (3.3 b, 3.5 e),
  lapped athletes (5.4), wheel stations (5.9), bike penalty boxes one per 10 km / 30 km (10.8 b),
  Technical Officials and Competition Jury (11.2, 12.6).
• World Triathlon Technical Officials' Checklist 2025: pre-event, event and post-event duties of every
  position (sections 1–24), assistant numbers, radio protocol (21).
• Briefings: Elite athletes' briefing at 16:00 the day before the first competition day; other categories the day
  before their first race; coaches' meeting 1 h before (CR 2.7 b). Jury meets after the briefing, 1 h before each
  start and after the last finisher (CR 12.9). Protest windows after results: Elite standard/shorter 5 + 15 min,
  middle/long and Age-Group 15 + 30 min (CR 12.4).
• ITU Event Organisers' Manual 2019 (Masterfile): race-week meetings (Table 14: TOs' meeting, start and finish
  rehearsals, motorbike & boat drivers' briefing, timing, medical, TV), swim and bike familiarisation (3.2.8),
  TO briefings and de-briefings on competition days (2.13), minimum time between Elite starts (2.10.2 Table 3),
  back-to-back race schedule example (lounge −75/−30 min,
  transition −60/−15 min, introduction −10 min), lap guidance, TO motorbikes (3.4.3), penalty box (4.13),
  radio talk groups (6.6.2: TO group min. 12 radios + 1 VCC radio), TO equipment list (25 radios).
• Typical Elite split times are not in these documents: they are editable defaults.
"""
