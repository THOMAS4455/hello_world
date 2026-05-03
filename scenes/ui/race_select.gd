extends Control
## Race selection screen shown before battle.

signal race_selected(race_id: int)

var race_scenes := {
	0: { "name": "Human", "desc": "+3 defense for infantry\nCastles gain 20% HP\nBest at holding territory", "color": Color(0.2, 0.4, 0.9) },
	1: { "name": "Orc", "desc": "+2 attack for all units\nCavalry gain 15% HP\nStrong frontal pressure", "color": Color(0.9, 0.2, 0.2) },
	2: { "name": "Undead", "desc": "Future revive mechanics\nStable baseline roster\nAttrition-focused fantasy", "color": Color(0.6, 0.2, 0.9) },
	3: { "name": "Night Elf", "desc": "+30% move speed\nFast map rotation\nExcels at mobility", "color": Color(0.2, 0.8, 0.5) },
}


func _ready():
	set_anchors_preset(Control.PRESET_FULL_RECT)
	offset_left = 0
	offset_top = 0
	offset_right = 0
	offset_bottom = 0

	var bg = ColorRect.new()
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	bg.color = Color(0.05, 0.06, 0.04)
	bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(bg)

	var center = CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	center.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(center)

	var layout = VBoxContainer.new()
	layout.custom_minimum_size = Vector2(900, 520)
	layout.alignment = BoxContainer.ALIGNMENT_CENTER
	layout.add_theme_constant_override("separation", 20)
	center.add_child(layout)

	var heading = VBoxContainer.new()
	heading.alignment = BoxContainer.ALIGNMENT_CENTER
	heading.add_theme_constant_override("separation", 6)
	layout.add_child(heading)

	var title = Label.new()
	title.text = "Choose Your Race"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", 36)
	title.add_theme_color_override("font_color", Color.WHITE)
	heading.add_child(title)

	var subtitle = Label.new()
	subtitle.text = "RTS Battle"
	subtitle.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	subtitle.add_theme_font_size_override("font_size", 16)
	subtitle.add_theme_color_override("font_color", Color(0.6, 0.6, 0.6))
	heading.add_child(subtitle)

	var cards_center = CenterContainer.new()
	layout.add_child(cards_center)

	var cards = HBoxContainer.new()
	cards.alignment = BoxContainer.ALIGNMENT_CENTER
	cards.add_theme_constant_override("separation", 24)
	cards_center.add_child(cards)

	var race_ids = race_scenes.keys()
	race_ids.sort()
	for race_id in race_ids:
		cards.add_child(_make_race_card(race_id))


func _make_race_card(race_id: int) -> Control:
	var data: Dictionary = race_scenes[race_id]
	var panel = PanelContainer.new()
	panel.custom_minimum_size = Vector2(180, 280)
	panel.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	panel.add_theme_stylebox_override("panel", _make_stylebox(data["color"]))

	var body = VBoxContainer.new()
	body.add_theme_constant_override("separation", 10)
	panel.add_child(body)

	var swatch = ColorRect.new()
	swatch.custom_minimum_size = Vector2(0, 56)
	swatch.color = data["color"]
	body.add_child(swatch)

	var name_label = Label.new()
	name_label.text = data["name"]
	name_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	name_label.add_theme_font_size_override("font_size", 18)
	name_label.add_theme_color_override("font_color", Color.WHITE)
	body.add_child(name_label)

	var desc_label = Label.new()
	desc_label.text = data["desc"]
	desc_label.custom_minimum_size = Vector2(156, 92)
	desc_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	desc_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	desc_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	desc_label.add_theme_font_size_override("font_size", 12)
	desc_label.add_theme_color_override("font_color", Color(0.72, 0.72, 0.76))
	desc_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	body.add_child(desc_label)

	var spacer = Control.new()
	spacer.size_flags_vertical = Control.SIZE_EXPAND_FILL
	body.add_child(spacer)

	var btn = Button.new()
	btn.text = "Select"
	btn.custom_minimum_size = Vector2(0, 38)
	btn.pressed.connect(func(): race_selected.emit(race_id))
	body.add_child(btn)

	return panel


func _make_stylebox(border_color: Color) -> StyleBoxFlat:
	var sb = StyleBoxFlat.new()
	sb.bg_color = Color(0.1, 0.1, 0.15, 0.92)
	sb.border_width_left = 2
	sb.border_width_top = 2
	sb.border_width_right = 2
	sb.border_width_bottom = 2
	sb.border_color = border_color
	sb.content_margin_left = 10
	sb.content_margin_top = 10
	sb.content_margin_right = 10
	sb.content_margin_bottom = 10
	sb.set("corner_radius_top_left", 8)
	sb.set("corner_radius_top_right", 8)
	sb.set("corner_radius_bottom_left", 8)
	sb.set("corner_radius_bottom_right", 8)
	return sb
