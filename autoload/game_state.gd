extends Node

enum Owner {
	NEUTRAL = 0,
	PLAYER = 1,
	ENEMY = 2,
}

var player_gold: int = 150
var enemy_gold: int = 150
var gold_tick_interval: float = 2.0
var tick_timer: float = 0.0

var nodes: Dictionary = {}
var player_units: Array = []
var enemy_units: Array = []

# Road network for pathfinding
var road_graph: Dictionary = {}        # node_id -> [neighbor_ids]
var road_segments: Array = []           # [[Vector2, Vector2], ...] — world-space segment endpoints

var player_race: int = 0
var enemy_race: int = 1
var game_started: bool = false
var game_ended: bool = false


func reset_match_state():
	player_gold = 150
	enemy_gold = 150
	tick_timer = 0.0
	nodes.clear()
	player_units.clear()
	enemy_units.clear()
	road_graph.clear()
	road_segments.clear()
	game_started = false
	game_ended = false


func _process(delta):
	if not game_started or game_ended:
		return
	tick_timer += delta
	if tick_timer >= gold_tick_interval:
		tick_timer = 0.0
		_produce_gold()


func _produce_gold():
	var player_income := 0
	var enemy_income := 0
	for node in nodes.values():
		if node.node_owner == Owner.PLAYER:
			player_income += node.gold_per_tick
		elif node.node_owner == Owner.ENEMY:
			enemy_income += node.gold_per_tick

	player_gold += player_income
	enemy_gold += enemy_income
	EventBus.gold_changed.emit(Owner.PLAYER, player_gold)
	EventBus.gold_changed.emit(Owner.ENEMY, enemy_gold)


func get_total_income(owner: Owner) -> int:
	var total := 0
	for node in nodes.values():
		if node.node_owner == owner:
			total += node.gold_per_tick
	return total


func can_afford(which: Owner, cost: int) -> bool:
	match which:
		Owner.PLAYER: return player_gold >= cost
		Owner.ENEMY: return enemy_gold >= cost
	return false


func spend_gold(which: Owner, amount: int):
	match which:
		Owner.PLAYER:
			player_gold = max(0, player_gold - amount)
			EventBus.gold_changed.emit(Owner.PLAYER, player_gold)
		Owner.ENEMY:
			enemy_gold = max(0, enemy_gold - amount)
			EventBus.gold_changed.emit(Owner.ENEMY, enemy_gold)


func register_node(node):
	nodes[node.node_id] = node


func get_node_owner(node_id: String) -> Owner:
	if nodes.has(node_id):
		return nodes[node_id].node_owner
	return Owner.NEUTRAL


func is_enemy_node(node_id: String, my_owner: Owner) -> bool:
	var o = get_node_owner(node_id)
	return o != Owner.NEUTRAL and o != my_owner


func is_capturable(nid: String, my_owner: Owner) -> bool:
	var o = get_node_owner(nid)
	return o == Owner.NEUTRAL or (o != Owner.NEUTRAL and o != my_owner)


func end_game(winner: Owner):
	game_ended = true
	game_started = false
	EventBus.game_over.emit(winner)


# ---- Road pathfinding ----

func build_road_graph(roads_data: Array):
	road_graph.clear()
	road_segments.clear()
	for pair in roads_data:
		var a = pair[0]
		var b = pair[1]
		# Build adjacency graph
		if not road_graph.has(a):
			road_graph[a] = []
		if not road_graph.has(b):
			road_graph[b] = []
		if b not in road_graph[a]:
			road_graph[a].append(b)
		if a not in road_graph[b]:
			road_graph[b].append(a)


func build_road_segments():
	# Called after nodes are registered — builds world-space segment list
	road_segments.clear()
	for nid_a in road_graph:
		if not nodes.has(nid_a): continue
		for nid_b in road_graph[nid_a]:
			if not nodes.has(nid_b): continue
			# Avoid duplicate segments (only add a→b when a < b alphabetically)
			if nid_a < nid_b:
				road_segments.append([nodes[nid_a].global_position, nodes[nid_b].global_position])


func find_road_path(from_pos: Vector2, to_pos: Vector2) -> Array:
	# Returns Array[Vector2] of waypoints following the road network
	var start_nid = _nearest_node_id(from_pos)
	var end_nid = _nearest_node_id(to_pos)

	if start_nid == end_nid or not road_graph.has(start_nid) or not road_graph.has(end_nid):
		return [to_pos]

	# BFS shortest path on the road graph
	var came_from: Dictionary = {}
	var queue: Array = [start_nid]
	var visited: Dictionary = {start_nid: true}

	while queue.size() > 0:
		var cur = queue.pop_front()
		if cur == end_nid:
			break
		for nb in road_graph.get(cur, []):
			if not visited.has(nb):
				visited[nb] = true
				came_from[nb] = cur
				queue.append(nb)

	# No path found — fall back to direct movement
	if not came_from.has(end_nid):
		return [to_pos]

	# Reconstruct path: walk backward from end_nid to start_nid
	var path_ids: Array = [end_nid]
	var cur_id = end_nid
	while cur_id != start_nid:
		cur_id = came_from[cur_id]
		path_ids.push_front(cur_id)

	# Convert node IDs to world positions (skip first — unit is already near it)
	var path: Array = []
	for i in range(1, path_ids.size()):
		var nid = path_ids[i]
		if nodes.has(nid):
			path.append(nodes[nid].global_position)
	path.append(to_pos)
	return path


func is_near_road(pos: Vector2, threshold: float = 25.0) -> bool:
	for seg in road_segments:
		var closest = _closest_point_on_segment(pos, seg[0], seg[1])
		if pos.distance_to(closest) < threshold:
			return true
	return false


func _nearest_node_id(pos: Vector2) -> String:
	var best = ""
	var best_d = INF
	for nid in nodes:
		var d = nodes[nid].global_position.distance_to(pos)
		if d < best_d:
			best_d = d
			best = nid
	return best


func _closest_point_on_segment(p: Vector2, a: Vector2, b: Vector2) -> Vector2:
	var ab = b - a
	var t = clamp((p - a).dot(ab) / max(ab.length_squared(), 0.0001), 0.0, 1.0)
	return a + ab * t
