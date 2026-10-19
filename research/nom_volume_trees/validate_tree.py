"""Kiểm tra tree.json theo docs/schemas/balkan-node.schema.json và app.balkan_node của backend.

Chạy từ nlp_family_extractor/ (để import được app.*):
  PYTHONPATH=. .venv/Scripts/python ../research/nom_volume_trees/validate_tree.py <tree.json> ../docs/schemas/balkan-node.schema.json [thư mục chứa jsonschema]
"""
import json, sys
if len(sys.argv) > 3:
    sys.path.insert(0, sys.argv[3])
sys.path.insert(0, ".")
import jsonschema
from app.balkan_node import strip_nodes_and_collect_meta

tree = json.load(open(sys.argv[1], encoding="utf-8"))
schema = json.load(open(sys.argv[2], encoding="utf-8"))
for n in tree:
    jsonschema.validate(n, schema)
norm, _ = strip_nodes_and_collect_meta(tree)
assert norm == tree, "backend chuẩn hoá làm thay đổi node"
print(f"OK: {len(tree)} node hợp lệ theo balkan-node.schema.json và app.balkan_node")
