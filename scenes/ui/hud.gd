extends Control

var gold_label: Label
var income_label: Label
var selected_info: PanelContainer
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
	set_anchors_preset(Control.PRESET_FULL_RECT)
	offset_left = 0
	offset_top = 0
	offset_right = 0
	offset_bottom = 0
	add_to_group("ui_hud")
	_build_ui()
	EventBus.gold_changed.connect(_on_gold_changed)
	_refresh_gold()


func _build_ui():
	var left_margin = MarginContainer.new()
	left_margin.anchor_right = 0.0
	left_margin.anchor_bottom = 0.0
	left_margin.offset_left = 16
	left_margin.offset_top = 16
	left_margin.offset_right = 412
	left_margin.offset_bottom = 380
	add_child(left_margin)

	var left_stack = VBoxContainer.new()
	left_stack.add_theme_constant_override("separation", 10)
	left_margin.add_child(left_stack)

	var top_bar = _make_panel_container()
	left_stack.add_child(top_bar)
	var top_content = VBoxContainer.new()
	top_content.add_theme_constant_override("separation", 6)
	top_bar.add_child(top_content)

	gold_label = Label.new()
	gold_label.text = "Gold: 200"
	gold_label.add_theme_font_size_override("font_size", 20)
	gold_label.add_theme_color_override("font_color", Color(1, 0.85, 0.3))
	top_content.add_child(gold_label)

	income_label = Label.new()
	income_label.text = "Income: 0/tick"
	income_label.add_theme_font_size_override("font_size", 14)
	income_label.add_theme_color_override("font_color", Color(0.7, 0.7, 0.7))
	top_content.add_child(income_label)

	var skill_panel = _make_panel_container()
	left_stack.add_child(skill_panel)
	var skill_content = VBoxContainer.new()
	skill_content.add_theme_constant_override("separation", 8)
	skill_panel.add_child(skill_content)

	var skill_hint = Label.new()
	skill_hint.text = "Skills"
	skill_hint.add_theme_font_size_override("font_size", 12)
	skill_hint.add_theme_color_override("font_color", Color(0.65, 0.65, 0.7))
	skill_content.add_child(skill_hint)

	var skill_buttons = HBoxContainer.new()
	skill_buttons.add_theme_constant_override("separation", 8)
	skill_content.add_child(skill_buttons)

	btn_skill1 = _btn("1. Heal")
	btn_skill2 = _btn("2. Fireball")
	btn_skill3 = _btn("3. War Horn")
	btn_skill1.pressed.connect(func(): _use_skill(0))
	btn_skill2.pressed.connect(func(): _use_skill(1))
	btn_skill3.pressed.connect(func(): _use_skill(2))
	skill_buttons.add_child(btn_skill1)
	skill_buttons.add_child(btn_skill2)
	skill_buttons.add_child(btn_skill3)

	var unit_panel = _make_panel_container()
	left_stack.add_child(unit_panel)
	var unit_content = VBoxContainer.new()
	unit_content.add_theme_constant_override("separation", 8)
	unit_panel.add_child(unit_content)

	var unit_hint = Label.new()
	unit_hint.text = "Recruit Units"
	unit_hint.add_theme_font_size_override("font_size", 12)
	unit_hint.add_theme_color_override("font_color", Color(0.65, 0.65, 0.7))
	unit_content.add_child(unit_hint)

	var unit_buttons = HBoxContainer.new()
	unit_buttons.add_theme_constant_override("separation", 8)
	unit_content.add_child(unit_buttons)

	btn_melee = _btn("Swordsman 50g")
	btn_ranged = _btn("Archer 75g")
	btn_cavalry = _btn("Cavalry 100g")
	btn_melee.pressed.connect(_buy_melee)
	btn_ranged.pressed.connect(_buy_ranged)
	btn_cavalry.pressed.connect(_buy_cavalry)
	unit_buttons.add_child(btn_melee)
	unit_buttons.add_child(btn_ranged)
	unit_buttons.add_child(btn_cavalry)

	selected_info = _make_panel_container()
	selected_info.visible = false
	left_stack.add_child(selected_info)

	selected_label = Label.new()
	selected_label.custom_minimum_size = Vector2(0, 34)
	selected_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	selected_label.add_theme_font_size_override("font_size", 13)
	selected_label.add_theme_color_override("font_color", Color.WHITE)
	selected_info.add_child(selected_label)

	var hint_wrap = MarginContainer.new()
	hint_wrap.anchor_left = 1.0
	hint_wrap.anchor_top = 1.0
	hint_wrap.anchor_right = 1.0
	hint_wrap.anchor_bottom = 1.0
	hint_wrap.offset_left = -440
	hint_wrap.offset_top = -220
	hint_wrap.offset_right = -16
	hint_wrap.offset_bottom = -16
	add_child(hint_wrap)

	var hint_panel = _make_panel_container()
	hint_wrap.add_child(hint_panel)

	var hint_content = VBoxContainer.new()
	hint_content.add_theme_constant_override("separation", 8)
	hint_panel.add_child(hint_content)

	var hint_title = Label.new()
	hint_title.text = "Controls"
	hint_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint_title.add_theme_font_size_override("font_size", 15)
	hint_title.add_theme_color_override("font_color", Color(1, 0.85, 0.3))
	hint_content.add_child(hint_title)

	var hints_text = Label.new()
	hints_text.text = "Left click or drag to select units\nRight click to move or attack\nRight click enemy nodes to capture\nPress 1/2/3 for commander skills"
	hints_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	hints_text.add_theme_font_size_override("font_size", 12)
	hints_text.add_theme_color_override("font_color", Color(0.7, 0.7, 0.7))
	hint_content.add_child(hints_text)


func _make_panel_container() -> PanelContainer:
	var panel = PanelContainer.new()
	panel.custom_minimum_size = Vector2(396, 0)
	panel.add_theme_stylebox_override("panel", _make_panel())
	return panel


func _make_panel() -> StyleBoxFlat:
	var stylebox = StyleBoxFlat.new()
	stylebox.bg_color = Color(0.1, 0.1, 0.15, 0.88)
	stylebox.border_width_left = 1
	stylebox.border_width_top = 1
	stylebox.border_width_right = 1
	stylebox.border_width_bottom = 1
	stylebox.border_color = Color(0.3, 0.3, 0.45)
	stylebox.content_margin_left = 12
	stylebox.content_margin_top = 10
	stylebox.content_margin_right = 12
	stylebox.content_margin_bottom = 10
	return stylebox


func _btn(text_value: String) -> Button:
	var button = Button.new()
	button.text = text_value
	button.custom_minimum_size = Vector2(0, 34)
	button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
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
