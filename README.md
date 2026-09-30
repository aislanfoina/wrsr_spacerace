# Space Race for Workers & Resources: Soviet Republic

A mod that turns the sandbox into a race: build a Soviet space industry, train cosmonauts
and fly the milestones of the real programme — Sputnik, a man in orbit, the first
spacewalk, docking, the Moon — before the United States does. The last one is the N1
landing on the Moon before Apollo 11 (20 July 1969).

Nothing starts until you research the Rocket Research Institute, so the programme sits
quietly in any ordinary game (an Early Start 1920 game can reach it by the 1950s).

> **Status: in development.** Everything below has run in the game, but the balance has
> not been played through yet. `mod/plugins/spacerace/spacerace.ini` ships with
> `test_mode = 1` (space research at 5 % of its cost); set it to `0` for real play.

## What it adds

- **A space branch in the research tree** — 17 entries from 1946 to 1966, hanging off
  *Advanced Engineering Study* and *Electronic Circuits*, each unlocking its buildings.
- **16 buildings** modelled on the real ones: the R-7 launch complex (Gagarin's Start),
  the N1 heavy complex (Site 110), the MIK assembly building, the Progress rocket plant,
  OKB-456 engine works, an engine test stand, oxygen and propellant plants, instrument
  works, a spacecraft hall, the Pluton tracking station, Star City, OKB-1, a recovery
  field and two monuments.
- **Five rockets** — R-7 Sputnik, Vostok-K, Soyuz, Proton and the N1 — built at the MIK
  from rocket stages, engines and avionics, rolled out onto the launch pad the MIK is
  linked to (each rocket only fits its own kind of pad), and launched by the programme:
  the propellant and payload are taken from nearby storages, and the rocket climbs away
  on flame and smoke — or blows up on the pad.
- **Six new goods** — rocket stages, rocket engines, avionics, liquid oxygen, hypergolic
  propellant and spacecraft — each made by its own industry chain.
- **Cosmonauts: a fourth education tier.** Graduates who work at Star City join a
  training class and become *experts* (education 3+); OKB-1 trains chief designers the
  same way. Crewed milestones need them. The tier is a separate, reusable plugin.
- **The programme**: eight milestones with objectives, launch success and failure, and
  the American timeline running beside you — first is rewarded, second costs prestige.

## Requirements

- Workers & Resources: Soviet Republic **1.1.1.9** (the plugins patch this exact build).
- [Republic Mod Loader](https://steamcommunity.com/sharedfiles/filedetails/?id=3787969749)
  (RML), which hosts the plugins.
- To build: Windows, Visual Studio Build Tools (MSVC x64, Windows 10/11 SDK) and PowerShell.
- To regenerate the models, textures and scripts: Python 3 with `numpy` and `pillow`,
  and Blender 5.2 (`tools/build_space.py`). `capstone` is needed only by the
  reverse-engineering helpers in `tools/`.

**Saves:** the new goods change the save format. A game started with this mod needs it
to load, and games started without it will not load with it.

## Build and install

```powershell
.\build.ps1 -Install            # compile the plugins, then deploy into the game
.\build.ps1 -Install -Game 'D:\Games\SovietRepublic'
```

This installs seven local development items into `media_soviet\workshop_wip`:

| Item | What |
|---|---|
| 9000100 | *Space Race* package: the `spacerace`, `experts` and `resources` plugins |
| 9000101 | the building kit |
| 9000111–9000115 | the five rockets |

Close the game and the loader before installing. Then open Republic Mod Loader, enable
those development items and the Space Race plugins, and launch.

## Rebuilding the content

The research icons and the programme's window images are cut from the Blender renders,
so run `build_space.py` first (it leaves them in `build/space` and `build/space_vehicles`):

```
python tools/build_space.py            # textures, building kit, rockets, previews (needs Blender)
python tools/build_space.py kit mik    # one stage for some buildings only
python tools/space_research.py         # research branch, names and icons (needs the renders)
python tools/space_scenario.py         # the programme script + launches.ini, checked by tools/vmcheck.py (needs the renders)
python tools/space_goods_icons.py      # icons of the new goods
python tools/space_layout.py           # checks every truck bay against the building models
python tools/port_resources.py         # re-ports the TesmioLoader resources plugin
```

Set `BLENDER` and `WRSR_GAME` if Blender or the game are not in their default folders.

## Repository layout

```
mod/plugins/spacerace/   research branch, programme autostart, launches, pad rules, goods for scripts
mod/plugins/experts/     the expert education tier (training classes per building)
mod/plugins/resources/   new goods: the TesmioLoader resources plugin, ported to RML
mod/packages/space_race/ the workshop item the plugins ship in
mod/buildings/space_kit/ the 16 buildings (generated)
mod/vehicles/sr_*/       the five rockets (generated)
tools/                   generators, checks and reverse-engineering helpers
tools/dev/               in-game test helpers (read/write a running game's memory)
docs/                    the design document, including what was verified in game and how
vendor/TesmioLoader/     the loader API headers and the resources plugin source it was ported from
```

`docs/space-race-design.md` is the long version: the design, every engine address the
plugins rely on, and the test history.

## Branches

| Branch | What | How changes get in |
|---|---|---|
| `unstable` | day-to-day work; may not build | pushed to directly |
| `dev` | the next release, tested in game | pull request from `unstable`, approved by two maintainers |
| `main` | releases | pull request from `dev`, approved by @aislanfoina (code owner) |

`dev` and `main` are protected: no direct pushes, force pushes or deletions.

## Licence and credits

GPL-3.0 — see `LICENSE`. The resources plugin is a port of the one in
[TesmioLoader](vendor/TesmioLoader), and every plugin builds against its GPL-3.0 API
headers, so the whole repository uses the same licence.

Workers & Resources: Soviet Republic is © 3Division. This mod contains none of the
game's files; its models, textures and scripts are generated by the tools in this
repository.
