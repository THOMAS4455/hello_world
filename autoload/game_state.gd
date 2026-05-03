extends Node

enum Owner {
	NEUTRAL = 0,
	PLAYER = 1,
	ENEMY = 2,
}

const UNIT_COST_DISCOUNT := 15
const SKILL_COOLDOWN_MULT := 0.85
const BONUS_INCOME_LUMBER_MILL := 2
const BONUS_CASTLE_HP_MULT := 1.2

var player_gold: int = 150
var enemy_gold: int = 150
var gold_tick_interval: float = 2.0
var tick_timer: float = 0.0

var nodes: Dictionary = {}
var player_units: Array = []
var enemy_units: Array = []

var road_graph: Dictionary = {}
var road_segments: Array = []

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
	player_gold += get_total_income(Owner.PLAYER)
	enemy_gold += get_total_income(Owner.ENEMY)
	EventBus.gold_changed.emit(Owner.PLAYER, player_gold)
	EventBus.gold_changed.emit(Owner.ENEMY, enemy_gold)
	EventBus.income_tick.emit()


func get_total_income(owner: Owner) -> int:
	var total := 0
	for node in nodes.values():
		if node.node_owner != owner:
			continue
		total += int(node.gold_per_tick)
		if node.bonus_effect == "bonus_income":
			total += BONUS_INCOME_LUMBER_MILL
	return total


func can_afford(which: Owner, cost: int) -> bool:
	match which:
		Owner.PLAYER:
			return player_gold >= cost
		Owner.ENEMY:
			return enemy_gold >= cost
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


func get_owned_nodes(owner: Owner) -> Array:
	var result: Array = []
	for node in nodes.values():
		if node.node_owner == owner and not node.is_dead:
			result.append(node)
	return result


func get_enemy_nodes(owner: Owner) -> Array:
	var result: Array = []
	for node in nodes.values():
		if node.node_owner != Owner.NEUTRAL and node.node_owner != owner and not node.is_dead:
			result.append(node)
	return result


func has_bonus(owner: Owner, bonus_effect: String) -> bool:
	for node in nodes.values():
		if node.node_owner == owner and node.bonus_effect == bonus_effect and not node.is_dead:
			return true
	return false


func get_unit_cost(owner: Owner, unit_type: int) -> int:
	var base_cost = int(RaceData.base_units[unit_type].cost)
	if has_bonus(owner, "unit_cost_discount"):
		base_cost = max(25, base_cost - UNIT_COST_DISCOUNT)
	return base_cost


func get_skill_cooldown_multiplier(owner: Owner) -> float:
	if has_bonus(owner, "skill_haste"):
		return SKILL_COOLDOWN_MULT
	return 1.0


func get_race_for_owner(owner: Owner) -> int:
	if owner == Owner.PLAYER:
		return player_race
	if owner == Owner.ENEMY:
		return enemy_race
	return player_race


func get_unit_count(owner: Owner) -> int:
	var units = player_units if owner == Owner.PLAYER else enemy_units
	var count := 0
	for unit in units:
		if is_instance_valid(unit) and not unit.is_dead:
			count += 1
	return count


func get_node_owner(node_id: String) -> Owner:
	if nodes.has(node_id):
		return nodes[node_id].node_owner
	return Owner.NEUTRAL


func is_enemy_node(node_id: String, my_owner: Owner) -> bool:
	var owner = get_node_owner(node_id)
	return owner != Owner.NEUTRAL and owner != my_owner


func is_capturable(node_id: String, my_owner: Owner) -> bool:
	var owner = get_node_owner(node_id)
	return owner == Owner.NEUTRAL or owner != my_owner


func get_frontline_target(owner: Owner) -> Node:
	var neutral_targets: Array = []
	var enemy_targets: Array = []
	var fallback: Node = null
	var origin = get_stronghold(owner)
	for node in nodes.values():
		if node.is_dead:
			continue
		if node.node_owner == Owner.NEUTRAL:
			neutral_targets.append(node)
		elif node.node_owner != owner:
			enemy_targets.append(node)
		if node.node_type == GameNode.NodeType.MAIN_CASTLE and node.node_owner != owner:
			fallback = node

	var sorter = func(a, b):
		var a_score = a.get_priority_score(owner)
		var b_score = b.get_priority_score(owner)
		if not is_equal_approx(a_score, b_score):
			return a_score > b_score
		if origin:
			return a.global_position.distance_to(origin.global_position) < b.global_position.distance_to(origin.global_position)
		return a.node_id < b.node_id

	if neutral_targets.size() > 0:
		neutral_targets.sort_custom(sorter)
		return neutral_targets[0]
	if enemy_targets.size() > 0:
		enemy_targets.sort_custom(sorter)
		return enemy_targets[0]
	return fallback


func get_stronghold(owner: Owner) -> Node:
	for node in nodes.values():
		if node.node_owner == owner and node.node_type == GameNode.NodeType.MAIN_CASTLE:
			return node
	return null


func get_nearest_node(pos: Vector2) -> Node:
	var nearest_id = _nearest_node_id(pos)
	if nearest_id != "" and nodes.has(nearest_id):
		return nodes[nearest_id]
	return null


func get_nearest_road_point(pos: Vector2) -> Vector2:
	var projection = get_nearest_road_projection(pos)
	if not projection.is_empty():
		return projection["point"]
	var nearest = get_nearest_node(pos)
	return nearest.global_position if nearest else pos


func get_nearest_road_projection(pos: Vector2) -> Dictionary:
	if road_segments.is_empty():
		var nearest = get_nearest_node(pos)
		if nearest:
			return {
				"point": nearest.global_position,
				"distance": pos.distance_to(nearest.global_position),
				"a_id": nearest.node_id,
				"b_id": nearest.node_id,
				"a_pos": nearest.global_position,
				"b_pos": nearest.global_position,
				"t": 0.0,
			}
		return {}

	var best_point := pos
	var best_distance := INF
	var best_segment: Dictionary = {}
	for seg in road_segments:
		var point = _closest_point_on_segment(pos, seg["a_pos"], seg["b_pos"])
		var distance = pos.distance_to(point)
		if distance < best_distance:
			best_distance = distance
			best_point = point
			best_segment = seg

	if best_segment.is_empty():
		return {}

	var segment_vector: Vector2 = best_segment["b_pos"] - best_segment["a_pos"]
	var t := 0.0
	if segment_vector.length_squared() > 0.001:
		t = clamp((best_point - best_segment["a_pos"]).dot(segment_vector) / segment_vector.length_squared(), 0.0, 1.0)
	return {
		"point": best_point,
		"distance": best_distance,
		"a_id": best_segment["a_id"],
		"b_id": best_segment["b_id"],
		"a_pos": best_segment["a_pos"],
		"b_pos": best_segment["b_pos"],
		"t": t,
	}


func end_game(winner: Owner):
	game_ended = true
	game_started = false
	EventBus.game_over.emit(winner)


func build_road_graph(roads_data: Array):
	road_graph.clear()
	road_segments.clear()
	for pair in roads_data:
		var a = pair[0]
		var b = pair[1]
		if not road_graph.has(a):
			road_graph[a] = []
		if not road_graph.has(b):
			road_graph[b] = []
		if b not in road_graph[a]:
			road_graph[a].append(b)
		if a not in road_graph[b]:
			road_graph[b].append(a)


func build_road_segments():
	road_segments.clear()
	for nid_a in road_graph:
		if not nodes.has(nid_a):
			continue
		for nid_b in road_graph[nid_a]:
			if not nodes.has(nid_b):
				continue
			if nid_a < nid_b:
				road_segments.append({
					"a_id": nid_a,
					"b_id": nid_b,
					"a_pos": nodes[nid_a].global_position,
					"b_pos": nodes[nid_b].global_position,
				})


func find_road_path(from_pos: Vector2, to_pos: Vector2) -> Array:
	var start_proj = get_nearest_road_projection(from_pos)
	var end_proj = get_nearest_road_projection(to_pos)
	if start_proj.is_empty() or end_proj.is_empty():
		return [to_pos]

	if start_proj["a_id"] == end_proj["a_id"] and start_proj["b_id"] == end_proj["b_id"]:
		return [start_proj["point"], end_proj["point"]]

	var start_options = [
		{"id": start_proj["a_id"], "cost": start_proj["point"].distance_to(start_proj["a_pos"])},
		{"id": start_proj["b_id"], "cost": start_proj["point"].distance_to(start_proj["b_pos"])},
	]
	var end_options = [
		{"id": end_proj["a_id"], "cost": end_proj["point"].distance_to(end_proj["a_pos"])},
		{"id": end_proj["b_id"], "cost": end_proj["point"].distance_to(end_proj["b_pos"])},
	]

	var best_total := INF
	var best_path_ids: Array = []
	for start_option in start_options:
		for end_option in end_options:
			var result = _find_node_path(str(start_option["id"]), str(end_option["id"]))
			if result.is_empty():
				continue
			var total_cost = float(start_option["cost"]) + float(result["distance"]) + float(end_option["cost"])
			if total_cost < best_total:
				best_total = total_cost
				best_path_ids = result["path"]

	if best_path_ids.is_empty():
		return [start_proj["point"], end_proj["point"]]

	var path: Array = [start_proj["point"]]
	for nid in best_path_ids:
		if nodes.has(nid):
			var node_pos: Vector2 = nodes[nid].global_position
			if path[-1].distance_to(node_pos) > 2.0:
				path.append(node_pos)
	if path[-1].distance_to(end_proj["point"]) > 2.0:
		path.append(end_proj["point"])
	return path


func is_near_road(pos: Vector2, threshold: float = 25.0) -> bool:
	for seg in road_segments:
		var closest = _closest_point_on_segment(pos, seg["a_pos"], seg["b_pos"])
		if pos.distance_to(closest) < threshold:
			return true
	return false


func get_spawn_road_point(node_id: String, fallback_pos: Vector2, distance_along_road: float = 52.0) -> Vector2:
	if not nodes.has(node_id):
		return get_nearest_road_point(fallback_pos)
	var node_pos: Vector2 = nodes[node_id].global_position
	var neighbors: Array = road_graph.get(node_id, [])
	if neighbors.is_empty():
		return get_nearest_road_point(node_pos)
	var neighbor_id = str(neighbors[0])
	if not nodes.has(neighbor_id):
		return get_nearest_road_point(node_pos)
	return node_pos.move_toward(nodes[neighbor_id].global_position, distance_along_road)


func _nearest_node_id(pos: Vector2) -> String:
	var best := ""
	var best_distance := INF
	for nid in nodes:
		var distance = nodes[nid].global_position.distance_to(pos)
		if distance < best_distance:
			best_distance = distance
			best = nid
	return best


func _closest_point_on_segment(point: Vector2, a: Vector2, b: Vector2) -> Vector2:
	var ab = b - a
	var t = clamp((point - a).dot(ab) / max(ab.length_squared(), 0.0001), 0.0, 1.0)
	return a + ab * t


func _find_node_path(start_nid: String, end_nid: String) -> Dictionary:
	if start_nid == end_nid:
		return {"path": [start_nid], "distance": 0.0}
	if not road_graph.has(start_nid) or not road_graph.has(end_nid):
		return {}

	var open: Array = [start_nid]
	var came_from: Dictionary = {}
	var costs: Dictionary = {start_nid: 0.0}

	while not open.is_empty():
		var current := ""
		var current_index := 0
		var current_cost := INF
		for i in range(open.size()):
			var candidate: String = str(open[i])
			var candidate_cost = float(costs.get(candidate, INF))
			if candidate_cost < current_cost:
				current = candidate
				current_index = i
				current_cost = candidate_cost
		open.remove_at(current_index)

		if current == end_nid:
			break

		for raw_neighbor in road_graph.get(current, []):
			var neighbor := str(raw_neighbor)
			if not nodes.has(current) or not nodes.has(neighbor):
				continue
			var new_cost = current_cost + nodes[current].global_position.distance_to(nodes[neighbor].global_position)
			if new_cost < float(costs.get(neighbor, INF)):
				costs[neighbor] = new_cost
				came_from[neighbor] = current
				if neighbor not in open:
					open.append(neighbor)

	if not came_from.has(end_nid):
		return {}

	var path_ids: Array = [end_nid]
	var cursor = end_nid
	while cursor != start_nid:
		cursor = str(came_from[cursor])
		path_ids.push_front(cursor)
	return {
		"path": path_ids,
		"distance": float(costs.get(end_nid, INF)),
	}
