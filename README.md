# Blue Mesa — de_blue_mesa_v2

An original Counter-Strike 1.6 desert map inspired by the atmosphere of **Breaking Bad**: a sun-faded RV, a roadside motel row, a family residence, a chicken stop, a fuel stop, and an industrial laundry with blue tanks. The architecture, signs, textures, character art, and layout were created for this map.

**A map by YAMAN.**

**Delivery status: version 1.0.1 (`de_blue_mesa_v2`). A compiled `.bsp` is included and ready to play.**

New in 1.0.1 (`de_blue_mesa_v2`): **no more see-through walls.** 230 undrawn faces - the backs and edges of signs and pictures, left undrawn to save memory - were exposed, and the game showed each as a flat smear with players visible through it. The worst were the back of the motel sign, the residence garage door and the sign over the B stairwell. The generator now draws any such face that nothing covers, and the validator fails if one is ever exposed again.

New in 1.0, a balance pass so neither site is easier for either team:
- **Both sites now give CTs about the same head start.** CTs used to have 5.1 s to set up at A but only 2.7 s at B, so A favoured CTs and B favoured Ts. Now it is **4.8 s at A** and **4.4 s at B** (through the hatch). See *Balance* below.
- **A one-way CT drop hatch into B**, hazard-striped, beside the laundry's north door. A 16-unit kerb you step over, then a fall onto a crate on the plant floor for about 17 HP. It's a rotation route, not a retake route: Ts holding B can aim at the landing. There is no way back up.
- **The B plant zone moved north, around the reactor**, which is now the site's main cover, with a crouch-high crate on its open side. Ts need 0.6 s longer to reach it.
- **The stairwell rail can't be hopped any more.** CTs could jump it and drop onto the lower flight for about 23 HP, an unintended shortcut. An invisible clip above the rail stops that; you can still see and shoot over it.
- **A car wreck in the middle of Long** breaks the 760-unit AWP line from Long Doors to A. Its bonnet is crouch cover (44 units) and its cabin full cover (84), so there is no height where only a head shows over it.
- **The CT Gate moved 128 units west**, so CTs reach A 0.4 s later.
- **The map now carries its version in its name (`de_blue_mesa_v2` since 1.0.1), and other PCs update themselves.** A PC that joins your game downloads the map and its sounds automatically, with nothing to copy. Each release gets a new name; see *Hosting and joining* below.
- **Credits:** "BLUE MESA - A MAP BY YAMAN" boards at T spawn and on Hermanos's back wall facing CT spawn, a YAMAN licence plate on the RV, and the credit in the map description and the overview key.

New in 0.9, after a playtest found the map confusing to find your way around:
- **You can always tell where you are.** There are 21 painted **A / B direction signs**, in orange and teal, at every junction and chokepoint. Four **tall landmarks** stand above the walls: a water tower on the A side, a smokestack on the laundry (B), a fuel pylon on the east route, and a raised Hermanos sign in mid. A landmark is now visible from 74% of the map, up from 18%.
- **Each route has its own material:** red canyon rock on Long, whitewash in mid and the B alley, corrugated metal on the east route, and timber on the CT side. The flat rock cubes are now stepped cliffs.
- **Clean-up from a full audit:**
  - Every object now either touches the wall beside it or leaves at least 48 units, so no gap can swallow a dropped gun or the bomb. The audit found 16 such gaps at bomb site A, 30 in the lanes and about 40 indoors.
  - The crawl-space under the RV is closed.
  - Ten doorways are cleared of furniture.
  - Dead-end pockets are filled in.
  - Round props slide instead of snagging.
  - The two near-black areas (the motel porch and the RV) are lit.
- **The bomb can't be planted on the RV roof** any more; inside the RV is fine.
- **Kill sounds:** the second clip now plays on **HE grenade** kills instead of the C4 blast, and the knife clip is the new one. The plugin plays exactly one sound per death. See *Kill sounds*.

New in 0.8: **death, knife and bomb sounds** from clips the map's owner supplied.

New in 0.7: **music.** A boombox on the RV's counter plays *Blue Mesa Radio*, an original desert-western track written for this map. Shoot the radio and the music stops, like the radio in Valve's `cs_italy`. See *Music* below.

New in 0.6, tuned for **10v10 (20 players)**:
- **A second full-width way into B.** The blockhouse ladder is now a 128-wide smooth stair, the same as the main one, ending at a 128-wide doorway beside the plant zone. Ten attackers are no longer queuing for one staircase, and B has two group entrances plus the lift.
- **A bigger lift.** The car carries about four players instead of two.
- **Hermanos's front windows break.** They look straight down mid, so CTs can shoot them out and hold mid from inside. That gives CTs an answer to Ts, who reach Mid Doors 3.6 s before CTs can contest it.
- **The Scrapyard Gate is its full width.** A fuel-canopy post stood in its mouth and narrowed it to 80 units.

See *Playing 10v10* below for the measurements behind these.

New in 0.5, after the first playtest found the map open and aimless:
- **Lanes and chokepoints.** Walls, rock and fences turn the open desert into three T routes: **Long A**, **Mid** and **East**. They meet the sites at named doorways. See *Layout* below.
- **A new lift.** You step onto a flat car, press **E** on its washer console, and ride about 2.5 s instead of 6.4 s. A call button on each floor fetches it, and it stays where you leave it.
- **A new stair.** One wide, straight flight directly ahead of the laundry's south door, with an invisible ramp so the walk down is smooth. It replaces the narrow, bumpy switchback.
- **Hermanos is usable as a connector.** Its booths used to block both side doors, so it only ever had one working entrance.

New in 0.4: a **spectator / radar overview**, **ambient sound** from stock game files, and **working door sounds**. The lift and shop door were silent in 0.3 because they used Quake's `sounds` key, which GoldSrc's `func_door` ignores.

**Bomb site B is underground.** The industrial laundry is no longer the objective - it is the way in. The superlab sits 288 units beneath it, with three separate descents.

All artwork and music is original homage work generated by the source scripts - no show assets, music, screenshots, or trademarked logos are used or redistributed. Every display string lives in the `LORE` dictionary at the top of `source/generate_map.py`, so the wording can be renamed in one place.

The map compiles clean with SDHLT 1.3.0: no leaks, no tool errors, and every engine budget in single digits or low teens (see *Compile budgets* below). In-game behavior, real RAD lighting levels, and match balance still need a playtest.

## The map

| Item | Included |
| --- | --- |
| Author | YAMAN |
| Game | Counter-Strike 1.6 / GoldSrc |
| Mode | Bomb defusal, selected as the default for this first version |
| Players | 16 T spawns + 16 CT spawns; start playtesting at 5v5 or 8v8 |
| Site A | RV yard, enterable RV with a ladder to its roof, shed, breakable windows. Four entrances |
| Site B | **The superlab, 288 units underground.** Reactor column, fume hoods, chemical cage, control nook. Reached by three descents, plus a one-way CT drop hatch |
| The laundry | Ground level above site B - washers, tanks, workbench, four doors. The approach, not the objective |
| Routes | Long A (west canyon), Mid (the road, through Mid Doors), East (fuel stop and scrapyard) |
| Landmarks | The superlab, the residence, Hermanos chicken stop, the law offices. Seen over the walls: a water tower (A side), the laundry smokestack (B), a fuel pylon (east) and the Hermanos sign (mid) |
| Wayfinding | 22 painted A / B direction signs; each route walled in its own material |
| Descents to B | Two 128-wide smooth stairs (ahead of the laundry's south door, and inside the blockhouse to the south-east) and a four-person press-E lift. CTs also have a one-way drop hatch beside the laundry's north door |
| Interactive elements | Lift with call buttons, sliding shop door, three breakable RV windows, breakable vending machine and lab glassware, two ladders to high ground |
| Sound | 16 looping ambient emitters and two door sound sets from files that ship with CS 1.6, the map's own radio track, and death, knife and grenade clips |
| Overview | 1024x768 spectator / radar image. Inside the laundry walls it shows the superlab level, with site B and the four ways down marked |
| Source format | Valve 220 `.map` with texture axes, editable in a GoldSrc editor |
| Custom assets | 87-entry WAD3 texture set, six TGA skybox faces, the overview image, one music track, three kill-sound clips |
| Dependencies at runtime | Standard CS 1.6 assets, plus the included skybox, overview and music track; no AMXX plugin |

### Layout

CTs start near both sites; Ts leave a walled plaza in the south by one of three exits. Every route to a site passes through a named chokepoint. See `preview/layout.png` for the callouts, `preview/lanes.png` for views of them, and `preview/overview.png` for the in-game image.

| Route | From T spawn | Chokepoint | Arrives |
| --- | --- | --- | --- |
| **Long A** | West exit, past the residence, up the canyon | **Long Doors**, a timber doorway across the canyon | The west side of the A yard |
| **Short A** | Up mid, through Mid Doors, onto the law office porch | The law office: in at the porch door, out of its **north door** | The south side of the A yard |
| **B main** | Up mid, through Mid Doors, east along the **B alley** | The laundry's **south door**, with the stair straight ahead | The stair down to the plant floor |
| **East** | East exit, across the fuel stop | The **Scrapyard Gate** behind the canopy | The laundry's **east door**, or the **east stair** in the blockhouse, straight down to B |

**Connectors.** The **motel** joins mid (T side) to outside Long. **Hermanos** joins mid (CT side) to the A yard through its west door and to the CT pocket through its east door. **Mid Doors** is the pivot: past it, Ts can take Short A, the B alley or Hermanos. CTs reach A through the **CT Gate** in the fence or through Hermanos. They reach B through the laundry's west and north doors, next to the lift, and can drop straight onto the plant floor through the hatch beside the north door.

**High ground.** A ladder at the back of the RV reaches its roof, which overlooks A but is exposed from Long and Short. The maintenance platform in the scrapyard overlooks the east route.

**Timings** (from the validator's route check, at 250 units per second):

| Route | Seconds |
| --- | --- |
| T to A | 11.9 - 12.9 |
| T to B | 11.9 - 13.1 |
| CT to A | 6.6 - 7.8 |
| CT to B | 7.4 - 8.6 |

This check counts the lift as instant and can't fall, so it knows nothing of the hatch. *Balance* below has the realistic figures.

### Playing 10v10

Measured from the validator's walk model, at 250 units per second:

| Point | T arrives | CT arrives | What it means |
| --- | --- | --- | --- |
| Mid Doors | 5.5 s | 9.2 s | Ts own their side of mid; CTs answer from Hermanos's windows |
| Scrapyard Gate | 5.9 s | 13.4 s | The east route is T territory until the scrapyard |
| Motel west door | 7.2 s | 13.1 s | Ts own the link to Long |
| B alley mouth | 7.4 s | 7.7 s | Contested: the mid-to-B cross |
| East stair top | 8.6 s | 10.8 s | Ts reach it first; the fight is in its tunnel |
| Long Doors | 9.2 s | 10.4 s | Contested: a fight at the doors |
| Site A | 12.4 s | 7.6 s | 4.8 s of CT setup |
| Site B | 12.4 s | 8.0 s | 4.4 s of CT setup, through the hatch |

- **Entrances:** A has four (Long Doors, Short A, Hermanos, the CT Gate). B has two 128-wide stairs plus a four-person lift, and a one-way drop hatch for CTs. The laundry above it has four doors.
- **Spawns:** 16 per side, so a 10v10 uses 10 of them. The T plaza's three exits are 128-160 wide.
- **Rotation:** about 12 s from site to site.
- **Frame rate:** read from the compiled BSP's visibility data, the typical spot at player height can see about 850 world faces (27% fewer than before the lanes), and the worst, over mid, about 3250. That's comfortable for modern hardware with 20 player models.

### Balance

The goal is that neither site is easier or harder for either team. These figures come from a walk model that, unlike the validator, can jump up to 45 units and fall, and doesn't count the lift (a real lift trip takes about 10 s):

| | CT arrives | T arrives | CT setup time |
| --- | --- | --- | --- |
| Site A | 7.6 s | 12.4 s (Long; Short 12.6 s) | **4.8 s** |
| Site B, through the hatch (about 17 HP) | 8.0 s | 12.4 s (east; Mid Doors 13.1 s) | **4.4 s** |
| Site B, by the stairs | 9.5 s | 12.4 s | 2.9 s |

In 0.9 the same model gave A 5.1 s and B 2.7 s: A favoured CTs, B favoured Ts.

- **The sites don't need identical numbers.** A has three T entrances, so its CTs must split. B has two, and CTs have three ways down. How long attackers stay exposed on the way in measured about the same at both sites.
- **The hatch is for rotating, not retaking.** It is one-way and always lands on the same crate, so Ts holding B after a plant can aim at it. Retakes go down the stairs or the lift.
- **Cover is kept clear of head-glitch heights.** New cover is either crouch-high (44 units) or taller than a standing player (84 units). Nothing is 56-72 units, where a player could see over it with only their head showing.

### The three landmarks

| Landmark | Where | What it is |
| --- | --- | --- |
| The residence | New build, southwest desert beside the west lane | Beige stucco ranch with a carport, driveway, mailbox, above-ground pool and a decorative garage door. Kitchen, living room, dining table, a laundry nook of washers, and family portraits on the back wall. Two doors, so it is a pass-through landmark that adds cover rather than a wall. |
| Hermanos chicken stop | North end of mid, CT side | Checkerboard floor, two clipped booths under the front windows, order counter, fry line, drinks cooler, three backlit menu boards, and a lit rooftop sign readable from mid and the CT road. Three working doors. |
| The law offices | Motel row, north unit | Short A runs through it. Storefront glazing lettered for the practice, carpet, panelled wall with a wall of diplomas, an oversized desk, filing cabinets, and a rooftop inflatable. |

### Sound

Sound in GoldSrc passes through walls, so the mix is controlled by distance and volume. The underground sources use a small radius and low volume, so from the laundry floor above they are only a faint hum. The surface wind is placed at least 800 units from the superlab, so the lab stays quiet. Volumes near both bomb sites are low so footsteps stay readable.

| Where | Sound | Why |
| --- | --- | --- |
| The lift | Looping motor while moving, braking clang on arrival | Heard on both floors: a signal for both teams that someone is riding it |
| Superlab | Reactor drone, a ceiling extractor fan, the control-room monitors | The room sounds sealed and mechanical, distinct from the surface |
| Access shaft and tunnel | Dripping water | Marks the flank route by ear |
| Laundry floor | The one washer still running | Tells you you're above the lab |
| Open ground | Desert wind at seven points | The surface sounds open, not dead silent |
| Signs, scrapyard, RV | Neon buzz on the Hermanos and motel signs, flies at the scrapyard, the RV's generator | Landmarks you can place by ear |
| The RV radio | *Blue Mesa Radio*, the map's own track | Atmosphere at A; shoot the radio to silence it |

Each file has loop markers (GoldSrc plays a WAV without them once and stops). Apart from the radio track, each is either used by Valve's own CS maps or ships in the stock `cstrike` folder. The emitters are placed by `soundscape()` in the generator.

Room reverb (`env_sound`) was deliberately left out. In GoldSrc a player's reverb setting can stick after they leave the room, which could carry an underground echo out onto the surface, and it can't be judged without playing. Most of Valve's CS maps don't use it either.

### Music

*Blue Mesa Radio* is a 37-second loop in D minor at 78 BPM:
- a tremolo baritone twang lead with slides
- a fingerpicked guitar
- plucked bass, brushes and a shaker over a low drone
- slapback and reverb, and a slightly band-limited tone, because it's coming out of a radio in a camper

It is composed and synthesised note by note in `source/make_music.py`, so it is original, and the package can redistribute it. **It is not the Breaking Bad theme or an arrangement of it.** That theme is copyrighted, and a custom map redistributes its sounds: every server running the map sends the file to every player who joins.

The file is `cstrike/sound/bluemesa/v1/mesa_radio.wav`: 22050 Hz, 16-bit mono, 1.6 MB, with a cue point so GoldSrc loops it seamlessly. The `.res` lists it, so players download it from a server. The radio works like the one in `cs_italy`: a breakable whose target is the `ambient_generic` playing the track, so breaking it switches the music off. Its range is small, so it colours the RV and the plant zone without covering footsteps across the whole A yard.

### Kill sounds (death, knife, grenade)

> **Not included in this repository.** The three clips are third-party audio, so they are not redistributed. To add your own, put a PCM WAV at `source/sounds/death_source.wav`, `knife_source.wav` and/or `grenade_source.wav` and re-run `source/generate_map.py`. Clips you leave out are dropped from the map automatically. The original *Blue Mesa Radio* track is included.

Three short clips, each played once to everyone on the server:

| Clip | Plays when | Needs the plugin? |
| --- | --- | --- |
| `death` | Any player dies (except knife and grenade kills, where the plugin runs) | No. CS 1.6 fires every entity named `game_playerdie` on each death |
| `knife` | A player is killed with the knife | Yes |
| `grenade` | A player is killed by an HE grenade | Yes |

The C4 explosion has no sound of its own. Players the blast kills get the death sound.

**Why a plugin:** the game never tells map entities which weapon made a kill. `tools/amxx/bluemesa_sounds.sma` is a small AMX Mod X plugin. It reads the weapon from the kill feed, then fires exactly one of the map's three sound entities: `bm_snd_knife`, `bm_snd_grenade` or the death sound. So a knife kill plays only the knife sound, never the knife sound plus the death sound. It only activates on Blue Mesa, under any release name (`de_blue_mesa`, `de_blue_mesa_v2`, ...), and only the PC that hosts the game needs it: players who join hear the sounds without it. On a server **without** the plugin, the map still plays the death sound on every death, including knife and grenade kills.

To use it on a server, or a game you host, with Metamod and AMX Mod X installed:
1. Copy `tools/amxx/bluemesa_sounds.amxx` to `cstrike/addons/amxmodx/plugins/`.
2. Add the line `bluemesa_sounds.amxx` to `cstrike/addons/amxmodx/configs/plugins.ini`. If an older `bluemesa_knife.amxx` line is there, remove it.
3. It needs the `engine` and `hamsandwich` modules, which ship with AMX Mod X.

The clips were supplied as MP3s, decoded to `source/sounds/<name>_source.wav`, and cut by ear:
- **Death:** the opening 1.2 s of the 9.3 s clip.
- **Knife:** 1.2 s from 3.7 s into the 7.4 s clip (`new sound for knife.mp3`).
- **Grenade:** the whole 2.2 s clip (`for bomb died.mp3`), trimmed to 2 s.

To change one, replace its `source/sounds/<name>_source.wav` (any sample rate, mono or stereo), adjust its `seconds` / `start` / `volume` in the `CLIPS` table in the generator, run `python3 source/generate_map.py`, and compile. Every player who joins a server running the map downloads the clips.

### The overview

CS 1.6 shows one flat image for the whole map, and places each player's dot by X and Y alone, ignoring height. Site B is directly under the laundry, so inside the laundry walls the overview shows the **superlab level**: the plant zone, the lab's cover, the stairwell treads, the lift and the tunnel from the blockhouse. The laundry's own floor props are drawn as faint outlines. Each of the four ways down, including the CT hatch, has a ▼ badge, and a small key in the margin explains both. The key also carries the author's credit. See `preview/overview.png`.

The image is placed by `ZOOM 1.70`, `ORIGIN 0 0 -288`, `ROTATED 1`. That mapping was verified by projecting Valve's `de_inferno` and `de_dust2` geometry onto their own overview images, where the outlines line up exactly. The generator draws the image and writes the `.txt` from the same constants.

## Files

| Path | Purpose |
| --- | --- |
| `source/de_blue_mesa.map` | Editable level source |
| `source/bluemesa.wad` | 87 texture entries, including tool textures |
| `source/generate_map.py` | Rebuilds geometry and original assets |
| `source/make_music.py` | Composes and renders the radio track; `generate_map.py` runs it |
| `source/geometry.json` | Generated face geometry for the source previews |
| `tools/compile_windows.bat` | Windows compile launcher |
| `tools/compile_linux.sh` | Linux compile launcher |
| `tools/compile_map.py` | Four-stage compiler runner; Python standard library only |
| `tools/validate_source.py` | Independent MAP / WAD / source navigation checks |
| `tools/render_preview.py` | Software renderer of actual source faces |
| `tools/amxx/bluemesa_sounds.sma` / `.amxx` | AMX Mod X plugin for the knife and grenade kill sounds, source and compiled |
| `cstrike/gfx/env/bmesa*.tga` | Six custom skybox faces |
| `cstrike/maps/de_blue_mesa_v2.res` | Resource list: what the game sends to players who join |
| `cstrike/maps/de_blue_mesa_v2.txt` | In-game map description |
| `cstrike/overviews/de_blue_mesa_v2.bmp` / `.txt` | Spectator / radar overview and its placement |
| `cstrike/sound/bluemesa/v1/` | The RV radio's music and the death, knife and grenade clips |
| `preview/overview.png` | The overview, viewable without the game |
| `preview/lanes.png` | Long Doors, Mid Doors, both stairs, the lift and the CT hatch, rendered from the source |
| `preview/blue_mesa_preview.png` | RV and laundry views |
| `preview/landmarks.png` | Superlab, residence, chicken stop and law office interiors |
| `preview/superlab.png` | Bomb site B, underground |
| `preview/layout.png` | Actual source footprints with roofs omitted |
| `preview/textures.png` | Original texture contact sheet |
| `cstrike/maps/de_blue_mesa_v2.bsp` | Compiled, playable map |
| `cstrike.zip` | Just the game files, ready to merge into `cstrike/` |
| `validation/source_report.json` | Static validation results and explicit unverified items |

## Play it now

The map is already compiled, so no toolchain is needed to play:

1. Close CS 1.6.
2. Merge this package's **`cstrike`** folder into your game's `cstrike` folder - for a typical Steam install that is `Steam/steamapps/common/Half-Life/cstrike`. `cstrike.zip` holds exactly those files if you prefer to unzip it directly.
3. Start the game and open the console:

```text
map de_blue_mesa_v2
```

Custom textures are embedded in the BSP, so players do not need a separate `bluemesa.wad`. The six skybox TGAs do need to be present under `cstrike/gfx/env/`, and the overview under `cstrike/overviews/`.

**Bots** learn a new map name from scratch the first time they are added, which takes a minute or two, so nothing needs deleting when you upgrade. Bots can't press the lift's buttons, so they use the two stairs; they may learn the hatch drop.

### Hosting and joining (automatic updates)

Only the PC that **hosts** the game needs this package. Everyone who **joins** gets the map, sky, overview and sounds downloaded automatically the first time, with nothing to copy. On a home network that takes about a minute.

The plugin that plays the knife and grenade sounds also runs only on the host. Everyone who joins hears them, as long as the host has it. If a PC without the plugin hosts, every death plays the death sound, knife and grenade kills included.

**Why the name has a version.** CS 1.6 downloads only the files a player doesn't have, and never replaces one they do. A player with an older `de_blue_mesa.bsp` would be refused ("map differs from server"), and an older sound would keep playing the old clip. So every release gets a new map name (`de_blue_mesa_v1`, `de_blue_mesa_v2`, ...), and the sounds a new folder (`sound/bluemesa/v1/`, `v2/`, ...) whenever a sound changes. Each release is new to everyone, so it always downloads, and unchanged sounds aren't downloaded again. Older copies can stay; they don't get in the way.

**To release an update:** change `MAP_VERSION` at the top of `source/generate_map.py` (and `SOUND_VERSION` too if a sound changed), rename `cstrike/maps/de_blue_mesa_<old>.txt` to the new version, then run the generator and the compile helper. They name everything from `MAP_VERSION`. Install the result on the host only.

Downloads need `sv_allowdownload 1` on the host and `cl_allowdownload 1` on each player, which are the defaults.

The rest of this file covers rebuilding the map from source.

## Compile on Windows

You need a GoldSrc compiler distribution containing CSG, BSP, VIS and RAD, and Python 3.10 or newer for the supplied helper. The helper needs no pip packages. A GoldSrc-capable editor is only needed if you want to edit the level.

1. Extract this package to a normal writable folder.
2. Obtain a GoldSrc compiler distribution such as [SDHLT](https://github.com/seedee/SDHLT), or an existing VHLT installation. Keep the four executables and their supplied support files together. For SDHLT, keep `sdhlt.wad` next to the executables.
3. Install Python 3 if it is not already installed, or use the editor workflow below.
4. Double-click `tools/compile_windows.bat`.
5. Enter the folder that contains the four compiler executables when prompted. The helper recognizes `hlcsg`, `hlbsp`, `hlvis`, `hlrad`, and the corresponding `sdHL…` names, including Windows x64 editions.
6. Wait for all four stages to finish. Full VIS may take time. Each stage's log is retained in `build/`.
7. On success, the helper validates the basic BSP header and writes `cstrike/maps/de_blue_mesa_v2.bsp`.

From a terminal, the equivalent is:

```powershell
py -3 tools/compile_map.py --tools "C:\Mapping\SDHLT"
```

The compile helper creates a working copy in `build/`, copies the required WADs there, and leaves the editable source unchanged. It embeds the used textures with `-nowadtextures`, so players will not need a separate `bluemesa.wad` after this compile.

The compiler stages are:

```text
CSG -nowadtextures de_blue_mesa_v2
BSP de_blue_mesa_v2
VIS -full de_blue_mesa_v2
RAD -extra -bounce 2 de_blue_mesa_v2
```

The helper copies `source/de_blue_mesa.map` to that release name in `build/` first. A level editor compiling the source directly will produce `de_blue_mesa.bsp`; rename it to the release name before shipping.

These are commands for a GoldSrc toolchain. Source / CS2 compile tools do not compile this format.

## Compile through a level editor

1. Configure a **GoldSrc-capable** Hammer or J.A.C.K. installation for Counter-Strike 1.6 and load its Counter-Strike FGD.
2. Add `source/bluemesa.wad` to the editor's texture list. If using SDHLT, also add the `sdhlt.wad` supplied by that compiler and its FGD as instructed by SDHLT.
3. Open `source/de_blue_mesa.map`. Keep the Valve 220 texture format.
4. Check that the world's WAD references resolve to your local texture files. The shipped `bluemesa.wad` reference is relative to the source folder.
5. Run CSG, BSP, full VIS, then RAD. Enable embedding of custom textures (`-nowadtextures`) and copy the successful BSP into this package's `cstrike/maps/` folder.

See the [Valve GoldSrc Hammer documentation](https://developer.valvesoftware.com/wiki/Valve_Hammer_Editor_%28GoldSrc%29) and the [SDHLT usage instructions](https://github.com/seedee/SDHLT) for the editor and compiler configuration.

## Linux compilation

Use Linux-native GoldSrc compiler binaries:

```bash
bash tools/compile_linux.sh --tools /path/to/compile-tools
```

Windows executables need a Windows environment; the helper does not install or configure Wine.

## Install after compilation

1. Close CS 1.6.
2. Merge this package's **`cstrike`** folder into your game's existing **`cstrike`** folder. For a typical Steam installation, that is `Steam/steamapps/common/Half-Life/cstrike`.
3. Confirm the compiled map is at `cstrike/maps/de_blue_mesa_v2.bsp` and all six skybox TGAs are under `cstrike/gfx/env/`.
4. Start the game and enter the console command:

```text
map de_blue_mesa_v2
```

For a server, install the same compiled BSP, `.res`, map description, skybox and overview files, then add `de_blue_mesa_v2` to the map cycle if desired. Preserve the lowercase filenames. The `.res` lists the overview, so clients download it from the server. No bot navigation file is shipped: CS 1.6's built-in bots generate `de_blue_mesa.nav` themselves the first time they are added. Third-party bot plugins (POD-bot and similar) use their own waypoint formats, which are not included.

## What has been checked

The included validator reparses the exported MAP file and reconstructs convex brush vertices from its planes. It does not rely on the generator's in-memory brush list. It also reads the actual WAD3 directory, mip levels, and palettes.

- Every exported brush has positive volume, valid outward plane orientation, and coordinates within ±4096.
- Every texture referenced by the map exists in the WAD3.
- All 32 player spawn hulls are clear of source solids, stand on a floor, and sit inside their matching buy zone.
- The six outer world slabs form a closed source enclosure.
- A conservative 16-unit grid, expanded for a 32-unit-wide standing player, finds a route from every spawn to both objective areas. Doors are treated as open. This is a source approximation, not the engine collision hull.
- **The route check understands more than one floor.** Every grid cell carries each height a player could stand at, and two cells connect when their floors are within one 18-unit step - which is what makes a staircase traversable rather than a wall. A ladder joins the floors within its own height, and the lift joins the floors across its travel. Sliding doors lift nobody. (Before 0.5, any door or ladder joined every floor above it, which let the check "climb" a doorway onto the sky ceiling. Nothing depended on that until the lanes, whose check exposed it.)
- **The lanes are proven, not assumed.** Each site has named entrances: A has Long Doors, Short A, Hermanos's west door and the CT Gate; B has Mid Doors and the Scrapyard Gate. With all of a site's entrances shut, Ts must be unable to reach it. With any one open alone, they must be able to. That proves the walls leave no way round, and that no entrance is blocked. The check found two real problems during 0.5, both now fixed: the motel and law office porches formed a side path around Mid Doors, and the door leaves plus the parked pickup boxed in the Mid Doors exit.
- The stair's invisible ramp is checked to be walkable (a slope under about 45 degrees).
- **Each descent into the superlab is verified on its own**, by routing to site B with the others severed. The CT hatch is a one-way drop, so this walk, which only steps, never counts it: the report shows three of the four shafts working. The report lists which ones work; the check fails if fewer than two do, because a bomb site with a single way in is a deathtrap to attack. The shafts themselves are found from the gaps in the ground slab rather than declared by the generator.
- The RV has standing clearance, and all six skybox faces exist.
- **The overview is read back the way the game reads it.** The validator parses the `.txt` for ZOOM / ORIGIN / ROTATED, checks that the image is a 1024x768 8-bit BMP like the stock ones, and maps every spawn and both bomb sites through it. Each must land on drawn map, not the void. It also checks that the `.res` lists the overview, so servers send it. This catches gross mistakes like a wrong zoom or a large offset. The fine alignment comes from the generator writing the image and the `.txt` from the same constants.
- **Every ambient emitter sits in open air inside the sealed world**: not inside a solid, and with geometry in all six directions. An emitter out in the rock beneath the desert would leak the compile. Doors must use `movesnd`, not Quake's `sounds`. With `--game "<path to your CS 1.6 folder>"` the validator also confirms every stock sound file exists in that install. A sound the map ships itself must be in the package, listed in the `.res`, and mono 8- or 16-bit PCM at 11/22/44 kHz. A looping sound must carry a cue point at sample 0. A one-shot kill sound must not, or it would repeat until stopped.
- Each of these new checks was fed a deliberately broken input (an emitter in the rock, one outside the lab wall, one inside the reactor, a missing sound file, a door using `sounds`, a shifted overview origin, an overview zoomed off the map) and failed as it should.
- **No gaps that swallow dropped guns or the bomb.** Every pair of solids at standing height is checked. A gap of 1-47 units that opens onto the floor is an error: too narrow to walk into, wide enough for a gun or the bomb to be lost. Every object must touch its neighbour or leave at least 48 units. Gaps a third object fills, and gaps inside player clip that nobody can reach, don't count.
- **No see-through faces.** A face textured `NULL` isn't drawn. That is free lightmap space where it is buried against a wall, and a see-through hole with players visible through it anywhere else. Every `NULL` face is probed one unit in front of its centre and near each corner, and must find a solid there. Fed the 1.0 map, the check reports its 230 exposed faces.
- **No crawl-spaces:** there is no floor with something overhead 36-72 units up, where a crouching player fits but a standing one can't. The underside of the RV used to be one.
- **The A plant zone stops below the RV roof.**
- These three were also tested with broken inputs (the A rear cover pulled 20 units off the fence, the RV skirt removed, the plant zone raised over the roof), and each failed as it should.

The full output is in `validation/source_report.json`.

## Compile budgets

From the shipped `build/de_blue_mesa_v2.log`, compiled with SDHLT 1.3.0 (`-nowadtextures`, full VIS, `-extra -bounce 2`). No leaks and no tool errors.

| Budget | Used | Limit | Fullness |
| --- | --- | --- | --- |
| AllocBlock | 17 | 64 | 27% |
| Clipnodes | 6265 | 32767 | 19% |
| World faces | 5742 | 32768 | 18% |
| World leaves | 1662 | 8192 | 20% |
| Models | 21 | 512 | 4% |
| Texture data | 2.27 MB | 32 MB | 7% |

AllocBlock is the budget that actually caps a GoldSrc map, and it is the one to watch when adding detail. Faces that are never visible - the backs of every wall-mounted picture - are textured `NULL` so they cost nothing, which is why the detail pass moved it by a single block.

## Required first playtest

This remaining work cannot be verified from the source preview:

1. Load the map in CS 1.6. Check textures, skybox orientation, and floor / doorway collision.
2. Judge the real RAD lighting. Interior brightness is the least predictable part of this pass - the residence, the law office and the restaurant each got new light entities, and the signage is lit by `info_texlights`, which cannot be judged from the software previews. Check that the two "A MAP BY YAMAN" boards (T spawn, and Hermanos's back wall facing CT spawn) and the RV's plate are readable.
3. Join each team, buy a weapon, and plant / defuse at both sites.
4. Enter and leave the RV, shoot its windows and the fuel-stop vending machine, break the lab glassware, open the shop door, and climb the platform ladder.
5. **Judge the underground bomb site.** This is the least predictable part of the map and the most likely to need changes. Watch whether attackers can take the lab at all, whether defenders can retake it, and whether the fight is decided at the descents rather than on the plant floor. CTs get about 4.4 s to set up through the hatch and 2.9 s by the stairs, against 4.8 s at A. If B still falls too easily, narrow the east stair or move the Scrapyard Gate further out.
6. **Ride the lift.** Four players should fit. Step on, press **E** on the washer console, and it should take about 2.5 seconds down. Press the yellow call button on the laundry's north wall, or on the lab's west wall just south of the shaft, to fetch it. Check that standing under the arriving car makes it reverse rather than trap you. **Listen to it** from both floors while someone else rides it: the motor should be clearly audible on both.
7. **Follow the signs.** From each spawn, follow only the orange A or the teal B signs, and you should reach the site without a wrong turn. Check that the water tower, the laundry smokestack, the fuel pylon and the Hermanos sign are visible over the walls from the lanes.
8. **Walk the stair.** It should feel like one smooth slope, not steps. The rails should stop you stepping off the sides, and the far rail should stop you walking into the drop from the north. Try to jump the rail: an invisible clip should stop you.
9. **Drop through the CT hatch** beside the laundry's north door. The kerb should step over without a jump, the fall should land on the crate for about 17 HP, and there should be no way back up, even with a boost from the crate.
10. **Play each chokepoint** - Long Doors, Mid Doors, Short A through the law office, the B alley, the Scrapyard Gate and the CT Gate - and note which feel one-sided. They are the pieces most likely to need a nudge.
11. **Check the overview.** Die or join as a spectator, open the map overview and watch a player walk from spawn to each site. The dots should follow the roads and doorways on the image. In the superlab they should sit on the lab plan inside the laundry walls.
12. **Listen to the radio** from the A plant zone, then shoot it: the music should stop. Next round, check whether it comes back (in `cs_italy` it does).
13. **Check the kill sounds** (on a game you host, with the plugin): a knife kill plays only the knife clip, an HE grenade kill only the grenade clip, and any other death the death clip. In the console, `amxx plugins` should list "Blue Mesa kill sounds".
14. **Judge the sound mix.** Stand on the B plant floor and listen for footsteps coming down each descent over the reactor hum. If the ambience masks them, lower the `labdrone2` and `fans/fan4` volumes in `soundscape()`; volume is the third value on each `ambient(...)` line.
15. Test with multiple players. Adjust cover, arrival timings, dominant angles, and visibility based on the matches.
16. Check frame rate from the open yard, the superlab, the restaurant, and the lab entrances before deploying to a public server.

## Rebuild or customize the source

Editing the MAP directly is the quickest route in a level editor. Re-running the generator overwrites that MAP, so keep editor revisions in a separate copy.

For scripted changes, install these development dependencies:

```bash
python -m pip install pillow numpy scipy
python source/generate_map.py
python tools/validate_source.py
python tools/render_preview.py
```

The generator owns the buildings, prop placement, textures, and skybox. The software previews use the exported source faces and simple directional shading; **they are not CS 1.6 screenshots and do not show the final RAD lighting**.

To rename any of the landmarks or the wall art wording, edit the `LORE` dictionary at the top of `source/generate_map.py` and re-run the generator; nothing else needs to change.

Useful helpers if you extend the map:

| Helper | Purpose |
| --- | --- |
| `wall_art(x, y, z, w, h, tex, facing)` | Hang a picture at any world size on a `-y` / `+y` / `-x` / `+x` wall. Backs are auto-`NULL`ed. |
| `building(..., windows=, light=, roof=, glass=)` | Walls, roof and a ceiling light, now with window openings and per-building light colour. |
| `weather(name, ...)` | Multiply grime, run-off streaks and a ground-line dirt band over a finished texture. |
| `clip(...)` / `null_faces(...)` | Collision smoothing and lightmap budget control. |
| `slab_with_holes(...)` | Emits a slab as convex boxes around rectangular cutouts - how the ground slab and the lab ceiling are pierced for the descents. Hole-facing sides get their own texture. |
| `stair_run(...)` | A straight flight of treads standing on a base. |
| `furnish(...)` | A carcass plus a contrasting worktop, for desks, counters and benches. |
| `ambient(origin, sound, volume, radius)` | A looping stock sound. `radius` is `SMALL` / `MEDIUM` / `LARGE`, falling silent at about 500 / 800 / 1250 units. |
| `lane_wall(...)` / `gateway(...)` | A 192-high lane wall, and a wall run with one timber doorway and optional open door leaves. The layout lives in `lanes()`. |
| `wreck(...)` / `barrier(...)` / `cover()` | A stripped car, a jersey barrier, and the placement of all the added cover. |
| `overview()` | Redraws the overview and rewrites its `.txt`. Change `OVERVIEW_ZOOM` / `OVERVIEW_ORIGIN` there and both stay in step. |
| `direction_sign(...)` / `signs()` | A painted A / B sign on a wall face. Its arrow is worked out from where the next point on the route lies for the person reading it. All signs are placed in `signs()`. |
| `landmarks()` / `cliff(...)` | The four tall landmarks, and a rock mass built as a stepped cliff. |
| `lane_wall(..., sides=...)` | A lane wall whose faces each take the material of the route they face. |
