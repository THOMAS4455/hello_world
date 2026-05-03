extends Node2D
## RTS-style unit selection and command input.
## Attach to main scene. Captures mouse events and translates them to unit orders.

var selected_units: Array = []
var is_dragging: bool = false
var drag_start: Vector2
var drag_rect: ColorRect                     # visual selection box
func _ready():
	add_to_group("rts_controller")


func _create_drag_rect():
	# Simple placeholder — visual drag rect disabled for now
	drag_rect = ColorRect.new()
	drag_rect.visible = false


func _input(event):
	# Don't process input before game starts or after it ends
	if not GameState.game_started or GameState.game_ended:
		return
	# Skill mode: if commander is active, skip RTS input
	if _is_skill_mode():
		return

	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:
			if event.pressed:
				_start_drag(event.position)
			else:
				_end_drag(event.position)

		elif event.button_index == MOUSE_BUTTON_RIGHT and event.pressed:
			if selected_units.size() > 0:
				_issue_command(get_global_mouse_position())

	if event is InputEventMouseMotion and is_dragging:
		_update_drag(event.position)


# ---- Selection ----

func _start_drag(pos: Vector2):
	is_dragging = true
	drag_start = pos


func _update_drag(_pos: Vector2):
	pass  # visual drag rect disabled for now


func _end_drag(pos: Vector2):
	is_dragging = false
	var drag_end = pos

	if drag_start.distance_to(drag_end) < 8:
		# Click select
		_select_single(get_global_mouse_position())
	else:
		# Box select
		_select_rect(Rect2(drag_start, drag_end - drag_start).abs())


func _select_single(global_pos: Vector2):
	_clear_selection()

	var unit = _get_unit_at(global_pos)
	if unit and unit.is_player_owned():
		_add_to_selection(unit)


func _select_rect(rect: Rect2):
	_clear_selection()

	for unit in GameState.player_units:
		if unit.is_dead:
			continue
		if rect.has_point(unit.global_position):
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


# ---- Commands ----

func _issue_command(target_pos: Vector2):
	var clicked_unit = _get_unit_at(target_pos)
	var clicked_node = _get_node_at(target_pos)

	# Determine target owner via first selected unit's owner
	if selected_units.is_empty():
		return
	var my_owner = selected_units[0].unit_owner

	if clicked_unit and clicked_unit.unit_owner != my_owner:
		# Attack enemy unit
		for unit in selected_units:
			unit.command_attack(clicked_unit)
	elif clicked_node and GameState.is_capturable(clicked_node.node_id, my_owner):
		# Attack neutral/enemy node
		for unit in selected_units:
			unit.command_attack_node(clicked_node)
	else:
		# Move to position
		for unit in selected_units:
			unit.command_move(target_pos)


# ---- Helpers ----

func _get_unit_at(global_pos: Vector2) -> Node:
	# Check player units first, then enemy
	var all_units = GameState.player_units + GameState.enemy_units
	for unit in all_units:
		if unit.is_dead or not is_instance_valid(unit):
			continue
		if unit.global_position.distance_to(global_pos) < 30:
			return unit
	return null


func _get_node_at(global_pos: Vector2) -> Node:
	for node in GameState.nodes.values():
		if is_instance_valid(node) and node.global_position.distance_to(global_pos) < 50:
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
