extends Control
## Race selection screen shown before battle.

signal race_selected(race_id: int)

var race_scenes := {
	0: {"name": "人族", "desc": "步兵护甲 +3\n主城生命 +20%\n擅长阵地防守", "color": Color(0.22, 0.44, 0.9)},
	1: {"name": "兽族", "desc": "全体攻击 +2\n骑兵生命 +15%\n正面推进凶猛", "color": Color(0.86, 0.24, 0.2)},
	2: {"name": "亡灵", "desc": "消耗战强势\n续战能力稳定\n适合拖长战线", "color": Color(0.6, 0.24, 0.88)},
	3: {"name": "暗夜精灵", "desc": "移动速度 +30%\n转线速度极快\n擅长抢图游击", "color": Color(0.22, 0.76, 0.54)},
}


func _ready():
	set_anchors_preset(Control.PRESET_FULL_RECT)
	offset_left = 0
	offset_top = 0
	offset_right = 0
	offset_bottom = 0

	var bg = ColorRect.new()
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	bg.color = Color(0.04, 0.05, 0.04)
	bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(bg)

	var top_glow = ColorRect.new()
	top_glow.anchor_right = 1.0
	top_glow.offset_bottom = 220
	top_glow.color = Color(0.18, 0.17, 0.09, 0.16)
	top_glow.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(top_glow)

	var center = CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	center.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(center)

	var layout = VBoxContainer.new()
	layout.custom_minimum_size = Vector2(1080, 620)
	layout.alignment = BoxContainer.ALIGNMENT_CENTER
	layout.add_theme_constant_override("separation", 26)
	center.add_child(layout)

	var heading = VBoxContainer.new()
	heading.alignment = BoxContainer.ALIGNMENT_CENTER
	heading.add_theme_constant_override("separation", 8)
	layout.add_child(heading)

	var title = Label.new()
	title.text = "选择你的军团"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", 40)
	title.add_theme_color_override("font_color", Color.WHITE)
	heading.add_child(title)

	var subtitle = Label.new()
	subtitle.text = "围绕道路与据点，建立属于你的推进节奏"
	subtitle.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	subtitle.add_theme_font_size_override("font_size", 15)
	subtitle.add_theme_color_override("font_color", Color(0.72, 0.74, 0.76))
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
	panel.custom_minimum_size = Vector2(220, 340)
	panel.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	panel.add_theme_stylebox_override("panel", _make_stylebox(data["color"]))

	var body = VBoxContainer.new()
	body.add_theme_constant_override("separation", 12)
	panel.add_child(body)

	var banner = ColorRect.new()
	banner.custom_minimum_size = Vector2(0, 74)
	banner.color = data["color"]
	body.add_child(banner)

	var inner_band = ColorRect.new()
	inner_band.custom_minimum_size = Vector2(0, 10)
	inner_band.color = data["color"].lightened(0.25)
	body.add_child(inner_band)

	var name_label = Label.new()
	name_label.text = data["name"]
	name_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	name_label.add_theme_font_size_override("font_size", 20)
	name_label.add_theme_color_override("font_color", Color.WHITE)
	body.add_child(name_label)

	var desc_label = Label.new()
	desc_label.text = data["desc"]
	desc_label.custom_minimum_size = Vector2(180, 110)
	desc_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	desc_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	desc_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	desc_label.add_theme_font_size_override("font_size", 12)
	desc_label.add_theme_color_override("font_color", Color(0.8, 0.82, 0.84))
	desc_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	body.add_child(desc_label)

	var mood = Label.new()
	mood.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	mood.add_theme_font_size_override("font_size", 11)
	mood.add_theme_color_override("font_color", data["color"].lightened(0.18))
	mood.text = _get_mood_text(race_id)
	body.add_child(mood)

	var spacer = Control.new()
	spacer.size_flags_vertical = Control.SIZE_EXPAND_FILL
	body.add_child(spacer)

	var btn = Button.new()
	btn.text = "选择"
	btn.custom_minimum_size = Vector2(0, 42)
	btn.pressed.connect(func(): race_selected.emit(race_id))
	body.add_child(btn)

	return panel


func _make_stylebox(border_color: Color) -> StyleBoxFlat:
	var sb = StyleBoxFlat.new()
	sb.bg_color = Color(0.08, 0.1, 0.12, 0.94)
	sb.border_width_left = 2
	sb.border_width_top = 2
	sb.border_width_right = 2
	sb.border_width_bottom = 2
	sb.border_color = border_color
	sb.content_margin_left = 12
	sb.content_margin_top = 12
	sb.content_margin_right = 12
	sb.content_margin_bottom = 12
	sb.set("corner_radius_top_left", 6)
	sb.set("corner_radius_top_right", 6)
	sb.set("corner_radius_bottom_left", 6)
	sb.set("corner_radius_bottom_right", 6)
	return sb


func _get_mood_text(race_id: int) -> String:
	match race_id:
		0:
			return "稳步推进 / 铁壁守线"
		1:
			return "凶猛突击 / 正面碾压"
		2:
			return "拖垮对手 / 消耗制胜"
		3:
			return "高速转场 / 抢夺地图"
	return ""
