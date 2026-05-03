extends Node2D
## RTS-style unit selection and command input.

var selected_units: Array = []
var is_dragging: bool = false
var drag_start: Vector2
var drag_rect: ColorRect
var command_layer: Node2D


func _ready():
	add_to_group("rts_controller")
	_create_drag_rect()
	command_layer = Node2D.new()
	command_layer.name = "CommandLayer"
	add_child(command_layer)


func _create_drag_rect():
	drag_rect = ColorRect.new()
	drag_rect.visible = false
	drag_rect.color = Color(0.3, 0.8, 1.0, 0.16)
	drag_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	drag_rect.z_index = 100
	add_child(drag_rect)


func _input(event):
	if not GameState.game_started or GameState.game_ended:
		return
	if _is_skill_mode():
		return

	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:
			if event.pressed:
				_start_drag(event.position)
			else:
				_end_drag(event.position)
		elif event.button_index == MOUSE_BUTTON_RIGHT and event.pressed and selected_units.size() > 0:
			_issue_command(get_global_mouse_position())

	if event is InputEventMouseMotion and is_dragging:
		_update_drag(event.position)


func _start_drag(pos: Vector2):
	is_dragging = true
	drag_start = pos
	drag_rect.visible = true
	drag_rect.position = drag_start
	drag_rect.size = Vector2.ZERO


func _update_drag(pos: Vector2):
	var rect = Rect2(drag_start, pos - drag_start).abs()
	drag_rect.position = rect.position
	drag_rect.size = rect.size


func _end_drag(pos: Vector2):
	is_dragging = false
	drag_rect.visible = false
	var drag_end = pos

	if drag_start.distance_to(drag_end) < 8.0:
		_select_single(get_global_mouse_position())
	else:
		_select_rect(Rect2(drag_start, drag_end - drag_start).abs())


func _select_single(global_pos: Vector2):
	_clear_selection()
	var unit = _get_unit_at(global_pos)
	if unit and unit.is_player_owned():
		_add_to_selection(unit)


func _select_rect(screen_rect: Rect2):
	_clear_selection()
	var canvas_transform = get_viewport().get_canvas_transform()
	for unit in GameState.player_units:
		if not is_instance_valid(unit) or unit.is_dead:
			continue
		var screen_point = canvas_transform * unit.global_position
		if screen_rect.has_point(screen_point):
			_add_to_selection(unit)


func _add_to_selection(unit):
	if unit not in selected_units:
		selected_units.append(unit)
		unit.set_selected(true)


func _clear_selection():
	for unit in selected_units:
		if is_instance_valid(unit):
			unit.set_selected(false)
	selected_units.clear()


func _issue_command(target_pos: Vector2):
	var clicked_unit = _get_unit_at(target_pos)
	var clicked_node = _get_node_at(target_pos)

	if selected_units.is_empty():
		return

	var my_owner = selected_units[0].unit_owner
	if clicked_unit and clicked_unit.unit_owner != my_owner:
		_show_command_marker(clicked_unit.global_position, Color(0.95, 0.28, 0.24, 0.9), 20.0)
		for unit in selected_units:
			unit.command_attack(clicked_unit)
	elif clicked_node and GameState.is_capturable(clicked_node.node_id, my_owner):
		_show_command_marker(clicked_node.global_position, Color(1.0, 0.76, 0.28, 0.9), 24.0)
		for unit in selected_units:
			unit.command_attack_node(clicked_node)
	else:
		_show_command_marker(GameState.get_nearest_road_point(target_pos), Color(0.22, 0.84, 1.0, 0.9), 18.0)
		var formation = _make_formation_offsets(selected_units.size())
		for i in range(selected_units.size()):
			var snapped_target = GameState.get_nearest_road_point(target_pos + formation[i])
			selected_units[i].command_move(snapped_target)


func _make_formation_offsets(count: int) -> Array:
	var offsets: Array = []
	var columns = ceili(sqrt(float(count)))
	var spacing = 24.0
	for i in range(count):
		var x = (i % columns) - float(columns - 1) * 0.5
		var y = floori(float(i) / float(columns))
		offsets.append(Vector2(x * spacing, y * spacing))
	return offsets


func _get_unit_at(global_pos: Vector2) -> Node:
	var all_units = GameState.player_units + GameState.enemy_units
	for unit in all_units:
		if not is_instance_valid(unit) or unit.is_dead:
			continue
		if unit.global_position.distance_to(global_pos) < 26.0:
			return unit
	return null


func _get_node_at(global_pos: Vector2) -> Node:
	for node in GameState.nodes.values():
		if is_instance_valid(node) and node.global_position.distance_to(global_pos) < 52.0:
			return node
	return null


func _is_skill_mode() -> bool:
	var commander = get_tree().get_first_node_in_group("commander")
	if commander and commander.has_method("is_aiming"):
		return commander.is_aiming()
	return false


func deselect_dead():
	var to_remove := []
	for unit in selected_units:
		if not is_instance_valid(unit) or unit.is_dead:
			to_remove.append(unit)
	for unit in to_remove:
		selected_units.erase(unit)


func _show_command_marker(world_pos: Vector2, color: Color, radius: float):
	if not command_layer:
		return
	var marker = Node2D.new()
	marker.global_position = world_pos
	command_layer.add_child(marker)

	var outer = ColorRect.new()
	outer.size = Vector2(radius * 2.0, radius * 2.0)
	outer.position = -outer.size / 2.0
	outer.color = color
	outer.modulate.a = 0.26
	outer.rotation = deg_to_rad(45.0)
	marker.add_child(outer)

	var inner = ColorRect.new()
	inner.size = Vector2(radius, radius)
	inner.position = -inner.size / 2.0
	inner.color = color.lightened(0.15)
	inner.modulate.a = 0.8
	inner.rotation = deg_to_rad(45.0)
	marker.add_child(inner)

	var tw = marker.create_tween()
	tw.tween_property(marker, "scale", Vector2.ONE * 1.6, 0.18).from(Vector2.ONE * 0.4)
	tw.parallel().tween_property(marker, "modulate:a", 0.0, 0.22)
	tw.tween_callback(marker.queue_free)
