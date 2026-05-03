extends Control
## Selection indicator shown below a unit when selected.

func _ready():
	# Create a circle/ring visual
	var ring = ColorRect.new()
	ring.size = Vector2(36, 36)
	ring.position = -ring.size / 2
	ring.color = Color(0.2, 0.8, 0.2, 0.3)
	add_child(ring)

	# Pulsing animation
	var tw = create_tween()
	tw.set_loops()
	tw.tween_property(ring, "modulate:a", 0.15, 0.6).from_current(0.4)
	tw.tween_property(ring, "modulate:a", 0.4, 0.6)
