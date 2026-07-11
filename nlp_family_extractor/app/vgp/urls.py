from __future__ import annotations

BASE = "https://vietnamgiapha.com"


def giapha_url(tree_id: int) -> str:
    return f"{BASE}/XemGiaPha/{tree_id}/giapha.html"


def pha_ky_url(tree_id: int) -> str:
    return f"{BASE}/XemPhaKy/{tree_id}/pha_ky_gia_su.html"


def pha_he_url(tree_id: int) -> str:
    return f"{BASE}/XemPhaHe/{tree_id}/pha_he.html"


def pha_he_legacy_url(tree_id: int) -> str:
    return f"{BASE}/XemPhaHe/{tree_id}/cay_pha_he.html"


def hinh_anh_url(tree_id: int) -> str:
    return f"{BASE}/XemHinhAnh/{tree_id}/hinh_anh.html"


def store_id(tree_id: int) -> str:
    return f"vgp-{tree_id}"
