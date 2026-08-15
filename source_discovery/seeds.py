"""Seed sources for Firecrawl discovery — see planning/firecrawl_genealogy_source_discovery_plan.md."""

from __future__ import annotations

SEED_SOURCES: list[dict] = [
    {
        "source_id": "nomfoundation_c2",
        "track": "hannom",
        "name": "Nom Foundation — Collection 2 (Gia phả)",
        "base_url": "https://lib.nomfoundation.org/collection/2/",
        "map_search": "tộc phả",
        "status": "active_collector",
    },
    {
        "source_id": "nlv",
        "track": "hannom",
        "name": "Thư viện Quốc gia Việt Nam",
        "base_url": "https://nlv.gov.vn/",
        "map_search": "gia phả",
        "status": "seed",
    },
    {
        "source_id": "vietnamgiapha",
        "track": "quoc_ngu",
        "name": "VietnamGiaPha.com",
        "base_url": "https://vietnamgiapha.com/",
        "map_search": "pha_ky",
        "status": "active_collector",
    },
    {
        "source_id": "giaphavietnam",
        "track": "quoc_ngu",
        "name": "Gia phả Việt Nam",
        "base_url": "http://www.giaphavietnam.vn/",
        "map_search": "gia phả",
        "status": "seed",
    },
    {
        "source_id": "giaphadaiviet",
        "track": "quoc_ngu",
        "name": "Gia Phả Đại Việt Online",
        "base_url": "https://giaphadaiviet.vn/",
        "map_search": "phả",
        "status": "seed",
    },
    {
        "source_id": "giaphaonline",
        "track": "quoc_ngu",
        "name": "Gia Phả Online",
        "base_url": "https://giaphaonline.net/",
        "map_search": "gia phả",
        "status": "seed",
    },
]

HANNOM_URL_KEYWORDS = ("volume", "collection", "gia-pha", "toc-pha", "tộc-phả", ".jpg", ".pdf", "nom")
QUOC_NGU_URL_KEYWORDS = ("pha_ky", "pha-ky", "pha_he", "pha-he", "giapha", "genealogy", "xemgiapha", "xemphaky", "xemphehe")
