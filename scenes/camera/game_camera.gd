extends Camera2D
## Game camera with WASD pan, edge scroll, and mouse-wheel zoom.

@export var pan_speed: float = 400.0
@export var edge_margin: float = 20.0
@export var base_min_zoom: float = 0.6
@export var max_zoom: float = 2.0
@export var zoom_step: float = 0.1
@export var map_rect: Rect2 = Rect2(0, 0, 1920, 1080)

var viewport_size: Vector2 = Vector2.ZERO
var effective_min_zoom: float = 1.0


func _ready():
	_update_viewport_metrics()
	get_viewport().size_changed.connect(_on_viewport_resized)
	_apply_zoom(max(base_min_zoom, effective_min_zoom), viewport_size * 0.5)


func _process(delta):
	var move := Vector2.ZERO

	if Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT):
		move.x -= 1
	if Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT):
		move.x += 1
	if Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP):
		move.y -= 1
	if Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN):
		move.y += 1

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

	if move.length() > 0.0:
		position += move.normalized() * pan_speed * delta * (1.0 / zoom.x)

	_clamp_to_map()


func _input(event):
	if event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			_zoom_in(event.position)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_zoom_out(event.position)


func _zoom_in(mouse_pos: Vector2):
	var new_zoom = max(zoom.x - zoom_step, effective_min_zoom)
	_apply_zoom(new_zoom, mouse_pos)


func _zoom_out(mouse_pos: Vector2):
	var new_zoom = min(zoom.x + zoom_step, max_zoom)
	_apply_zoom(new_zoom, mouse_pos)


func _apply_zoom(new_zoom: float, mouse_pos: Vector2):
	var clamped_zoom = clamp(new_zoom, effective_min_zoom, max_zoom)
	var old_zoom = zoom.x
	if is_zero_approx(old_zoom):
		old_zoom = clamped_zoom
	if is_equal_approx(old_zoom, clamped_zoom):
		zoom = Vector2(clamped_zoom, clamped_zoom)
		_clamp_to_map()
		return

	zoom = Vector2(clamped_zoom, clamped_zoom)
	var ratio = 1.0 / old_zoom - 1.0 / clamped_zoom
	position += ratio * (mouse_pos - viewport_size * 0.5)
	_clamp_to_map()


func _on_viewport_resized():
	_update_viewport_metrics()
	zoom = Vector2(max(zoom.x, effective_min_zoom), max(zoom.y, effective_min_zoom))
	_clamp_to_map()


func _update_viewport_metrics():
	viewport_size = get_viewport_rect().size
	var fit_x = viewport_size.x / map_rect.size.x
	var fit_y = viewport_size.y / map_rect.size.y
	effective_min_zoom = max(base_min_zoom, fit_x, fit_y)


func _clamp_to_map():
	var half_viewport = viewport_size / (2.0 * zoom.x)

	if half_viewport.x >= map_rect.size.x * 0.5:
		position.x = map_rect.position.x + map_rect.size.x * 0.5
	else:
		position.x = clamp(position.x, map_rect.position.x + half_viewport.x, map_rect.end.x - half_viewport.x)

	if half_viewport.y >= map_rect.size.y * 0.5:
		position.y = map_rect.position.y + map_rect.size.y * 0.5
	else:
		position.y = clamp(position.y, map_rect.position.y + half_viewport.y, map_rect.end.y - half_viewport.y)
