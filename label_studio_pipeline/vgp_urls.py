"""URL templates for vietnamgiapha.com."""

from __future__ import annotations

VGP_BASE = "https://vietnamgiapha.com"


def giapha_url(tree_id: int) -> str:
    return f"{VGP_BASE}/XemGiaPha/{tree_id}/giapha.html"


def pha_ky_url(tree_id: int) -> str:
    return f"{VGP_BASE}/XemPhaKy/{tree_id}/pha_ky_gia_su.html"


def pha_he_url(tree_id: int) -> str:
    return f"{VGP_BASE}/XemPhaHe/{tree_id}/pha_he.html"


def pha_he_legacy_url(tree_id: int) -> str:
    return f"{VGP_BASE}/XemPhaHe/{tree_id}/cay_pha_he.html"
