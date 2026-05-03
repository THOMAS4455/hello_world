extends Control

var gold_label: Label
var income_label: Label
var selected_info: Panel
var selected_label: Label
var btn_skill1: Button
var btn_skill2: Button
var btn_skill3: Button
var btn_melee: Button
var btn_ranged: Button
var btn_cavalry: Button

var unit_scene = preload("res://scenes/unit/unit_base.tscn")
var _last_spawn_castle: GameNode = null


func _ready():
	add_to_group("ui_hud")
	_build_ui()
	EventBus.gold_changed.connect(_on_gold_changed)
	_refresh_gold()


func _build_ui():
	var stylebox = _make_panel()

	var top_bar = Panel.new()
	top_bar.position = Vector2(10, 10)
	top_bar.size = Vector2(380, 70)
	top_bar.add_theme_stylebox_override("panel", stylebox)
	add_child(top_bar)

	gold_label = Label.new()
	gold_label.position = Vector2(15, 8)
	gold_label.size = Vector2(350, 25)
	gold_label.text = "Gold: 200"
	gold_label.add_theme_font_size_override("font_size", 18)
	gold_label.add_theme_color_override("font_color", Color(1, 0.85, 0.3))
	top_bar.add_child(gold_label)

	income_label = Label.new()
	income_label.position = Vector2(15, 38)
	income_label.size = Vector2(350, 20)
	income_label.text = "Income: 0/tick"
	income_label.add_theme_font_size_override("font_size", 14)
	income_label.add_theme_color_override("font_color", Color(0.7, 0.7, 0.7))
	top_bar.add_child(income_label)

	var skill_panel = Panel.new()
	skill_panel.position = Vector2(10, 90)
	skill_panel.size = Vector2(380, 52)
	skill_panel.add_theme_stylebox_override("panel", stylebox)
	add_child(skill_panel)

	var skill_hint = Label.new()
	skill_hint.position = Vector2(10, 4)
	skill_hint.size = Vector2(360, 18)
	skill_hint.text = "Skills (1/2/3, then left click to cast)"
	skill_hint.add_theme_font_size_override("font_size", 11)
	skill_hint.add_theme_color_override("font_color", Color(0.6, 0.6, 0.6))
	skill_panel.add_child(skill_hint)

	btn_skill1 = _btn("1. Heal", Vector2(10, 24), Vector2(112, 24))
	btn_skill2 = _btn("2. Fireball", Vector2(132, 24), Vector2(112, 24))
	btn_skill3 = _btn("3. War Horn", Vector2(254, 24), Vector2(112, 24))
	btn_skill1.pressed.connect(func(): _use_skill(0))
	btn_skill2.pressed.connect(func(): _use_skill(1))
	btn_skill3.pressed.connect(func(): _use_skill(2))
	skill_panel.add_child(btn_skill1)
	skill_panel.add_child(btn_skill2)
	skill_panel.add_child(btn_skill3)

	var unit_panel = Panel.new()
	unit_panel.position = Vector2(10, 152)
	unit_panel.size = Vector2(380, 65)
	unit_panel.add_theme_stylebox_override("panel", stylebox)
	add_child(unit_panel)

	var unit_hint = Label.new()
	unit_hint.position = Vector2(10, 4)
	unit_hint.size = Vector2(360, 18)
	unit_hint.text = "Recruit Units"
	unit_hint.add_theme_font_size_override("font_size", 11)
	unit_hint.add_theme_color_override("font_color", Color(0.6, 0.6, 0.6))
	unit_panel.add_child(unit_hint)

	btn_melee = _btn("Swordsman 50g", Vector2(10, 24), Vector2(112, 32))
	btn_ranged = _btn("Archer 75g", Vector2(132, 24), Vector2(112, 32))
	btn_cavalry = _btn("Cavalry 100g", Vector2(254, 24), Vector2(112, 32))
	btn_melee.pressed.connect(_buy_melee)
	btn_ranged.pressed.connect(_buy_ranged)
	btn_cavalry.pressed.connect(_buy_cavalry)
	unit_panel.add_child(btn_melee)
	unit_panel.add_child(btn_ranged)
	unit_panel.add_child(btn_cavalry)

	selected_info = Panel.new()
	selected_info.position = Vector2(10, 227)
	selected_info.size = Vector2(260, 60)
	selected_info.add_theme_stylebox_override("panel", stylebox)
	selected_info.visible = false
	add_child(selected_info)

	selected_label = Label.new()
	selected_label.position = Vector2(10, 10)
	selected_label.size = Vector2(240, 40)
	selected_label.add_theme_font_size_override("font_size", 13)
	selected_label.add_theme_color_override("font_color", Color.WHITE)
	selected_info.add_child(selected_label)

	var hint_panel = Panel.new()
	hint_panel.position = Vector2(1500, 860)
	hint_panel.size = Vector2(400, 180)
	hint_panel.add_theme_stylebox_override("panel", stylebox)
	add_child(hint_panel)

	var hint_title = Label.new()
	hint_title.text = "-- Controls --"
	hint_title.position = Vector2(10, 6)
	hint_title.size = Vector2(380, 20)
	hint_title.add_theme_font_size_override("font_size", 14)
	hint_title.add_theme_color_override("font_color", Color(1, 0.85, 0.3))
	hint_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint_panel.add_child(hint_title)

	var hints_text = Label.new()
	hints_text.text = "Left click or drag to select units\nRight click to move or attack\nRight click enemy nodes to capture\nPress 1/2/3 for commander skills"
	hints_text.position = Vector2(10, 30)
	hints_text.size = Vector2(380, 140)
	hints_text.add_theme_font_size_override("font_size", 12)
	hints_text.add_theme_color_override("font_color", Color(0.7, 0.7, 0.7))
	hint_panel.add_child(hints_text)


func _make_panel() -> StyleBoxFlat:
	var stylebox = StyleBoxFlat.new()
	stylebox.bg_color = Color(0.1, 0.1, 0.15, 0.88)
	stylebox.border_width_left = 1
	stylebox.border_width_top = 1
	stylebox.border_width_right = 1
	stylebox.border_width_bottom = 1
	stylebox.border_color = Color(0.3, 0.3, 0.45)
	return stylebox


func _btn(text_value: String, pos: Vector2, size_value: Vector2) -> Button:
	var button = Button.new()
	button.text = text_value
	button.position = pos
	button.size = size_value
	button.add_theme_font_size_override("font_size", 12)
	return button


func _process(_delta):
	if not is_node_ready() or not GameState.game_started:
		return

	var income = GameState.get_total_income(GameState.Owner.PLAYER)
	income_label.text = "Income: +%d/tick" % income

	var rts = get_tree().get_first_node_in_group("rts_controller")
	if rts and rts.selected_units.size() > 0:
		selected_info.visible = true
		var units = rts.selected_units
		if units.size() == 1:
			var unit = units[0]
			if is_instance_valid(unit):
				selected_label.text = "%s | HP:%d/%d | ATK:%d" % [unit.unit_name, unit.hp, unit.max_hp, unit.attack_power]
		else:
			selected_label.text = "Selected: %d units" % units.size()
	else:
		selected_info.visible = false

	btn_melee.disabled = not GameState.can_afford(GameState.Owner.PLAYER, 50)
	btn_ranged.disabled = not GameState.can_afford(GameState.Owner.PLAYER, 75)
	btn_cavalry.disabled = not GameState.can_afford(GameState.Owner.PLAYER, 100)


func _on_gold_changed(owner: int, _amount: int):
	if owner == GameState.Owner.PLAYER:
		_refresh_gold()


func _refresh_gold():
	var income = GameState.get_total_income(GameState.Owner.PLAYER)
	gold_label.text = "Gold: %d  (+%d/tick)" % [GameState.player_gold, income]


func _spawn_unit(unit_type: int):
	var data: RaceData.UnitData = RaceData.base_units[unit_type]
	if not GameState.can_afford(GameState.Owner.PLAYER, data.cost):
		return

	var castle = _find_nearest_player_castle()
	if not castle:
		castle = _last_spawn_castle
	if not castle:
		return

	_last_spawn_castle = castle
	var main_node = get_tree().root.get_node_or_null("Main")
	if not main_node:
		return
	var units_layer = main_node.get_node_or_null("Battlefield/Units")
	if not units_layer:
		return
	GameState.spend_gold(GameState.Owner.PLAYER, data.cost)
	var unit = unit_scene.instantiate()
	unit.setup(unit_type, GameState.Owner.PLAYER, GameState.player_race)
	unit.global_position = castle.global_position + Vector2(randf_range(-30, 30), randf_range(40, 80))

	units_layer.add_child(unit)
	GameState.player_units.append(unit)
	EventBus.unit_spawned.emit(unit)


func _find_nearest_player_castle() -> GameNode:
	var best: GameNode = null
	var best_dist: float = INF
	for node in GameState.nodes.values():
		if node.node_owner == GameState.Owner.PLAYER and node.can_spawn_units():
			var distance = node.global_position.distance_to(Vector2(960, 540))
			if distance < best_dist:
				best_dist = distance
				best = node
	return best


func _buy_melee():
	_spawn_unit(RaceData.UnitType.MELEE)


func _buy_ranged():
	_spawn_unit(RaceData.UnitType.RANGED)


func _buy_cavalry():
	_spawn_unit(RaceData.UnitType.CAVALRY)


func _use_skill(index: int):
	var commander = get_tree().get_first_node_in_group("commander")
	if commander and commander.has_method("activate_skill"):
		commander.activate_skill(index)
