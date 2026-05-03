extends Node2D
## A capturable node on the map (castle, gold mine, etc.)
class_name GameNode

enum NodeType {
	MAIN_CASTLE = 0,
	CASTLE = 1,
	GOLD_MINE = 2,
	MAGIC_SPRING = 3,
	BARRACKS = 4,
	LUMBER_MILL = 5,
}

@export var node_id: String = ""
@export var node_name: String = "Node"
@export var node_type: NodeType = NodeType.CASTLE
@export var max_hp: int = 300
@export var gold_per_tick: int = 4
@export var bonus_effect: String = ""

var hp: int
var node_owner: int = GameState.Owner.NEUTRAL
var is_dead: bool = false

var _sprite: ColorRect
var _hp_bar: ColorRect
var _hp_bar_bg: ColorRect
var _label: Label
var _flag: ColorRect


func _ready():
	hp = max_hp
	_setup_display()
	GameState.register_node(self)
	add_to_group("map_nodes")
	refresh_display()


func _setup_display():
	_sprite = ColorRect.new()
	_sprite.size = Vector2(60, 60)
	_sprite.position = -_sprite.size / 2.0
	_sprite.color = Color(0.5, 0.5, 0.5)
	add_child(_sprite)

	_flag = ColorRect.new()
	_flag.size = Vector2(14, 14)
	_flag.position = Vector2(-30, -30)
	add_child(_flag)

	_hp_bar_bg = ColorRect.new()
	_hp_bar_bg.size = Vector2(60, 6)
	_hp_bar_bg.position = Vector2(-30, 30)
	_hp_bar_bg.color = Color(0.2, 0.2, 0.2)
	add_child(_hp_bar_bg)

	_hp_bar = ColorRect.new()
	_hp_bar.size = Vector2(60, 6)
	_hp_bar.position = Vector2(-30, 30)
	_hp_bar.color = Color(0.2, 0.8, 0.2)
	add_child(_hp_bar)

	_label = Label.new()
	_label.text = node_name
	_label.position = Vector2(-30, 38)
	_label.add_theme_font_size_override("font_size", 12)
	_label.add_theme_color_override("font_color", Color.WHITE)
	_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_label.size.x = 60
	add_child(_label)

	var gold_label = Label.new()
	gold_label.text = "+" + str(gold_per_tick) + "g"
	gold_label.position = Vector2(-20, 50)
	gold_label.add_theme_font_size_override("font_size", 10)
	gold_label.add_theme_color_override("font_color", Color(1, 0.85, 0.3))
	add_child(gold_label)


func take_damage(amount: int, attacker_node_owner: int):
	if is_dead:
		return
	if node_owner == attacker_node_owner:
		return
	if node_owner == GameState.Owner.NEUTRAL and attacker_node_owner == GameState.Owner.NEUTRAL:
		return

	hp -= amount
	EventBus.node_damaged.emit(node_id, hp, max_hp)

	if hp <= 0:
		if node_type == NodeType.MAIN_CASTLE:
			_destroy(attacker_node_owner)
		else:
			_capture(attacker_node_owner)
	refresh_display()


func _capture(new_owner: int):
	var old = node_owner
	node_owner = new_owner
	hp = max_hp
	EventBus.node_captured.emit(node_id, node_owner, old)


func _destroy(attacker_node_owner: int):
	node_owner = attacker_node_owner
	hp = 0
	is_dead = true
	hide()
	GameState.end_game(attacker_node_owner)


func heal(amount: int):
	if is_dead: return
	hp = min(hp + amount, max_hp)


func refresh_display():
	match node_owner:
		GameState.Owner.NEUTRAL:
			_sprite.color = Color(0.4, 0.4, 0.4)
			_flag.color = Color(0.4, 0.4, 0.4)
		GameState.Owner.PLAYER:
			_sprite.color = Color(0.2, 0.35, 0.8)
			_flag.color = Color(0.2, 0.35, 0.8)
		GameState.Owner.ENEMY:
			_sprite.color = Color(0.8, 0.2, 0.2)
			_flag.color = Color(0.8, 0.2, 0.2)

	match node_type:
		NodeType.MAIN_CASTLE:
			_sprite.size = Vector2(80, 80)
			_sprite.position = -_sprite.size / 2.0
		NodeType.GOLD_MINE:
			_sprite.color.r *= 0.7
			_sprite.color.g *= 1.3
			_sprite.color.b *= 0.7

	if max_hp > 0:
		var ratio = float(hp) / float(max_hp)
		_hp_bar.size.x = 60 * ratio
		if ratio > 0.6:
			_hp_bar.color = Color(0.2, 0.8, 0.2)
		elif ratio > 0.3:
			_hp_bar.color = Color(0.8, 0.8, 0.2)
		else:
			_hp_bar.color = Color(0.8, 0.2, 0.2)


func is_enemy_to(my_owner: int) -> bool:
	return node_owner != GameState.Owner.NEUTRAL and node_owner != my_owner


func set_display_name(new_name: String):
	node_name = new_name
	_label.text = new_name


func can_spawn_units() -> bool:
	return node_type in [NodeType.MAIN_CASTLE, NodeType.CASTLE]
