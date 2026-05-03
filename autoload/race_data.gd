extends Node

enum Race {
	HUMAN = 0,
	ORC = 1,
	UNDEAD = 2,
	NIGHT_ELF = 3,
}

enum UnitType {
	MELEE = 0,
	RANGED = 1,
	CAVALRY = 2,
}


class UnitData:
	var unit_name: String
	var unit_type: UnitType
	var cost: int
	var hp: int
	var attack: int
	var defense: int
	var speed: float
	var attack_range: float
	var attack_speed: float
	var color: Color
	var description: String

	func _init(p_name: String, p_type: UnitType, p_cost: int, p_hp: int, p_atk: int, p_def: int, p_spd: float, p_range: float, p_atk_spd: float, p_color: Color, p_desc: String = ""):
		unit_name = p_name
		unit_type = p_type
		cost = p_cost
		hp = p_hp
		attack = p_atk
		defense = p_def
		speed = p_spd
		attack_range = p_range
		attack_speed = p_atk_spd
		color = p_color
		description = p_desc


var race_names := {
	Race.HUMAN: "Human",
	Race.ORC: "Orc",
	Race.UNDEAD: "Undead",
	Race.NIGHT_ELF: "Night Elf",
}

var race_passives := {
	Race.HUMAN: {
		"name": "Fortified Kingdom",
		"desc": "Infantry gain +3 defense, castles gain 20% HP.",
		"bonus_defense": 3,
		"castle_hp_mult": 1.2,
	},
	Race.ORC: {
		"name": "Brutal Charge",
		"desc": "All units gain +2 attack, cavalry gain 15% HP.",
		"bonus_attack": 2,
	},
	Race.UNDEAD: {
		"name": "Deathless Legion",
		"desc": "Theme passive reserved for future revive mechanics.",
		"revive_chance": 0.2,
		"revive_hp_pct": 0.5,
	},
	Race.NIGHT_ELF: {
		"name": "Forest Stride",
		"desc": "All units gain 30% move speed.",
		"bonus_speed_mult": 1.3,
	},
}

var base_units := {
	UnitType.MELEE: UnitData.new("Swordsman", UnitType.MELEE, 50, 100, 10, 5, 150.0, 40.0, 1.0, Color(0.3, 0.3, 0.8)),
	UnitType.RANGED: UnitData.new("Archer", UnitType.RANGED, 75, 60, 15, 2, 120.0, 200.0, 1.2, Color(0.3, 0.8, 0.3)),
	UnitType.CAVALRY: UnitData.new("Cavalry", UnitType.CAVALRY, 100, 80, 8, 3, 250.0, 40.0, 0.8, Color(0.8, 0.8, 0.2)),
}

var race_colors := {
	Race.HUMAN: Color(0.2, 0.4, 0.9),
	Race.ORC: Color(0.9, 0.2, 0.2),
	Race.UNDEAD: Color(0.6, 0.2, 0.9),
	Race.NIGHT_ELF: Color(0.2, 0.8, 0.5),
}


func get_unit_data(race: Race, unit_type: UnitType) -> UnitData:
	var base: UnitData = base_units[unit_type]
	var data := UnitData.new(
		base.unit_name,
		base.unit_type,
		base.cost,
		base.hp,
		base.attack,
		base.defense,
		base.speed,
		base.attack_range,
		base.attack_speed,
		race_colors[race],
		base.description
	)

	var passive: Dictionary = race_passives.get(race, {})
	if passive.has("bonus_attack"):
		data.attack += int(passive["bonus_attack"])
	if passive.has("bonus_defense"):
		data.defense += int(passive["bonus_defense"])
	if passive.has("bonus_speed_mult"):
		data.speed *= float(passive["bonus_speed_mult"])
	if race == Race.ORC and unit_type == UnitType.CAVALRY:
		data.hp = int(round(data.hp * 1.15))

	return data


func get_race_color(race: Race) -> Color:
	return race_colors.get(race, Color.WHITE)


func get_race_name(race: Race) -> String:
	return race_names.get(race, "Unknown")
