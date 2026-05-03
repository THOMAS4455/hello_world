extends Camera2D
## Game camera with WASD pan, edge scroll, and mouse-wheel zoom.

@export var pan_speed: float = 400.0
@export var edge_scroll_speed: float = 300.0
@export var edge_margin: float = 20.0
@export var min_zoom: float = 0.5
@export var max_zoom: float = 2.0
@export var zoom_step: float = 0.1
@export var map_rect: Rect2 = Rect2(0, 0, 1920, 1080)

var viewport_size: Vector2


func _ready():
	viewport_size = get_viewport_rect().size


func _process(delta):
	var move := Vector2.ZERO

	# WASD keys
	if Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT):
		move.x -= 1
	if Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT):
		move.x += 1
	if Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP):
		move.y -= 1
	if Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN):
		move.y += 1

	# Edge scrolling (only if mouse inside viewport)
	var mouse_pos = get_viewport().get_mouse_position()
	if mouse_pos.x >= 0 and mouse_pos.x <= viewport_size.x and mouse_pos.y >= 0 and mouse_pos.y <= viewport_size.y:
		if mouse_pos.x < edge_margin:
			move.x -= 1
		if mouse_pos.x > viewport_size.x - edge_margin:
			move.x += 1
		if mouse_pos.y < edge_margin:
			move.y -= 1
		if mouse_pos.y > viewport_size.y - edge_margin:
			move.y += 1

	# Apply movement
	if move.length() > 0:
		move = move.normalized()
		position += move * pan_speed * delta * (1.0 / zoom.x)

	# Clamp to map bounds
	var half_viewport = viewport_size / (2.0 * zoom.x)
	position.x = clamp(position.x, map_rect.position.x + half_viewport.x, map_rect.end.x - half_viewport.x)
	position.y = clamp(position.y, map_rect.position.y + half_viewport.y, map_rect.end.y - half_viewport.y)


func _input(event):
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			_zoom_in(event.position)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_zoom_out(event.position)


func _zoom_in(mouse_pos: Vector2):
	var new_zoom = min(zoom.x + zoom_step, max_zoom)
	_apply_zoom(new_zoom, mouse_pos)


func _zoom_out(mouse_pos: Vector2):
	var new_zoom = max(zoom.x - zoom_step, min_zoom)
	_apply_zoom(new_zoom, mouse_pos)


func _apply_zoom(new_zoom: float, mouse_pos: Vector2):
	var old_zoom = zoom.x
	if old_zoom == new_zoom:
		return
	zoom = Vector2(new_zoom, new_zoom)
	# Adjust position to zoom toward mouse cursor
	var ratio = 1.0 / old_zoom - 1.0 / new_zoom
	position += ratio * (mouse_pos - viewport_size / 2.0)
