extends Node
## Enemy AI focused on claiming economic nodes and then pushing the player.

var think_interval: float = 2.2
var think_timer: float = 0.0
var unit_scene = preload("res://scenes/unit/unit_base.tscn")


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
	_buy_reinforcements()
	_assign_orders()


func _buy_reinforcements():
	var unit_count = GameState.get_unit_count(GameState.Owner.ENEMY)
	var player_count = GameState.get_unit_count(GameState.Owner.PLAYER)
	var preferred_type = _pick_unit_type(unit_count, player_count)
	var cost = GameState.get_unit_cost(GameState.Owner.ENEMY, preferred_type)

	if GameState.can_afford(GameState.Owner.ENEMY, cost):
		_spawn_unit(preferred_type, cost)

	if GameState.enemy_gold >= GameState.get_unit_cost(GameState.Owner.ENEMY, RaceData.UnitType.MELEE) * 2 and unit_count < player_count:
		var fallback_cost = GameState.get_unit_cost(GameState.Owner.ENEMY, RaceData.UnitType.MELEE)
		if GameState.can_afford(GameState.Owner.ENEMY, fallback_cost):
			_spawn_unit(RaceData.UnitType.MELEE, fallback_cost)


func _pick_unit_type(unit_count: int, player_count: int) -> int:
	if unit_count < 3:
		return RaceData.UnitType.MELEE
	if player_count > unit_count + 2:
		return RaceData.UnitType.RANGED
	if GameState.has_bonus(GameState.Owner.ENEMY, "unit_cost_discount") and randf() < 0.45:
		return RaceData.UnitType.CAVALRY
	var roll = randf()
	if roll < 0.45:
		return RaceData.UnitType.MELEE
	if roll < 0.78:
		return RaceData.UnitType.RANGED
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
	unit.global_position = GameState.get_spawn_road_point(castle.node_id, castle.global_position, randf_range(54.0, 92.0))
	units_layer.add_child(unit)
	unit.snap_to_road()
	GameState.enemy_units.append(unit)


func _find_enemy_spawn_castle() -> GameNode:
	var best: GameNode = null
	var best_score := -INF
	for node in GameState.get_owned_nodes(GameState.Owner.ENEMY):
		if not node.can_spawn_units():
			continue
		var score = node.get_priority_score(GameState.Owner.PLAYER)
		if score > best_score:
			best_score = score
			best = node
	return best


func _assign_orders():
	var focus_target = GameState.get_frontline_target(GameState.Owner.ENEMY)
	if not focus_target:
		return

	var assault_ready = GameState.get_unit_count(GameState.Owner.ENEMY) >= max(5, GameState.get_unit_count(GameState.Owner.PLAYER))
	for unit in GameState.enemy_units:
		if not is_instance_valid(unit) or unit.is_dead:
			continue
		if unit.order != UnitBase.Order.IDLE and randf() < 0.65:
			continue
		if focus_target.node_owner != GameState.Owner.ENEMY and (assault_ready or unit.unit_type != RaceData.UnitType.RANGED):
			unit.command_attack_node(focus_target)
		else:
			var staging = _get_staging_position(focus_target)
			unit.command_move(staging)


func _get_staging_position(target: GameNode) -> Vector2:
	var origin = GameState.get_stronghold(GameState.Owner.ENEMY)
	if not origin:
		return target.global_position
	return target.global_position.lerp(origin.global_position, 0.2)
