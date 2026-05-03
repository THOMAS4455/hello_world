extends Node2D
## A capturable node on the map (castle, gold mine, etc.)
class_name GameNode

enum NodeType {
	MAIN_CASTLE = 0,
	CASTLE = 1,
	GOLD_MINE = 2,
	MAGIC_SPRING = 3,
	BARRACKS = 4,
	LUMBER_MILL = 5,
}

@export var node_id: String = ""
@export var node_name: String = "据点"
@export var node_type: NodeType = NodeType.CASTLE
@export var max_hp: int = 300
@export var gold_per_tick: int = 4
@export var bonus_effect: String = ""

var hp: int
var node_owner: int = GameState.Owner.NEUTRAL
var is_dead: bool = false

var _plaza: ColorRect
var _frame: ColorRect
var _sprite: ColorRect
var _core: ColorRect
var _icon: ColorRect
var _flag: ColorRect
var _hp_bar: ColorRect
var _hp_bar_bg: ColorRect
var _label: Label
var _bonus_label: Label
var _income_label: Label


func _ready():
	hp = get_effective_max_hp()
	_setup_display()
	GameState.register_node(self)
	add_to_group("map_nodes")
	refresh_display()


func _setup_display():
	_plaza = ColorRect.new()
	_plaza.size = Vector2(110, 110)
	_plaza.position = -_plaza.size / 2.0
	_plaza.color = Color(0.18, 0.17, 0.16, 0.45)
	add_child(_plaza)

	_frame = ColorRect.new()
	_frame.size = Vector2(78, 78)
	_frame.position = -_frame.size / 2.0
	_frame.color = Color(0.08, 0.08, 0.1, 0.85)
	add_child(_frame)

	_sprite = ColorRect.new()
	_sprite.size = Vector2(68, 68)
	_sprite.position = -_sprite.size / 2.0
	add_child(_sprite)

	_core = ColorRect.new()
	_core.size = Vector2(42, 42)
	_core.position = -_core.size / 2.0
	_core.color = Color(0.95, 0.95, 0.95, 0.12)
	add_child(_core)

	_icon = ColorRect.new()
	_icon.size = Vector2(16, 16)
	_icon.position = -_icon.size / 2.0
	_icon.color = Color(1, 1, 1, 0.85)
	add_child(_icon)

	_flag = ColorRect.new()
	_flag.size = Vector2(16, 16)
	_flag.position = Vector2(-34, -34)
	add_child(_flag)

	_hp_bar_bg = ColorRect.new()
	_hp_bar_bg.size = Vector2(72, 7)
	_hp_bar_bg.position = Vector2(-36, 36)
	_hp_bar_bg.color = Color(0.12, 0.12, 0.12, 0.85)
	add_child(_hp_bar_bg)

	_hp_bar = ColorRect.new()
	_hp_bar.size = Vector2(72, 7)
	_hp_bar.position = Vector2(-36, 36)
	add_child(_hp_bar)

	_label = Label.new()
	_label.position = Vector2(-60, 48)
	_label.size = Vector2(120, 18)
	_label.add_theme_font_size_override("font_size", 12)
	_label.add_theme_color_override("font_color", Color.WHITE)
	_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(_label)

	_bonus_label = Label.new()
	_bonus_label.position = Vector2(-60, 64)
	_bonus_label.size = Vector2(120, 16)
	_bonus_label.add_theme_font_size_override("font_size", 10)
	_bonus_label.add_theme_color_override("font_color", Color(0.72, 0.78, 0.84))
	_bonus_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(_bonus_label)

	_income_label = Label.new()
	_income_label.position = Vector2(-48, 78)
	_income_label.size = Vector2(96, 16)
	_income_label.add_theme_font_size_override("font_size", 10)
	_income_label.add_theme_color_override("font_color", Color(1, 0.85, 0.3))
	_income_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(_income_label)


func get_effective_max_hp() -> int:
	var effective_hp = max_hp
	if node_type == NodeType.MAIN_CASTLE:
		var race = GameState.get_race_for_owner(node_owner)
		var passive: Dictionary = RaceData.race_passives.get(race, {})
		if passive.has("castle_hp_mult"):
			effective_hp = int(round(max_hp * float(passive["castle_hp_mult"])))
	return effective_hp


func take_damage(amount: int, attacker_owner: int):
	if is_dead:
		return
	if node_owner == attacker_owner:
		return
	if node_owner == GameState.Owner.NEUTRAL and attacker_owner == GameState.Owner.NEUTRAL:
		return

	hp -= amount
	EventBus.node_damaged.emit(node_id, hp, get_effective_max_hp())
	_flash_damage()

	if hp <= 0:
		if node_type == NodeType.MAIN_CASTLE:
			_destroy(attacker_owner)
		else:
			_capture(attacker_owner)
	refresh_display()


func _capture(new_owner: int):
	var old_owner = node_owner
	node_owner = new_owner
	hp = get_effective_max_hp()
	EventBus.node_captured.emit(node_id, node_owner, old_owner)
	_pulse_capture()


func _destroy(attacker_owner: int):
	node_owner = attacker_owner
	hp = 0
	is_dead = true
	hide()
	GameState.end_game(attacker_owner)


func heal(amount: int):
	if is_dead:
		return
	hp = min(hp + amount, get_effective_max_hp())
	refresh_display()


func refresh_display():
	var owner_color = _get_owner_color()
	_plaza.color = owner_color.darkened(0.72).lerp(Color(0.26, 0.23, 0.19, 0.42), 0.55)
	_frame.color = owner_color.darkened(0.6)
	_sprite.color = owner_color
	_flag.color = owner_color

	match node_type:
		NodeType.MAIN_CASTLE:
			_plaza.size = Vector2(132, 132)
			_plaza.position = -_plaza.size / 2.0
			_sprite.size = Vector2(84, 84)
			_sprite.position = -_sprite.size / 2.0
			_core.size = Vector2(52, 52)
			_core.position = -_core.size / 2.0
			_icon.size = Vector2(24, 24)
			_icon.position = -_icon.size / 2.0
			_icon.color = Color(1, 0.95, 0.85, 0.9)
		NodeType.GOLD_MINE:
			_plaza.size = Vector2(112, 112)
			_plaza.position = -_plaza.size / 2.0
			_sprite.size = Vector2(60, 60)
			_sprite.position = -_sprite.size / 2.0
			_sprite.color = owner_color.lerp(Color(0.85, 0.72, 0.18), 0.5)
			_core.size = Vector2(30, 30)
			_core.position = -_core.size / 2.0
			_icon.size = Vector2(18, 18)
			_icon.position = -_icon.size / 2.0
			_icon.color = Color(1.0, 0.86, 0.34, 0.92)
		NodeType.MAGIC_SPRING:
			_plaza.size = Vector2(108, 108)
			_plaza.position = -_plaza.size / 2.0
			_sprite.size = Vector2(54, 54)
			_sprite.position = -_sprite.size / 2.0
			_sprite.color = owner_color.lerp(Color(0.4, 0.8, 1.0), 0.35)
			_core.size = Vector2(30, 30)
			_core.position = -_core.size / 2.0
			_icon.size = Vector2(12, 24)
			_icon.position = -_icon.size / 2.0
			_icon.color = Color(0.58, 0.9, 1.0, 0.92)
		NodeType.BARRACKS:
			_plaza.size = Vector2(116, 116)
			_plaza.position = -_plaza.size / 2.0
			_sprite.size = Vector2(58, 58)
			_sprite.position = -_sprite.size / 2.0
			_sprite.color = owner_color.lerp(Color(0.9, 0.55, 0.28), 0.25)
			_core.size = Vector2(34, 34)
			_core.position = -_core.size / 2.0
			_icon.size = Vector2(20, 12)
			_icon.position = -_icon.size / 2.0
			_icon.color = Color(0.95, 0.72, 0.52, 0.95)
		NodeType.LUMBER_MILL:
			_plaza.size = Vector2(110, 110)
			_plaza.position = -_plaza.size / 2.0
			_sprite.size = Vector2(56, 56)
			_sprite.position = -_sprite.size / 2.0
			_sprite.color = owner_color.lerp(Color(0.3, 0.78, 0.4), 0.25)
			_core.size = Vector2(32, 32)
			_core.position = -_core.size / 2.0
			_icon.size = Vector2(14, 22)
			_icon.position = -_icon.size / 2.0
			_icon.color = Color(0.72, 0.94, 0.72, 0.92)
		_:
			_plaza.size = Vector2(110, 110)
			_plaza.position = -_plaza.size / 2.0
			_sprite.size = Vector2(68, 68)
			_sprite.position = -_sprite.size / 2.0
			_core.size = Vector2(42, 42)
			_core.position = -_core.size / 2.0
			_icon.size = Vector2(16, 16)
			_icon.position = -_icon.size / 2.0
			_icon.color = Color(1, 1, 1, 0.8)

	var effective_max = get_effective_max_hp()
	var ratio = clamp(float(hp) / max(1.0, float(effective_max)), 0.0, 1.0)
	_hp_bar.size.x = 72.0 * ratio
	if ratio > 0.6:
		_hp_bar.color = Color(0.2, 0.82, 0.28)
	elif ratio > 0.3:
		_hp_bar.color = Color(0.88, 0.74, 0.18)
	else:
		_hp_bar.color = Color(0.88, 0.22, 0.2)

	_label.text = node_name
	_bonus_label.text = get_bonus_text()
	_income_label.text = get_income_text()


func is_enemy_to(my_owner: int) -> bool:
	return node_owner != GameState.Owner.NEUTRAL and node_owner != my_owner


func set_display_name(new_name: String):
	node_name = new_name
	_label.text = new_name


func can_spawn_units() -> bool:
	return node_type in [NodeType.MAIN_CASTLE, NodeType.CASTLE]


func get_priority_score(attacker_owner: int) -> float:
	var score := float(gold_per_tick)
	match node_type:
		NodeType.MAIN_CASTLE:
			score += 100.0
		NodeType.GOLD_MINE:
			score += 14.0
		NodeType.BARRACKS:
			score += 10.0
		NodeType.MAGIC_SPRING:
			score += 8.0
		NodeType.LUMBER_MILL:
			score += 7.0
		NodeType.CASTLE:
			score += 9.0

	if node_owner == GameState.Owner.NEUTRAL:
		score += 6.0
	elif node_owner != attacker_owner:
		score += 10.0

	score += clamp((1.0 - float(hp) / max(1.0, float(get_effective_max_hp()))) * 12.0, 0.0, 12.0)
	return score


func get_bonus_text() -> String:
	match bonus_effect:
		"unit_cost_discount":
			return "招募减费"
		"skill_haste":
			return "技能冷却缩短"
		"bonus_income":
			return "额外产金"
		_:
			match node_type:
				NodeType.MAIN_CASTLE:
					return "主城"
				NodeType.CASTLE:
					return "前线据点"
				NodeType.GOLD_MINE:
					return "高收益金矿"
				NodeType.MAGIC_SPRING:
					return "技能强化"
				NodeType.BARRACKS:
					return "征募中心"
				NodeType.LUMBER_MILL:
					return "后勤工坊"
	return ""


func get_income_text() -> String:
	var total_income = gold_per_tick
	if bonus_effect == "bonus_income":
		total_income += GameState.BONUS_INCOME_LUMBER_MILL
	return "+%dg" % total_income


func _get_owner_color() -> Color:
	match node_owner:
		GameState.Owner.PLAYER:
			return Color(0.22, 0.42, 0.95)
		GameState.Owner.ENEMY:
			return Color(0.9, 0.22, 0.22)
		_:
			return Color(0.42, 0.44, 0.48)


func _flash_damage():
	var tw = create_tween()
	tw.tween_property(_sprite, "modulate", Color(1, 1, 1, 0.75), 0.08)
	tw.tween_property(_sprite, "modulate", Color.WHITE, 0.12)
	tw.parallel().tween_property(_frame, "scale", Vector2.ONE * 1.06, 0.08)
	tw.parallel().tween_property(_frame, "scale", Vector2.ONE, 0.12)


func _pulse_capture():
	scale = Vector2.ONE * 1.08
	var tw = create_tween()
	tw.tween_property(self, "scale", Vector2.ONE, 0.18)
