extends Node2D

@onready var race_select = $UI/RaceSelect
@onready var game_over = $UI/GameOver
@onready var hud = $UI/HUD


func _ready():
	add_to_group("main_scene")
	GameState.reset_match_state()

	for child in $Battlefield/Nodes.get_children():
		if child is GameNode:
			GameState.register_node(child)
			if child.node_id == "player_main":
				child.node_owner = GameState.Owner.PLAYER
			elif child.node_id == "enemy_main":
				child.node_owner = GameState.Owner.ENEMY
			child.refresh_display()

	_draw_roads()

	$Battlefield/Units.add_to_group("battlefield_units")

	race_select.race_selected.connect(_on_race_selected)
	game_over.restart_requested.connect(_on_restart)
	game_over.back_to_menu.connect(_on_back_to_menu)

	print("[Main] Ready - awaiting race selection")


func _on_race_selected(race_id: int):
	GameState.player_race = race_id
	GameState.enemy_race = randi() % 4
	if GameState.enemy_race == GameState.player_race:
		GameState.enemy_race = (GameState.player_race + 1) % 4

	for child in $Battlefield/Nodes.get_children():
		if child is GameNode and child.node_id == "enemy_main":
			child.set_display_name(RaceData.get_race_name(GameState.enemy_race))
		elif child is GameNode and child.node_id == "player_main":
			child.set_display_name(RaceData.get_race_name(GameState.player_race))

	GameState.player_gold = 200
	GameState.enemy_gold = 200
	GameState.game_ended = false

	race_select.visible = false
	hud.visible = true

	_spawn_starting_units()
	GameState.game_started = true
	EventBus.gold_changed.emit(GameState.Owner.PLAYER, GameState.player_gold)
	EventBus.gold_changed.emit(GameState.Owner.ENEMY, GameState.enemy_gold)

	var banner = Label.new()
	banner.text = "Battle Start"
	banner.position = Vector2(0, 400)
	banner.size = Vector2(1920, 60)
	banner.add_theme_font_size_override("font_size", 48)
	banner.add_theme_color_override("font_color", Color(1, 0.85, 0.3))
	banner.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(banner)

	var tw = create_tween()
	tw.tween_property(banner, "modulate:a", 0.0, 2.0)
	tw.tween_callback(banner.queue_free)
	print("[Main] Battle started")


func _on_restart():
	get_tree().reload_current_scene()


func _on_back_to_menu():
	get_tree().reload_current_scene()


func _draw_roads():
	var roads_layer = $Battlefield/Roads
	var roads_data = [
		["player_main", "gold_mine"], ["player_main", "neutral_castle"],
		["gold_mine", "neutral_castle"], ["gold_mine", "barracks"],
		["neutral_castle", "magic_spring"], ["neutral_castle", "lumber_mill"],
		["magic_spring", "lumber_mill"], ["barracks", "enemy_main"],
		["barracks", "magic_spring"], ["lumber_mill", "enemy_main"],
	]
	var node_positions := {}

	for child in $Battlefield/Nodes.get_children():
		if child is GameNode:
			node_positions[child.node_id] = child.position

	for pair in roads_data:
		if node_positions.has(pair[0]) and node_positions.has(pair[1]):
			var line = Line2D.new()
			line.points = PackedVector2Array([node_positions[pair[0]], node_positions[pair[1]]])
			line.width = 3.0
			line.default_color = Color(0.3, 0.25, 0.15, 0.6)
			roads_layer.add_child(line)

	GameState.build_road_graph(roads_data)
	GameState.build_road_segments()


func _spawn_starting_units():
	var unit_scene = load("res://scenes/unit/unit_base.tscn")
	var units_layer = $Battlefield/Units

	for i in range(3):
		var unit = unit_scene.instantiate()
		unit.setup(RaceData.UnitType.MELEE, GameState.Owner.PLAYER, GameState.player_race)
		unit.global_position = Vector2(200 + i * 40, 460)
		units_layer.add_child(unit)
		GameState.player_units.append(unit)

	for i in range(2):
		var unit = unit_scene.instantiate()
		unit.setup(RaceData.UnitType.MELEE, GameState.Owner.ENEMY, GameState.enemy_race)
		unit.global_position = Vector2(1650 + i * 40, 400)
		units_layer.add_child(unit)
		GameState.enemy_units.append(unit)
