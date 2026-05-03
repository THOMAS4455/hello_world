extends Area2D
## Base unit for all troop types. RTS-controlled movement, auto-attack, node capture.
class_name UnitBase

enum Order { IDLE, MOVE, ATTACK_UNIT, ATTACK_NODE }

var unit_type: int
var unit_owner: int
var race: int
var unit_name: String
var description: String

var max_hp: int = 100
var hp: int = 100
var attack_power: int = 10
var defense: int = 3
var move_speed: float = 150.0
var attack_range: float = 40.0
var attack_speed: float = 1.0
var unit_cost: int = 50
var siege_damage_mult: float = 1.0

var is_dead: bool = false

var order: Order = Order.IDLE
var move_target: Vector2
var attack_target = null
var attack_cooldown: float = 0.0
var _waypoints: Array = []
var _velocity := Vector2.ZERO
var _repath_timer: float = 0.0

var _body_rect: ColorRect
var _hp_bar: ColorRect
var _hp_bar_bg: ColorRect
var _selection_ring: Control
var _type_indicator: ColorRect
var _shadow: ColorRect
var _banner: ColorRect
var _trim: ColorRect


func setup(p_type, p_owner, p_race):
	unit_type = p_type
	unit_owner = p_owner
	race = p_race

	var data: RaceData.UnitData = RaceData.get_unit_data(race, unit_type)
	unit_name = data.unit_name
	description = data.description
	max_hp = data.hp
	hp = data.hp
	attack_power = data.attack
	defense = data.defense
	move_speed = data.speed
	attack_range = data.attack_range
	attack_speed = data.attack_speed
	unit_cost = GameState.get_unit_cost(unit_owner, unit_type)
	siege_damage_mult = RaceData.get_siege_multiplier(unit_type)
	_create_visuals()


func _create_visuals():
	_shadow = ColorRect.new()
	_shadow.size = Vector2(26, 10)
	_shadow.position = Vector2(-13, 10)
	_shadow.color = Color(0, 0, 0, 0.22)
	add_child(_shadow)

	_body_rect = ColorRect.new()
	match unit_type:
		RaceData.UnitType.MELEE:
			_body_rect.size = Vector2(24, 24)
		RaceData.UnitType.RANGED:
			_body_rect.size = Vector2(18, 24)
		RaceData.UnitType.CAVALRY:
			_body_rect.size = Vector2(28, 18)
	_body_rect.position = -_body_rect.size / 2.0
	_body_rect.color = RaceData.get_race_color(race)
	add_child(_body_rect)

	_trim = ColorRect.new()
	_trim.size = _body_rect.size - Vector2(6, 6)
	_trim.position = -_trim.size / 2.0
	_trim.color = RaceData.get_race_color(race).lightened(0.2)
	add_child(_trim)

	_banner = ColorRect.new()
	_banner.size = Vector2(6, 18)
	_banner.position = Vector2(_body_rect.size.x * 0.5 - 1, -_body_rect.size.y * 0.5 - 8)
	_banner.color = RaceData.get_race_color(race).lightened(0.25)
	add_child(_banner)

	_type_indicator = ColorRect.new()
	_type_indicator.size = Vector2(8, 8)
	_type_indicator.position = Vector2(-4, -_body_rect.size.y / 2 - 12)
	match unit_type:
		RaceData.UnitType.MELEE:
			_type_indicator.color = Color.WHITE
		RaceData.UnitType.RANGED:
			_type_indicator.color = Color(0.2, 1, 0.2)
		RaceData.UnitType.CAVALRY:
			_type_indicator.color = Color(1, 0.9, 0.2)
	add_child(_type_indicator)

	_hp_bar_bg = ColorRect.new()
	_hp_bar_bg.size = Vector2(30, 4)
	_hp_bar_bg.position = Vector2(-15, -_body_rect.size.y / 2 - 6)
	_hp_bar_bg.color = Color(0.14, 0.14, 0.14)
	add_child(_hp_bar_bg)

	_hp_bar = ColorRect.new()
	_hp_bar.size = Vector2(30, 4)
	_hp_bar.position = Vector2(-15, -_body_rect.size.y / 2 - 6)
	_hp_bar.color = Color(0.2, 0.8, 0.2)
	add_child(_hp_bar)

	var collision = CollisionShape2D.new()
	var circle = CircleShape2D.new()
	circle.radius = 22.0
	collision.shape = circle
	add_child(collision)


func set_selected(sel: bool):
	if is_dead:
		return
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
	rc.size = Vector2(34, 34)
	rc.position = -rc.size / 2
	rc.color = Color(0.3, 0.9, 0.3, 0.35)
	rc.rotation = deg_to_rad(45.0)
	ring.add_child(rc)
	var tw = create_tween()
	tw.set_loops()
	tw.tween_property(rc, "modulate:a", 0.15, 0.45)
	tw.tween_property(rc, "modulate:a", 0.42, 0.45)
	return ring


func command_move(pos: Vector2):
	order = Order.MOVE
	move_target = GameState.get_nearest_road_point(pos)
	attack_target = null
	_waypoints = GameState.find_road_path(global_position, move_target)


func command_attack(target):
	order = Order.ATTACK_UNIT
	attack_target = target
	_repath_timer = 0.0
	_refresh_attack_route()


func command_attack_node(node: GameNode):
	order = Order.ATTACK_NODE
	attack_target = node
	_repath_timer = 0.0
	_waypoints = GameState.find_road_path(global_position, GameState.get_nearest_road_point(node.global_position))


func snap_to_road():
	global_position = GameState.get_nearest_road_point(global_position)


func _physics_process(delta):
	if is_dead:
		return

	if attack_cooldown > 0.0:
		attack_cooldown = max(0.0, attack_cooldown - delta)
	_repath_timer = max(0.0, _repath_timer - delta)

	match order:
		Order.IDLE:
			_process_idle()
		Order.MOVE:
			_process_move(delta)
		Order.ATTACK_UNIT:
			_process_attack_unit(delta)
		Order.ATTACK_NODE:
			_process_attack_node(delta)

	_update_hp_bar()


func _process_idle():
	var enemy = _find_nearest_enemy_in_range(attack_range * 1.7)
	if enemy:
		order = Order.ATTACK_UNIT
		attack_target = enemy


func _process_move(delta):
	var enemy = _find_nearest_enemy_in_range(attack_range * 1.5)
	if enemy:
		order = Order.ATTACK_UNIT
		attack_target = enemy
		_waypoints.clear()
		return

	if _waypoints.is_empty():
		order = Order.IDLE
		return

	var waypoint: Vector2 = _waypoints[0]
	var distance = global_position.distance_to(waypoint)
	if distance < 6.0:
		_waypoints.pop_front()
		if _waypoints.is_empty():
			order = Order.IDLE
			return
		waypoint = _waypoints[0]

	_move_towards(waypoint, delta)


func _process_attack_unit(delta):
	if not is_instance_valid(attack_target) or attack_target.is_dead:
		order = Order.IDLE
		return

	var distance = global_position.distance_to(attack_target.global_position)
	if distance > attack_range:
		if _repath_timer <= 0.0:
			_refresh_attack_route()
		_follow_waypoints(delta)
	else:
		_waypoints.clear()
		_try_attack(attack_target)


func _process_attack_node(delta):
	if not is_instance_valid(attack_target):
		order = Order.IDLE
		return
	if attack_target.node_owner == unit_owner:
		order = Order.IDLE
		return

	var distance = global_position.distance_to(attack_target.global_position)
	if distance > attack_range:
		if _waypoints.is_empty():
			_waypoints = GameState.find_road_path(global_position, attack_target.global_position)
		_follow_waypoints(delta)
	else:
		_waypoints.clear()
		_try_attack_node()


func _move_towards(target_pos: Vector2, delta: float):
	var direction = global_position.direction_to(target_pos)
	var speed = move_speed
	if GameState.is_near_road(global_position):
		speed *= 1.18
	_velocity = direction * speed
	var moved_position = global_position + _velocity * delta
	global_position = GameState.get_nearest_road_point(moved_position)


func _follow_waypoints(delta: float):
	if _waypoints.is_empty():
		return

	var waypoint: Vector2 = _waypoints[0]
	if global_position.distance_to(waypoint) < 5.0:
		_waypoints.pop_front()
		if _waypoints.is_empty():
			return
		waypoint = _waypoints[0]
	_move_towards(waypoint, delta)


func _refresh_attack_route():
	if not is_instance_valid(attack_target):
		return
	move_target = GameState.get_nearest_road_point(attack_target.global_position)
	_waypoints = GameState.find_road_path(global_position, move_target)
	_repath_timer = 0.45


func _try_attack(target):
	if attack_cooldown > 0.0:
		return
	if not is_instance_valid(target) or target.is_dead:
		return

	attack_cooldown = attack_speed
	var damage = max(1, attack_power - target.defense)
	target.take_damage(damage)
	_play_attack_feedback(target.global_position)


func _try_attack_node():
	if attack_cooldown > 0.0:
		return
	if not is_instance_valid(attack_target):
		return

	attack_cooldown = attack_speed
	var damage = int(round(attack_power * siege_damage_mult))
	attack_target.take_damage(max(1, damage), unit_owner)
	_play_attack_feedback(attack_target.global_position)


func take_damage(amount: int):
	if is_dead:
		return
	var damage = max(1, amount - defense)
	hp -= damage
	_flash_hit()
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

	var tw = create_tween()
	tw.tween_property(self, "modulate:a", 0.0, 0.18)
	tw.tween_callback(queue_free)

	var rts = get_tree().get_first_node_in_group("rts_controller")
	if rts and rts.has_method("deselect_dead"):
		rts.deselect_dead()


func is_player_owned() -> bool:
	return unit_owner == GameState.Owner.PLAYER


func _find_nearest_enemy_in_range(range_px: float) -> Node:
	var enemies = GameState.enemy_units if unit_owner == GameState.Owner.PLAYER else GameState.player_units
	var closest = null
	var min_distance = range_px
	for unit in enemies:
		if not is_instance_valid(unit) or unit.is_dead:
			continue
		var distance = global_position.distance_to(unit.global_position)
		if distance < min_distance:
			min_distance = distance
			closest = unit
	return closest


func _update_hp_bar():
	if not _hp_bar:
		return
	var ratio = clamp(float(hp) / max(1.0, float(max_hp)), 0.0, 1.0)
	_hp_bar.size.x = 30.0 * ratio
	if ratio > 0.6:
		_hp_bar.color = Color(0.2, 0.8, 0.2)
	elif ratio > 0.3:
		_hp_bar.color = Color(0.85, 0.8, 0.2)
	else:
		_hp_bar.color = Color(0.9, 0.2, 0.2)


func _flash_hit():
	if not _body_rect:
		return
	var tw = create_tween()
	tw.tween_property(_body_rect, "modulate", Color(1, 1, 1, 0.45), 0.05)
	tw.tween_property(_body_rect, "modulate", Color.WHITE, 0.12)


func _play_attack_feedback(hit_pos: Vector2):
	scale = Vector2.ONE * 1.08
	var tw = create_tween()
	tw.tween_property(self, "scale", Vector2.ONE, 0.08)

	var flash = ColorRect.new()
	flash.size = Vector2(8, 8)
	flash.position = global_position.lerp(hit_pos, 0.45) - flash.size * 0.5
	flash.color = Color(1.0, 0.82, 0.28, 0.95)
	flash.rotation = randf_range(0.0, PI)
	get_tree().current_scene.add_child(flash)

	var flash_tw = flash.create_tween()
	flash_tw.tween_property(flash, "scale", Vector2.ONE * 2.3, 0.1)
	flash_tw.parallel().tween_property(flash, "modulate:a", 0.0, 0.12)
	flash_tw.tween_callback(flash.queue_free)
