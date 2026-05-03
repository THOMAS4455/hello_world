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
	var bg = ColorRect.new()
	bg.size = Vector2(1920, 1080)
	bg.color = Color(0.05, 0.06, 0.04)
	bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(bg)

	var title = Label.new()
	title.text = "Choose Your Race"
	title.position = Vector2(0, 160)
	title.size = Vector2(1920, 50)
	title.add_theme_font_size_override("font_size", 36)
	title.add_theme_color_override("font_color", Color.WHITE)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(title)

	var subtitle = Label.new()
	subtitle.text = "RTS Battle"
	subtitle.position = Vector2(0, 220)
	subtitle.size = Vector2(1920, 24)
	subtitle.add_theme_font_size_override("font_size", 16)
	subtitle.add_theme_color_override("font_color", Color(0.6, 0.6, 0.6))
	subtitle.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(subtitle)

	var card_y = 280
	var card_w = 180
	var card_h = 280
	var gap = 24
	var total_w = card_w * 4 + gap * 3
	var start_x = (1920 - total_w) / 2

	var race_ids = race_scenes.keys()
	race_ids.sort()
	for i in race_ids.size():
		var race_id = race_ids[i]
		var card = _make_race_card(race_id, card_w, card_h)
		card.position = Vector2(start_x + i * (card_w + gap), card_y)
		add_child(card)


func _make_race_card(race_id: int, card_w: int, card_h: int) -> Control:
	var data: Dictionary = race_scenes[race_id]
	var panel = Panel.new()
	panel.size = Vector2(card_w, card_h)
	panel.add_theme_stylebox_override("panel", _make_stylebox(data["color"]))

	var margin = 12
	var inner_w = card_w - margin * 2

	var color_swatch = ColorRect.new()
	color_swatch.size = Vector2(inner_w, 70)
	color_swatch.position = Vector2(margin, margin)
	color_swatch.color = data["color"]
	panel.add_child(color_swatch)

	var name_label = Label.new()
	name_label.text = data["name"]
	name_label.position = Vector2(margin, margin + 76)
	name_label.size = Vector2(inner_w, 30)
	name_label.add_theme_font_size_override("font_size", 20)
	name_label.add_theme_color_override("font_color", Color.WHITE)
	name_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	panel.add_child(name_label)

	var desc_label = Label.new()
	desc_label.text = data["desc"]
	desc_label.position = Vector2(margin, margin + 110)
	desc_label.size = Vector2(inner_w, 80)
	desc_label.add_theme_font_size_override("font_size", 12)
	desc_label.add_theme_color_override("font_color", Color(0.7, 0.7, 0.7))
	desc_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	desc_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	desc_label.autowrap_mode = TextServer.AUTOWRAP_WORD
	panel.add_child(desc_label)

	var btn = Button.new()
	btn.text = "Select"
	btn.position = Vector2(margin, card_h - 50)
	btn.size = Vector2(inner_w, 36)
	btn.add_theme_font_size_override("font_size", 16)
	btn.pressed.connect(func(): race_selected.emit(race_id))
	panel.add_child(btn)

	return panel


func _make_stylebox(border_color: Color) -> StyleBoxFlat:
	var sb = StyleBoxFlat.new()
	sb.bg_color = Color(0.1, 0.1, 0.15, 0.9)
	sb.border_width_left = 2
	sb.border_width_top = 2
	sb.border_width_right = 2
	sb.border_width_bottom = 2
	sb.border_color = border_color
	sb.set("corner_radius_top_left", 8)
	sb.set("corner_radius_top_right", 8)
	sb.set("corner_radius_bottom_left", 8)
	sb.set("corner_radius_bottom_right", 8)
	return sb
