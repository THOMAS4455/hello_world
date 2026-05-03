extends Control

var gold_label: Label
var income_label: Label
var objective_label: Label
var race_label: Label
var strategy_label: Label
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
	EventBus.node_captured.connect(_on_node_captured)
	_refresh_gold()
	_refresh_objective()


func _build_ui():
	var top_band = ColorRect.new()
	top_band.anchor_right = 1.0
	top_band.offset_bottom = 126
	top_band.color = Color(0.03, 0.04, 0.05, 0.62)
	add_child(top_band)

	var left_margin = MarginContainer.new()
	left_margin.anchor_right = 0.0
	left_margin.anchor_bottom = 0.0
	left_margin.offset_left = 18
	left_margin.offset_top = 18
	left_margin.offset_right = 388
	left_margin.offset_bottom = 470
	add_child(left_margin)

	var left_stack = VBoxContainer.new()
	left_stack.add_theme_constant_override("separation", 12)
	left_margin.add_child(left_stack)

	var command_panel = _make_panel_container()
	left_stack.add_child(command_panel)

	var command_content = VBoxContainer.new()
	command_content.add_theme_constant_override("separation", 8)
	command_panel.add_child(command_content)

	var command_title = _section_title("战场总览")
	command_content.add_child(command_title)

	gold_label = _value_label(20, Color(1, 0.84, 0.32))
	command_content.add_child(gold_label)

	income_label = _value_label(13, Color(0.76, 0.79, 0.82))
	command_content.add_child(income_label)

	race_label = _value_label(12, Color(0.68, 0.8, 1.0))
	command_content.add_child(race_label)

	strategy_label = _value_label(11, Color(0.75, 0.84, 0.75))
	strategy_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	strategy_label.custom_minimum_size = Vector2(0, 40)
	command_content.add_child(strategy_label)

	var objective_panel = _make_panel_container()
	left_stack.add_child(objective_panel)

	var objective_content = VBoxContainer.new()
	objective_content.add_theme_constant_override("separation", 8)
	objective_panel.add_child(objective_content)

	objective_content.add_child(_section_title("推进目标"))

	objective_label = _value_label(12, Color(0.87, 0.88, 0.91))
	objective_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	objective_label.custom_minimum_size = Vector2(0, 52)
	objective_content.add_child(objective_label)

	var skill_panel = _make_panel_container()
	left_stack.add_child(skill_panel)

	var skill_content = VBoxContainer.new()
	skill_content.add_theme_constant_override("separation", 8)
	skill_panel.add_child(skill_content)
	skill_content.add_child(_section_title("指挥官军令"))

	var skill_buttons = HBoxContainer.new()
	skill_buttons.add_theme_constant_override("separation", 8)
	skill_content.add_child(skill_buttons)

	btn_skill1 = _command_button("1. 治疗")
	btn_skill2 = _command_button("2. 火球")
	btn_skill3 = _command_button("3. 战吼")
	btn_skill1.pressed.connect(func(): _use_skill(0))
	btn_skill2.pressed.connect(func(): _use_skill(1))
	btn_skill3.pressed.connect(func(): _use_skill(2))
	skill_buttons.add_child(btn_skill1)
	skill_buttons.add_child(btn_skill2)
	skill_buttons.add_child(btn_skill3)

	var recruit_panel = _make_panel_container()
	left_stack.add_child(recruit_panel)

	var recruit_content = VBoxContainer.new()
	recruit_content.add_theme_constant_override("separation", 8)
	recruit_panel.add_child(recruit_content)
	recruit_content.add_child(_section_title("征募队列"))

	var unit_buttons = HBoxContainer.new()
	unit_buttons.add_theme_constant_override("separation", 8)
	recruit_content.add_child(unit_buttons)

	btn_melee = _command_button("剑士")
	btn_ranged = _command_button("弓手")
	btn_cavalry = _command_button("骑兵")
	btn_melee.pressed.connect(_buy_melee)
	btn_ranged.pressed.connect(_buy_ranged)
	btn_cavalry.pressed.connect(_buy_cavalry)
	unit_buttons.add_child(btn_melee)
	unit_buttons.add_child(btn_ranged)
	unit_buttons.add_child(btn_cavalry)

	selected_info = _make_panel_container()
	selected_info.visible = false
	left_stack.add_child(selected_info)

	selected_label = _value_label(13, Color.WHITE)
	selected_label.custom_minimum_size = Vector2(0, 60)
	selected_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	selected_info.add_child(selected_label)

	var help_wrap = MarginContainer.new()
	help_wrap.anchor_left = 1.0
	help_wrap.anchor_top = 1.0
	help_wrap.anchor_right = 1.0
	help_wrap.anchor_bottom = 1.0
	help_wrap.offset_left = -362
	help_wrap.offset_top = -210
	help_wrap.offset_right = -18
	help_wrap.offset_bottom = -18
	add_child(help_wrap)

	var help_panel = _make_panel_container()
	help_wrap.add_child(help_panel)

	var help_content = VBoxContainer.new()
	help_content.add_theme_constant_override("separation", 8)
	help_panel.add_child(help_content)
	help_content.add_child(_section_title("战场手册"))

	var help_text = _value_label(12, Color(0.76, 0.78, 0.8))
	help_text.text = "左键拖拽框选部队\n右键沿道路行军、追击或争夺据点\n先拿金矿和兵营，再压前线城堡\n1/2/3 释放军令，改变局部战局"
	help_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	help_content.add_child(help_text)


func _make_panel_container() -> PanelContainer:
	var panel = PanelContainer.new()
	panel.custom_minimum_size = Vector2(360, 0)
	panel.add_theme_stylebox_override("panel", _make_panel())
	return panel


func _make_panel() -> StyleBoxFlat:
	var stylebox = StyleBoxFlat.new()
	stylebox.bg_color = Color(0.08, 0.1, 0.12, 0.9)
	stylebox.border_width_left = 1
	stylebox.border_width_top = 1
	stylebox.border_width_right = 1
	stylebox.border_width_bottom = 1
	stylebox.border_color = Color(0.32, 0.37, 0.43, 0.95)
	stylebox.content_margin_left = 14
	stylebox.content_margin_top = 12
	stylebox.content_margin_right = 14
	stylebox.content_margin_bottom = 12
	stylebox.set("corner_radius_top_left", 6)
	stylebox.set("corner_radius_top_right", 6)
	stylebox.set("corner_radius_bottom_left", 6)
	stylebox.set("corner_radius_bottom_right", 6)
	return stylebox


func _section_title(text_value: String) -> Label:
	var label = Label.new()
	label.text = text_value
	label.add_theme_font_size_override("font_size", 12)
	label.add_theme_color_override("font_color", Color(0.94, 0.78, 0.35))
	return label


func _value_label(size: int, color: Color) -> Label:
	var label = Label.new()
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", color)
	return label


func _command_button(text_value: String) -> Button:
	var button = Button.new()
	button.text = text_value
	button.custom_minimum_size = Vector2(0, 36)
	button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	button.add_theme_font_size_override("font_size", 11)
	var normal = StyleBoxFlat.new()
	normal.bg_color = Color(0.15, 0.18, 0.22)
	normal.border_color = Color(0.38, 0.42, 0.48)
	normal.border_width_left = 1
	normal.border_width_top = 1
	normal.border_width_right = 1
	normal.border_width_bottom = 1
	normal.set("corner_radius_top_left", 4)
	normal.set("corner_radius_top_right", 4)
	normal.set("corner_radius_bottom_left", 4)
	normal.set("corner_radius_bottom_right", 4)
	button.add_theme_stylebox_override("normal", normal)
	button.add_theme_stylebox_override("hover", normal.duplicate())
	button.add_theme_stylebox_override("pressed", normal.duplicate())
	return button


func _process(_delta):
	if not is_node_ready() or not GameState.game_started:
		return

	var income = GameState.get_total_income(GameState.Owner.PLAYER)
	income_label.text = "收入：+%d / 回合  |  兵力：%d" % [income, GameState.get_unit_count(GameState.Owner.PLAYER)]
	race_label.text = "%s军势：%s" % [RaceData.get_race_name(GameState.player_race), RaceData.race_passives[GameState.player_race]["name"]]
	strategy_label.text = _build_strategy_text()

	var rts = get_tree().get_first_node_in_group("rts_controller")
	if rts and rts.selected_units.size() > 0:
		selected_info.visible = true
		var units = rts.selected_units
		if units.size() == 1:
			var unit = units[0]
			if is_instance_valid(unit):
				selected_label.text = "%s\n生命 %d/%d  攻击 %d  防御 %d\n%s" % [unit.unit_name, unit.hp, unit.max_hp, unit.attack_power, unit.defense, unit.description]
		else:
			selected_label.text = "已选中 %d 个单位\n保持编队，沿道路推进下一处关键据点。" % units.size()
	else:
		selected_info.visible = false

	_refresh_unit_buttons()


func _on_gold_changed(owner: int, _amount: int):
	if owner == GameState.Owner.PLAYER:
		_refresh_gold()


func _refresh_gold():
	var income = GameState.get_total_income(GameState.Owner.PLAYER)
	gold_label.text = "军费：%d  |  税收：+%d / 回合" % [GameState.player_gold, income]


func _refresh_unit_buttons():
	var melee_cost = GameState.get_unit_cost(GameState.Owner.PLAYER, RaceData.UnitType.MELEE)
	var ranged_cost = GameState.get_unit_cost(GameState.Owner.PLAYER, RaceData.UnitType.RANGED)
	var cavalry_cost = GameState.get_unit_cost(GameState.Owner.PLAYER, RaceData.UnitType.CAVALRY)

	btn_melee.text = "剑士 %dg" % melee_cost
	btn_ranged.text = "弓手 %dg" % ranged_cost
	btn_cavalry.text = "骑兵 %dg" % cavalry_cost
	btn_melee.disabled = not GameState.can_afford(GameState.Owner.PLAYER, melee_cost)
	btn_ranged.disabled = not GameState.can_afford(GameState.Owner.PLAYER, ranged_cost)
	btn_cavalry.disabled = not GameState.can_afford(GameState.Owner.PLAYER, cavalry_cost)


func _refresh_objective():
	var target = GameState.get_frontline_target(GameState.Owner.PLAYER)
	if target:
		objective_label.text = "下一目标：%s\n收益 %s  |  特性：%s" % [target.node_name, target.get_income_text(), target.get_bonus_text()]
	else:
		objective_label.text = "摧毁敌方主城。"


func _build_strategy_text() -> String:
	var owned_nodes = GameState.get_owned_nodes(GameState.Owner.PLAYER).size()
	var enemy_nodes = GameState.get_owned_nodes(GameState.Owner.ENEMY).size()
	var bonuses: Array[String] = []
	if GameState.has_bonus(GameState.Owner.PLAYER, "unit_cost_discount"):
		bonuses.append("兵营减费")
	if GameState.has_bonus(GameState.Owner.PLAYER, "skill_haste"):
		bonuses.append("技能加速")
	if GameState.has_bonus(GameState.Owner.PLAYER, "bonus_income"):
		bonuses.append("木场增收")
	var bonus_text = "暂无战场加成"
	if not bonuses.is_empty():
		bonus_text = "已获加成：" + " / ".join(bonuses)
	return "据点：我方 %d  |  敌方 %d\n%s" % [owned_nodes, enemy_nodes, bonus_text]


func _spawn_unit(unit_type: int):
	var cost = GameState.get_unit_cost(GameState.Owner.PLAYER, unit_type)
	if not GameState.can_afford(GameState.Owner.PLAYER, cost):
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

	GameState.spend_gold(GameState.Owner.PLAYER, cost)
	var unit = unit_scene.instantiate()
	unit.setup(unit_type, GameState.Owner.PLAYER, GameState.player_race)
	unit.global_position = GameState.get_spawn_road_point(castle.node_id, castle.global_position, randf_range(54.0, 92.0))
	units_layer.add_child(unit)
	unit.snap_to_road()
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


func _on_node_captured(_node_id: String, _new_owner: int, _old_owner: int):
	_refresh_objective()
