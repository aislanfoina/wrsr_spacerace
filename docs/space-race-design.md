# Red Star Rising: a Space Race scenario for Workers & Resources

Design proposal, 2026-09-29. Companion to the Korea Year Zero work; everything
learned about the engine in that project (RML plugins, workshop items, the
scenario VM, map format, id-prefixed idents) carries over.

## 1. The pitch

The republic is handed the Soviet space programme. From 1955 the player has to
build, out of the ordinary industrial chains of the game, the specialised
chains that put a satellite, a dog, a man, a woman, a probe and finally a crew
into space - while the USA moves along its historical timeline on the other
side of the world. Every milestone is a launch: a real rocket has to be built
in the republic's factories, moved by rail to a cosmodrome the player built,
fuelled from propellant plants the player runs, and fired. Launches fail. The
race is scored milestone by milestone; the game ends with the Moon.

Why it fits the game: WRSR already has the heavy chains a space programme
consumed (steel, aluminium, chemicals, electronics, mechanical components,
fuel, nuclear, explosives), a research tree, vehicle production lines that turn
materials into vehicles, airports and heliports, and a scenario VM that can
read building storages, statistics, research and dates. The mod adds the
missing last mile: propellants, rocket hardware, a launch complex, and the
race itself.

Target audience: advanced players who have run a full republic with research
on. Recommended settings: Research enabled, Realistic mode, Energy management
with vehicles, Maintenance on. The scenario refuses to start otherwise
(`GameSetting.GetCurrentGameSettigns` is readable from the script).

## 2. What the engine gives us (verified in the files)

**Scenario VM** (`media_soviet/scripts/SOVIETInstructions.txt`, 260
instructions). The ones the race is built on:

| Need | Instruction |
|---|---|
| Read what a building holds | `Resources.GetFromBuilding(idx)`, `GetFromBuildingStorage`, `GetCapacityFromBuilding`, `GetProductionFromBuilding` |
| Take goods out of a building at launch | `Resources.AddFromBuilding(idx)` (negative amounts to be confirmed in the first spike) |
| Republic-wide production totals | `StatRecord.ResourcesProduced` per resource, `StatRecord_GetNumberOfRecords` |
| Find the player's buildings | `Building_SetTag/GetByTag`, `Building.GetDataByIndex` (type, subtype, position, workers, `fCurrentProduction`, `nStorageNum`) |
| Vehicles at the pad | `Building_VehiclesWorking_GetID`, `Vehicle.GetDataByIndex` (`nBuilding_CurrentID`, `fFuel_Current`, `bBrandNew`), `Vehicle_SetTag/GetByTag` |
| Consume a rocket | `Vehicle_Sell(id, 0, 0)` erases it |
| Spawn a returning capsule or a foreign vehicle | `Scenario_OrderHelicopterToBuilding`, `Scenario_OrderAirplaneToBuilding`, `Scenario_AddRoadVehicleToBuilding` |
| Research | `Research_IsCompleted`, `Research_PercFinished`, `Scenario_UnlockResearch`, `Research_GetUniversityType` |
| Time | `Date_GetCurrentDate_DMY`, `Script_Sleep`, `Script_GetGameTime` |
| Objectives with progress bars | `Scenario_ObjectiveCreate`, `Objective_AddRequirement` (x/x display with an icon), `Objective_UpdateRequirement`, `Scenario_ObjectiveSetCompleted`, `ScenarioPersistent_*` |
| Story | `Scenario_WindowWithImageLeft`, `Notification_CreateNewStringPic` (world position), `Scenario_ObjectiveMoveCameraTo`, `Scenario_CreateWorldArrow`, `Scenario_FollowCameraOnVehicle` |
| Economy levers | `Money_*`, `Permissions_*` (block buying rockets abroad), `Resources_SetCost*` (price the goods) |
| People | `Person_SetStatus` (loyalty jumps after a triumph), `Person_GetNumberOfPeople` |
| Randomness | `Random(int)` for the US timeline and launch failures |

Scenarios ship as `WORKSHOP_ITEMTYPE_SCRIPT` items and can auto-start from a
map's `stats.ini` (`$ScenarioAutoStart <scenario> <mission>`), or be offered
on all maps.

**Research** is data (`media_soviet/research/research.ini`, 117 entries):
`$RESEARCH id`, `$TYPE_TECHNICAL|SOVIET|MEDICAL`, `$COST`, `$YEAR`,
`$UNLOCK_RESEARCH`, `$UNLOCK_BUILDING <ident>`, `$UNLOCK_BUILDING_PRODUCTION
<resource>`, `$UNLOCK_TOOLS`. The file path is a single literal in the exe, so
new entries need either a file redirect (a small import hook on `fopen`, the
technique the vendored TesmioLoader used for its VFS; RML itself has no VFS)
or a scenario-emulated programme (objectives that unlock buildings through
`Scenario_UnlockResearch` on entries we control). Both are planned, see 7.

**Vehicle production lines** are the engine's way of turning materials into
hardware: `production_airplane.ini` is `$TYPE_PRODUCTION_LINE
$SUBTYPE_AIRPLANE`, 500 workers + 300 engineers, consumes steel, aluminium,
plastics, mcomponents, ecomponents, fabric, eletronics and produces
`vehicles`; a vehicle type carries `$VEHICLE_BUILT_IN_PRODUCTION_LINE`. A
rocket can therefore be a **vehicle** assembled from real materials.

**Helicopters** are the vertical-take-off vehicle class
(`$TYPE VEHICLETYPE_HELICOPTER`, `$HELIPORT_STATION` on a
`$TYPE_AIRPLANE_PARKING` building). A rocket modelled as a helicopter lifts
straight up from a pad, climbs to cruise altitude and flies off; the script
erases it downrange. No new vehicle class is needed.

**New goods are possible**, with limits. The engine keeps 57 resources in a
vector with room for 63; the vendored `vendor/TesmioLoader/plugins/resources`
plugin (docs `04-adding-resources.md`, `02-findings.md`, `07-pitfalls.md`)
claims free slots, clones or builds a record (transport class, price, meshes,
icon, caption) and the engine's own resolver then accepts the name in any
`$PRODUCTION / $CONSUMPTION / $STORAGE` line. Constraints that shape the
design: the resource count is part of the save format (new game required);
every "else" branch the fixed set kept dead becomes reachable (one purchase
bucket needed a fix); icons are found by name under `media_soviet/resources/`
(an install step or a file hook, RML has no VFS); and the VM's `Resources`
struct exposes only four extra slots (`_Resources_reserved_16_` .. `_19_`),
so **at most four new goods can be read by the scenario script**. Intermediate
goods that only factories touch are unlimited.

**Vanilla resources worth reusing** (all script-readable): `fuel`, `chemicals`,
`explosives`, `steel`, `aluminium`, `plastics`, `ecomponents`, `mcomponents`,
`eletronics`, `fabric`, `nuclearfuel`, `uranium`, `water`, `eletric`, `food`,
`vehicles`.

Everything else we already have: RML plugins with inline hooks (blueprint flag
at VehicleTypes+0x9C88, tick hooks, crash logger), the text item mechanism for
renaming strings, the map converter for a themed start map, id-prefixed idents.

## 3. The history, as a supply chain

What each Soviet milestone actually consumed is the design brief for the
industries. Dates are the historical ones; the US column is the clock the
player races.

| Year | Soviet milestone | Hardware and what it took | USA |
|---|---|---|---|
| 1955-57 | Baikonur built in the Kazakh steppe; R-7 developed (first success 21 Aug 1957) | A rail-supplied launch complex; R-7: kerosene T-1 + liquid oxygen, hydrogen peroxide for turbopumps, aluminium-alloy tanks, five RD-107/108 engines from Glushko's plant; stages shipped by rail from Kuibyshev | Vanguard programme, Atlas/Redstone tests |
| 4 Oct 1957 | **Sputnik 1** (83.6 kg) | Radio transmitter, silver-zinc batteries, polished aluminium sphere | Vanguard TV-3 explodes on the pad (6 Dec 1957) |
| 3 Nov 1957 | Sputnik 2, Laika | Life-support box, telemetry, food | **Explorer 1**, 31 Jan 1958; NASA founded Oct 1958 |
| Sep-Oct 1959 | Luna 2 hits the Moon, Luna 3 photographs the far side | Third stage (Blok E), film camera and scanner, tracking stations across the country | Pioneer failures |
| 24 Oct 1960 | Nedelin catastrophe (R-16 explodes on the pad, ~100 dead) | Hypergolic propellants (UDMH + nitric acid) handled badly | |
| 12 Apr 1961 | **Gagarin, Vostok 1** | Vostok capsule 4.7 t: ablative heat shield, ejection seat, parachutes, pressure suit, cosmonaut training centre, recovery teams, tracking ships | Shepard suborbital 5 May 1961; Kennedy's Moon speech 25 May 1961 |
| 16 Jun 1963 | Tereshkova, Vostok 6 | | Glenn orbits, 20 Feb 1962 |
| 12 Oct 1964 | Voskhod 1, three crew | Stripped capsule, no suits | Gemini flights begin Mar 1965 |
| 18 Mar 1965 | **Leonov's spacewalk** | Inflatable airlock, EVA suit | White's EVA 3 Jun 1965; rendezvous Dec 1965; docking Mar 1966 |
| 16 Jul 1965 | Proton flies (UR-500) | UDMH / N2O4 hypergolics, Chelomei's bureau | Saturn IB, Saturn V development |
| 3 Feb 1966 | **Luna 9 soft landing**; Luna 10 in lunar orbit (Apr) | Ye-6 lander, airbags, retro-rocket | Surveyor 1 lands 2 Jun 1966 |
| 14 Jan 1966 | Korolev dies | The programme loses its integrator | |
| 24 Apr 1967 | Soyuz 1: Komarov killed, parachute failure | Soyuz 6.5 t, orbital module, solar panels | Apollo 1 fire, 27 Jan 1967 |
| Sep 1968 | Zond 5 loops the Moon with tortoises | Proton + Soyuz-derived capsule | **Apollo 8 orbits the Moon, Dec 1968** |
| Jan 1969 | Soyuz 4/5 docking and crew transfer | | |
| Feb & Jul 1969 | **N1 fails twice** | 30 NK-15 engines, no test stand for the full stage - the lesson the mod teaches | **Apollo 11, 20 Jul 1969** |
| Sep-Nov 1970 | Luna 16 returns samples; Lunokhod 1 drives | Robotic alternative to the crewed race | Apollo 12-14 |
| 19 Apr 1971 | **Salyut 1**, first space station; Soyuz 11 crew killed on return (Jun 1971) | 18.5 t station on Proton, long-duration life support | Apollo 17 (Dec 1972), Skylab (May 1973) |
| 17 Jul 1975 | Apollo-Soyuz handshake | Détente ending | |
| 1986-88 | Mir; Energia/Buran (15 Nov 1988) | Hydrogen/oxygen upper stage, orbiter | Shuttle |

The pattern to turn into mechanics: **propellant chemistry** (kerosene/LOX,
hypergolics, later hydrogen), **light alloys and precision parts** (aluminium,
mcomponents), **avionics and radio** (electronics, tracking network), **life
support and crew** (food, textiles, training, medicine), **logistics** (stages
by rail, propellant by tanker, a cosmodrome far from the factories), **testing**
(Nedelin and N1 are what happens when it is skipped) and **a clock that does not
wait**.

## 4. Goods

**Decision (2026-09-29): Track B.** The user chose the industry-specific goods
over the vanilla-only variant; Track A below stays documented only as the
fallback if the resources plugin cannot be made stable under RML.

Two tracks, so the core loop can be played before any engine surgery.

### Track A - vanilla goods only (no resources plugin)

| Role | Game resource | Note |
|---|---|---|
| Kerosene (T-1 / RP-1) | `fuel` | from the refinery chain |
| Liquid oxygen, hydrogen peroxide, hypergolics | `chemicals` | from the chemical plant (oil / coal chains) |
| Solid boosters, separation charges | `explosives` | already produced from chemicals |
| Structures, tanks, engines | `steel`, `aluminium`, `mcomponents` | the rocket is a vehicle built on a production line, which consumes exactly these |
| Avionics, telemetry, guidance | `ecomponents`, `eletronics` | |
| Parachutes, suits, insulation | `fabric`, `plastics` | |
| Crew supplies | `food`, `water` | |
| RTG / nuclear upper-stage flavour | `nuclearfuel` | late game |
| The rocket itself | a **vehicle** (helicopter class) | built from the seven production-line inputs, moved by rail wagon or road transporter |

Track A already yields a full programme: propellant is fuel + chemicals stored
at the pad, the rocket is a vehicle, the payload is a requirement on
electronics/food/etc. delivered to the cosmodrome's covered storage.

### Track B - new goods (resources plugin, four script-visible)

The four goods the scenario must count, one per launch requirement:

| Ident | Class (template) | Made from | Where |
|---|---|---|---|
| `lox` Liquid oxygen | liquid (`oil`) | electricity + water | Air separation plant |
| `hypergolic` UDMH/N2O4 | liquid (`oil`) | chemicals + fuel | Propellant plant |
| `rocket_stage` | open (`steel`) | aluminium + steel + rocket engines | Rocket assembly plant (or the vehicle route above) |
| `spacecraft` | covered (`eletronics`) | avionics + fabric + plastics + food | Spacecraft assembly hall |

Intermediate goods nobody scripts (unlimited, factories only):
`rocket_engine` (steel + mcomponents + chemicals, from the Engine plant),
`avionics` (eletronics + ecomponents + plastics, from the Instrument works),
`heat_shield` (chemicals + fabric), `space_food` (food + plastics), and for the
late game `lh2` liquid hydrogen (electricity + water, cryogenic) for the
Energia/N1-successor tier.

Boil-off is the mechanic that makes liquids interesting: a plugin tick drains
`lox`/`lh2` storages by a few percent per day, so oxygen has to be produced
near the pad and just before a launch, exactly as at Baikonur.

Track B saves are incompatible with vanilla saves once the list is set; the
list must be frozen before release.

## 5. Industries and buildings

Grouped by chain. "Research" is the entry that unlocks the building (7 for how
that is delivered). Worker counts are for balance discussion, not final.

**Propellants**
- Air separation plant (LOX): electricity 4 MW, water; 40 workers. Research `cryogenics`. Places near the pad, boil-off punishes distance.
- Propellant plant (hypergolics): chemicals + fuel -> hypergolic; toxic, pollution 3x, 60 workers; a fire/explosion event chance while stocked (Nedelin). Research `hypergolic_chemistry`.
- Kerosene comes from the vanilla refinery; hydrogen plant (LH2) late, needs nuclear-scale electricity. Research `hydrogen_engines`.

**Hardware**
- Rocket engine plant (OKB-456 / Glushko): steel, mcomponents, chemicals -> rocket engines; 300 workers, 100 engineers. Research `rocket_engines_1`, `_2` (RD-107 -> RD-253 -> NK-33 tiers raise engine count per stage and lower failure chance).
- Engine test stand: consumes engines + propellant, produces nothing but **reliability** (a plugin-tracked number per engine tier that lowers launch failure odds); sited away from the town, noise and pollution. Skipping it is allowed and is how you get N1.
- Rocket assembly plant (Progress, Kuibyshev): the production line. Track A: `$TYPE_PRODUCTION_LINE $SUBTYPE_AIRPLANE` clone that builds rocket vehicles from steel/aluminium/plastics/mcomponents/ecomponents/fabric/eletronics; Track B: factory making `rocket_stage` from aluminium + steel + rocket engines. 500 workers, 300 engineers.
- Instrument works (Zelenograd): eletronics + ecomponents + plastics -> avionics; 200 workers, 150 engineers, needs a university nearby. Research `guidance_systems`.
- Spacecraft assembly hall: avionics + fabric + plastics + heat shield (+ space food for crewed) -> spacecraft; 250 workers, 200 engineers. Research `orbital_capsule`, `crewed_capsule`, `lunar_lander`, `space_station`.
- Parachute and suit works: fabric + plastics -> (Track A) counted as fabric at the pad; (Track B) part of the spacecraft recipe.

**Launch complex (the cosmodrome, must be rail-connected, on flat ground, far from housing)**
- Assembly and test building (MIK): rail cargo station + covered storage for stages/spacecraft; the "integration" step is a 3-day timer in the script.
- Launch pad: `$TYPE_AIRPLANE_PARKING` with `$HELIPORT_STATION`, liquid storages for LOX/kerosene/hypergolics, an explosives storage, 120 workers. Its tag is what the script reads. Pad tiers: R-7 pad (1955), Proton pad (1965, hypergolics), heavy pad (N1/Energia, 1968).
- Tracking station (NIP): TYPE_BROADCAST clone with a big antenna; three needed across the map for crewed flights, each with electronics upkeep. Research `tracking_network`.
- Recovery zone / landing field: airport-like building where the returning capsule (a helicopter vehicle spawned by `Scenario_OrderHelicopterToBuilding`) lands; ambulance + the cosmonaut returns to the training centre.

**People and prestige**
- Cosmonaut training centre (Star City): TYPE_UNIVERSITY subtype technical clone; trains "crew" as a researched status; needs hospital, sport hall, high-quality housing nearby (the game's existing needs).
- Design bureau (OKB-1): the research building of the space tree, TYPE_UNIVERSITY-like with professors; also where the scenario's "programme" objectives are attached.
- Space museum / Gagarin monument: TYPE_MONUMENT with loyalty radius that scales with milestones achieved (built with concrete + steel; unlocked after the first human in orbit).
- Planetarium / cinema newsreel: an attraction; scenario bumps loyalty republic-wide after triumphs, drops it after disasters (`Person_SetStatus`).

**Vehicles**
- Rockets: `r7_semyorka` (1957, ~280 t, kerosene/LOX), `vostok_k` (1960), `molniya` (1960, probes), `proton` (1965, hypergolic), `soyuz_u` (1966), `n1_heavy` (1968, needs the heavy pad and test-stand reliability), `energia` (1987, LH2). Helicopter class, no rotor, exhaust particle, custom vertical flight profile via plugin if the stock climb looks wrong.
- Rail transporters: flat-wagon skins for stages; road erector-transporter (skin of a heavy truck) for pad delivery.
- Recovery: capsule "helicopter" (parachute animation as rotor), search Mi-8 skin.

## 5b. The expert tier (a fourth education level)

Asked 2026-09-29: can cosmonauts be a fourth education tier above university,
earned by time at the training centre, and reusable by other mods? **Yes, and
cheaply**, because of how the engine stores education (verified in
SOVIET64.exe 1.1.1.9, scans kept in `build/edu_hits.json`):

- Education is **one float per citizen at `person+0xA8`** (`Person.fEducation`
  in the VM). Bands: `[0,1)` none, `[1,2)` basic, `[2,3)` higher. The integer
  part is the tier and the fraction is progress inside it: the study update at
  `0x4C21F0` keeps `floor(edu)` and moves only the fraction. School and
  university attendance add to it (`0x1B9F39`, `0x1BB47B`, `0x1BE2A3`,
  `0x1D0FE9`, `0x17AA06`...); new citizens are seeded with a random value in a
  band (`0x834D8C`: 1.0-1.2).
- **Nothing caps it at 3.** None of the 21 writers clamps; the script
  instruction `Person_SetEducation` (VM interpreter `0x5BF51F`) only rejects
  negatives, despite its comment saying 0-3.
- **Every reader uses thresholds, not indices.** 138 float reads of the field
  were decoded; the tests are `>= 1` and `>= 2` (job categories, citizen model
  choice at `0x822E60`/`0x83E2E0`, the citizen window's icon chain at
  `0x7C009D`: `< 1` none, `< 2` basic, else higher). No read turns education
  into an array index. The one arithmetic use, a ranking key `3 - edu + age/k +
  (1 - loyalty)` over residents (`0x1C88E0`), just keeps ordering experts after
  the rest.
- So a value in `[3,4)` is a **valid "expert"** that the vanilla game already
  treats as higher-educated everywhere (fills professor slots, higher-education
  citizen model, shows the higher icon with its raw value above 3), and it is
  **saved with the citizen as it is**: no save format change, and removing the
  plugin leaves experts as ordinary graduates. That is the opposite of new
  resources, which do change the save format.

What turns it into a feature, as a **standalone RML plugin `experts`** with an
ini so other mods reuse it:

1. **Training rule**: a citizen with education `>= 2` (plus optional gates:
   age window from `person+0xD4`, health `person+0xE0`) who is physically
   inside a listed training building (`person+0x58`, as the fallout plugin
   already reads it) gains education at a configured rate up to 3.99; crossing
   3.0 makes an expert. The training centre is built as a workplace whose
   `$PROFESORS_NEEDED` are the trainee seats, so the game's own job system
   brings graduates there every day and the plugin only adds the progress.
   Example: `cosmonaut_centre = 1.0/year, min 2.0, age 23-35, health 0.8`.
2. **Using experts, two levels**:
   - scenario level, available now: count experts employed at a tagged
     building (`Building_Workers_GetID` + `Person.fEducation >= 3`) as a launch
     requirement, e.g. "2 cosmonauts at the Cosmonaut Corps";
   - engine level, later: "expert-only" professor slots for listed building
     types, by detouring the professor acceptance test in the job search so
     those buildings compare against 3.0 instead of 2.0. The exact site is not
     located yet; this is the one piece needing a focused RE session.
3. **Polish**: a fourth icon in the citizen window (patch the compare chain at
   `0x7C009D` and load one more texture), an "Experts" line in the statistics
   window, and a VM-free counter published through the plugin noticeboard
   (`H->provide`) so other plugins can ask how many experts a building has.

Space-race uses: cosmonauts (training centre, crewed launches), chief
designers at the design bureau (research speed), test engineers at the engine
test stand (reliability gain), flight controllers at tracking stations. Other
mods: reactor operators, surgeons, test pilots.

Risks: experts age and die or emigrate like anyone, so the pipeline must be
kept full (a feature: the Soviet programme lost several cosmonauts); the
engine-level expert slots need the job-search test found and hooked; the
training rule depends on `person+0x58` meaning "inside this building", which
the fallout plugin relies on too but has only been validated on the tick
where it was read.

## 6. Mechanics

**The programme board.** One persistent objective per milestone in
historical order, each with requirement bars fed by the script every 30 s:
stages at the MIK, spacecraft at the MIK, LOX at the pad, kerosene at the pad,
crew trained, tracking stations online, research done. When every bar is full
the objective offers a launch window (a story window with a Launch button via
`Scenario_GetUserInput` or a simple confirm).

**A launch.** The script: takes the goods out of the pad and MIK
(`AddFromBuilding` negative, or `Vehicle_Sell` for the rocket vehicle), rolls
the failure chance (base 25% for a new rocket, minus reliability from the
test stand and research, minus 5% per previous success of that rocket, plus
15% if the pad crew is under-staffed, plus 10% in winter), shows the
countdown notification at the pad, follows the camera on the rocket
(`Scenario_FollowCameraOnVehicle`) as it climbs, then either credits the
milestone or triggers the disaster: a fire at the pad (`Building_StartFire`),
loss of the pad crew for the season, a loyalty drop, and the hypergolic
storage emptied.

**The USA.** A table of milestone dates with a random spread (Explorer 1
Jan 1958 +/- 2 months, Shepard May 1961, Glenn Feb 1962, first EVA Jun 1965,
docking Mar 1966, Surveyor Jun 1966, Apollo 8 Dec 1968, Apollo 11 Jul 1969
+/- 4 months, Skylab May 1973). The script announces each US success as a
newspaper notification; if the player already holds that milestone the US date
slips by a random 3-9 months (the historical reaction), if not the player loses
prestige. The US never stops: the Moon lands in 1969-1970 regardless.

**Prestige** is the score: +points per first, a smaller amount for seconds,
minus for disasters. It converts into things the republic feels: a USD
"Interkosmos" income after each first (foreign contracts for launches),
immigration from the East rising with prestige, a loyalty bonus, and research
speed at the design bureau. Losing the Moon does not end the game; the epilogue
branches (Salyut station route, Lunokhod route, Buran route) so an advanced
player still has 15 years of programme after 1969.

**The clock.** The scenario starts 1 Jan 1955 with a working but small
republic (a themed start map, or `$AVAILABLE_ON_ALL_MAPS` with a checklist
that the map must satisfy: a rail line to a flat 2 km x 2 km steppe zone). The
first R-7 launch is possible about 1957 only if the player has already got a
refinery, a chemical plant, aluminium and electronics running - which is the
challenge for advanced players: the vanilla mid-game chains are the
prerequisites, not the goal.

**Difficulty levers** (exposed in the scenario's first window): tons per
launch, US timeline speed (historical / relaxed / brutal), failure base rate,
whether propellant can be imported (default: rockets and propellants cannot be
bought abroad - `Permissions_*` and prices), boil-off rate.

## 7. Technical architecture

Workshop items (all under one collection):
1. `spacerace_scenario` - SCRIPT item: `script.ini`, missions `programme` (main loop), `usa` (the American timeline as a second script via `Script_StartNew`), `launch` (per-launch routine). Text via `$ADD_CUSTOM_TEXT_UTF8`.
2. `spacerace_buildings` - the buildings above (Blender scene scripts as for the Mad-Max kit; vanilla donor meshes recoloured for the first iteration, custom meshes later).
3. `spacerace_vehicles` - rockets, transporters, capsule.
4. `spacerace_words` - TEXT item renaming what needs renaming (none of the vanilla systems is re-purposed this time, so this stays small).
5. Optional `spacerace_map` - a Kazakh-steppe start map from the converter.

RML plugin `spacerace` (one DLL, C++ like `fallout`):
- research injection: import-swap `fopen` to redirect `research/research.ini` to a merged file (vanilla + `research_space.ini`) - the TesmioLoader VFS technique, scoped to one path; fallback is the scenario-emulated programme.
- rocket blueprints: set the blueprint flag (VehicleTypes+0x9C88) for rocket types when their research completes; keep them out of the purchase window.
- launch flight: post-hook on helicopter movement for vehicles whose ident starts with `9000xxx/rocket_` so they climb steeper and higher, plus exhaust particles; erase at altitude by calling the script's contract (a tagged building the script polls).
- boil-off and reliability bookkeeping (Track B), with the storage tick hook we already have in `survivors`.
- (Track B) the vendored `resources` plugin ported to the RML host: it only needs `configInt/configString/provide` plus hooks the RML compat layer already offers; the icon files are the one install step (a `resources/*.png` copy into `media_soviet`, or a second import hook on the icon path).

Script-side contract with the plugin: tagged buildings (`Building_SetTag`)
and tagged vehicles; the plugin writes its numbers into a scratch storage of
the design bureau (a covered storage the script reads with
`GetFromBuildingStorage`), which avoids inventing an IPC.

## 8. Build plan

Phase 0, spikes (each is an afternoon, all in one throwaway map):
- `AddFromBuilding` with a negative amount removes goods; `Vehicle_Sell` on a helicopter parked at a heliport; `Scenario_OrderHelicopterToBuilding` spawn behaviour.
- A helicopter-class rocket without rotors: does it take off, what does the climb look like, can a hook steepen it.
- `research.ini` redirect via an import swap under RML; does the game accept 118 entries and does the tree window draw them.
- The `resources` plugin under RML with one cloned good (`lox` from `oil`): declare, store, produce, transport, save/load.
- Expert tier: set one citizen to 3.5 with `Person_SetEducation`, watch the citizen window, a professor job, the statistics window and a save/load round trip; then a first `experts` plugin that raises education inside one listed building.

Phase 1, core loop with Track A goods: cosmodrome (pad + MIK), rocket assembly
line, design bureau, one rocket (R-7), Sputnik milestone, launch routine with
failure roll, story windows. Playable end to end.

Phase 2, the race: US timeline script, prestige, objectives board, disasters,
the human-flight chain (training centre, tracking stations, recovery),
Gagarin and Leonov milestones, Proton and hypergolics.

Phase 3, Track B goods and the propellant chains (LOX plant, boil-off,
propellant plant, engine plant + test stand, instrument works, spacecraft
hall), research tree injection, the Moon programme (Luna landers, N1 with the
reliability rule, Zond).

Phase 4, end game and epilogues (Moon landing, Salyut, Lunokhod, Buran),
custom meshes, balancing passes with the difficulty levers, text polish,
the start map.

Phase 5, publishing: the same id-prefix regeneration rule as Korea Year Zero,
collection, README.

## 9. Risks and open questions

- Track B's resource count changes break saves and reach untested engine
  code; keep the list to the four script-visible goods plus at most four
  intermediates, freeze it early, and ship Track A as the fallback.
- The VM cannot read a new good beyond the four reserved slots; the design
  above respects that, but any fifth "countable" good must be a vanilla one.
- Helicopter flight for a rocket may look wrong at altitude; the plugin hook is
  the fix, and a static "launch" animation (rocket disappears behind a smoke
  particle effect at the pad) is the fallback.
- `research.ini` redirect: if the import swap is refused by RML's fail-closed
  rules, the programme falls back to scenario-emulated research entirely.
- Production-line recipes are per vehicle class, not per vehicle; a rocket
  costs what an airplane of its weight costs. Acceptable for Track A, replaced
  by explicit `rocket_stage` recipes in Track B.
- Map dependence: the cosmodrome needs flat steppe and rail; either ship a map
  or check the placed pad's terrain from the script (`Terrain_GetHeight`).

## 10. Built so far (2026-09-29) - first in-game test done, fixes pending a retest

Everything here is generated from `tools/` and installed; the game was not run
(the user tests by hand). All offline checks pass: no `$` token in a comment,
every mesh's material list matches its `.mtl` in name and order, every
referenced vanilla file exists, both new DLLs export the three Tesmio entry
points, the merged research tree has 134 unique entries with no dangling
unlock, every space entry has a name, a description and an icon, and the
generated VM script has balanced braces and no undeclared names.

### The 3D kit (item 9000101, `mod/buildings/space_kit`)

`python tools/build_space.py` runs textures, kit, vehicles and previews
(`research` and `deploy` are separate stages). Blender 5.2 headless through
`tools/space_scene.py` and `tools/space_vehicles.py`, helpers in
`tools/srkit.py`, palette in `tools/space_palette.py` (import-free so Blender
can load it), textures from `tools/space_textures.py` (21 materials plus the
night windows). `mmkit.Builder` now takes a palette (`mats=`, `tile=`); the Mad
Max kit keeps the default.

| Object | Model after | Provisional type |
|---|---|---|
| `sr_pad_r7` | Gagarin's Start: raised deck over the flame duct, tulip arms, two service towers, cable and fuelling masts, rail ramp, LOX tanks, bunker, lightning masts | heliport (`$HELIPORT_STATION` = the rocket's stand) |
| `sr_pad_n1` | Site 110: 14 m plateau, three flame trenches, launch table ring, 145 m gantry on its rail arc, four 180 m lightning towers, LOX spheres | heliport |
| `sr_mik` | assembly and testing hall with rail gates, an R-7 on its transporter-erector | aircraft production line: pick the rocket, link the MIK to a pad |
| `sr_rocket_plant` | Progress (Kuibyshev): sawtooth halls, tall bay, Stalinist office, stage on a trailer | factory |
| `sr_engine_plant` | OKB-456: halls, test cell with exhaust stack, an RD-107 on a plinth | factory |
| `sr_test_stand` | vertical stand, stage in its frame, flame channel, bunker | factory |
| `sr_lox_plant` | cold boxes, columns, spheres, cooling tower | factory |
| `sr_propellant` | UDMH / N2O4 columns, bunded tank farm, flare | factory |
| `sr_instruments` | institute block and a sawtooth clean hall | factory |
| `sr_spacecraft` | high hall, vacuum chamber, a Vostok on a stand | factory |
| `sr_tracking` | Pluton: eight 16 m dishes on a bridge truss on a turret | broadcast (radio) |
| `sr_training` | Star City: training block, TsF-18 centrifuge dome, hydrolab, Gagarin statue | broadcast, staff only (6 workers, 40 graduate seats) |
| `sr_bureau` | OKB-1: Stalinist block with portico, star, Sputnik on a column | university, technical |
| `sr_recovery` | helipad, charred descent sphere, parachute, trucks | heliport |
| `sr_monument` | Monument to the Conquerors of Space (107 m titanium trail) | monument |
| `sr_gagarin` | the Gagarin column | monument |

Factory recipes are written in Track B goods and swapped for vanilla stand-ins
while `USE_NEW_GOODS = False` in `space_scene.py` (lox and hypergolics =
chemicals, engines and stages = mcomponents, avionics and spacecraft =
eletronics, heat shield = plastics, space food = food).

### The rockets (items 9000111-9000115, `mod/vehicles/sr_*`)

Helicopter-class vehicles. The class insists on a rotor, so each rocket ships
its own 40 cm block (`screwcon/hi/lo.nmf`, `material_propeler.mtl`; workshop
paths resolve in the item folder, and the line needs all four paths) hidden
inside the body. Crew are passengers. Heights: Sputnik 31.6 m,
Vostok-K 38.4 m, Soyuz 50.1 m, Proton 53.0 m, N1-L3 104.8 m. Each has a
distinct `$MOVEMENT_POWER_KW` (9001..9005) because that is the only per-type
number the VM's Vehicle struct exposes; the programme script identifies
rockets by it.

### Space tech in an ordinary game

**Research** (`tools/space_research.py` writes `mod/plugins/spacerace/data`):
17 entries hanging off *Advanced Engineering Study* and *Electronic Circuits*,
costs 1,500-9,000 (vanilla tops out at 3,700), years 1946-1966, names at
language ids 591000+. Each unlocks its buildings with
`$UNLOCK_BUILDING {KIT}/sr_<building>`. The chain: rocketry (OKB-1), then
liquid engines (engine works, test stand), cryogenics (LOX plant) and guidance
(instrument works); then the R-7 (rocket plant, MIK, R-7 pad); satellite
(spacecraft hall, tracking); biosatellites (recovery field); manned flight
(Star City); glory (monuments), EVA, Soyuz; storable propellants (propellant
plant) and Proton; Soyuz plus Proton open the N1 programme (N1 pad), then
NK-33 engines and lunar landing.

**Plugin `spacerace`** (off by default in RML): at start it copies the icons
into `media_soviet/research` and the programme into
`media_soviet/scenarios/spacerace`, writes `research_merged.ini` (vanilla,
plus parent links from `inject.ini`, plus our entries with `{KIT}` replaced by
`kit_item` from `spacerace.ini`), swaps SOVIET64's `fopen` import so only the
research file opens the merged copy, swaps its `C3D_LANGUAGE::GetString`
import to answer 591000-591999, and pre-hooks the scenario enumeration
(0x5CB7C0, which runs on every world load after stats.ini): if the world has
no scenario, it sets `spacerace / programme` with the auto-start flag, exactly
what a map's `$ScenarioAutoStart` does (scenario std::string 0x9E8648, mission
0x9E8668, flag byte 0x9E8688 = 1, assign helper 0x8EB20).

**Plugin `experts`** (off by default): the fourth education tier.
`experts.ini` has Star City (365 days per tier, graduates aged 23-35 with
health at least 0.8) and OKB-1 (730 days, chief designers up to 3.6, aged
30-65).

**The programme** (`tools/space_scenario.py`, one mission, 1,555 VM lines)
sleeps until *Rocket Research Institute* is researched (since 2026-10-09: and the
Design Bureau built, see "Opening the programme" below), then runs eight
milestones in order. Each waits for its research, then shows progress bars and
launches when everything is in place: a rocket of the right type assigned to a
heliport-type building and parked within 90 m of it; propellant and payload in
storages within 450 m of that pad; cosmonauts (citizens with education at
least 3); tracking stations (broadcast buildings with 40 workers and 30
professors, which is ours). Launch: goods consumed (negative
`AddFromBuilding`), rocket removed (`Vehicle_Sell`), failure roll = base minus
5 per earlier success of that rocket (the N1 gets 35 off with NK-33); a failure
sets the pad on fire.

| Milestone | Research | Rocket | Crew | Tracking | Propellant (t) | Payload (t) | US date to beat |
|---|---|---|---|---|---|---|---|
| Sputnik | satellite | R-7 Sputnik | - | - | 28 | 1 | Explorer 1, 31 Jan 1958 |
| Passenger in orbit | biosatellites | R-7 Sputnik | - | - | 28 | 2 + food | Ham, 31 Jan 1961 |
| To the Moon | lunar probes | Vostok-K | - | 1 | 35 | 2 | Ranger 4, 26 Apr 1962 |
| First man | manned flight | Vostok-K | 1 | 1 | 35 | 5 + food | Glenn, 20 Feb 1962 |
| Spacewalk | EVA | Soyuz | 2 | 1 | 42 | 6 + food | White, 3 Jun 1965 |
| Docking | Soyuz | Soyuz | 3 | 2 | 42 | 7 + food | Gemini 8, 16 Mar 1966 |
| Around the Moon | Proton | Proton | - | 2 | 60 | 8 | Apollo 8, 21 Dec 1968 |
| Moon landing | lunar landing | N1-L3 | 2 | 3 | 280 | 25 + food | **Apollo 11, 20 Jul 1969** |

First: +10 prestige, 25,000 USD and +0.12 loyalty for every citizen. Second:
+3 and 5,000 USD. The US getting there first costs 5 prestige and 0.05
loyalty. Land before 20 July 1969 and the race is won (100,000 USD, +0.2
loyalty).

### First in-game test (2026-09-29)

Confirmed: plugins load from the dev package (3/3 hooks, 34 strings, 17
research entries, autostart fires); `$UNLOCK_BUILDING <item>/<object>` gates
workshop buildings; the models render; a rocket stands on the pad, lifts off
vertically, then flies level to its destination.

Found and fixed:

| Report | Cause | Fix |
|---|---|---|
| `Syntax error: fj>` on load | the VM has no `>=` `<=` `==` `!=` | `x > n-1` forms; the generator asserts none are left and reflows to one statement per line like vanilla |
| `Line 121: No return found at the end of function SumNear` | every function but `main` must end in `return(x)` or `returnVoid();` | `returnVoid();` closes the void helpers; `tools/vmcheck.py` (argument types against `SOVIETInstructions.txt`, struct fields, function endings, operators, `else` placement; 0 false errors over the 71 vanilla scripts) now runs at the end of `space_scenario.py` and fails the build |
| mirrored signs and icons | the engine mirrors models left-right | lettering built mirrored (`srkit.mtext`), icons and collage flipped (idempotent, marked in the PNG) |
| floor flicker that changes with rotation | lot plates at y = 0 fight the terrain | plates at +0.10 first; still showed terrain in patches on the user's buildings (placed on ground that was only roughly flat), so every model is now lifted 0.4 m: the plate is a 0.5 m podium with a skirt 2 m into the ground, like vanilla podiums (cinema 0.66, aluminium plant 0.97); truck bays and pad stations move up to match, road and path connections stay at 0 |
| Star City took students under 2 | it was a university | staff-only broadcast type: graduates fill the 40 seats |
| rotor file errors in `log.html` | vanilla rotor path, one path instead of four | own hidden rotor files, four paths |
| paths cannot connect | `$CONNECTION_PEDESTRIAN` points were inside-to-outside | outside point first, as vanilla (`kino.ini`) |
| MIK accepts every good, bays wrong, no rocket to pick | it was a general storage with bays inside the hall | aircraft production line, bays in the east yard |
| truck bays inside buildings | rocket plant, tracking, LOX plant, instruments | moved; `tools/space_layout.py` draws every lot and fails on a bay through tall geometry |

Second in-game round (2026-09-29, driven by Claude with research off and
unlimited money, so buildings complete without workers). Confirmed: the
programme compiles; no rotor file errors; floors clean; Star City opens as a
staff-only building with 6 staff and 40 graduate seats. It shows as a radio
station ("Actors/Moderators"), and broadcasting is a harmless side effect. The
buy list at the pad shows all five rockets under "Workshop items", priced
about 106,060₽ each whatever `$COST_RUB` says. The MIK opens as a production
line. It takes blueprints (buy with ₽ or $), and its import warehouse holds the
engine's fixed vehicle-parts set: plastics, mechanical components, electrical
components, electronics, fabric and steel, whatever `$CONSUMPTION` says. With
no pad linked it says "No airplane parking areas", and the blueprint list
refuses ("Connect any parking areas first!").

Third round, on the user's own game (5,550 people). The MIK sat at 0%
with all parts in stock: "No Resources! Missing - Steel, Plastics, Fabric,
Electro comp." Those are exactly the parts of the rocket's bill that the MIK's
`$CONSUMPTION` did not list. Plastics (5.96 t on hand, 0.45 t needed) and steel
(59 t) were "missing", while the listed mechanical components, 5 t short, were
not. The recipe comes from the vehicle (0x178FE0 walks vehicletype+0x85C8), but
a part is only drawn if the line declares it. The MIK now declares all seven
parts at 1.0, like `production_airplane.ini`. After a reload it shows
"Operating without issues" and the Soyuz advances. A save made with the old
definition loads fine.

Star City trained nobody (log: 0 citizens training, no per-building census)
although 17 people worked there. The experts plugin looked for citizens whose
person+0x58 was the training building. A read of the running game
(`build/memprobe.py`, game context at RVA 0x9D4F10) shows that +0x58 is the
customs house the citizen immigrated through, +0x40 the building they are in
right now (never home), and +0x80 the workplace (17 at Star City = 6 staff +
11 graduates; 206 at the MIK). Training then ran on the workplace, and eligible
staff did gain 0.033 per game day (2.073 to 2.106 at the day change). But the
game hands out jobs day by day: every one of the 13 people at Star City had
moved on three game days later, and none reached 2.15. Per-person time at the
building never adds up.

Lots, 2026-09-29: with the podium the flicker is gone, but the sand-coloured
`sr_ground` lots looked like sand boxes in game. `sr_ground` is now a steppe lawn
in the game's own grass tones (olive, about (108, 97, 48) in daylight). It covers
Star City, tracking, the recovery field and the earth-covered bunkers. The two
launch pads and the test stand stand on concrete aprons.

The experts plugin therefore runs a **class** per training building
(`class_size`, 40 at Star City, 20 at OKB-1). Eligible citizens who work a
shift there join while seats are free, best-educated first, and keep their
seat whatever job they take next. Each game day every member gains `rate ×
min(1, eligible staff today / class_size)`, so a full house trains the class a
tier in `days_per_tier` days. Members leave at `max_education` (3.0 at Star
City, where they graduate as experts), on failing a gate, or on leaving the
republic. The class lives in memory; after a reload it refills, and partly
trained citizens come back first because seats go to the best-educated.

Linking. A new airplane-parking building takes a parent at placement
(0x2BADE0 around 0x2C70F8). Its footprint is sampled, and a sample inside
another building's `Collision2DBBox` that is also inside that building's
`$CONNECTIONS_SPACE` (typedesc+0xA00) makes that building the parent. Any other
collision is "too close". Three `$CONNECTIONS_SPACE` strips on the MIK all still
gave "too close" or no link, so the spacerace plugin now makes the link itself.
Every 120 building ticks it sets pad+0x5B0 = MIK and calls 0x3BB8F0(game, MIK,
pad) for every unlinked `sr_pad_*` within `link_range` (2000 m) of a MIK. This
is what the game does when it loads a saved link. Logged as `linked launch pad
sr_pad_r7 to the MIK 215 m away`.

The production line (`$TYPE_PRODUCTION_LINE` 0x28, `$SUBTYPE_AIRPLANE` 0x21)
accepts vehicle types 8 (airplane) and 10 (helicopter) (SOVIET64 0x3E3104).
When one is finished it goes to a free station, of kind 0x1F-0x23, on a
building linked to the line (building+0x5B8, 0x1CA97D). A pad is
`$TYPE_AIRPLANE_PARKING` (0x2F), and its `$HELIPORT_STATION` is kind 0x22.

### Launch sequence (2026-09-29, built, not yet run)

The first Sputnik launched in game, but its goods stayed in the storages. The
VM's `Resources.*FromBuilding` calls only read (vanilla uses `AddFromBuilding` to
total up storages), and no VM instruction can take goods out of a building or
move a vehicle. So a launch is now split between the programme and the
spacerace plugin:

- **Script, for new games.** When everything is in place it rolls the outcome and
  calls `Vehicle_SetCanSell(rocket, 0)`, the only vehicle write the VM has. It
  sets a byte at vehicle+0x38A, which scripts read back as `bDisableSell`. On
  success it waits until the plugin clears the flag (at most 60 s), then
  `Vehicle_Sell`. On failure it removes the rocket after 3 s and sets the pad on
  fire. The rocket is found again each time (`FindLaunched`: flagged, or more
  than 20 m above its pad), never by a stale index.
- **Plugin.** Every tick it scans the vehicle list (`ctx+0x12810`; type at
  vehicle+0x1708, ident at type+0x200). When a rocket named in `launches.ini`
  is flagged, it takes that rocket's load from storage buildings (type 5)
  within 450 m of it, then lifts it for `climb_seconds` (18): height
  1.2·t² + 0.25·t³, about 60 m at 5 s and 370 m at 10 s. It writes both world
  matrices (+0xD60 and +0x1080), their inverse translations and the position
  copies (+0xDE0, +0x1100); the game doesn't recompute a parked vehicle's
  matrices. At the end it clears the flag.
- **One load per rocket**, the largest its milestones need, and the objective
  asks for exactly that load: Sputnik 8/20/2/1 (fuel, liquid oxygen, payload,
  food), Vostok-K 10/25/5/1, Soyuz 12/30/7/2, Proton 0/60/8/0, N1 80/200/25/3.
  Goods are counted in storage buildings only, no longer in the MIK or shops.
- **Also in this programme version:**
  - a "Next: <milestone> - research <name>" line;
  - a permanent "Experts: cosmonauts and chief designers" line, with a
    notification at each new expert's position;
  - research switched off (`GameSetting.Research = 0`) counts as researched.
- **Separate mission.** This programme is the `race` mission. Your existing save keeps running
  the old `programme` mission, frozen in `mod/plugins/spacerace/legacy/`, so testing it needs a
  new game.
- **Still to do:** exhaust fire and smoke. Vehicles only emit
  `$PARTICLE_MOVEMENT` while the game moves them, so the plugin would have to
  spawn `airplane_jet` / `big_firesmoke` itself. Also a gentle pitch-over.

### Track B: real goods (2026-09-29, built; launch chain verified in game)

Verified in a test game: all six goods load and appear in general storages with their
icons. The programme read 20 t of LOX through the hooked field. A Sputnik launch took
exactly 8 t fuel, 20 t LOX, 2 t spacecraft and 1 t food from the storages. All five rocket
bills read back from memory as stages, engines and avionics. Still to see in a populated
game: the MIK actually drawing stages, engines and avionics from its import stores and
finishing a rocket.

**Goods.** Six new goods come from the vendored TesmioLoader resources plugin, ported for RML
(`mod/plugins/resources`, regenerated from the vendor copy by `tools/port_resources.py`):

- `rocket_stage` (cloned from aluminium, OPEN);
- `rocket_engine` (from mcomponents, COVERED);
- `avionics` (from eletronics);
- `lox` and `hypergolic` (from oil, OIL, family none);
- `spacecraft` (from eletronics).

The engine's spare records (63 allocated, 57 used) hold all six, so the array never moves.
In game: all six load. General storages offer them with our icons and names: an oil/fuel
tank lists Liquid Oxygen and Hypergolic Propellant, and an industrial warehouse lists Rocket
Engines, Avionics and Spacecraft. **Saves are not compatible across this change.**

**Porting changes from the vendor copy:**

- its ini is read from beside the DLL, because RML's config calls do not find plugin files;
- its hooks are installed in `TsmPluginStart`;
- the customhouse hook is off (survivors owns that tick);
- the price table is not logged.

**Scripts and added goods.** `Resources.GetFromBuilding` and the other Resources calls
place each good by asking 0x59B3F0(vm, name) for its byte offset. That function is a chain
of string compares against the base game's names, and it answers **0, the `workers` field**,
for any other name. So without help an added good is invisible to scripts, or worse, counted
as workers. The earlier "4 script-visible goods" idea assumed an index mapping, which is
wrong. The spacerace plugin now hooks 0x59B3F0 and answers `vm_goods` (lox, hypergolic,
spacecraft, avionics) with `_Resources_reserved_16_..19_` (0xEC..0xF8).

**Chains.** None of them loops; the generator now asserts that. An import storage exists
for every input and an export storage for every output (before, factories producing a
stand-in they also used had no export store).

| Building | Inputs | Output |
|---|---|---|
| Engine works | steel, mechanical components, chemicals | rocket_engine |
| Rocket plant | aluminium, steel, avionics | rocket_stage |
| Instrument works | electronics, electrical components, plastics | avionics |
| Spacecraft hall | avionics, plastics (heat shield), fabric, food | spacecraft |
| LOX plant | a trickle of chemicals and power (water comes only by pipe) | lox |
| Propellant plant | chemicals, fuel | hypergolic |
| Test stand | rocket_engine, lox, fuel | mechanical components (back to the engine works) |

While a test stand is working, launches fail 10 points less often.

**The MIK** consumes `rocket_stage`, `rocket_engine` and `avionics` from its own import
stores. The engine computes every vehicle's bill from its weight in fixed vanilla goods
(0x3F8D10 into vehicle type +0x85C8, 16-byte `{Resource*, float}` entries), so the plugin
rewrites each rocket's bill from `launches.ini` `bill` lines, keeping the workdays:

| Rocket | Stages | Engines | Avionics |
|---|---|---|---|
| Sputnik | 16 t | 6 t | 1 t |
| Vostok | 20 t | 7 t | 2 t |
| Soyuz | 26 t | 9 t | 3 t |
| Proton | 45 t | 14 t | 4 t |
| N1 | 120 t | 40 t | 8 t |

**Launch loads** are named goods per rocket: the Proton flies on 60 t of hypergolics, the
others on fuel and LOX, and every rocket carries spacecraft. Food stays a vanilla stand-in
for space food, and plastics for heat shields.

**Also this round:**

- **Pad rule.** 0x3E2900 decides whether a vehicle type may use a building (purchase lists,
  assignments, production-line delivery). The plugin hooks it, chaining after two other
  plugins' 14-byte jumps. A launch pad now takes only its own rockets, and the recovery
  field takes none. In game, an R-7 pad lists Sputnik, Vostok-K, Soyuz and Proton; no N1 and
  no vanilla helicopters.
- **Launch effects.** The plugin spawns `airplane_jet` flame and a `big_firesmoke` trail
  under the climbing rocket, `factory_big_white` steam at the pad, and a `buildingfall2`
  explosion plus smoke for a failure. It uses `C3D_PARTICLEFFECT_LIBRARY::GetEffect` and
  `C3D_PARTICLEFFECT::SpawnParticles`; the library is at `[SOVIET64+0x9941F0]+0xF60`.
  Verified in game.
- **Games without building fires.** A failed launch closes the pad for 30 days instead of
  setting it on fire.
- **Construction costs.** Rocket empty weights are Sputnik 25 t, Vostok 30, Soyuz 40,
  Proton 70 and N1 180, so they cost 90,818₽ to 217,355₽ and more. The N1 pad's
  construction cost is cut to a quarter.

### Settings and the goods switch (2026-09-30, built, tested offline and in game)

Every balance number moved into `spacerace.ini` (generated below a marker by
`tools/space_settings.py`, with `data/defaults.ini` as the fallback the plugin reads first):
`[research]` years and costs (+ `year_shift`, `cost_scale`), `[america]` dates (`YYYY-MM-DD` or
`never`, + `year_shift`), `[milestones]` failure / crew / tracking, `[rockets]` loads,
`[rocket_parts]` MIK bills, `[launches]` radius / park distance / climb / repair days / failure
modifiers, `[rewards]` money and loyalty, `[buildings]` `cost_scale` and `[building:<object>]`
cost (`auto` or absolute amounts with workers = workdays), `cost_scale`, workers, educated,
production, consumption. The dead `prestige` counter is gone.

How each reaches the game:
- **Research** - `ResearchSettings()` rewrites `$YEAR` / `$COST` while the merged research.ini is
  built (before test mode's filter).
- **Buildings** - the building-type loader opens every `building.ini` through SOVIET64's `fopen`
  import (call at 0x10E37E in 0x10E1F0, just before its "Failed to open %s"), the same import the
  research merge swaps. `DetourFopen` recognises `...\<kit_item>\sr_*\building.ini` and serves
  `spacerace_data\buildings\<object>.ini`, patched: absolute costs become groundworks (asphalt,
  gravel) / skeleton casting (everything else, workdays) / steel laying phases, each with
  `$COST_WORK_BUILDING_ALL`.
- **Programme** - `data/programme/race.tmpl` has 114 `@tokens@` (listed in `milestones.txt`);
  the plugin renders it at start into `scenarios\spacerace\race_<fnv>\` with `rules.ini`
  (radius and loads) and starts that mission in new games. A save keeps its running script, so a
  republic keeps the rules it began with; the plugin never deletes a mission it wrote. On every
  world load `ApplyRules()` reads the running mission's `rules.ini` (a legacy mission without one
  gets launches.ini's loads). The old `race` mission is frozen in `legacy/race`.
- Tracking stations and test stands are recognised by the script through their staff numbers,
  so those two buildings' `workers` / `educated` also feed the template.

**`new_goods`** (`[general]`, default 0). The kit's `building.ini` on disk now uses vanilla
stand-ins (space_scene.py writes every building twice; a stand-in factory drops an input that
became its own output, and the oxygen plant takes mechanical components); the new-goods variant
is `data/goods_buildings/sr_<key>.ini`, which the plugin serves with `new_goods = 1`. With 0 the
resources plugin adds nothing (it reads `spacerace.ini` beside it), launch loads are mapped through
launches.ini's `standin` lines, the MIK keeps the engine's weight-based bill, the ResourceField
hook is not installed, and the programme reads `res.chemicals` / `res.eletronics`. The two modes
render different missions.

Checked offline with a harness that compiles spacerace.cpp against a stub host
(scratch `sr_harness.cpp` / `sr_test.py`): with default settings the plugin's render is
byte-identical to `build/space_programme_default_goods0/1.txt` and all 16 buildings come out
unchanged in both modes; edited settings reach every token, file and rules line.

**In game, 2026-09-30 (Claude, user away):**
- Start-up in both modes: settings read, research merged, `race_d874e562` (stand-ins) and
  `race_710a135c` (new goods) rendered byte-identical to the Python renders; all 16 kit
  buildings served patched when the types load (with a world, not at the menu).
- An existing save (26063, running the frozen `race`) loads with the new build; its programme
  keeps launches.ini's rules. New games on "Flatland with hills" auto-start the rendered mission,
  the script compiles, `rules.ini` is applied.
- `log.html` noise that is the base game's: `ResourceGet - not found waste` (fertiliser and
  incinerator inis name a resource `waste`), `Read error (8)` on `replace_history.bin` /
  `usedveh.bin` (every save, fresh ones too).
- **Construction costs** live in the building type: phases at type+0x370/+0x378 (records of
  0x21B8 bytes), each with a std::vector of {Resource*, float, pad} - auto costs resolved into
  real goods (ground works: workdays, concrete, gravel, asphalt; casting: workdays, concrete,
  steel, bricks, boards; steel laying: workdays, steel, mechanical components).
  `build/costdump.py kit` reads them from a running game; its totals are
  `tools/space_kit_costs.txt`, now the absolute `cost =` defaults (read back in game after the
  switch: within 0.01 %).
- **Saves and the goods** (matched fresh saves of the same map, then loads both ways):
  `stats.ini`'s per-resource sections are by name and `$end`-terminated (unknown names are
  skipped with "ResourceGet - not found"); the only other difference was customhouse trade state.
  A plain save loads with `new_goods = 1` and saves fine - the goods simply join. A new-goods save
  loads with `new_goods = 0`, but **the save writer crashes (0xC0000005)** on a warehouse slot
  whose good was not found. Fix: with `new_goods = 0` the resources plugin hooks only ResourceGet
  and answers the six names with their stand-ins' records (`standin` lines); the new-goods world
  (autosave from the Track B test) then loads and saves as a clean plain save (no new-goods name
  left in it). No converter tool needed for the goods.
- Not tested: a save loaded with the plugins switched off in RML altogether (the scenario, the
  space research entries and the kit buildings would remain in it).

### Opening the programme: OKB-1 and the late start (2026-10-09, built, tested offline)

Two player reports against the first Workshop release (missions `race_d874e562` /
`race_710a135c`):

- **Window spam in an old save.** The programme woke on `IsResearched("sr_rocketry")`
  alone, which is also true in any game with research switched off. It then opened the
  welcome window and went straight through every milestone whose research was done.
- **Loyalty crash in a late save.** `CheckUSA()` ran inside the waiting loop, before the
  programme had even started, so every American date already past cost
  `america_first_loyalty` (-5 %) at once: -40 % in a 1975 save.

The new template:

- **Dormant until the republic joins:** `sr_rocketry` researched (or research off) **and** a
  finished Design Bureau (OKB-1), found by its fingerprint: `BUILDINGTYPE_UNIVERSITY`,
  80 workers, 120 professors (tokens `bureau_workers` / `bureau_educated` from
  `[building:sr_bureau]`). No vanilla university matches (75/75, 50/50, 100/100, 70/70).
  Nothing runs before that, the American timeline included. One notification, once the
  research is done, says OKB-1 opens the race.
- **The American timeline starts with the programme.** At opening (`nStart`, year*365+day)
  the script computes `usDue[i]` = the American date + `nShift`. With `[america] late_start =
  shift` (default) and an opening after `start` (default 1954-01-01, token `start_day`),
  `nShift` = the delay, so every American date moves and the race stays whole. With
  `history` the real dates stand. Either way, a milestone whose `usDue` falls on or before
  the opening is marked done for the Americans silently: no notification, no loyalty lost.
  Reaching it later pays the catch-up reward.
- **The welcome window and race objective** have four variants:
  - on time;
  - shifted: "they mean to land on the Moon in about 16 years", token `moon_after`, worded
    the same in Python `years_text` and C `YearsText`;
  - behind (some American milestones already history);
  - the Moon already lost.

  No runtime-built text: the game's own scripts never pass a `char[]` to a window, so it is
  untested ground.
- **Legacy:** both released renders are frozen in `legacy/` (byte-identical to the
  plugin's output). A save keeps the programme it began with, so republics already
  loaded with the first release keep its behaviour. The fix reaches new games and saves
  first loaded with this version.

Offline: `vmcheck` 0 problems on both renders. The harness renders the template
identically to Python for both goods modes (`race_6c98eb85`, `race_06f5fb56`), and custom
`start` / `late_start` / OKB-1 staff reach the script. Not yet seen in game:
- the hint;
- opening on OKB-1;
- each window variant;
- a shifted American notification.

### Pending: showing the experts in game (done in the launch-sequence programme)

Before it, cosmonauts showed only in `rml-runtime.log` ("N experts in the republic", "promoted") and as
education 3.xx in a citizen window; the Objectives window counts them only during crewed
milestones. Planned for the programme: a `CheckCosmonauts()` called from `CheckUSA()` that counts
citizens with education >= 3, keeps a permanent "Experts: cosmonauts and chief designers" line in
the Objectives window and posts a notification at a cosmonaut's position when the count rises.
Not done mid-test: a save keeps the running programme in `runningScripts.bin` (its texts and data),
so changing `programme.txt` under an existing save risks the restored state no longer matching the
code. Ship it with the next new game, and test whether a changed programme loads into an old save.

### Retest checklist

1. `log.html`: no programme syntax error, no `FAILED fopen ... screw` lines.
2. Signs read correctly (MIK, PROGRESS...), menu icons match the buildings.
3. No flickering floors on any space building from any angle.
4. Paths connect to every space building (the arrow points into the lot).
5. Star City: only graduates (education 2+) in its 40 seats. After a minute
   `rml-runtime.log` shows `experts    sr_training: N inside - ...` with the
   gate that stops each one. `days_per_tier = 30` in the deployed
   `9000100/plugins/experts.ini` for the test, so a graduate aged 23-35 in good
   health reaches 3.0 within about a month of game time.
6. MIK: build a launch pad within 2 km. Within a few seconds `rml-runtime.log`
   says `linked launch pad sr_pad_r7 to the MIK ... m away` and the MIK drops
   "No airplane parking areas". Buy a rocket blueprint with the ₽ blueprint
   button, then pick it with the first button ("Select blueprint to
   manufacture"). Confirmed by Claude up to here. Still to see: with workers
   and parts delivered (steel, aluminium, plastics, fabric, mechanical and
   electrical components, electronics; 30 t empty weight = 6,600 workdays, 22
   t aluminium, 11 t mechanical components...) the finished rocket should
   appear standing on the linked pad.
7. Truck bays on the MIK, rocket plant, tracking station, LOX plant and
   instrument works are in open yard.
