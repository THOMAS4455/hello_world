extends Area2D
## Road segment. Units walking over roads get a speed boost.
class_name Road

@export var speed_multiplier: float = 1.5

var _active_units: Dictionary = {}  # { unit_id: original_speed }


func _ready():
	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)
	add_to_group("roads")


func _on_body_entered(body):
	if body is UnitBase and not _active_units.has(body.get_instance_id()):
		_active_units[body.get_instance_id()] = body.move_speed
		body.move_speed *= speed_multiplier


func _on_body_exited(body):
	if _active_units.has(body.get_instance_id()):
		body.move_speed = _active_units[body.get_instance_id()]
		_active_units.erase(body.get_instance_id())
