extends Node2D

@onready var race_select = $UI/RaceSelect
@onready var game_over = $UI/GameOver
@onready var hud = $UI/HUD


func _ready():
	add_to_group("main_scene")
	GameState.reset_match_state()
	_decorate_battlefield()

	for child in $Battlefield/Nodes.get_children():
		if child is GameNode:
			GameState.register_node(child)
			if child.node_id == "player_main":
				child.node_owner = GameState.Owner.PLAYER
				child.hp = child.get_effective_max_hp()
			elif child.node_id == "enemy_main":
				child.node_owner = GameState.Owner.ENEMY
				child.hp = child.get_effective_max_hp()
			child.refresh_display()

	_draw_roads()
	$Battlefield/Units.add_to_group("battlefield_units")

	race_select.race_selected.connect(_on_race_selected)
	game_over.restart_requested.connect(_on_restart)
	game_over.back_to_menu.connect(_on_back_to_menu)
	EventBus.node_captured.connect(_on_node_captured)

	print("[Main] 已加载，等待玩家选择种族")


func _on_race_selected(race_id: int):
	GameState.player_race = race_id
	GameState.enemy_race = randi() % 4
	if GameState.enemy_race == GameState.player_race:
		GameState.enemy_race = (GameState.player_race + 1) % 4

	for child in $Battlefield/Nodes.get_children():
		if child is GameNode and child.node_id == "enemy_main":
			child.set_display_name(RaceData.get_race_name(GameState.enemy_race) + "主城")
		elif child is GameNode and child.node_id == "player_main":
			child.set_display_name(RaceData.get_race_name(GameState.player_race) + "主城")

	GameState.player_gold = 240
	GameState.enemy_gold = 240
	GameState.game_ended = false

	race_select.visible = false
	hud.visible = true

	_spawn_starting_units()
	GameState.game_started = true
	EventBus.gold_changed.emit(GameState.Owner.PLAYER, GameState.player_gold)
	EventBus.gold_changed.emit(GameState.Owner.ENEMY, GameState.enemy_gold)

	_show_banner("先夺取金矿和兵营，再沿道路向敌方主城推进。")
	print("[Main] 战斗开始")


func _on_restart():
	get_tree().reload_current_scene()


func _on_back_to_menu():
	get_tree().reload_current_scene()


func _draw_roads():
	var roads_layer = $Battlefield/Roads
	for child in roads_layer.get_children():
		child.queue_free()

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
		if not node_positions.has(pair[0]) or not node_positions.has(pair[1]):
			continue
		var from_pos: Vector2 = node_positions[pair[0]]
		var to_pos: Vector2 = node_positions[pair[1]]
		var normal := (to_pos - from_pos).normalized().orthogonal()
		var midpoint := (from_pos + to_pos) * 0.5

		var base = Line2D.new()
		base.points = PackedVector2Array([from_pos, to_pos])
		base.width = 36.0
		base.default_color = Color(0.1, 0.08, 0.06, 0.84)
		base.joint_mode = Line2D.LINE_JOINT_ROUND
		roads_layer.add_child(base)

		var shoulder = Line2D.new()
		shoulder.points = PackedVector2Array([from_pos, to_pos])
		shoulder.width = 28.0
		shoulder.default_color = Color(0.2, 0.16, 0.11, 0.9)
		shoulder.joint_mode = Line2D.LINE_JOINT_ROUND
		roads_layer.add_child(shoulder)

		var road = Line2D.new()
		road.points = PackedVector2Array([from_pos, to_pos])
		road.width = 16.0
		road.default_color = Color(0.46, 0.35, 0.19, 0.96)
		road.joint_mode = Line2D.LINE_JOINT_ROUND
		roads_layer.add_child(road)

		var center = Line2D.new()
		center.points = PackedVector2Array([from_pos, to_pos])
		center.width = 4.0
		center.default_color = Color(0.72, 0.61, 0.35, 0.96)
		center.joint_mode = Line2D.LINE_JOINT_ROUND
		roads_layer.add_child(center)

		for offset in [-24.0, 0.0, 24.0]:
			var stone = ColorRect.new()
			stone.size = Vector2(8, 8)
			stone.position = midpoint + normal * offset - stone.size * 0.5
			stone.color = Color(0.78, 0.68, 0.42, 0.72)
			stone.rotation = deg_to_rad(45.0)
			roads_layer.add_child(stone)

	GameState.build_road_graph(roads_data)
	GameState.build_road_segments()


func _decorate_battlefield():
	var battlefield = $Battlefield
	var background = $Battlefield/Background
	background.color = Color(0.09, 0.12, 0.08, 1.0)

	for child in battlefield.get_children():
		if child.name.begins_with("Terrain"):
			child.queue_free()

	var layers = [
		{"name":"TerrainVeilNorth","pos":Vector2(0, 0),"size":Vector2(1920, 180),"color":Color(0.24, 0.21, 0.11, 0.08)},
		{"name":"TerrainVeilSouth","pos":Vector2(0, 870),"size":Vector2(1920, 210),"color":Color(0.02, 0.04, 0.04, 0.18)},
		{"name":"TerrainPatchWest","pos":Vector2(120, 120),"size":Vector2(620, 340),"color":Color(0.14, 0.2, 0.12, 0.45)},
		{"name":"TerrainPatchCenter","pos":Vector2(500, 480),"size":Vector2(820, 420),"color":Color(0.12, 0.17, 0.1, 0.42)},
		{"name":"TerrainPatchEast","pos":Vector2(1180, 80),"size":Vector2(620, 300),"color":Color(0.16, 0.14, 0.09, 0.4)},
		{"name":"TerrainPatchSouth","pos":Vector2(980, 680),"size":Vector2(760, 260),"color":Color(0.08, 0.13, 0.09, 0.4)}
	]
	for layer_data in layers:
		var patch = ColorRect.new()
		patch.name = layer_data["name"]
		patch.position = layer_data["pos"]
		patch.size = layer_data["size"]
		patch.color = layer_data["color"]
		battlefield.add_child(patch)
		battlefield.move_child(patch, 1)

	var zone_data = [
		{"name":"TerrainZoneMine","pos":Vector2(320, 286),"size":Vector2(240, 170),"color":Color(0.34, 0.25, 0.12, 0.2)},
		{"name":"TerrainZoneCastle","pos":Vector2(790, 258),"size":Vector2(300, 220),"color":Color(0.28, 0.28, 0.3, 0.16)},
		{"name":"TerrainZoneSpring","pos":Vector2(1130, 296),"size":Vector2(250, 180),"color":Color(0.15, 0.28, 0.34, 0.18)},
		{"name":"TerrainZoneBarracks","pos":Vector2(520, 620),"size":Vector2(260, 190),"color":Color(0.34, 0.2, 0.14, 0.18)},
		{"name":"TerrainZoneMill","pos":Vector2(1270, 636),"size":Vector2(260, 190),"color":Color(0.18, 0.3, 0.16, 0.18)}
	]
	for zone in zone_data:
		var area = ColorRect.new()
		area.name = zone["name"]
		area.position = zone["pos"]
		area.size = zone["size"]
		area.color = zone["color"]
		battlefield.add_child(area)
		battlefield.move_child(area, 1)

	var plaza_spots = [
		Vector2(150, 400), Vector2(600, 400), Vector2(600, 200),
		Vector2(950, 700), Vector2(1300, 200), Vector2(1300, 600), Vector2(1750, 400)
	]
	for index in range(plaza_spots.size()):
		var plaza = ColorRect.new()
		plaza.name = "TerrainPlaza%d" % index
		plaza.size = Vector2(132, 132)
		plaza.position = plaza_spots[index] - plaza.size * 0.5
		plaza.color = Color(0.22, 0.2, 0.16, 0.22)
		battlefield.add_child(plaza)
		battlefield.move_child(plaza, 1)

	var tree_positions = [
		Vector2(90, 110), Vector2(180, 180), Vector2(250, 120), Vector2(410, 165),
		Vector2(520, 760), Vector2(640, 860), Vector2(760, 790), Vector2(890, 860),
		Vector2(1120, 96), Vector2(1240, 144), Vector2(1380, 110), Vector2(1540, 150),
		Vector2(1540, 760), Vector2(1660, 820), Vector2(1760, 720), Vector2(1840, 800)
	]
	for index in range(tree_positions.size()):
		var trunk = ColorRect.new()
		trunk.name = "TerrainTree%d" % index
		trunk.position = tree_positions[index]
		trunk.size = Vector2(18, 30)
		trunk.color = Color(0.12, 0.23, 0.12, 0.9)
		battlefield.add_child(trunk)
		battlefield.move_child(trunk, 2)

		var crown = ColorRect.new()
		crown.name = "TerrainTreeCrown%d" % index
		crown.position = tree_positions[index] + Vector2(-10, -18)
		crown.size = Vector2(38, 28)
		crown.color = Color(0.18, 0.34, 0.16, 0.82)
		battlefield.add_child(crown)
		battlefield.move_child(crown, 2)

	var rock_positions = [
		Vector2(470, 310), Vector2(820, 540), Vector2(1080, 610), Vector2(1450, 500)
	]
	for index in range(rock_positions.size()):
		var rock = ColorRect.new()
		rock.name = "TerrainRock%d" % index
		rock.position = rock_positions[index]
		rock.size = Vector2(26, 18)
		rock.color = Color(0.24, 0.26, 0.25, 0.7)
		battlefield.add_child(rock)
		battlefield.move_child(rock, 2)

	var mist_positions = [
		{"name":"TerrainMistNorth","pos":Vector2(440, 60),"size":Vector2(360, 70)},
		{"name":"TerrainMistSouth","pos":Vector2(1060, 930),"size":Vector2(420, 66)},
		{"name":"TerrainMistCenter","pos":Vector2(760, 410),"size":Vector2(460, 90)}
	]
	for mist_data in mist_positions:
		var mist = ColorRect.new()
		mist.name = mist_data["name"]
		mist.position = mist_data["pos"]
		mist.size = mist_data["size"]
		mist.color = Color(0.68, 0.73, 0.66, 0.08)
		battlefield.add_child(mist)
		battlefield.move_child(mist, 2)


func _spawn_starting_units():
	var unit_scene = load("res://scenes/unit/unit_base.tscn")
	var units_layer = $Battlefield/Units

	for i in range(2):
		var unit = unit_scene.instantiate()
		unit.setup(RaceData.UnitType.MELEE, GameState.Owner.PLAYER, GameState.player_race)
		unit.global_position = GameState.get_spawn_road_point("player_main", Vector2(200 + i * 40, 460), 58.0 + i * 20.0)
		units_layer.add_child(unit)
		unit.snap_to_road()
		GameState.player_units.append(unit)

	var player_archer = unit_scene.instantiate()
	player_archer.setup(RaceData.UnitType.RANGED, GameState.Owner.PLAYER, GameState.player_race)
	player_archer.global_position = GameState.get_spawn_road_point("player_main", Vector2(310, 445), 102.0)
	units_layer.add_child(player_archer)
	player_archer.snap_to_road()
	GameState.player_units.append(player_archer)

	for i in range(2):
		var unit = unit_scene.instantiate()
		unit.setup(RaceData.UnitType.MELEE, GameState.Owner.ENEMY, GameState.enemy_race)
		unit.global_position = GameState.get_spawn_road_point("enemy_main", Vector2(1650 + i * 40, 400), 58.0 + i * 20.0)
		units_layer.add_child(unit)
		unit.snap_to_road()
		GameState.enemy_units.append(unit)

	var enemy_archer = unit_scene.instantiate()
	enemy_archer.setup(RaceData.UnitType.RANGED, GameState.Owner.ENEMY, GameState.enemy_race)
	enemy_archer.global_position = GameState.get_spawn_road_point("enemy_main", Vector2(1590, 380), 102.0)
	units_layer.add_child(enemy_archer)
	enemy_archer.snap_to_road()
	GameState.enemy_units.append(enemy_archer)


func _on_node_captured(node_id: String, new_owner: int, old_owner: int):
	if new_owner == old_owner:
		return
	var node = GameState.nodes.get(node_id)
	if not node:
		return

	var owner_name = "中立"
	match new_owner:
		GameState.Owner.PLAYER:
			owner_name = "我方"
		GameState.Owner.ENEMY:
			owner_name = "敌方"
	_show_banner("%s已占领 %s" % [owner_name, node.node_name], 1.4)


func _show_banner(text_value: String, duration: float = 2.0):
	var banner = Label.new()
	banner.text = text_value
	banner.position = Vector2(0, 38)
	banner.size = Vector2(1920, 40)
	banner.add_theme_font_size_override("font_size", 24)
	banner.add_theme_color_override("font_color", Color(1, 0.9, 0.38))
	banner.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(banner)

	var backer = ColorRect.new()
	backer.position = Vector2(520, 28)
	backer.size = Vector2(880, 48)
	backer.color = Color(0.05, 0.05, 0.06, 0.46)
	add_child(backer)
	move_child(backer, get_child_count() - 2)

	var tw = create_tween()
	tw.tween_property(banner, "modulate:a", 0.0, duration)
	tw.parallel().tween_property(backer, "modulate:a", 0.0, duration)
	tw.tween_callback(banner.queue_free)
	tw.tween_callback(backer.queue_free)
