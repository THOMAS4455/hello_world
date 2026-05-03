extends Node
## Simple enemy AI. Periodically buys units and sends them to attack.

var think_interval: float = 3.0
var think_timer: float = 0.0

var unit_scene = preload("res://scenes/unit/unit_base.tscn")
var _last_spawn_node: GameNode = null


func _ready():
	add_to_group("enemy_ai")


func _process(delta):
	if not GameState.game_started or GameState.game_ended:
		return

	think_timer += delta
	if think_timer >= think_interval:
		think_timer = 0.0
		think()


func think():
	# Step 1: Buy a unit if we can afford it
	var unit_type = _pick_unit_type()
	var data = RaceData.base_units[unit_type]
	if GameState.can_afford(GameState.Owner.ENEMY, data.cost):
		_spawn_unit(unit_type, data.cost)

	# Step 2: Command idle units to attack neutral/enemy nodes
	_command_idle_units()


func _pick_unit_type() -> int:
	# Simple heuristic: prefer melee, mix in others
	var r = randf()
	if r < 0.5:
		return RaceData.UnitType.MELEE
	elif r < 0.8:
		return RaceData.UnitType.RANGED
	else:
		return RaceData.UnitType.CAVALRY


func _spawn_unit(unit_type: int, cost: int):
	var castle = _find_enemy_spawn_castle()
	if not castle:
		return

	var units_layer = get_tree().get_first_node_in_group("battlefield_units")
	if not units_layer:
		units_layer = get_parent().get_node_or_null("Battlefield/Units") if get_parent() else null
	if not units_layer:
		return
	GameState.spend_gold(GameState.Owner.ENEMY, cost)
	var unit = unit_scene.instantiate()
	unit.setup(unit_type, GameState.Owner.ENEMY, GameState.enemy_race)
	unit.global_position = castle.global_position + Vector2(randf_range(-30, 30), randf_range(-80, -40))
	units_layer.add_child(unit)
	GameState.enemy_units.append(unit)


func _find_enemy_spawn_castle() -> GameNode:
	# Find nearest enemy-owned castle
	var best: GameNode = null
	var best_dist: float = INF
	var enemy_units = _get_enemy_unit_center()
	for node in GameState.nodes.values():
		if node.node_owner == GameState.Owner.ENEMY and node.can_spawn_units():
			var dist = node.global_position.distance_to(enemy_units)
			if dist < best_dist:
				best_dist = dist
				best = node
	return best


func _command_idle_units():
	var target_node = _pick_target_node()
	if not target_node:
		return

	for unit in GameState.enemy_units:
		if not is_instance_valid(unit) or unit.is_dead:
			continue
		if unit.order == UnitBase.Order.IDLE:
			# Send toward target node
			unit.command_move(target_node.global_position)
			# Or attack it directly
			if unit.global_position.distance_to(target_node.global_position) < 300:
				unit.command_attack_node(target_node)


func _pick_target_node() -> GameNode:
	# Priority: neutral nodes > player nodes
	var neutrals: Array[GameNode] = []
	var player_nodes: Array[GameNode] = []
	for node in GameState.nodes.values():
		if node.is_dead: continue
		if node.node_owner == GameState.Owner.NEUTRAL:
			neutrals.append(node)
		elif node.node_owner == GameState.Owner.PLAYER:
			player_nodes.append(node)

	# Prioritize closest neutral node
	if neutrals.size() > 0:
		neutrals.sort_custom(func(a, b):
			var center = _get_enemy_unit_center()
			return a.global_position.distance_to(center) < b.global_position.distance_to(center)
		)
		return neutrals[0]

	# If no neutrals, attack player's weakest node
	if player_nodes.size() > 0:
		player_nodes.sort_custom(func(a, b): return a.hp < b.hp)
		return player_nodes[0]

	return null


func _get_enemy_unit_center() -> Vector2:
	var sum = Vector2.ZERO
	var count = 0
	for unit in GameState.enemy_units:
		if is_instance_valid(unit) and not unit.is_dead:
			sum += unit.global_position
			count += 1
	if count > 0:
		return sum / count
	# If no units, return enemy main castle position
	for node in GameState.nodes.values():
		if node.node_owner == GameState.Owner.ENEMY and node.node_type == GameNode.NodeType.MAIN_CASTLE:
			return node.global_position
	return Vector2(1750, 400)
