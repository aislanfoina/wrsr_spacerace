Frozen copies of programme missions that saves may still be running.

A save keeps the running programme's state (runningScripts.bin), so a mission
that saves already use must never change under them. When the programme is
rewritten it gets a new mission folder (tools/space_scenario.py MISSION), and
the old folder is kept here byte for byte; space_scenario.py copies every
folder in legacy/ into the scenario next to the new mission.

  programme/   the 2026-09-29 programme (1,559 lines, returnVoid fix): the first
               in-game Sputnik launch ran on it. Superseded by race/.
