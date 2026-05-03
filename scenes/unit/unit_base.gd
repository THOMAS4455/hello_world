extends Area2D
## Base unit for all troop types. RTS-controlled movement, auto-attack, node capture.
class_name UnitBase

enum Order { IDLE, MOVE, ATTACK_UNIT, ATTACK_NODE }

var unit_type: int
var unit_owner: int
var race: int
var unit_name: String

var max_hp: int = 100
var hp: int = 100
var attack_power: int = 10
var defense: int = 3
var move_speed: float = 150.0
var attack_range: float = 40.0
var attack_speed: float = 1.0
var unit_cost: int = 50

var is_dead: bool = false

var order: Order = Order.IDLE
var move_target: Vector2
var attack_target = null
var attack_cooldown: float = 0.0
var _waypoints: Array = []   # Vector2 waypoints from road pathfinding

var _body_rect: ColorRect
var _hp_bar: ColorRect
var _hp_bar_bg: ColorRect
var _selection_ring: Control


func setup(p_type, p_owner, p_race):
	unit_type = p_type
	unit_owner = p_owner
	race = p_race
	var data = RaceData.get_unit_data(race, unit_type)
	unit_name = data.unit_name
	max_hp = data.hp
	hp = data.hp
	attack_power = data.attack
	defense = data.defense
	move_speed = data.speed
	attack_range = data.attack_range
	attack_speed = data.attack_speed
	unit_cost = data.cost
	_create_visuals()


func _create_visuals():
	_body_rect = ColorRect.new()
	match unit_type:
		RaceData.UnitType.MELEE:
			_body_rect.size = Vector2(24, 24)
		RaceData.UnitType.RANGED:
			_body_rect.size = Vector2(20, 20)
		RaceData.UnitType.CAVALRY:
			_body_rect.size = Vector2(28, 20)
	_body_rect.position = -_body_rect.size / 2.0
	_body_rect.color = RaceData.get_race_color(race)
	add_child(_body_rect)

	var type_indicator = ColorRect.new()
	type_indicator.size = Vector2(6, 6)
	type_indicator.position = Vector2(-3, -_body_rect.size.y / 2 - 10)
	match unit_type:
		RaceData.UnitType.MELEE:   type_indicator.color = Color.WHITE
		RaceData.UnitType.RANGED:  type_indicator.color = Color(0.2, 1, 0.2)
		RaceData.UnitType.CAVALRY: type_indicator.color = Color(1, 1, 0.2)
	add_child(type_indicator)

	_hp_bar_bg = ColorRect.new()
	_hp_bar_bg.size = Vector2(28, 4)
	_hp_bar_bg.position = Vector2(-14, -_body_rect.size.y / 2 - 6)
	_hp_bar_bg.color = Color(0.2, 0.2, 0.2)
	add_child(_hp_bar_bg)

	_hp_bar = ColorRect.new()
	_hp_bar.size = Vector2(28, 4)
	_hp_bar.position = Vector2(-14, -_body_rect.size.y / 2 - 6)
	_hp_bar.color = Color(0.2, 0.8, 0.2)
	add_child(_hp_bar)

	var collision = CollisionShape2D.new()
	var circle = CircleShape2D.new()
	circle.radius = 30.0
	collision.shape = circle
	add_child(collision)


func set_selected(sel: bool):
	if is_dead: return
	if sel:
		if not _selection_ring:
			_selection_ring = _make_ring()
			add_child(_selection_ring)
	else:
		if _selection_ring:
			_selection_ring.queue_free()
			_selection_ring = null


func _make_ring() -> Control:
	var ring = Control.new()
	var rc = ColorRect.new()
	rc.size = Vector2(32, 32)
	rc.position = -rc.size / 2
	rc.color = Color(0.3, 0.9, 0.3, 0.35)
	ring.add_child(rc)
	var tw = create_tween()
	tw.set_loops()
	tw.tween_property(rc, "modulate:a", 0.15, 0.5)
	tw.tween_property(rc, "modulate:a", 0.4, 0.5)
	return ring


func command_move(pos: Vector2):
	order = Order.MOVE
	move_target = pos
	attack_target = null
	_waypoints = GameState.find_road_path(global_position, pos)


func command_attack(target):
	order = Order.ATTACK_UNIT
	attack_target = target


func command_attack_node(node: GameNode):
	order = Order.ATTACK_NODE
	attack_target = node


func _physics_process(delta):
	if is_dead: return
	if attack_cooldown > 0:
		attack_cooldown -= delta

	match order:
		Order.IDLE:         _process_idle(delta)
		Order.MOVE:         _process_move(delta)
		Order.ATTACK_UNIT:  _process_attack_unit(delta)
		Order.ATTACK_NODE:  _process_attack_node(delta)

	_update_hp_bar()


func _process_idle(_delta):
	var enemy = _find_nearest_enemy()
	if enemy:
		order = Order.ATTACK_UNIT
		attack_target = enemy


func _process_move(delta):
	# Auto-engage nearby enemies while moving
	var enemy = _find_nearest_enemy_in_range(attack_range * 1.5)
	if enemy:
		order = Order.ATTACK_UNIT
		attack_target = enemy
		_waypoints.clear()
		return

	# Follow road waypoints
	if _waypoints.is_empty():
		order = Order.IDLE
		return

	var wp = _waypoints[0]
	var dir = global_position.direction_to(wp)
	var dist = global_position.distance_to(wp)

	if dist < 4.0:
		_waypoints.pop_front()
		if _waypoints.is_empty():
			order = Order.IDLE
			return
		wp = _waypoints[0]
		dir = global_position.direction_to(wp)

	var speed = move_speed
	if GameState.is_near_road(global_position):
		speed *= 1.5

	global_position += dir * speed * delta


func _process_attack_unit(delta):
	if (not is_instance_valid(attack_target)) or attack_target.is_dead:
		order = Order.IDLE
		return
	var dist = global_position.distance_to(attack_target.global_position)
	if dist > attack_range:
		global_position += global_position.direction_to(attack_target.global_position) * move_speed * delta
	else:
		_try_attack(attack_target)


func _process_attack_node(delta):
	if not is_instance_valid(attack_target):
		order = Order.IDLE
		return
	if attack_target.node_owner == unit_owner:
		order = Order.IDLE
		return
	var dist = global_position.distance_to(attack_target.global_position)
	if dist > attack_range:
		global_position += global_position.direction_to(attack_target.global_position) * move_speed * delta
	else:
		_try_attack_node()


func _try_attack(target):
	if attack_cooldown > 0: return
	attack_cooldown = attack_speed
	if not is_instance_valid(target) or target.is_dead: return
	var dmg = max(1, attack_power - target.defense)
	target.take_damage(dmg)


func _try_attack_node():
	if attack_cooldown > 0: return
	attack_cooldown = attack_speed
	if not is_instance_valid(attack_target): return
	attack_target.take_damage(attack_power, unit_owner)


func take_damage(amount: int):
	if is_dead: return
	var dmg = max(1, amount - defense)
	hp -= dmg
	if hp <= 0:
		die()


func die():
	is_dead = true
	set_selected(false)
	EventBus.unit_died.emit(self)

	if unit_owner == GameState.Owner.PLAYER:
		GameState.player_units.erase(self)
	else:
		GameState.enemy_units.erase(self)

	var rts = get_tree().get_first_node_in_group("rts_controller")
	if rts and rts.has_method("deselect_dead"):
		rts.deselect_dead()

	queue_free()


func is_player_owned() -> bool:
	return unit_owner == GameState.Owner.PLAYER


func _find_nearest_enemy() -> Node:
	var enemies = GameState.enemy_units if unit_owner == GameState.Owner.PLAYER else GameState.player_units
	var closest = null
	var min_dist = attack_range * 1.2
	for unit in enemies:
		if not is_instance_valid(unit) or unit.is_dead: continue
		var d = global_position.distance_to(unit.global_position)
		if d < min_dist:
			min_dist = d
			closest = unit
	return closest


func _find_nearest_enemy_in_range(range_px: float) -> Node:
	var enemies = GameState.enemy_units if unit_owner == GameState.Owner.PLAYER else GameState.player_units
	var closest = null
	var min_dist = range_px
	for unit in enemies:
		if not is_instance_valid(unit) or unit.is_dead: continue
		var d = global_position.distance_to(unit.global_position)
		if d < min_dist:
			min_dist = d
			closest = unit
	return closest


func _update_hp_bar():
	if not _hp_bar: return
	var ratio = float(hp) / float(max_hp)
	_hp_bar.size.x = 28.0 * ratio
	if ratio > 0.6:
		_hp_bar.color = Color(0.2, 0.8, 0.2)
	elif ratio > 0.3:
		_hp_bar.color = Color(0.8, 0.8, 0.2)
	else:
		_hp_bar.color = Color(0.8, 0.2, 0.2)
