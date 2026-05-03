extends Control
## Game over screen.

signal restart_requested
signal back_to_menu

var _overlay: ColorRect
var _title: Label
var _detail: Label
var _btn_restart: Button
var _btn_menu: Button


func _ready():
	visible = false

	_overlay = ColorRect.new()
	_overlay.size = Vector2(1920, 1080)
	_overlay.color = Color(0, 0, 0, 0.6)
	_overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_overlay)

	var panel = Panel.new()
	panel.size = Vector2(400, 280)
	panel.position = Vector2(760, 350)
	var sb = StyleBoxFlat.new()
	sb.bg_color = Color(0.1, 0.1, 0.15, 0.95)
	sb.border_width_left = 2
	sb.border_width_top = 2
	sb.border_width_right = 2
	sb.border_width_bottom = 2
	sb.border_color = Color(0.4, 0.5, 0.6)
	sb.set("corner_radius_top_left", 12)
	sb.set("corner_radius_top_right", 12)
	sb.set("corner_radius_bottom_left", 12)
	sb.set("corner_radius_bottom_right", 12)
	panel.add_theme_stylebox_override("panel", sb)
	add_child(panel)

	_title = Label.new()
	_title.position = Vector2(0, 30)
	_title.size = Vector2(400, 50)
	_title.add_theme_font_size_override("font_size", 32)
	_title.add_theme_color_override("font_color", Color.WHITE)
	_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	panel.add_child(_title)

	_detail = Label.new()
	_detail.position = Vector2(0, 90)
	_detail.size = Vector2(400, 50)
	_detail.add_theme_font_size_override("font_size", 16)
	_detail.add_theme_color_override("font_color", Color(0.7, 0.7, 0.7))
	_detail.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	panel.add_child(_detail)

	_btn_restart = Button.new()
	_btn_restart.text = "Restart"
	_btn_restart.position = Vector2(120, 160)
	_btn_restart.size = Vector2(160, 40)
	_btn_restart.add_theme_font_size_override("font_size", 16)
	_btn_restart.pressed.connect(func(): restart_requested.emit())
	panel.add_child(_btn_restart)

	_btn_menu = Button.new()
	_btn_menu.text = "Back to Menu"
	_btn_menu.position = Vector2(120, 210)
	_btn_menu.size = Vector2(160, 40)
	_btn_menu.add_theme_font_size_override("font_size", 16)
	_btn_menu.pressed.connect(func(): back_to_menu.emit())
	panel.add_child(_btn_menu)

	EventBus.game_over.connect(_on_game_over)


func _on_game_over(winner: int):
	visible = true
	if winner == GameState.Owner.PLAYER:
		_title.text = "Victory"
		_title.add_theme_color_override("font_color", Color(0.2, 0.9, 0.2))
		_detail.text = "The enemy stronghold has fallen."
	else:
		_title.text = "Defeat"
		_title.add_theme_color_override("font_color", Color(0.9, 0.2, 0.2))
		_detail.text = "Your stronghold has been destroyed."
