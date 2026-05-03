extends Node

# ---- Economy ----
signal gold_changed(owner: int, new_amount: int)
signal income_tick()

# ---- Nodes ----
signal node_damaged(node_id: String, hp: int, max_hp: int)
signal node_captured(node_id: String, new_owner: int, old_owner: int)

# ---- Units ----
signal unit_died(unit: Node)
signal unit_spawned(unit: Node)

# ---- Game ----
signal game_over(winner: int)
