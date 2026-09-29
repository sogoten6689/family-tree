"""Đường dẫn dùng chung sau khi gộp code vào family-tree (2026-09-29).

Trước khi gộp, code này ở repo riêng `hannom-bilingual-dataset` (sibling của
`family-tree` trên đĩa), và mọi script tự tính `FAMILY_TREE` bằng đường dẫn
tuyệt đối hardcode theo máy 1 người (`/Users/forestlam/...`). Từ 2026-09-29,
code đã dọn vào `family-tree/research/hannom-bilingual-dataset/` — theo yêu
cầu người dùng, chỉ dọn CODE, còn `data/` và `runs/` (nặng, ~82MB) VẪN Ở LẠI
repo `hannom-bilingual-dataset` cũ (từ giờ chỉ còn giữ vai trò kho dữ liệu).

Module này tính 2 đường dẫn gốc 1 LẦN duy nhất (mọi script khác import lại,
không tự tính `parents[N]` riêng — tránh sai số tầng thư mục rải rác nhiều
file):

  FAMILY_TREE_ROOT — root của repo family-tree (chính code này đang nằm
      trong đó: scripts/ -> hannom-bilingual-dataset/ -> research/ ->
      family-tree/, đúng 3 cấp lên từ file này).

  DATA_REPO_ROOT — root của repo dữ liệu (mặc định: thư mục sibling
      `hannom-bilingual-dataset` cạnh `family-tree`, đúng vị trí repo cũ vẫn
      đang nằm sau khi dọn code — override bằng biến môi trường
      `HANNOM_DATA_ROOT` nếu bạn clone repo dữ liệu ở chỗ khác).
"""
from __future__ import annotations

import os
from pathlib import Path

_THIS_FILE = Path(__file__).resolve()

# scripts/_repo_paths.py -> parents[0]=scripts, [1]=hannom-bilingual-dataset,
# [2]=research, [3]=family-tree
FAMILY_TREE_ROOT: Path = _THIS_FILE.parents[3]

DATA_REPO_ROOT: Path = Path(
    os.environ.get("HANNOM_DATA_ROOT", str(FAMILY_TREE_ROOT.parent / "hannom-bilingual-dataset"))
)

# Alias giữ tương thích tên biến cũ (`FAMILY_TREE`) mà nhiều script đã dùng —
# ý nghĩa KHÔNG đổi: vẫn là root của repo family-tree, chỉ đổi cách tính từ
# hardcode máy 1 người sang tính tương đối theo vị trí file thật.
FAMILY_TREE: Path = FAMILY_TREE_ROOT
