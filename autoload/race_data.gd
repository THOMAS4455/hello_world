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
	Race.HUMAN: "人族",
	Race.ORC: "兽族",
	Race.UNDEAD: "亡灵",
	Race.NIGHT_ELF: "暗夜精灵",
}

var race_passives := {
	Race.HUMAN: {
		"name": "坚城王国",
		"desc": "步兵护甲 +3，主城生命值 +20%。",
		"bonus_defense": 3,
		"castle_hp_mult": 1.2,
	},
	Race.ORC: {
		"name": "狂暴冲锋",
		"desc": "全体单位攻击 +2，骑兵生命值 +15%。",
		"bonus_attack": 2,
	},
	Race.UNDEAD: {
		"name": "不朽军团",
		"desc": "偏向消耗战的阵营，后续可扩展复活与续战机制。",
		"revive_chance": 0.2,
		"revive_hp_pct": 0.5,
	},
	Race.NIGHT_ELF: {
		"name": "林地疾行",
		"desc": "全体单位移动速度 +30%。",
		"bonus_speed_mult": 1.3,
	},
}

var base_units := {
	UnitType.MELEE: UnitData.new("剑士", UnitType.MELEE, 55, 130, 12, 6, 145.0, 42.0, 0.9, Color(0.3, 0.3, 0.8), "前排主力，适合推进、防守和拆除据点。"),
	UnitType.RANGED: UnitData.new("弓手", UnitType.RANGED, 80, 72, 17, 2, 122.0, 220.0, 1.15, Color(0.3, 0.8, 0.3), "后排输出核心，射程远但需要前排保护。"),
	UnitType.CAVALRY: UnitData.new("骑兵", UnitType.CAVALRY, 105, 96, 11, 4, 240.0, 48.0, 0.72, Color(0.8, 0.8, 0.2), "高机动突击单位，擅长换线、追击和绕后。"),
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
	return race_names.get(race, "未知")


func get_siege_multiplier(unit_type: UnitType) -> float:
	match unit_type:
		UnitType.MELEE:
			return 1.25
		UnitType.RANGED:
			return 0.85
		UnitType.CAVALRY:
			return 0.95
	return 1.0
