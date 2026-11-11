// Blue Mesa kill sounds - an AMX Mod X plugin.
//
// The map carries three one-shot, play-everywhere sounds (ambient_generic):
//   game_playerdie  - the death sound; CS fires it by name on every death
//   bm_snd_knife    - the knife-kill sound; nothing in the map fires it
//   bm_snd_grenade  - the HE-grenade-kill sound; nothing in the map fires it
//
// A map cannot tell which weapon made a kill, so this plugin does: it reads the
// weapon from the kill feed (DeathMsg) and, once the death has happened, fires
// exactly one of the three. To stop the death sound also playing on knife and
// grenade kills, it renames game_playerdie so the game no longer fires it, and
// plays it itself for every other death.
//
// Without this plugin the map still plays the death sound on every death.
// Active only on Blue Mesa, under any release name (de_blue_mesa, de_blue_mesa_v1,
// de_blue_mesa_v2, ...). Only the server needs it: players who join hear the
// sounds without it. Needs Metamod + AMX Mod X 1.8.2 or later with
// the engine and hamsandwich modules (both ship with AMX Mod X).
//
// Install: bluemesa_sounds.amxx in addons/amxmodx/plugins/, and the line
// "bluemesa_sounds.amxx" in addons/amxmodx/configs/plugins.ini.

#include <amxmodx>
#include <engine>
#include <hamsandwich>

// Each release carries its version in its name, so match the start of it.
new const MAP_PREFIX[] = "de_blue_mesa"

enum { KIND_OTHER, KIND_KNIFE, KIND_GRENADE }

new g_death, g_knife, g_grenade
new g_kind[33]

public plugin_init()
{
	register_plugin("Blue Mesa kill sounds", "2.1", "de_blue_mesa")

	new map[32]
	get_mapname(map, charsmax(map))
	if (!equali(map, MAP_PREFIX, charsmax(MAP_PREFIX)))
		return

	g_knife = find_ent_by_tname(-1, "bm_snd_knife")
	g_grenade = find_ent_by_tname(-1, "bm_snd_grenade")
	g_death = find_ent_by_tname(-1, "game_playerdie")
	// From here on this plugin decides which sound each death gets.
	if (g_death)
		entity_set_string(g_death, EV_SZ_targetname, "bm_snd_death")

	register_event("DeathMsg", "on_death_msg", "a")
	RegisterHam(Ham_Killed, "player", "on_killed", 1)
}

// DeathMsg: 1 killer, 2 victim, 3 headshot, 4 weapon name. It is sent while
// the victim is being killed, so it always arrives before on_killed below.
public on_death_msg()
{
	new victim = read_data(2)
	if (victim < 1 || victim > 32)
		return
	new weapon[16]
	read_data(4, weapon, charsmax(weapon))
	if (equal(weapon, "knife"))
		g_kind[victim] = KIND_KNIFE
	else if (equal(weapon, "grenade"))
		g_kind[victim] = KIND_GRENADE
	else
		g_kind[victim] = KIND_OTHER
}

// Every death, including ones with no kill-feed entry, such as the bomb.
public on_killed(victim)
{
	if (victim < 1 || victim > 32)
		return
	new ent = g_death
	if (g_kind[victim] == KIND_KNIFE && g_knife)
		ent = g_knife
	else if (g_kind[victim] == KIND_GRENADE && g_grenade)
		ent = g_grenade
	g_kind[victim] = KIND_OTHER
	if (ent)
		force_use(victim, ent)
}
