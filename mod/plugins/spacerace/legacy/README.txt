Frozen copies of programme missions that saves may still be running.

A save keeps the running programme's state (runningScripts.bin), so a mission
that saves already use must never change under them. When the programme is
rewritten it gets a new mission folder (tools/space_scenario.py MISSION), and
the old folder is kept here byte for byte; space_scenario.py copies every
folder in legacy/ into the scenario next to the new mission.

  programme/   the 2026-09-29 programme (1,559 lines, returnVoid fix): the first
               in-game Sputnik launch ran on it. Superseded by race/.
  race/        the 2026-09-30 programme (Track B goods, cosmonaut objective, pad
               closure without fires). Superseded by the settings-driven
               programme: the plugin now renders data/programme/race.tmpl with
               spacerace.ini into race_<hash>/ missions of its own.
  race_d874e562/, race_710a135c/
               the first Workshop release (2026-10-05), rendered with the
               default settings for new_goods = 0 and = 1. That programme woke
               on the research alone and ran the American timeline from day one;
               the 2026-10-09 template waits for the Design Bureau and starts
               the Americans from that day. The plugin renders every mission it
               runs, so these exist on players' disks already; the copies here
               restore them if media_soviet was ever cleaned.
