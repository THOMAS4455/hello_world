extends Node2D
## Commander ability system. Handles skill activation, aiming, and effects.

enum SkillState { READY, AIMING, COOLDOWN }

var skills: Array = [
	{ "name": "Heal", "cooldown": 60.0, "radius": 150.0, "timer": 0.0, "state": SkillState.READY },
	{ "name": "Fireball", "cooldown": 45.0, "radius": 100.0, "timer": 0.0, "state": SkillState.READY },
	{ "name": "War Horn", "cooldown": 90.0, "radius": 200.0, "timer": 0.0, "state": SkillState.READY },
]

var _active_skill_index: int = -1
var _aiming: bool = false
var _cursor_sprite: ColorRect
var _cast_click_armed: bool = false


func _ready():
	add_to_group("commander")
	_create_cursor()
	for i in skills.size():
		_update_skill_button(i)


func _create_cursor():
	_cursor_sprite = ColorRect.new()
	_cursor_sprite.size = Vector2(60, 60)
	_cursor_sprite.position = -_cursor_sprite.size / 2.0
	_cursor_sprite.color = Color(1, 0.5, 0.5, 0.3)
	_cursor_sprite.visible = false
	add_child(_cursor_sprite)


func _process(delta):
	for i in skills.size():
		var skill: Dictionary = skills[i]
		if skill["state"] == SkillState.COOLDOWN:
			skill["timer"] = max(0.0, float(skill["timer"]) - delta)
			if skill["timer"] <= 0.0:
				skill["state"] = SkillState.READY
			_update_skill_button(i)

	if _aiming:
		_cursor_sprite.global_position = get_global_mouse_position()
		_cursor_sprite.visible = true
	else:
		_cursor_sprite.visible = false


func _input(event):
	if not GameState.game_started or GameState.game_ended:
		return

	if event is InputEventKey and event.pressed and not event.echo:
		match event.physical_keycode:
			KEY_1:
				activate_skill(0)
			KEY_2:
				activate_skill(1)
			KEY_3:
				activate_skill(2)

	if not _aiming:
		return

	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed:
			_cast_click_armed = true
		elif _cast_click_armed:
			_cast_click_armed = false
			_cast_active_skill()
	elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_RIGHT and event.pressed:
		_cancel_active_skill()


func activate_skill(index: int):
	if index < 0 or index >= skills.size():
		return

	var skill: Dictionary = skills[index]
	if skill["state"] != SkillState.READY:
		return

	_active_skill_index = index
	_aiming = true
	_cast_click_armed = false
	skill["state"] = SkillState.AIMING

	match index:
		0:
			_cursor_sprite.color = Color(0.2, 1, 0.2, 0.3)
		1:
			_cursor_sprite.color = Color(1, 0.3, 0.3, 0.3)
		2:
			_cursor_sprite.color = Color(0.3, 0.5, 1, 0.3)

	var radius := float(skill["radius"])
	_cursor_sprite.size = Vector2(radius * 2.0, radius * 2.0)
	_cursor_sprite.position = -_cursor_sprite.size / 2.0
	_update_skill_button(index)


func is_aiming() -> bool:
	return _aiming


func _cast_active_skill():
	if _active_skill_index < 0 or _active_skill_index >= skills.size():
		return

	var skill: Dictionary = skills[_active_skill_index]
	var pos = get_global_mouse_position()

	match _active_skill_index:
		0:
			_cast_heal(pos, float(skill["radius"]))
		1:
			_cast_fireball(pos, float(skill["radius"]))
		2:
			_cast_war_horn(pos, float(skill["radius"]))

	var finished_index := _active_skill_index
	skill["state"] = SkillState.COOLDOWN
	skill["timer"] = float(skill["cooldown"])
	_aiming = false
	_active_skill_index = -1
	_update_skill_button(finished_index)


func _cancel_active_skill():
	if _active_skill_index < 0 or _active_skill_index >= skills.size():
		return

	var index := _active_skill_index
	var skill: Dictionary = skills[index]
	skill["state"] = SkillState.READY
	_aiming = false
	_cast_click_armed = false
	_active_skill_index = -1
	_update_skill_button(index)


func _cast_heal(pos: Vector2, radius: float):
	for unit in GameState.player_units:
		if not is_instance_valid(unit) or unit.is_dead:
			continue
		if unit.global_position.distance_to(pos) <= radius:
			var heal_amount = int(unit.max_hp * 0.3)
			unit.hp = min(unit.hp + heal_amount, unit.max_hp)


func _cast_fireball(pos: Vector2, radius: float):
	for unit in GameState.enemy_units:
		if not is_instance_valid(unit) or unit.is_dead:
			continue
		if unit.global_position.distance_to(pos) <= radius:
			unit.take_damage(30)


func _cast_war_horn(pos: Vector2, radius: float):
	for unit in GameState.player_units:
		if not is_instance_valid(unit) or unit.is_dead:
			continue
		if unit.global_position.distance_to(pos) <= radius:
			unit.move_speed *= 1.5
			get_tree().create_timer(8.0).timeout.connect(func():
				if is_instance_valid(unit):
					unit.move_speed /= 1.5
			)


func _update_skill_button(index: int):
	if index < 0 or index >= skills.size():
		return

	var hud = get_tree().get_first_node_in_group("ui_hud")
	if not hud:
		return

	var btns = [hud.btn_skill1, hud.btn_skill2, hud.btn_skill3]
	var skill: Dictionary = skills[index]
	if skill["state"] == SkillState.COOLDOWN:
		btns[index].text = "%s %ss" % [skill["name"], int(ceil(float(skill["timer"])))]
		btns[index].disabled = true
	elif skill["state"] == SkillState.AIMING:
		btns[index].text = "Cast %s" % skill["name"]
		btns[index].disabled = false
	else:
		btns[index].text = "%d. %s" % [index + 1, skill["name"]]
		btns[index].disabled = false
