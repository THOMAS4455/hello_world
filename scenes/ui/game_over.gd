extends Control
## Game over screen.

signal restart_requested
signal back_to_menu

var _title: Label
var _detail: Label
var _btn_restart: Button
var _btn_menu: Button


func _ready():
	set_anchors_preset(Control.PRESET_FULL_RECT)
	offset_left = 0
	offset_top = 0
	offset_right = 0
	offset_bottom = 0
	visible = false

	var overlay = ColorRect.new()
	overlay.set_anchors_preset(Control.PRESET_FULL_RECT)
	overlay.color = Color(0, 0, 0, 0.6)
	overlay.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(overlay)

	var center = CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(center)

	var panel = PanelContainer.new()
	panel.custom_minimum_size = Vector2(420, 280)
	panel.add_theme_stylebox_override("panel", _make_panel_style())
	center.add_child(panel)

	var content = VBoxContainer.new()
	content.alignment = BoxContainer.ALIGNMENT_CENTER
	content.add_theme_constant_override("separation", 16)
	panel.add_child(content)

	_title = Label.new()
	_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_title.add_theme_font_size_override("font_size", 32)
	_title.add_theme_color_override("font_color", Color.WHITE)
	content.add_child(_title)

	_detail = Label.new()
	_detail.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_detail.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_detail.custom_minimum_size = Vector2(320, 48)
	_detail.add_theme_font_size_override("font_size", 16)
	_detail.add_theme_color_override("font_color", Color(0.7, 0.7, 0.7))
	content.add_child(_detail)

	_btn_restart = Button.new()
	_btn_restart.text = "Restart"
	_btn_restart.custom_minimum_size = Vector2(180, 40)
	_btn_restart.add_theme_font_size_override("font_size", 16)
	_btn_restart.pressed.connect(func(): restart_requested.emit())
	content.add_child(_btn_restart)

	_btn_menu = Button.new()
	_btn_menu.text = "Back to Menu"
	_btn_menu.custom_minimum_size = Vector2(180, 40)
	_btn_menu.add_theme_font_size_override("font_size", 16)
	_btn_menu.pressed.connect(func(): back_to_menu.emit())
	content.add_child(_btn_menu)

	EventBus.game_over.connect(_on_game_over)


func _make_panel_style() -> StyleBoxFlat:
	var sb = StyleBoxFlat.new()
	sb.bg_color = Color(0.1, 0.1, 0.15, 0.95)
	sb.border_width_left = 2
	sb.border_width_top = 2
	sb.border_width_right = 2
	sb.border_width_bottom = 2
	sb.border_color = Color(0.4, 0.5, 0.6)
	sb.content_margin_left = 28
	sb.content_margin_top = 26
	sb.content_margin_right = 28
	sb.content_margin_bottom = 26
	sb.set("corner_radius_top_left", 12)
	sb.set("corner_radius_top_right", 12)
	sb.set("corner_radius_bottom_left", 12)
	sb.set("corner_radius_bottom_right", 12)
	return sb


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
